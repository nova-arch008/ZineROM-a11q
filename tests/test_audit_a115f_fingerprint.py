from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_a115f_fingerprint.py"
SPEC = importlib.util.spec_from_file_location("audit_a115f_fingerprint", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class AuditA115FFingerprintTests(unittest.TestCase):
    def test_reads_fingerprint_configuration_strings_from_framework_dex(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory) / "framework.jar"
            with zipfile.ZipFile(jar, "w") as archive:
                archive.writestr(
                    "classes.dex",
                    b"\x00google_touch_side,settings=3,navi=1\x00rear,settings=0\x00unrelated-string\x00",
                )
            values = AUDIT.framework_candidates(jar)
        self.assertIn("google_touch_side,settings=3,navi=1", values)
        self.assertIn("rear,settings=0", values)
        self.assertNotIn("unrelated-string", values)

    def test_lists_stock_vendor_fingerprint_hal_service_and_binary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vendor = Path(directory) / "vendor"
            (vendor / "etc/vintf").mkdir(parents=True)
            (vendor / "etc/vintf/manifest.xml").write_text(
                '<manifest><hal><name>android.hardware.biometrics.fingerprint</name>'
                '<version>2.1</version><interface><instance>default</instance></interface></hal></manifest>',
                encoding="utf-8",
            )
            (vendor / "etc/init").mkdir(parents=True)
            (vendor / "etc/init/fingerprint.rc").write_text(
                "service vendor.fingerprint /vendor/bin/hw/android.hardware.biometrics.fingerprint-service\n",
                encoding="utf-8",
            )
            binary = vendor / "bin/hw/android.hardware.biometrics.fingerprint-service"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"service")
            manifest, services, binaries = AUDIT.vendor_fingerprint_inventory(vendor)
        self.assertTrue(any("android.hardware.biometrics.fingerprint" in item for item in manifest))
        self.assertTrue(any("fingerprint.rc" in item for item in services))
        self.assertIn("bin/hw/android.hardware.biometrics.fingerprint-service", binaries)

    def test_reports_vndk_property_and_apex_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            system = Path(directory) / "system"
            nested_apex = system / "system/system_ext/apex"
            nested_apex.mkdir(parents=True)
            (system / "vendor").mkdir(parents=True)
            (system / "vendor/build.prop").write_text(
                "ro.vndk.version=30\nro.build.version.sdk=31\n", encoding="utf-8"
            )
            apex = nested_apex / "com.android.vndk.current.apex"
            with zipfile.ZipFile(apex, "w") as archive:
                archive.writestr("apex_manifest.pb", b"name:com.android.vndk.v30")
            properties, apexes = AUDIT.system_vndk_inventory(system)
        self.assertTrue(any("ro.vndk.version=30" in item for item in properties))
        self.assertTrue(any("system_ext/apex/com.android.vndk.current.apex" in item for item in apexes))
        self.assertTrue(any("com.android.vndk.v30" in item for item in apexes))


if __name__ == "__main__":
    unittest.main()
