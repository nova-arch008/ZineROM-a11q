#!/usr/bin/env python3
"""Read-only boot-chain, logical-partition, and vendor inventory for A115F firmware."""
from __future__ import annotations

import argparse
import hashlib
import struct
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def elf_inventory(vendor_root: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not vendor_root.exists():
        return counts
    for path in vendor_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            with path.open("rb") as stream:
                header = stream.read(20)
        except OSError:
            counts["unreadable"] += 1
            continue
        if len(header) < 20 or header[:4] != b"\x7fELF":
            continue
        elf_class = {1: "ELF32" , 2: "ELF64"}.get(header[4], f"ELF-class-{header[4]}")
        byte_order = "<" if header[5] == 1 else ">" if header[5] == 2 else None
        machine = struct.unpack_from(f"{byte_order}H", header, 18)[0] if byte_order else 0
        machine_name = {40: "ARM", 183: "AArch64", 3: "x86", 62: "x86_64"}.get(machine, f"machine-{machine}")
        counts[f"{elf_class}/{machine_name}"] += 1
    return counts


def vintf_hal_names(vendor_root: Path) -> list[str]:
    names: set[str] = set()
    vintf = vendor_root / "etc/vintf"
    if not vintf.exists():
        return []
    for path in vintf.rglob("*.xml"):
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError):
            continue
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1] == "name" and node.text:
                names.add(node.text.strip())
    return sorted(names)


def audit(root: Path) -> str:
    if not root.is_dir():
        raise ValueError(f"firmware directory does not exist: {root}")
    report = ["A115F stock firmware boot/vendor/partition audit", f"firmware_root={root}"]

    version_file = root / ".extracted"
    report.append(f"firmware_version={version_file.read_text(errors='replace').strip() if version_file.exists() else 'unknown'}")

    for relative in ("os_partitions_metadata.txt", "super_lpdump.txt"):
        path = root / relative
        report.append(f"\n[{relative}]")
        report.append(path.read_text(errors="replace").strip() if path.exists() else "MISSING")

    report.append("\n[stock target boot-chain images]")
    kernel_dir = root / "kernel"
    images = sorted(kernel_dir.glob("*.img")) if kernel_dir.exists() else []
    if not images:
        report.append("MISSING: no extracted target kernel images")
    for image in images:
        report.append(f"{image.name}: bytes={image.stat().st_size} sha256={sha256(image)}")
        metadata = root / f"{image.name}_metadata.txt"
        if metadata.exists():
            for line in metadata.read_text(errors="replace").splitlines():
                report.append(f"  {line}")
    if not (kernel_dir / "boot.img").is_file():
        report.append("ERROR: target boot.img is missing")

    report.append("\n[partition payload directories in extracted firmware]")
    for name in ("system", "vendor", "product", "odm", "system_ext", "vendor_dlkm", "odm_dlkm", "system_dlkm"):
        path = root / name
        if path.is_dir():
            report.append(f"{name}: present")
        else:
            report.append(f"{name}: absent")

    vendor = root / "vendor"
    report.append("\n[target vendor ELF ABI inventory]")
    counts = elf_inventory(vendor)
    if counts:
        for abi, count in sorted(counts.items()):
            report.append(f"{abi}: {count}")
    else:
        report.append("No ELF binaries found or vendor directory is missing")

    report.append("\n[target VINTF HAL declarations]")
    hal_names = vintf_hal_names(vendor)
    report.extend(hal_names if hal_names else ["No parseable VINTF HAL names found"])

    report.append("\n[target fstab encryption and mount entries]")
    fstab_files = sorted(set(vendor.glob("etc/fstab*")).union(vendor.glob("etc/*fstab*")))
    if not fstab_files:
        report.append("No vendor fstab files found")
    for path in fstab_files:
        report.append(f"{path.relative_to(root)}:")
        for line in path.read_text(errors="replace").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                report.append(f"  {stripped}")

    return "\n".join(report) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware_root", type=Path, help="extracted SM-A115F firmware directory")
    args = parser.parse_args()
    try:
        output = audit(args.firmware_root)
    except (OSError, ValueError) as error:
        print(f"A115F audit failed: {error}", file=sys.stderr)
        return 1
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
