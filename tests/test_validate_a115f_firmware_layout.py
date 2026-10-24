from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_a115f_firmware_layout.py"
SPEC = importlib.util.spec_from_file_location("validate_a115f_firmware_layout", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

CONFIG = {
    "TARGET_CODENAME": "a115f",
    "TARGET_FIRMWARE_VERSION": "A115FXXS6CWK2/A115FOJM6CWK1/A115FXXS6CWK1/A115FXXS6CWK2",
    "TARGET_SUPER_GROUP_NAME": "qti_dynamic_partitions",
    "TARGET_SUPER_GROUP_SIZE": 4320133120,
    "TARGET_SUPER_PARTITION_SIZE": 4324327424,
}
VERSION = "A115FXXS6CWK2/A115FOJM6CWK1/A115FXXS6CWK1/A115FXXS6CWK2"
METADATA = """use_dynamic_partitions=true
super_partition_size=4324327424
super_partition_group=qti_dynamic_partitions
super_qti_dynamic_partitions_group_size=4320133120
super_qti_dynamic_partitions_partition_list=system product vendor
"""


class ValidateA115FFirmwareLayoutTests(unittest.TestCase):
    def make_firmware(self, root: Path, metadata: str = METADATA) -> Path:
        firmware = root / "SM-A115F_INS"
        firmware.mkdir()
        (firmware / ".extracted").write_text(VERSION, encoding="utf-8")
        (firmware / "os_partitions_metadata.txt").write_text(metadata, encoding="utf-8")
        vendor = firmware / "vendor"
        (vendor / "etc/vintf").mkdir(parents=True)
        (vendor / "etc/vintf/manifest.xml").write_text(
            '<manifest><hal><name>android.hardware.keymaster</name></hal></manifest>',
            encoding="utf-8",
        )
        init_dir = vendor / "etc/init"
        init_dir.mkdir(parents=True)
        (init_dir / "keymaster.rc").write_text(
            "service keymaster-4-0 /vendor/bin/hw/android.hardware.keymaster@4.0-service-qti\n",
            encoding="utf-8",
        )
        service_bin = vendor / "bin/hw/android.hardware.keymaster@4.0-service-qti"
        service_bin.parent.mkdir(parents=True)
        service_bin.write_bytes(b"keymaster")
        service_bin.chmod(0o755)
        (vendor / "etc/fstab.qcom").write_text(
            "/dev/block/userdata /data f2fs noatime fileencryption=ice\n",
            encoding="utf-8",
        )
        (vendor / "lib64").mkdir()
        (vendor / "lib64/libexample.so").write_bytes(b"vendor")
        (firmware / "fs_config-vendor").write_text("vendor 0 0 755\n", encoding="utf-8")
        (firmware / "file_context-vendor").write_text("/vendor u:object_r:vendor_file:s0\n", encoding="utf-8")
        kernel = firmware / "kernel"
        kernel.mkdir()
        (kernel / "boot.img").write_bytes(b"boot")
        (kernel / "dtbo.img").write_bytes(b"dtbo")
        return firmware

    def test_accepts_complete_target_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory))
            messages = VALIDATOR.validate(firmware, CONFIG, VERSION)
        self.assertTrue(any("Target vendor-side partitions: PASS (vendor)" in message for message in messages))

    def test_rejects_missing_partition_list_entry(self) -> None:
        metadata = METADATA.replace("system product vendor", "system product vendor vendor_dlkm")
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory), metadata)
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "vendor_dlkm"):
                VALIDATOR.validate(firmware, CONFIG, VERSION)

    def test_rejects_wrong_super_group_size(self) -> None:
        metadata = METADATA.replace("4320133120", "4320133000")
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory), metadata)
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "group size mismatch"):
                VALIDATOR.validate(firmware, CONFIG, VERSION)

    def test_rejects_wrong_physical_super_size(self) -> None:
        metadata = METADATA.replace("super_partition_size=4324327424", "super_partition_size=4324327000")
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory), metadata)
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "physical super size mismatch"):
                VALIDATOR.validate(firmware, CONFIG, VERSION)

    def test_rejects_wrong_pinned_firmware_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory))
            (firmware / ".extracted").write_text("different-version", encoding="utf-8")
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "version mismatch"):
                VALIDATOR.validate(firmware, CONFIG)

    def test_rejects_cli_version_different_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory))
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "does not match target config"):
                VALIDATOR.validate(firmware, CONFIG, "different-version")

    def test_rejects_manifest_without_keymaster(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory))
            manifest = firmware / "vendor/etc/vintf/manifest.xml"
            manifest.write_text("<manifest><hal><name>android.hardware.audio</name></hal></manifest>", encoding="utf-8")
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "Keymaster/KeyMint"):
                VALIDATOR.validate(firmware, CONFIG, VERSION)

    def test_rejects_missing_vintf_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory))
            (firmware / "vendor/etc/vintf/manifest.xml").unlink()
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "VINTF device manifest"):
                VALIDATOR.validate(firmware, CONFIG, VERSION)

    def test_rejects_missing_keymaster_service_binary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory))
            (firmware / "vendor/bin/hw/android.hardware.keymaster@4.0-service-qti").unlink()
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "executable is missing"):
                VALIDATOR.validate(firmware, CONFIG, VERSION)

    def test_rejects_non_executable_keymaster_service_binary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory))
            service_bin = firmware / "vendor/bin/hw/android.hardware.keymaster@4.0-service-qti"
            service_bin.chmod(0o644)
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "not executable"):
                VALIDATOR.validate(firmware, CONFIG, VERSION)

    def test_accepts_keymint_only_manifest_and_service(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory))
            manifest = firmware / "vendor/etc/vintf/manifest.xml"
            manifest.write_text(
                '<manifest><hal><name>android.hardware.security.keymint</name></hal></manifest>',
                encoding="utf-8",
            )
            init_dir = firmware / "vendor/etc/init"
            (init_dir / "keymint.rc").write_text(
                "service keymint /vendor/bin/hw/android.hardware.security.keymint-service-qti\n",
                encoding="utf-8",
            )
            keymint_bin = firmware / "vendor/bin/hw/android.hardware.security.keymint-service-qti"
            keymint_bin.write_bytes(b"keymint")
            keymint_bin.chmod(0o755)
            messages = VALIDATOR.validate(firmware, CONFIG, VERSION)
        self.assertTrue(any("keymint" in message for message in messages))

    def test_rejects_missing_data_fileencryption_flag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory))
            (firmware / "vendor/etc/fstab.qcom").write_text(
                "/dev/block/userdata /data f2fs noatime\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "fileencryption flag"):
                VALIDATOR.validate(firmware, CONFIG, VERSION)

    def test_requires_cryptfshw_for_ice_if_manifest_declares_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            firmware = self.make_firmware(Path(directory))
            manifest = firmware / "vendor/etc/vintf/manifest.xml"
            manifest.write_text(
                '<manifest><hal><name>android.hardware.keymaster</name></hal>'
                '<hal><name>vendor.qti.hardware.cryptfshw</name></hal></manifest>',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "no cryptfshw service executable"):
                VALIDATOR.validate(firmware, CONFIG, VERSION)


if __name__ == "__main__":
    unittest.main()
