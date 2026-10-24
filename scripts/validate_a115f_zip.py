#!/usr/bin/env python3
"""Static safety checks for the experimental SM-A115F flashable ROM ZIP."""

from __future__ import annotations

import argparse
import ast
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "out/ZineROM_OneUI7_A115F-Port-A057F.zip"
CONFIG = ROOT / "target/a115f/config.sh"


class ValidationError(Exception):
    pass


def load_target_config(path: Path) -> dict[str, object]:
    """Read simple TARGET_* assignments without evaluating shell code."""
    result: dict[str, object] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.match(r"^\s*(TARGET_[A-Z0-9_]+)\s*=\s*(.*?)\s*$", line)
        if not match:
            continue
        key, raw = match.groups()
        if raw.startswith(('"', "'")):
            try:
                value = ast.literal_eval(raw)
            except (SyntaxError, ValueError) as exc:
                raise ValidationError(f"Invalid quoted value for {key} at {path}:{line_no}") from exc
        elif raw.lower() in {"true", "false"}:
            value = raw.lower() == "true"
        elif re.fullmatch(r"[0-9]+", raw):
            value = int(raw)
        else:
            value = raw
        result[key] = value
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate(zip_path: Path, config: dict[str, object]) -> list[str]:
    require(zip_path.is_file() and zip_path.stat().st_size > 0, f"ZIP not found or empty: {zip_path}")

    codename = str(config.get("TARGET_CODENAME", ""))
    model_value = str(config.get("TARGET_ASSERT_MODEL", ""))
    models = [model for model in model_value.split(":") if model]
    group_size = config.get("TARGET_SUPER_GROUP_SIZE")
    super_size = config.get("TARGET_SUPER_PARTITION_SIZE")
    group_name = str(config.get("TARGET_SUPER_GROUP_NAME", ""))
    has_system_ext = config.get("TARGET_HAS_SYSTEM_EXT")
    require(codename == "a115f", f"Unexpected target codename in config: {codename!r}")
    require("SM-A115F" in models, f"SM-A115F is not asserted by target config: {models!r}")
    require(isinstance(group_size, int) and group_size > 0, "TARGET_SUPER_GROUP_SIZE is missing or invalid")
    require(isinstance(super_size, int) and super_size > 0, "TARGET_SUPER_PARTITION_SIZE is missing or invalid")
    require(group_size <= super_size, "TARGET_SUPER_GROUP_SIZE exceeds TARGET_SUPER_PARTITION_SIZE")
    require(bool(group_name), "TARGET_SUPER_GROUP_NAME is missing")
    require(isinstance(has_system_ext, bool), "TARGET_HAS_SYSTEM_EXT must be a literal true/false")

    try:
        archive = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValidationError(f"Cannot open ROM ZIP: {exc}") from exc

    with archive:
        bad_member = archive.testzip()
        require(bad_member is None, f"ZIP CRC failure in member: {bad_member}")
        member_names = archive.namelist()
        names = set(member_names)
        require(len(names) == len(member_names), "ZIP contains duplicate member names")

        required = {
            "META-INF/com/google/android/update-binary",
            "META-INF/com/google/android/updater-script",
            "META-INF/com/android/metadata",
            "dynamic_partitions_op_list",
            "build_info.txt",
            "unsparse_super_empty.img",
            "target_os_partitions_metadata.txt",
            "boot.img",
            "dtbo.img",
            "system.new.dat.br",
            "system.transfer.list",
            "vendor.new.dat.br",
            "vendor.transfer.list",
            "product.new.dat.br",
            "product.transfer.list",
        }
        missing = sorted(required - names)
        require(not missing, "Missing required ZIP members: " + ", ".join(missing))
        empty = sorted(name for name in required if archive.getinfo(name).file_size <= 0)
        require(not empty, "Required ZIP members are empty: " + ", ".join(empty))

        if not has_system_ext:
            separate_system_ext = sorted(
                name for name in names if name == "system_ext.img" or name.startswith("system_ext.")
            )
            require(
                not separate_system_ext,
                "Target declares merged system_ext, but ZIP contains separate system_ext files: "
                + ", ".join(separate_system_ext),
            )

        updater = archive.read("META-INF/com/google/android/updater-script").decode("utf-8", errors="replace")
        require(
            re.search(r'getprop\("ro\.boot\.em\.model"\)\s*==\s*"SM-A115F"', updater) is not None,
            "Updater does not assert exact model SM-A115F via ro.boot.em.model",
        )
        for token in (
            "update_dynamic_partitions",
            'map_partition("system")',
            'map_partition("vendor")',
            'map_partition("product")',
        ):
            require(token in updater, f"Updater is missing required operation: {token}")
        forbidden_patterns = (
            r"\bformat\s*\(",
            r"delete_recursive\s*\(\s*['\"]/?data(?:/|['\"])",
            r"package_extract_file\s*\(\s*['\"]userdata\.img['\"]",
        )
        for pattern in forbidden_patterns:
            require(re.search(pattern, updater) is None, f"Unexpected destructive/data-format operation: {pattern}")

        metadata = archive.read("META-INF/com/android/metadata").decode("utf-8", errors="replace")
        require(
            re.search(rf"(?m)^pre-device={re.escape(codename)}$", metadata) is not None,
            f"OTA metadata does not target {codename}",
        )

        build_info = archive.read("build_info.txt").decode("utf-8", errors="replace")
        require(
            re.search(rf"(?m)^device={re.escape(codename)}$", build_info) is not None,
            f"build_info.txt does not identify {codename}",
        )

        target_layout_text = archive.read("target_os_partitions_metadata.txt").decode("utf-8", errors="replace")
        target_layout: dict[str, str] = {}
        for line_no, line in enumerate(target_layout_text.splitlines(), 1):
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            require(key not in target_layout, f"Duplicate target layout key at line {line_no}: {key}")
            target_layout[key] = value.strip()
        require(
            target_layout.get("super_partition_group") == group_name,
            "Target firmware super group does not match target config",
        )
        target_group_size = target_layout.get(f"super_{group_name}_group_size", "")
        require(
            target_group_size.isdigit() and int(target_group_size) == group_size,
            "Target firmware super group size does not match target config",
        )
        target_super_size = target_layout.get("super_partition_size", "")
        require(
            target_super_size.isdigit() and int(target_super_size) == super_size,
            "Target physical super size does not match target config",
        )
        target_partition_list = set(
            target_layout.get(f"super_{group_name}_partition_list", "").split()
        )
        require(
            {"system", "vendor"}.issubset(target_partition_list),
            "Target firmware partition list is missing system or vendor",
        )

        op_list = archive.read("dynamic_partitions_op_list").decode("utf-8", errors="replace")
        operation_lines = [line.split() for line in op_list.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        remove_all_groups_positions = [
            index for index, fields in enumerate(operation_lines) if fields == ["remove_all_groups"]
        ]
        require(
            remove_all_groups_positions == [0],
            "Dynamic-partition op list must contain exactly one remove_all_groups operation at the beginning",
        )

        groups: list[tuple[str, int]] = []
        adds: dict[str, str] = {}
        resized: dict[str, int] = {}
        for fields in operation_lines:
            if len(fields) == 3 and fields[0] == "add_group":
                try:
                    size = int(fields[2])
                except ValueError as exc:
                    raise ValidationError(f"Invalid add_group size: {' '.join(fields)}") from exc
                require(size > 0, f"Non-positive dynamic group size: {' '.join(fields)}")
                groups.append((fields[1], size))
            elif len(fields) == 3 and fields[0] == "add":
                require(fields[1] not in adds, f"Duplicate dynamic partition add: {fields[1]}")
                adds[fields[1]] = fields[2]
            elif len(fields) == 3 and fields[0] == "resize":
                try:
                    size = int(fields[2])
                except ValueError as exc:
                    raise ValidationError(f"Invalid resize size: {' '.join(fields)}") from exc
                require(size > 0, f"Non-positive dynamic partition size: {' '.join(fields)}")
                require(fields[1] not in resized, f"Duplicate dynamic partition resize: {fields[1]}")
                resized[fields[1]] = size
            else:
                require(fields == ["remove_all_groups"], f"Unrecognized dynamic partition operation: {' '.join(fields)}")

        require(groups == [(group_name, group_size)],
                f"Expected only group {group_name} sized {group_size}; found {groups!r}")
        used_size = sum(resized.values())
        require(used_size <= group_size,
                f"Dynamic images need {used_size} bytes, exceeding group capacity {group_size}")

        payloads = {
            name.removesuffix(".new.dat.br")
            for name in names
            if re.fullmatch(r"[a-z0-9_]+\.new\.dat\.br", name)
        }
        transfer_lists = {
            name.removesuffix(".transfer.list")
            for name in names
            if re.fullmatch(r"[a-z0-9_]+\.transfer\.list", name)
        }
        require(payloads == transfer_lists,
                f"Compressed payloads and transfer lists differ: payloads={sorted(payloads)}, lists={sorted(transfer_lists)}")
        require({"system", "vendor", "product"}.issubset(payloads),
                "ZIP is missing a system, vendor, or product payload")
        updater_writes = re.findall(
            r'block_image_update\s*\(\s*map_partition\(\s*"([^"]+)"\s*\)', updater
        )
        require(
            len(updater_writes) == len(set(updater_writes)),
            "Updater writes one or more dynamic partitions more than once",
        )
        require(
            set(updater_writes) == payloads,
            "Updater block_image_update calls do not match dynamic payload partitions: "
            f"writes={sorted(updater_writes)}, payloads={sorted(payloads)}",
        )
        target_side_partitions = target_partition_list - {"system", "product"}
        if not has_system_ext:
            target_side_partitions.discard("system_ext")
        require(
            target_side_partitions.issubset(payloads),
            "ZIP is missing target-side dynamic partition payload(s): "
            + ", ".join(sorted(target_side_partitions - payloads)),
        )
        require(set(adds) == payloads,
                f"Dynamic add operations do not match payload partitions: adds={sorted(adds)}, payloads={sorted(payloads)}")
        require(set(resized) == payloads,
                f"Dynamic resize operations do not match payload partitions: resized={sorted(resized)}, payloads={sorted(payloads)}")
        require(all(group == group_name for group in adds.values()),
                f"One or more dynamic partitions reference the wrong group (expected {group_name})")
        require(has_system_ext or "system_ext" not in payloads,
                "Dynamic op list creates system_ext although target has no separate partition")

        return [
            f"ZIP CRC and members: PASS ({len(names)} unique members)",
            f"Target assertions/metadata: PASS ({codename}, {', '.join(models)})",
            f"Payload/transfer-list coverage: PASS ({', '.join(sorted(payloads))})",
            "Target firmware partition preservation: PASS ("
            + ", ".join(sorted(target_side_partitions))
            + ")",
            f"Dynamic group: PASS ({group_name}, {used_size}/{group_size} bytes; super={super_size})",
            "Updater safety: PASS (exact model guard; no detected data-format operation)",
        ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", nargs="?", type=Path, default=DEFAULT_ZIP, help="flashable ROM ZIP")
    parser.add_argument("--config", type=Path, default=CONFIG, help="A115F target config")
    args = parser.parse_args()

    try:
        config = load_target_config(args.config)
        messages = validate(args.zip, config)
    except (OSError, ValidationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    for message in messages:
        print(f"PASS: {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
