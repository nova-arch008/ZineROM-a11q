from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CUSTOMIZER = ROOT / "unica/patches/stock_blobs/customize.sh"


class StockBlobsTests(unittest.TestCase):
    def run_customizer(self, target_saiv_present: bool) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            firmware_root = root / "fw"
            target_root = firmware_root / "SM-A115F_MWD"
            work_dir = root / "work"
            calls = root / "calls.log"
            (work_dir / "system/system/saiv").mkdir(parents=True)
            (work_dir / "system/system/etc/saiv").mkdir(parents=True)
            if target_saiv_present:
                (target_root / "system/system/saiv").mkdir(parents=True)

            harness = r'''
set -euo pipefail
LOG_STEP_IN() { :; }
LOG_STEP_OUT() { :; }
LOG() { printf 'LOG %s\n' "$*" >> "$CALLS"; }
DELETE_FROM_WORK_DIR() { printf 'DELETE %s %s\n' "$1" "$2" >> "$CALLS"; }
ADD_TO_WORK_DIR() { printf 'ADD %s %s\n' "$2" "$3" >> "$CALLS"; }
source "$CUSTOMIZER"
'''
            env = os.environ.copy()
            env.update(
                {
                    "FW_DIR": str(firmware_root),
                    "WORK_DIR": str(work_dir),
                    "CALLS": str(calls),
                    "CUSTOMIZER": str(CUSTOMIZER),
                    "TARGET_SINGLE_SYSTEM_IMAGE": "qssi",
                    "TARGET_FIRMWARE": "SM-A115F/MWD/A115FXXS6CWK2",
                    "SOURCE_FIRMWARE": "SM-A057F/TUR/A057FXXUFDZH2",
                }
            )
            subprocess.run(
                ["bash", "-euo", "pipefail", "-c", harness],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            return calls.read_text(encoding="utf-8").splitlines()

    def test_skips_saiv_replacement_when_target_tree_is_missing(self) -> None:
        calls = self.run_customizer(target_saiv_present=False)
        self.assertIn("DELETE system system/saiv", calls)
        self.assertNotIn("ADD system system/saiv", calls)
        self.assertTrue(any("Target SAIV tree is absent" in item for item in calls))

    def test_replaces_saiv_when_target_tree_is_present(self) -> None:
        calls = self.run_customizer(target_saiv_present=True)
        self.assertIn("DELETE system system/saiv", calls)
        self.assertIn("ADD system system/saiv", calls)


if __name__ == "__main__":
    unittest.main()
