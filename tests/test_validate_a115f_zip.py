from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_a115f_zip.py"
SPEC = importlib.util.spec_from_file_location("validate_a115f_zip", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

CONFIG = {
    "TARGET_CODENAME": "a115f",
    "TARGET_ASSERT_MODEL": "SM-A115F",
    "TARGET_SUPER_PARTITION_SIZE": 4324327424,
    "TARGET_SUPER_GROUP_SIZE": 4320133120,
    "TARGET_SUPER_GROUP_NAME": "qti_dynamic_partitions",
    "TARGET_HAS_SYSTEM_EXT": False,
}

TARGET_LAYOUT = b"""use_dynamic_partitions=true
super_partition_size=4324327424
super_partition_group=qti_dynamic_partitions
super_qti_dynamic_partitions_group_size=4320133120
super_qti_dynamic_partitions_partition_list=system product vendor
"""

BASE_OPS = """# operations
remove_all_groups
add_group qti_dynamic_partitions 4320133120
add system qti_dynamic_partitions
add vendor qti_dynamic_partitions
add product qti_dynamic_partitions
resize system 100
resize vendor 100
resize product 100
"""

BASE_UPDATER = '''
getprop("ro.boot.em.model") == "SM-A115F" || abort("wrong model");
assert(update_dynamic_partitions(package_extract_file("dynamic_partitions_op_list")));
block_image_update(map_partition("system"), "system.transfer.list", "system.new.dat.br", "system.patch.dat");
block_image_update(map_partition("vendor"), "vendor.transfer.list", "vendor.new.dat.br", "vendor.patch.dat");
block_image_update(map_partition("product"), "product.transfer.list", "product.new.dat.br", "product.patch.dat");
'''

REQUIRED_MEMBERS = {
    "META-INF/com/google/android/update-binary": b"fake-test-binary",
    "META-INF/com/google/android/updater-script": BASE_UPDATER.encode(),
    "META-INF/com/android/metadata": b"pre-device=a115f\n",
    "dynamic_partitions_op_list": BASE_OPS.encode(),
    "build_info.txt": b"device=a115f\n",
    "unsparse_super_empty.img": b"test-super-metadata",
    "target_os_partitions_metadata.txt": TARGET_LAYOUT,
    "boot.img": b"test-boot",
    "dtbo.img": b"test-dtbo",
    "system.new.dat.br": b"system-payload",
    "system.transfer.list": b"4\n",
    "vendor.new.dat.br": b"vendor-payload",
    "vendor.transfer.list": b"4\n",
    "product.new.dat.br": b"product-payload",
    "product.transfer.list": b"4\n",
}


class ValidateA115FZipTests(unittest.TestCase):
    def make_zip(self, directory: str, overrides: dict[str, bytes] | None = None) -> Path:
        path = Path(directory) / "test-rom.zip"
        members = dict(REQUIRED_MEMBERS)
        if overrides:
            members.update(overrides)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in members.items():
                archive.writestr(name, data)
        return path

    def test_accepts_valid_a115f_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            messages = VALIDATOR.validate(self.make_zip(directory), CONFIG)
        self.assertTrue(any("Dynamic group: PASS" in message for message in messages))
        self.assertTrue(any("Target firmware partition preservation: PASS (vendor)" in message for message in messages))

    def test_loads_and_accepts_repository_target_config(self) -> None:
        target_config = VALIDATOR.load_target_config(ROOT / "target/a115f/config.sh")
        with tempfile.TemporaryDirectory() as directory:
            messages = VALIDATOR.validate(self.make_zip(directory), target_config)
        self.assertTrue(any("qti_dynamic_partitions" in message for message in messages))

    def test_rejects_missing_required_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            members = dict(REQUIRED_MEMBERS)
            del members["dtbo.img"]
            path = Path(directory) / "missing-dtbo.zip"
            with zipfile.ZipFile(path, "w") as archive:
                for name, data in members.items():
                    archive.writestr(name, data)
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "dtbo.img"):
                VALIDATOR.validate(path, CONFIG)

    def test_rejects_separate_system_ext_for_merged_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_zip(directory, {"system_ext.new.dat.br": b"unexpected"})
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "merged system_ext"):
                VALIDATOR.validate(path, CONFIG)

    def test_rejects_dynamic_group_overflow(self) -> None:
        ops = BASE_OPS.replace("resize system 100", "resize system 4320133100")
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_zip(directory, {"dynamic_partitions_op_list": ops.encode()})
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "exceeding group capacity"):
                VALIDATOR.validate(path, CONFIG)

    def test_rejects_duplicate_remove_all_groups(self) -> None:
        ops = BASE_OPS.replace("remove_all_groups\n", "remove_all_groups\nremove_all_groups\n")
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_zip(directory, {"dynamic_partitions_op_list": ops.encode()})
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "exactly one remove_all_groups"):
                VALIDATOR.validate(path, CONFIG)

    def test_rejects_trailing_remove_all_groups(self) -> None:
        ops = BASE_OPS + "remove_all_groups\n"
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_zip(directory, {"dynamic_partitions_op_list": ops.encode()})
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "exactly one remove_all_groups"):
                VALIDATOR.validate(path, CONFIG)

    def test_rejects_partition_added_to_wrong_group(self) -> None:
        ops = BASE_OPS.replace("add vendor qti_dynamic_partitions", "add vendor wrong_group")
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_zip(directory, {"dynamic_partitions_op_list": ops.encode()})
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "wrong group"):
                VALIDATOR.validate(path, CONFIG)

    def test_rejects_payload_without_transfer_list(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_zip(directory, {"extra.new.dat.br": b"unexpected"})
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "payloads and transfer lists differ"):
                VALIDATOR.validate(path, CONFIG)

    def test_rejects_missing_target_side_partition(self) -> None:
        layout = TARGET_LAYOUT.replace(b"system product vendor", b"system product vendor odm")
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_zip(directory, {"target_os_partitions_metadata.txt": layout})
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "target-side dynamic partition.*odm"):
                VALIDATOR.validate(path, CONFIG)

    def test_rejects_missing_target_side_updater_write(self) -> None:
        layout = TARGET_LAYOUT.replace(b"system product vendor", b"system product vendor odm")
        ops = BASE_OPS.replace(
            "add vendor qti_dynamic_partitions",
            "add vendor qti_dynamic_partitions\nadd odm qti_dynamic_partitions",
        ).replace("resize vendor 100", "resize vendor 100\nresize odm 100")
        overrides = {
            "target_os_partitions_metadata.txt": layout,
            "dynamic_partitions_op_list": ops.encode(),
            "odm.new.dat.br": b"odm-payload",
            "odm.transfer.list": b"4\n",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_zip(directory, overrides)
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError,
                "Updater block_image_update calls do not match dynamic payload partitions",
            ):
                VALIDATOR.validate(path, CONFIG)

    def test_rejects_target_group_size_mismatch(self) -> None:
        layout = TARGET_LAYOUT.replace(b"4320133120", b"4320133000")
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_zip(directory, {"target_os_partitions_metadata.txt": layout})
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "group size does not match"):
                VALIDATOR.validate(path, CONFIG)

    def test_rejects_target_physical_super_size_mismatch(self) -> None:
        layout = TARGET_LAYOUT.replace(
            b"super_partition_size=4324327424",
            b"super_partition_size=4324327000",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_zip(directory, {"target_os_partitions_metadata.txt": layout})
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "physical super size"):
                VALIDATOR.validate(path, CONFIG)

    def test_rejects_data_format_command(self) -> None:
        updater = BASE_UPDATER + '\nformat("ext4", "EMMC", "/dev/block/userdata");\n'
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_zip(directory, {"META-INF/com/google/android/updater-script": updater.encode()})
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "data-format operation"):
                VALIDATOR.validate(path, CONFIG)

    def test_rejects_wrong_device_identity(self) -> None:
        wrong_config = dict(CONFIG, TARGET_ASSERT_MODEL="SM-A115M")
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_zip(directory)
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "not asserted"):
                VALIDATOR.validate(path, wrong_config)

    def test_a115f_local_zip_builder_invokes_validator(self) -> None:
        builder = (ROOT / "scripts/internal/build_flashable_zip.sh").read_text(encoding="utf-8")
        self.assertIn('if [[ "$TARGET_CODENAME" == "a115f" ]]; then', builder)
        self.assertIn('python3 "$SRC_DIR/scripts/validate_a115f_zip.py"', builder)
        self.assertIn('rm -f "$OUT_DIR/$ZIP_FILE_NAME"', builder)


if __name__ == "__main__":
    unittest.main()
