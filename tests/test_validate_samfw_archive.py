from __future__ import annotations

import importlib.util
import stat
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_samfw_archive.py"
SPEC = importlib.util.spec_from_file_location("validate_samfw_archive", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

MODEL = "SM-A115F"
VERSION = "A115FXXS6CWK2/A115FOJM6CWK1/A115FXXS6CWK1/A115FXXS6CWK2"
VALID_NAMES = [
    "AP_A115FXXS6CWK2.tar.md5",
    "BL_A115FXXS6CWK2.tar.md5",
    "CP_A115FXXS6CWK1.tar.md5",
    "CSC_OJM6CWK1_A115FOJM6CWK1.tar.md5",
    "HOME_CSC_OJM6CWK1_A115FOJM6CWK1.tar.md5",
]


class ValidateSamfwArchiveTests(unittest.TestCase):
    def write_archive(self, path: Path, names: list[str] | None = None) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            for name in names if names is not None else VALID_NAMES:
                archive.writestr(name, b"payload")

    def test_accepts_pinned_versions_with_distinct_cp_and_bl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "firmware.zip"
            self.write_archive(path)
            result = VALIDATOR.validate_archive(str(path), MODEL, VERSION)
        self.assertEqual(set(result), set(VALID_NAMES))

    def test_rejects_model_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "firmware.zip"
            self.write_archive(path)
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "do not match model"):
                VALIDATOR.validate_archive(str(path), "SM-A115M", VERSION)

    def test_accepts_cached_payload_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload_dir = Path(directory) / "cached"
            payload_dir.mkdir()
            for name in VALID_NAMES:
                (payload_dir / name).write_bytes(b"payload")
            result = VALIDATOR.validate_payload_directory(payload_dir, MODEL, VERSION)
        self.assertEqual(set(result), set(VALID_NAMES))

    def test_rejects_wrong_cp_in_cached_payload_directory(self) -> None:
        names = [name.replace("CP_A115FXXS6CWK1", "CP_A115FXXS6CWK2") for name in VALID_NAMES]
        with tempfile.TemporaryDirectory() as directory:
            payload_dir = Path(directory) / "cached"
            payload_dir.mkdir()
            for name in names:
                (payload_dir / name).write_bytes(b"payload")
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "CP payload"):
                VALIDATOR.validate_payload_directory(payload_dir, MODEL, VERSION)

    def test_rejects_symlink_in_cached_payload_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload_dir = Path(directory) / "cached"
            payload_dir.mkdir()
            for name in VALID_NAMES:
                (payload_dir / name).write_bytes(b"payload")
            (payload_dir / "unsafe.tar.md5").symlink_to(payload_dir / VALID_NAMES[0])
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "symbolic link"):
                VALIDATOR.validate_payload_directory(payload_dir, MODEL, VERSION)

    def test_rejects_wrong_cp_component(self) -> None:
        names = [name.replace("CP_A115FXXS6CWK1", "CP_A115FXXS6CWK2") for name in VALID_NAMES]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "firmware.zip"
            self.write_archive(path, names)
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "CP payload"):
                VALIDATOR.validate_archive(str(path), MODEL, VERSION)

    def test_rejects_wrong_bl_component(self) -> None:
        names = [name.replace("BL_A115FXXS6CWK2", "BL_A115FXXS6CWK1") for name in VALID_NAMES]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "firmware.zip"
            self.write_archive(path, names)
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "BL payload"):
                VALIDATOR.validate_archive(str(path), MODEL, VERSION)

    def test_rejects_wrong_csc_component(self) -> None:
        names = [name.replace("A115FOJM6CWK1", "A115FOJM6CWK2") for name in VALID_NAMES]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "firmware.zip"
            self.write_archive(path, names)
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "CSC build"):
                VALIDATOR.validate_archive(str(path), MODEL, VERSION)

    def test_rejects_duplicate_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "firmware.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                self.write_archive(path, VALID_NAMES + [VALID_NAMES[0]])
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "duplicate"):
                VALIDATOR.validate_archive(str(path), MODEL, VERSION)

    def test_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "firmware.zip"
            self.write_archive(path, VALID_NAMES + ["../escape.tar.md5"])
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "unsafe archive member"):
                VALIDATOR.validate_archive(str(path), MODEL, VERSION)

    def test_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "firmware.zip"
            with zipfile.ZipFile(path, "w") as archive:
                for name in VALID_NAMES:
                    archive.writestr(name, b"payload")
                link = zipfile.ZipInfo("link.tar.md5")
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(link, "target")
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "symbolic link"):
                VALIDATOR.validate_archive(str(path), MODEL, VERSION)

    def test_rejects_unexpected_archive_members(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "firmware.zip"
            self.write_archive(path, VALID_NAMES + ["README.txt"])
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "unexpected file"):
                VALIDATOR.validate_archive(str(path), MODEL, VERSION)

    def test_rejects_malformed_version_string(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "firmware.zip"
            self.write_archive(path)
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "AP/CSC/CP/BL"):
                VALIDATOR.validate_archive(str(path), MODEL, "A/B/C")


if __name__ == "__main__":
    unittest.main()
