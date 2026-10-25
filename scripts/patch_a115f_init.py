#!/usr/bin/env python3
"""Apply the A115F KeyMint readiness barrier before mounting /data."""

from __future__ import annotations

import sys
from pathlib import Path


MOUNT_ANCHOR = "mount_all /vendor/etc/fstab.qcom --late"
WAIT_COMMAND = "exec_start wait_for_keymaster"


class InitPatchError(ValueError):
    """Raised when the target init file differs from the expected layout."""


def patch_init_text(text: str) -> tuple[str, bool]:
    """Insert the Keymaster wait before A115F's late fstab mount, once only."""
    lines = text.splitlines()
    anchors = [i for i, line in enumerate(lines) if line.strip() == MOUNT_ANCHOR]
    if len(anchors) != 1:
        raise InitPatchError(
            f"Expected exactly one {MOUNT_ANCHOR!r} anchor; found {len(anchors)}"
        )

    mount_index = anchors[0]
    action_index = next(
        (i for i in range(mount_index - 1, -1, -1)
         if lines[i].strip().startswith("on ")),
        None,
    )
    if action_index is None or lines[action_index].strip() != "on late-fs":
        raise InitPatchError("A115F fstab late mount is not under an on late-fs action")

    if any(line.strip() == WAIT_COMMAND for line in lines[action_index + 1:mount_index]):
        return text, False

    indent = lines[mount_index][: len(lines[mount_index]) - len(lines[mount_index].lstrip())]
    lines.insert(mount_index, f"{indent}{WAIT_COMMAND}")
    patched = "\n".join(lines)
    if text.endswith("\n"):
        patched += "\n"
    return patched, True


def patch_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    patched, changed = patch_init_text(original)
    if changed:
        path.write_text(patched, encoding="utf-8")
    return changed


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {Path(argv[0]).name} <vendor-init-target-rc>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        changed = patch_file(path)
    except (OSError, InitPatchError) as error:
        print(f"A115F init patch failed: {error}", file=sys.stderr)
        return 1
    state = "inserted" if changed else "already present"
    print(f"A115F Keymaster readiness barrier {state} in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
