#!/usr/bin/env bash
# Fetch pinned Samsung firmware directly from Samsung FUS with the official-source
# Samloader client, validate the decrypted ZIP and Odin MD5 trailers, then extract
# one device at a time to keep peak disk usage down on GitHub-hosted runners.
set -euo pipefail

: "${SRC_DIR:?Source the repository buildenv.sh before running this script}"
: "${OUT_DIR:?OUT_DIR is not set}"
: "${ODIN_DIR:?ODIN_DIR is not set}"
: "${FW_DIR:?FW_DIR is not set}"
command -v samloader >/dev/null || { echo "samloader executable is required" >&2; exit 1; }

SOURCE_MODEL="SM-A057F"
SOURCE_CSC="TUR"
SOURCE_VERSION="A057FXXUFDZH2/A057FOJMFDZH2/A057FXXUFDZH2/A057FXXUFDZH2"
IFS='/' read -r TARGET_MODEL TARGET_CSC TARGET_AP_VERSION <<< "${TARGET_FIRMWARE:?Target config must pin model/CSC/AP}"
TARGET_VERSION="${TARGET_FIRMWARE_VERSION:?Target config must pin the exact A115F firmware tuple}"
if [[ "$TARGET_MODEL" != "${TARGET_ASSERT_MODEL:?Target config must assert the A115F model}" ]]; then
    echo "Target firmware model $TARGET_MODEL does not match TARGET_ASSERT_MODEL=$TARGET_ASSERT_MODEL" >&2
    exit 1
fi
if [[ ! "$TARGET_CSC" =~ ^[A-Z0-9]{3}$ ]] || [[ "$TARGET_AP_VERSION" != "${TARGET_VERSION%%/*}" ]]; then
    echo "Target firmware model/CSC/AP does not match the pinned target version tuple" >&2
    exit 1
fi

export SAMFW_PINNED_FIRMWARES="${SOURCE_MODEL}/${SOURCE_CSC}=${SOURCE_VERSION}
${TARGET_MODEL}/${TARGET_CSC}=${TARGET_VERSION}"

verify_archive_members() {
    local zip_path="$1" model="$2" version="$3"
    python3 "$SRC_DIR/scripts/validate_samfw_archive.py" zip "$zip_path" "$model" "$version"
}

verify_odin_md5() {
    local dir="$1" fw_file file_name tail_len stored_hash calculated_hash found=0
    while IFS= read -r -d '' fw_file; do
        found=1
        file_name="$(basename "$fw_file")"
        file_name="${file_name%.md5}"
        tail_len="$((32 + 2 + ${#file_name} + 1))"
        stored_hash="$(tail -c "$tail_len" "$fw_file" | cut -d ' ' -f 1 -s)"
        if [[ ! "$stored_hash" =~ ^[[:xdigit:]]{32}$ ]]; then
            echo "Invalid embedded MD5 trailer: $file_name" >&2
            return 1
        fi
        calculated_hash="$(head -c-"$tail_len" "$fw_file" | md5sum | cut -d ' ' -f 1)"
        if [[ "${stored_hash,,}" != "${calculated_hash,,}" ]]; then
            echo "Embedded MD5 mismatch: $file_name" >&2
            return 1
        fi
        echo "Verified embedded MD5: $file_name"
    done < <(find "$dir" -maxdepth 1 -type f -name '*.tar.md5' -print0)
    [[ "$found" -eq 1 ]] || { echo "No Odin tar.md5 payloads found in $dir" >&2; return 1; }
}

required_odin_payloads_present() {
    local dir="$1" model="$2" version="$3"
    python3 "$SRC_DIR/scripts/validate_samfw_archive.py" dir "$dir" "$model" "$version" >/dev/null
}

extracted_outputs_complete() {
    local label="$1" model="$2" csc="$3" part
    local dir="$FW_DIR/${model}_${csc}"
    case "$label" in
        source) set -- system product ;;
        target) set -- vendor ;;
        *) return 1 ;;
    esac
    for part in "$@"; do
        [[ -d "$dir/$part" ]] || return 1
        [[ -n "$(find "$dir/$part" -type f -print -quit 2>/dev/null)" ]] || return 1
        [[ -s "$dir/fs_config-$part" && -s "$dir/file_context-$part" ]] || return 1
    done
    if [[ "$label" == "target" ]]; then
        [[ -s "$dir/kernel/boot.img" && -s "$dir/kernel/dtbo.img" ]] || return 1
    fi
}

