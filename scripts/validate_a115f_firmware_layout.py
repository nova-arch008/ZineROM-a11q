#!/usr/bin/env python3
"""Validate the extracted stock SM-A115F vendor-side firmware layout."""

from __future__ import annotations

import argparse
import ast
import re
import stat
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "target/a115f/config.sh"
DONOR_REPLACED_PARTITIONS = {"system", "product", "system_ext"}


class ValidationError(Exception):
    pass


def load_config(path: Path) -> dict[str, object]:
    result: dict[str, object] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.match(r"^\s*(TARGET_[A-Z0-9_]+)\s*=\s*(.*?)\s*$", line)
        if not match:
            continue
        key, raw = match.groups()
        if raw.startswith(("'", '"')):
            try:
                value = ast.literal_eval(raw)
            except (SyntaxError, ValueError) as exc:
                raise ValidationError(f"Invalid value for {key} at {path}:{line_no}") from exc
        elif raw.lower() in {"true", "false"}:
            value = raw.lower() == "true"
        elif re.fullmatch(r"[0-9]+", raw):
            value = int(raw)
        else:
            value = raw
        result[key] = value
    return result


def read_metadata(path: Path) -> dict[str, str]:
    require(path.is_file() and path.stat().st_size > 0, f"Missing target super metadata: {path}")
    values: dict[str, str] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in values:
            raise ValidationError(f"Duplicate metadata key {key!r} at {path}:{line_no}")
        values[key] = value.strip()
    return values


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate(
    firmware_dir: Path,
    config: dict[str, object],
    expected_version: str | None = None,
) -> list[str]:
    require(firmware_dir.is_dir(), f"Target firmware directory not found: {firmware_dir}")
    require(config.get("TARGET_CODENAME") == "a115f", "Config must target codename a115f")
    require(firmware_dir.name.startswith("SM-A115F_"),
            f"Firmware directory is not an SM-A115F target: {firmware_dir.name}")

    extracted = firmware_dir / ".extracted"
    require(extracted.is_file() and extracted.stat().st_size > 0, "Target .extracted marker is missing")
    extracted_version = extracted.read_text(encoding="utf-8").strip()
    configured_version = config.get("TARGET_FIRMWARE_VERSION")
    require(isinstance(configured_version, str) and bool(configured_version),
            "TARGET_FIRMWARE_VERSION is missing or invalid")
    version_components = configured_version.split("/")
    require(len(version_components) == 4 and all(version_components),
            "TARGET_FIRMWARE_VERSION must contain AP/CSC/CP/BL components")
    if expected_version is not None:
        require(
            expected_version == configured_version,
            f"Expected firmware version {expected_version!r} does not match target config {configured_version!r}",
        )
    require(
        extracted_version == configured_version,
        f"Target extraction version mismatch: expected {configured_version!r}, found {extracted_version!r}",
    )

    metadata = read_metadata(firmware_dir / "os_partitions_metadata.txt")
    group_name = str(config.get("TARGET_SUPER_GROUP_NAME", ""))
    group_size = config.get("TARGET_SUPER_GROUP_SIZE")
    super_size = config.get("TARGET_SUPER_PARTITION_SIZE")
    require(bool(group_name), "TARGET_SUPER_GROUP_NAME is missing")
    require(isinstance(group_size, int) and group_size > 0, "TARGET_SUPER_GROUP_SIZE is missing or invalid")
    require(isinstance(super_size, int) and super_size > 0,
            "TARGET_SUPER_PARTITION_SIZE is missing or invalid")
    require(group_size <= super_size, "TARGET_SUPER_GROUP_SIZE exceeds TARGET_SUPER_PARTITION_SIZE")
    metadata_super_size = metadata.get("super_partition_size", "")
    require(metadata_super_size.isdigit(), "Target super metadata has no valid physical super_partition_size")
    require(
        int(metadata_super_size) == super_size,
        f"Target physical super size mismatch: config={super_size}, firmware={metadata_super_size}",
    )
    require(
        metadata.get("super_partition_group") == group_name,
        "Target super group mismatch: "
        f"config={group_name!r}, firmware={metadata.get('super_partition_group')!r}",
    )
    metadata_group_size = metadata.get(f"super_{group_name}_group_size")
    require(
        metadata_group_size is not None and metadata_group_size.isdigit(),
        f"Target super metadata has no valid size for group {group_name}",
    )
    require(
        int(metadata_group_size) == group_size,
        f"Target super group size mismatch: config={group_size}, firmware={metadata_group_size}",
    )

    raw_partitions = metadata.get(f"super_{group_name}_partition_list", "")
    partitions = set(raw_partitions.split())
    require(partitions, "Target super partition list is empty or missing")
    require("system" in partitions and "vendor" in partitions, "Target super list must include system and vendor")

    # system/product/system_ext are supplied by the donor or merged by the port.
    # Every other logical partition is hardware-specific and must be extracted
    # from the exact A115F firmware rather than silently dropped by remove_all_groups.
    hardware_partitions = partitions - DONOR_REPLACED_PARTITIONS
    for partition in sorted(hardware_partitions):
        tree = firmware_dir / partition
        require(tree.is_dir(), f"Target super lists {partition}, but its extracted tree is missing")
        require(
            any(item.is_file() for item in tree.rglob("*")),
            f"Target partition tree is empty: {partition}",
        )
        for metadata_name in (f"fs_config-{partition}", f"file_context-{partition}"):
            metadata_file = firmware_dir / metadata_name
            require(metadata_file.is_file() and metadata_file.stat().st_size > 0,
                    f"Missing extraction metadata for target partition {partition}: {metadata_name}")

    kernel_dir = firmware_dir / "kernel"
    for image in ("boot.img", "dtbo.img"):
        path = kernel_dir / image
        require(path.is_file() and path.stat().st_size > 0, f"Target kernel image is missing: kernel/{image}")

    manifest_paths = [
        firmware_dir / "vendor/manifest.xml",
        firmware_dir / "vendor/etc/vintf/manifest.xml",
        firmware_dir / "odm/manifest.xml",
        firmware_dir / "odm/etc/vintf/manifest.xml",
    ]
    for root in (firmware_dir / "vendor/etc/vintf/manifest", firmware_dir / "odm/etc/vintf/manifest"):
        if root.is_dir():
            manifest_paths.extend(sorted(root.glob("*.xml")))
    manifests = [path for path in manifest_paths if path.is_file() and path.stat().st_size > 0]
    require(manifests, "No target VINTF device manifest or manifest fragments found under vendor/odm")
    manifest_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in manifests)
    security_hal_tokens = []
    if re.search(r"android\.hardware\.keymaster", manifest_text, re.IGNORECASE):
        security_hal_tokens.append("keymaster")
    if re.search(r"android\.hardware\.(?:security\.)?keymint", manifest_text, re.IGNORECASE):
        security_hal_tokens.append("keymint")
    require(security_hal_tokens,
            "Target VINTF manifest does not declare a Keymaster/KeyMint HAL; FBE compatibility is unverified")

    init_files: list[Path] = []
    for root in (firmware_dir / "vendor/etc/init", firmware_dir / "odm/etc/init"):
        if root.is_dir():
            init_files.extend(sorted(root.rglob("*.rc")))
    init_contents = [path.read_text(encoding="utf-8", errors="replace") for path in init_files]

    def require_service_executable(token: str) -> None:
        declared_paths: list[str] = []
        for content in init_contents:
            for line in content.splitlines():
                match = re.match(r"^\s*service\s+\S+\s+(/(?:vendor|odm)/\S+)", line)
                if match and token in match.group(1).lower():
                    declared_paths.append(match.group(1).rstrip(","))
        require(declared_paths, f"Target init configuration has no {token} service executable")
        for service_path in declared_paths:
            if service_path.startswith("/vendor/"):
                root = firmware_dir / "vendor"
                relative = service_path.removeprefix("/vendor/")
            else:
                root = firmware_dir / "odm"
                relative = service_path.removeprefix("/odm/")
            executable = root / relative
            require(
                executable.is_file() and (executable.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)) != 0,
                f"Target init declares {service_path}, but its executable is missing or not executable",
            )

    for token in security_hal_tokens:
        require_service_executable(token)

    fstab_files: list[Path] = []
    for root in (firmware_dir / "vendor/etc", firmware_dir / "odm/etc"):
        if root.is_dir():
            fstab_files.extend(path for path in root.rglob("fstab*") if path.is_file())
    data_rows: list[list[str]] = []
    fstab_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace") for path in fstab_files
    )
    for line in fstab_text.splitlines():
        fields = line.split()
        if len(fields) >= 4 and fields[1] == "/data":
            data_rows.append(fields)
    require(data_rows, "Target vendor/odm fstab has no /data mount entry")
    fbe_rows = [row for row in data_rows if any("fileencryption=" in item for item in row[3:])]
    require(fbe_rows, "Target /data fstab has no fileencryption flag; FBE support is unverified")

    cryptfshw_checked = False
    if re.search(r"vendor\.qti\.hardware\.cryptfshw", manifest_text, re.IGNORECASE) and re.search(
        r"fileencryption=[^,\s]*\bice\b", fstab_text, re.IGNORECASE
    ):
        require_service_executable("cryptfshw")
        cryptfshw_checked = True

    return [
        f"Target firmware version: PASS ({extracted_version})",
        f"Target super geometry: PASS (physical={super_size}, group={group_name}:{group_size} bytes)",
        "Target vendor-side partitions: PASS (" + ", ".join(sorted(hardware_partitions)) + ")",
        "Target boot/DTBO images: PASS",
        f"Target VINTF security HAL declaration: PASS ({len(manifests)} manifest file(s), Keymaster/KeyMint)",
        "Target FBE stack declarations: PASS (/data fileencryption, " + "/".join(security_hal_tokens)
        + (", cryptfshw service" if cryptfshw_checked else "")
        + ")",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware_dir", type=Path, help="extracted SM-A115F firmware directory")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="A115F target config")
    parser.add_argument("--expected-version", help="exact pinned PDA/CSC/CP/BL version string")
    args = parser.parse_args()
    try:
        messages = validate(args.firmware_dir, load_config(args.config), args.expected_version)
    except (OSError, ValidationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    for message in messages:
        print(f"PASS: {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
