from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "unica/patches/stock_blobs/customize.sh"


class StockBlobsSaivTests(unittest.TestCase):
    def run_stock_blobs(self, root: Path, target_has_saiv: bool) -> tuple[Path, str]:
        fw = root / "fw"
        work = root / "work"
        source = fw / "SM-A057F_TUR"
        target = fw / "SM-A115F_MWD"
        (source / "system/system/saiv/textrecognition").mkdir(parents=True)
        (source / "system/system/saiv/textrecognition/source.bin").write_text("source")
        (source / "system/system/saiv/source-only.bin").write_text("source")
        (target / "system/system").mkdir(parents=True)
        if target_has_saiv:
            (target / "system/system/saiv").mkdir(parents=True)
            (target / "system/system/saiv/target-only.bin").write_text("target")
        (work / "system/system/saiv").mkdir(parents=True)
        (work / "system/system/saiv/donor-only.bin").write_text("donor")
        (work / "system/system/etc/saiv").mkdir(parents=True)
        (work / "system/system/etc/saiv/donor.xml").write_text("donor")
        (work / "system/system/cameradata").mkdir(parents=True)

        harness = root / "harness.sh"
        harness.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    "set -euo pipefail",
                    f'export TARGET_SINGLE_SYSTEM_IMAGE=qssi FW_DIR="{fw}" WORK_DIR="{work}"',
                    "export SOURCE_FIRMWARE=SM-A057F/TUR/A057FXXUFDZH2",
                    "export TARGET_FIRMWARE=SM-A115F/MWD/A115FXXS6CWK2",
                    "LOG_STEP_IN() { :; }",
                    "LOG_STEP_OUT() { :; }",
                    'LOG() { echo "LOG:$*"; }',
                    'LOGW() { echo "WARN:$*"; }',
                    'LOGE() { echo "ERROR:$*" >&2; exit 1; }',
                    'DELETE_FROM_WORK_DIR() { rm -rf "$WORK_DIR/$1/$2"; }',
                    "ADD_TO_WORK_DIR() {",
                    '  local source="$1"; local partition="$2"; local path="$3"',
                    '  if [[ "$source" != /* ]]; then source="$FW_DIR/${source//\\//_}"; fi',
                    '  local from="$source/$partition/$path"',
                    '  local to="$WORK_DIR/$partition/$path"',
                    '  test -e "$from" || { echo "missing source: $from" >&2; exit 21; }',
                    '  mkdir -p "$(dirname "$to")"',
                    '  cp -a "$from" "$to"',
                    "}",
                    f'source "{SCRIPT}"',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        result = subprocess.run(["bash", str(harness)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return work, result.stdout

    def test_missing_target_saiv_drops_donor_tree_without_aborting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work, output = self.run_stock_blobs(Path(directory), target_has_saiv=False)
            saiv = work / "system/system/saiv"
            self.assertIn("Target firmware has no system/saiv; dropping donor-only SAIV tree", output)
            self.assertFalse((saiv / "donor-only.bin").exists())
            self.assertFalse((saiv / "source-only.bin").exists())
            self.assertTrue((saiv / "textrecognition/source.bin").is_file())

    def test_target_saiv_replaces_donor_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work, output = self.run_stock_blobs(Path(directory), target_has_saiv=True)
            saiv = work / "system/system/saiv"
            self.assertNotIn("dropping donor-only SAIV tree", output)
            self.assertFalse((saiv / "donor-only.bin").exists())
            self.assertTrue((saiv / "target-only.bin").is_file())
            self.assertTrue((saiv / "textrecognition/source.bin").is_file())


if __name__ == "__main__":
    unittest.main()
