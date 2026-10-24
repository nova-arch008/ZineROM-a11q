# Boot-first target cleanup. The current A11 stock extraction contains an empty
# directory literally named `""` under /vendor/lib with no fs_config or SELinux
# context entry; e2fsdroid cannot label it when assembling vendor.img. Remove only
# this empty directory from the generated work tree, never from extracted firmware.
A11_QUOTED_VENDOR_DIR="$WORK_DIR/vendor/lib/\"\""
if [ -d "$A11_QUOTED_VENDOR_DIR" ] && [ ! -L "$A11_QUOTED_VENDOR_DIR" ] \
    && [ -z "$(find "$A11_QUOTED_VENDOR_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    LOG "Removing empty malformed target artifact /vendor/lib/\"\""
    DELETE_FROM_WORK_DIR "vendor" 'lib/""'
elif [ -e "$A11_QUOTED_VENDOR_DIR" ] || [ -L "$A11_QUOTED_VENDOR_DIR" ]; then
    LOGW "Preserving unexpected or non-empty target path /vendor/lib/\"\""
fi

SYSTEM_EXT_MAPPING="$WORK_DIR/system/system/system_ext/etc/selinux/mapping/31.0.cil"
if [ -f "$SYSTEM_EXT_MAPPING" ]; then
    for A11_POLICY_ATTR in perf_prop_31_0 qb_id_prop_31_0; do
        if grep -Fq "(expandtypeattribute ($A11_POLICY_ATTR) true)" "$SYSTEM_EXT_MAPPING" \
            && grep -Fq "(typeattributeset $A11_POLICY_ATTR (" "$SYSTEM_EXT_MAPPING" \
            && ! grep -Eq "^\(typeattribute[[:space:]]+$A11_POLICY_ATTR\)$" "$SYSTEM_EXT_MAPPING"; then
            sed -i "0,/^(expandtypeattribute /s//(typeattribute $A11_POLICY_ATTR)\\n&/" "$SYSTEM_EXT_MAPPING"
            LOG "Added missing compatibility typeattribute $A11_POLICY_ATTR to system_ext policy mapping"
        fi
    done
fi

ANDROID_INIT_RC="$WORK_DIR/system/system/etc/init/hw/init.rc"
if [ -f "$ANDROID_INIT_RC" ]; then
    python3 - "$ANDROID_INIT_RC" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()

# The A11's 4.9 schedtune driver has a hard limit of five boost groups.
# Drop donor-only audio-app/camera-daemon/nnapi-hal groups and their
# util-clamp groups; those are not required for Android's core boot.
text = "\n".join(
    line for line in text.split("\n")
    if "/dev/stune/audio-app" not in line
)
start = "    # Create a cpu group for NNAPI HAL processes"
end = "    # Create blkio group and apply initial settings."
if start in text and end in text:
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    text = before + "    # A11 kernel lacks donor-only camera/NNAPI cgroups.\n" + end + after
elif start in text or (end in text and "A11 kernel lacks donor-only camera/NNAPI cgroups." not in text):
    raise SystemExit("Unexpected partial donor camera/NNAPI cgroup block")

# Kernel 4.9 on the A11 exposes legacy binder character devices, not binderfs.
# ueventd.rc already assigns permissions for /dev/binder{,hwbinder,vndbinder}.
binder_start = "    # Mount binderfs\n"
binder_end = "    mkdir /mnt/secure 0700 root root"
if binder_start in text and binder_end in text:
    before, rest = text.split(binder_start, 1)
    _, after = rest.split(binder_end, 1)
    text = before + "    # A11 kernel 4.9 uses legacy binder device nodes; binderfs is unsupported.\n\n" + binder_end + after
elif binder_start in text or (binder_end in text and "A11 kernel 4.9 uses legacy binder device nodes; binderfs is unsupported." not in text):
    raise SystemExit("Unexpected partial binderfs block")

path.write_text(text)
print(f"Patched A11 schedtune and legacy binder compatibility in {path}")
PY
fi

# Android 15 linkerconfig reads the vendor's ro.vndk.version. The A11 vendor
# is VNDK 31, while the A05s donor only supplies VNDK 33; without the matching
# v31 APEX linkerconfig aborts with "SANITIZER_DEFAULT_VENDOR is not defined".
TARGET_FW_LABEL="$(cut -d "/" -f 1 <<< "$TARGET_FIRMWARE")_$(cut -d "/" -f 2 <<< "$TARGET_FIRMWARE")"
A11_VNDK31_SOURCE="$FW_DIR/$TARGET_FW_LABEL/system/system/apex/com.android.vndk.current.apex"
A11_VNDK33_DEST="$WORK_DIR/system/system/system_ext/apex/com.android.vndk.v33.apex"
A11_VNDK31_DEST="$WORK_DIR/system/system/system_ext/apex/com.android.vndk.v31.apex"
if [ -f "$A11_VNDK31_SOURCE" ] && unzip -p "$A11_VNDK31_SOURCE" apex_manifest.pb | grep -aFq 'com.android.vndk.v31'; then
    DELETE_FROM_WORK_DIR "system" "system/system_ext/apex/com.android.vndk.v33.apex"
    cp -p "$A11_VNDK31_SOURCE" "$A11_VNDK31_DEST"
    if ! grep -Fq 'system/system_ext/apex/com.android.vndk.v31.apex ' "$WORK_DIR/configs/fs_config-system"; then
        printf '%s\n' 'system/system_ext/apex/com.android.vndk.v31.apex 0 0 644 capabilities=0x0' \
            >> "$WORK_DIR/configs/fs_config-system"
    fi
    if ! grep -Fq '/system/system_ext/apex/com\.android\.vndk\.v31\.apex ' "$WORK_DIR/configs/file_context-system"; then
        printf '%s\n' '/system/system_ext/apex/com\.android\.vndk\.v31\.apex u:object_r:system_file:s0' \
            >> "$WORK_DIR/configs/file_context-system"
    fi
    LOG "Replaced donor VNDK 33 APEX with target-matched A11 VNDK 31 APEX"
elif [ -f "$A11_VNDK31_DEST" ] && unzip -p "$A11_VNDK31_DEST" apex_manifest.pb | grep -aFq 'com.android.vndk.v31'; then
    LOG "Target-matched VNDK 31 APEX is already staged"
else
    LOGE "Target firmware VNDK 31 APEX is missing or has an unexpected manifest"
    return 1
fi

LOG "A115F boot-first compatibility patches applied"
