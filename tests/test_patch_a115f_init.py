from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/patch_a115f_init.py"
SPEC = importlib.util.spec_from_file_location("patch_a115f_init", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCHER)


class PatchA115FInitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.init_text = (
            "on early-fs\n"
            "    mount_all /vendor/etc/fstab.qcom --early\n"
            "\n"
            "on late-fs\n"
            "    # Mount RW partitions and /data.\n"
            "    mount_all /vendor/etc/fstab.qcom --late\n"
            "\n"
            "on post-fs-data\n"
            "    start vold\n"
        )

    def test_inserts_wait_immediately_before_late_mount(self) -> None:
        patched, changed = PATCHER.patch_init_text(self.init_text)
        self.assertTrue(changed)
        self.assertIn(
            "    # Mount RW partitions and /data.\n"
            "    exec_start wait_for_keymaster\n"
            "    mount_all /vendor/etc/fstab.qcom --late\n",
            patched,
        )
        self.assertIn("    mount_all /vendor/etc/fstab.qcom --early\n", patched)
        self.assertEqual(patched.count("exec_start wait_for_keymaster"), 1)

    def test_is_idempotent(self) -> None:
        once, first_changed = PATCHER.patch_init_text(self.init_text)
        twice, second_changed = PATCHER.patch_init_text(once)
        self.assertTrue(first_changed)
        self.assertFalse(second_changed)
        self.assertEqual(once, twice)

    def test_rejects_missing_or_ambiguous_mount_anchor(self) -> None:
        with self.assertRaisesRegex(PATCHER.InitPatchError, "found 0"):
            PATCHER.patch_init_text("on late-fs\n    start vold\n")
        duplicate = self.init_text + "\non late-fs\n    " + PATCHER.MOUNT_ANCHOR + "\n"
        with self.assertRaisesRegex(PATCHER.InitPatchError, "found 2"):
            PATCHER.patch_init_text(duplicate)

    def test_rejects_mount_anchor_outside_late_fs(self) -> None:
        invalid = "on fs\n    " + PATCHER.MOUNT_ANCHOR + "\n"
        with self.assertRaisesRegex(PATCHER.InitPatchError, "not under an on late-fs"):
            PATCHER.patch_init_text(invalid)

    def test_file_patch_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "init.target.rc"
            path.write_text(self.init_text, encoding="utf-8")
            self.assertTrue(PATCHER.patch_file(path))
            content = path.read_text(encoding="utf-8")
            self.assertFalse(PATCHER.patch_file(path))
            self.assertEqual(path.read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()
