from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_a115f_boot.py"
SPEC = importlib.util.spec_from_file_location("audit_a115f_boot", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class AuditA115FBootTests(unittest.TestCase):
    def test_reports_stock_boot_hash_and_super_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".extracted").write_text("A115FXXS6CWK2", encoding="utf-8")
            kernel = root / "kernel"
            kernel.mkdir()
            (kernel / "boot.img").write_bytes(b"stock-a115f-boot")
            (root / "boot.img_metadata.txt").write_text("header_version=4\n", encoding="utf-8")
            (root / "os_partitions_metadata.txt").write_text(
                "super_partition_size=4324327424\nsuper_qti_dynamic_partitions_partition_list=system product vendor\n",
                encoding="utf-8",
            )
            (root / "super_lpdump.txt").write_text("Name: system\nName: product\nName: vendor\n", encoding="utf-8")
            (root / "vendor").mkdir()
            report = AUDIT.audit(root)
        self.assertIn("firmware_version=A115FXXS6CWK2", report)
        self.assertIn("boot.img: bytes=16 sha256=", report)
        self.assertIn("header_version=4", report)
        self.assertIn("Name: system", report)
        self.assertIn("vendor: present", report)

    def test_counts_32_and_64_bit_vendor_elf_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vendor = Path(directory) / "vendor"
            (vendor / "lib").mkdir(parents=True)
            (vendor / "lib64").mkdir()
            arm32 = bytearray(20)
            arm32[:6] = b"\x7fELF\x01\x01"
            arm32[18:20] = (40).to_bytes(2, "little")
            arm64 = bytearray(20)
            arm64[:6] = b"\x7fELF\x02\x01"
            arm64[18:20] = (183).to_bytes(2, "little")
            (vendor / "lib/liba.so").write_bytes(arm32)
            (vendor / "lib64/libb.so").write_bytes(arm64)
            inventory = AUDIT.elf_inventory(vendor)
        self.assertEqual(inventory["ELF32/ARM"], 1)
        self.assertEqual(inventory["ELF64/AArch64"], 1)


if __name__ == "__main__":
    unittest.main()