check_download_space() {
    local min_gib="${A11_MIN_DOWNLOAD_FREE_GIB:-24}" available_bytes
    [[ "$min_gib" =~ ^[0-9]+$ ]] || { echo "A11_MIN_DOWNLOAD_FREE_GIB must be an integer" >&2; return 1; }
    available_bytes="$(df -PB1 "$OUT_DIR" | awk 'END {print $4}')"
    [[ "$available_bytes" =~ ^[0-9]+$ ]] || { echo "Could not determine free disk space" >&2; return 1; }
    if (( available_bytes < min_gib * 1024 * 1024 * 1024 )); then
        echo "Need at least ${min_gib} GiB free before downloading Samsung firmware; available: $((available_bytes / 1024 / 1024 / 1024)) GiB" >&2
        return 1
    fi
    return 0
}

import_one() {
    local label="$1" model="$2" csc="$3" version="$4"
    local target_dir="$ODIN_DIR/${model}_${csc}"
    local zip_path="$OUT_DIR/tmp/${model}_${csc}_samloader.zip"
    local downloaded_marker="$target_dir/.downloaded"
    local extracted_marker="$FW_DIR/${model}_${csc}/.extracted"
    local reuse_odin=false

    mkdir -p "$OUT_DIR/tmp"
    if [[ -f "$extracted_marker" ]] && [[ "$(cat "$extracted_marker")" == "$version" ]] && \
            extracted_outputs_complete "$label" "$model" "$csc"; then
        echo "Already extracted matching $label firmware: $model/$csc"
        return 0
    fi

    if [[ -f "$downloaded_marker" ]] && [[ "$(cat "$downloaded_marker")" == "$version" ]] && \
            required_odin_payloads_present "$target_dir" "$model" "$version"; then
        if verify_odin_md5 "$target_dir"; then
            echo "Reusing previously verified $label Odin payloads: $model/$csc"
            reuse_odin=true
        else
            echo "Cached $label Odin payloads failed MD5; downloading a clean copy" >&2
        fi
    fi

    if ! $reuse_odin; then
        check_download_space
        rm -rf "$target_dir"
        mkdir -p "$target_dir"
        rm -f "$zip_path" "$zip_path.part"
        echo "Downloading pinned $label firmware from Samsung FUS: $model/$csc"
        samloader download --model "$model" --region "$csc" --version "$version" \
            --threads 8 --out-file "$zip_path"

        verify_archive_members "$zip_path" "$model" "$version"
        unzip -q -o "$zip_path" -d "$target_dir"
        rm -f "$zip_path" "$zip_path.part"
        verify_odin_md5 "$target_dir"
        required_odin_payloads_present "$target_dir" "$model" "$version" || {
            echo "Extracted Odin archive is missing one or more pinned payloads" >&2
            exit 1
        }
        printf '%s' "$version" > "$downloaded_marker.tmp"
        mv -f "$downloaded_marker.tmp" "$downloaded_marker"
    fi
    echo "Imported and verified $label firmware: $model/$csc"
}

# Extract each package immediately after import. extract_fw removes the Odin package
# on GitHub Actions after extracting the needed images, reducing peak disk usage.
import_one "source" "$SOURCE_MODEL" "$SOURCE_CSC" "$SOURCE_VERSION"
EXTRACT_PARTITIONS="system.img product.img system_ext.img" \
EXTRACT_REQUIRED_PARTITIONS="system product" \
"$SRC_DIR/scripts/extract_fw.sh" --ignore-target

import_one "target" "$TARGET_MODEL" "$TARGET_CSC" "$TARGET_VERSION"
EXTRACT_PARTITIONS="odm.img odm_dlkm.img system_dlkm.img vendor.img vendor_dlkm.img" \
EXTRACT_REQUIRED_PARTITIONS="vendor" \
EXTRACT_REQUIRED_KERNEL_IMAGES="boot.img dtbo.img" \
"$SRC_DIR/scripts/extract_fw.sh" --ignore-source

python3 "$SRC_DIR/scripts/validate_a115f_firmware_layout.py" \
    "$FW_DIR/${TARGET_MODEL}_${TARGET_CSC}" \
    --config "$SRC_DIR/target/a115f/config.sh" \
    --expected-version "$TARGET_VERSION"
