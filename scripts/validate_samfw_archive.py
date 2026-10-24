#!/usr/bin/env python3
"""Validate Samsung FUS archives and cached Odin payload names."""

from __future__ import annotations

import argparse
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

MAX_MEMBERS = 32
MAX_TOTAL_UNCOMPRESSED = 20 * 1024**3
MAX_MEMBER_UNCOMPRESSED = 12 * 1024**3


class ValidationError(Exception):
    pass


def version_components(version: str) -> tuple[str, str, str, str]:
    parts = version.split("/")
    if len(parts) != 4 or any(not part for part in parts):
        raise ValidationError("firmware version must contain AP/CSC/CP/BL components")
    return parts[0], parts[1], parts[2], parts[3]


def validate_payload_names(names: list[str], model: str, version: str) -> list[str]:
    ap_build, csc_build, cp_build, bl_build = version_components(version)
    model_token = model.removeprefix("SM-")
    if not model_token or any(
        not component.startswith(model_token)
        for component in (ap_build, csc_build, cp_build, bl_build)
    ):
        raise ValidationError(f"firmware version components do not match model {model}")
    tar_names = [name for name in names if name.endswith(".tar.md5")]
    if not tar_names:
        raise ValidationError("no Odin tar.md5 payloads found")

    expected_builds = {"AP": ap_build, "BL": bl_build, "CP": cp_build}
    for prefix, build in expected_builds.items():
        if not any(name.startswith(f"{prefix}_{build}") for name in tar_names):
            raise ValidationError(f"missing expected {prefix} payload for {model} build {build}")

    for prefix in ("CSC_", "HOME_CSC_"):
        if not any(name.startswith(prefix) and csc_build in name for name in tar_names):
            raise ValidationError(f"missing expected {prefix} payload for {model} CSC build {csc_build}")
    return sorted(tar_names)


def validate_payload_directory(directory: Path, model: str, version: str) -> list[str]:
    if not directory.is_dir():
        raise ValidationError(f"cached Odin payload directory is missing: {directory}")
    entries = list(directory.iterdir())
    for item in entries:
        if item.is_symlink():
            raise ValidationError(f"symbolic link not allowed in cached payload directory: {item.name}")
    names = [item.name for item in entries if item.is_file()]
    return validate_payload_names(names, model, version)


def validate_archive(zip_path: Path, model: str, version: str) -> list[str]:
    version_components(version)
    try:
        archive = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValidationError(f"cannot open firmware ZIP: {exc}") from exc

    with archive:
        entries = archive.infolist()
        files = [item for item in entries if not item.is_dir()]
        if not files:
            raise ValidationError("empty firmware archive")
        if len(files) > MAX_MEMBERS:
            raise ValidationError(f"too many archive members: {len(files)}")
        total_size = sum(item.file_size for item in files)
        if total_size > MAX_TOTAL_UNCOMPRESSED or any(
            item.file_size > MAX_MEMBER_UNCOMPRESSED for item in files
        ):
            raise ValidationError(f"archive expands beyond firmware size limits: {total_size} bytes")

        for item in entries:
            name = item.filename
            path_name = name.rstrip("/") if item.is_dir() else name
            path = PurePosixPath(path_name)
            if (
                path.is_absolute()
                or len(path.parts) != 1
                or ".." in path.parts
                or "\\" in name
                or "\0" in name
                or ":" in name
            ):
                raise ValidationError(f"unsafe archive member path: {name!r}")
            mode = (item.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise ValidationError(f"symbolic link not allowed in firmware archive: {name}")

        names = [item.filename for item in files]
        if len(names) != len(set(names)):
            raise ValidationError("duplicate firmware archive member names")
        tar_names = validate_payload_names(names, model, version)
        if any(not (name.endswith(".tar.md5") or name.startswith("_FirmwareInfo_")) for name in names):
            raise ValidationError("unexpected file in firmware archive")
        if any(item.file_size == 0 for item in files if item.filename.endswith(".tar.md5")):
            raise ValidationError("empty Odin tar.md5 payload")
        return tar_names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    zip_parser = subparsers.add_parser("zip", help="validate a decrypted Samsung FUS ZIP")
    zip_parser.add_argument("path", type=Path)
    zip_parser.add_argument("model")
    zip_parser.add_argument("version", help="pinned AP/CSC/CP/BL version string")
    dir_parser = subparsers.add_parser("dir", help="validate cached Odin payload filenames")
    dir_parser.add_argument("path", type=Path)
    dir_parser.add_argument("model")
    dir_parser.add_argument("version", help="pinned AP/CSC/CP/BL version string")
    args = parser.parse_args()

    try:
        if args.mode == "zip":
            tar_names = validate_archive(args.path, args.model, args.version)
        else:
            tar_names = validate_payload_directory(args.path, args.model, args.version)
    except (OSError, ValidationError) as exc:
        print(f"Firmware archive validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Validated Samsung FUS {args.mode} for {args.model}/{args.version}: {len(tar_names)} Odin payloads")
    for name in tar_names:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
