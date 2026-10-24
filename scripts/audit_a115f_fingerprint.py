from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


ASCII_RUN = re.compile(rb"[\x20-\x7e]{4,}")
SENSOR_CONFIG_TOKENS = ("side", "rear", "optical", "ultrasonic", "google_touch")


def framework_candidates(jar_path: Path) -> list[str]:
    if not jar_path.is_file():
        raise FileNotFoundError(f"Donor framework jar not found: {jar_path}")
    candidates: set[str] = set()
    with zipfile.ZipFile(jar_path) as archive:
        dex_names = [name for name in archive.namelist() if re.fullmatch(r"classes(?:\d+)?\.dex", name)]
        if not dex_names:
            raise ValueError(f"No classes*.dex entries in {jar_path}")
        for name in dex_names:
            dex = archive.read(name)
            for raw in ASCII_RUN.findall(dex):
                value = raw.decode("ascii", errors="ignore").strip()
                lower = value.lower()
                if "settings=" in lower and any(token in lower for token in SENSOR_CONFIG_TOKENS):
                    candidates.add(value)
    return sorted(candidates)


def vendor_fingerprint_inventory(vendor_root: Path) -> tuple[list[str], list[str], list[str]]:
    manifest_entries: list[str] = []
    init_services: list[str] = []
    binaries: list[str] = []

    manifest_root = vendor_root / "etc/vintf/manifest.xml"
    if manifest_root.is_file():
        root = ET.parse(manifest_root).getroot()
        for hal in root.iter("hal"):
            name = hal.findtext("name", default="").strip()
            if "fingerprint" in name.lower() or "biometric" in name.lower():
                versions = [node.text.strip() for node in hal.findall("version") if node.text]
                instances = [node.text.strip() for node in hal.findall("./interface/instance") if node.text]
                manifest_entries.append(f"{name} versions={','.join(versions) or '-'} instances={','.join(instances) or '-'}")
    else:
        manifest_entries.append("MISSING: vendor/etc/vintf/manifest.xml")

    init_root = vendor_root / "etc/init"
    if init_root.is_dir():
        for path in sorted(init_root.rglob("*.rc")):
            for line in path.read_text(errors="replace").splitlines():
                if "fingerprint" in line.lower() or "biometric" in line.lower():
                    init_services.append(f"{path.relative_to(vendor_root)}: {line.strip()}")

    for base in (vendor_root / "bin", vendor_root / "bin/hw", vendor_root / "lib", vendor_root / "lib64"):
        if base.exists():
            for path in base.rglob("*"):
                if path.is_file() and ("fingerprint" in path.name.lower() or "biometric" in path.name.lower()):
                    binaries.append(str(path.relative_to(vendor_root)))
    return manifest_entries, init_services, sorted(set(binaries))


def system_vndk_inventory(system_root: Path) -> tuple[list[str], list[str]]:
    properties: list[str] = []
    prop_files = sorted(set(system_root.rglob("build.prop")) | set(system_root.rglob("prop.default")))
    for prop_file in prop_files:
        for line in prop_file.read_text(errors="replace").splitlines():
            if re.match(r"^(ro\.vndk\.version|ro\.vndk\.lite|ro\.board\.api_level|ro\.build\.version\.sdk|ro\.product\.first_api_level)=", line):
                properties.append(f"{prop_file.relative_to(system_root)}: {line}")

    apexes: list[str] = []
    apex_paths = sorted(system_root.rglob("com.android.vndk*.apex"))
    for path in apex_paths:
        try:
            with zipfile.ZipFile(path) as archive:
                manifest = archive.read("apex_manifest.pb")
            strings = sorted({value.decode("ascii", errors="ignore") for value in ASCII_RUN.findall(manifest)})
            apex_ids = [value for value in strings if "com.android.vndk" in value]
            apexes.append(f"{path.relative_to(system_root)}: manifest={','.join(apex_ids) or '(id not found)'}")
        except (OSError, KeyError, zipfile.BadZipFile) as exc:
            apexes.append(f"{path.relative_to(system_root)}: unreadable manifest ({exc})")
    if not apexes:
        apexes.append(f"No com.android.vndk*.apex files found under {system_root}")
    return properties, apexes


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit A115F port fingerprint framework and stock vendor HAL.")
    parser.add_argument("--donor-framework", required=True, type=Path)
    parser.add_argument("--target-vendor", required=True, type=Path)
    parser.add_argument("--source-config", required=True, type=Path)
    parser.add_argument("--target-config", required=True, type=Path)
    parser.add_argument("--source-system", required=True, type=Path)
    parser.add_argument("--target-system", required=True, type=Path)
    args = parser.parse_args()

    try:
        candidates = framework_candidates(args.donor_framework)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Donor framework: {args.donor_framework}")
    print("Fingerprint sensor-config strings in donor DEX:")
    if candidates:
        for value in candidates[:100]:
            print(f"  {value}")
        if len(candidates) > 100:
            print(f"  ... {len(candidates) - 100} additional sensor config strings omitted")
    else:
        print("  (no matching strings found)")

    source_text = args.source_config.read_text(errors="replace")
    target_text = args.target_config.read_text(errors="replace")
    for label, text, var in (
        ("source", source_text, "SOURCE_FP_SENSOR_CONFIG"),
        ("target", target_text, "TARGET_FP_SENSOR_CONFIG"),
    ):
        match = re.search(rf"^{var}=\"?([^\"\n]*)\"?\s*$", text, re.MULTILINE)
        print(f"Configured {label} fingerprint: {match.group(1) if match else '(unset)'}")

    manifest, services, binaries = vendor_fingerprint_inventory(args.target_vendor)
    print(f"\nTarget stock vendor: {args.target_vendor}")
    for label, items in (("Fingerprint VINTF", manifest), ("Fingerprint init services", services), ("Fingerprint vendor binaries", binaries)):
        print(f"{label}:")
        if items:
            for item in items:
                print(f"  {item}")
        else:
            print("  (no matching entries found)")
    if not manifest or any(item.startswith("MISSING:") for item in manifest):
        print("WARNING: inspect stock target VINTF manually; no fingerprint HAL entry was confirmed.")

    for label, system_root in (("donor", args.source_system), ("target", args.target_system)):
        properties, apexes = system_vndk_inventory(system_root)
        print(f"\n{label.title()} system: {system_root}")
        print("VNDK/API properties:")
        for item in properties or ["(not found in inspected build.prop files)"]:
            print(f"  {item}")
        print("VNDK APEX manifests:")
        for item in apexes:
            print(f"  {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
