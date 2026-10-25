# A115F One UI 7 First-Boot Progress

- **Device guard:** Samsung Galaxy A11 `SM-A115F`, Binary 6 only.
- **Donor:** SM-A057F One UI 7 / Android 15.
- **Target firmware pin:** `A115FXXS6CWK2/A115FOJM6CWK1/A115FXXS6CWK1/A115FXXS6CWK2`.
- **Current source branch:** `a115f-audit-local`.
**Last prior public diagnostic ZIP:** SHA-256 `1103fc00b36b7aa427a7bec4dd43db8aad92f2254f6022253d09704f23667c3b`.

## Current milestone

**M2 — Android init starts; M3 — logo/boot animation not yet reached.** The available kernel log reaches second-stage init, starts Android/vendor processes, then fails while `vold` prepares file-based encryption for `/data` and requests a reboot to Recovery. That log does not identify the exact installed ZIP checksum, so it is not proof of the result from a particular release artifact.

No honest time-to-fix percentage can be derived from the present evidence. M0 audit work is complete; M1 ZIP structure and static checks passed, but device flashability for the exact artifact is not independently verified; M2 is observed in a prior log; M3 is not achieved. Do not describe this as a successful boot or a finished ROM.

## Main blocker and newly identified omission

The prior diagnostic ZIP copied the stock A115F `/system/bin/wait_for_keymaster`, its init service file, and selected 32-bit libraries into the Android 15 system. However, the target Vendor's `/vendor/etc/init/hw/init.target.rc` still ran:

```text
on late-fs
    mount_all /vendor/etc/fstab.qcom --late
```

That `mount_all --late` processes the userdata `/data` entry with `fileencryption=ice`. The staged helper was not explicitly executed before this mount, so the earlier build did **not** guarantee that Keymaster was ready before FBE initialization. Android's metadata-encryption guidance explicitly instructs vendors to put `exec_start wait_for_keymaster` before the late `mount_all` that mounts `/data`; it explains that this ordering prevents a KeyMint/init/vold readiness deadlock [1].

A narrow fail-closed patcher has now been added. It inserts exactly one `exec_start wait_for_keymaster` immediately before the unique A115F `mount_all /vendor/etc/fstab.qcom --late` anchor, refuses an unexpected init layout, and is idempotent. `customize.sh` invokes the patcher on the assembled target init file. This preserves the stock FBE fstab, kernel, Vendor HALs, model guard, and partitions. The target has not yet been device-tested with this corrected barrier.

The Android 12 AOSP helper constructs the vold Keymaster wrapper, which waits for `android.system.keystore2.IKeystoreService/default` and requests the TEE security level [3]. Therefore, seeing the helper report readiness would confirm Keystore2 registration/initialization reached that point; it would **not** prove that QSEE can successfully generate the FBE key or that `/data` will mount.

The old log also contains QSEE/SCM calls failing with function ID `0x72000206`, followed by `vold` reporting `K00R` and a failed `cryptfs enablefilecrypto`. The exact secure-world failure cause is **not** established from this kernel log; the barrier is a targeted ordering fix, not proof that the QSEE/TA problem is solved.

The earlier generated updater checked only `ro.boot.em.model == SM-A115F`; it did not enforce Binary 6. The supplied kernel command line reports `androidboot.bootloader=A115FXXS6CWK2`, and AOSP maps `androidboot.<key>` to `ro.boot.<key>` [4]. I added a fail-closed `ro.boot.bootloader == A115FXXS6CWK2` assertion and extended the ZIP validator to reject missing or widened guards. The candidate passes ZIP/CRC validation. Compared with the preceding local build, `boot.img`, `dtbo.img`, transfer lists, dynamic-partition operations, and partition metadata match; the compressed system/vendor/product/odm image payloads differ byte-for-byte because the ZIP builder regenerated filesystem images from the same staged tree. GitHub's public asset digest now matches the validated local SHA-256.

## Completed and verified

- The A115F boot/vendor/partition audit and firmware pin are recorded in this repository. The stock A115F Kernel/ramdisk/DTB are used; no custom A115F kernel build is integrated into this target.
- The earlier ZIP passed structural, CRC, target-guard, and image-group checks. Its boot components were verified identical to the stock A115F components after accounting for Samsung signature removal.
- The new helper-order patcher and Binary 6 guard are implemented. The full suite now passes: **60 tests**. Python compilation, per-file `bash -n`, `git diff --check`, and the temporary-file init-order test passed.
- The A115F Binary 6 image build and guarded ZIP repack completed successfully. The candidate passed static ZIP/CRC validation and has replaced the asset in the public GitHub release. It has not been physically boot-tested.

## Public test artifact

- **Release page:** https://github.com/nova-arch008/ZineROM-A115F-OneUI7-boot-test/releases/tag/a115f-boot-test
- **Direct download:** https://github.com/nova-arch008/ZineROM-A115F-OneUI7-boot-test/releases/download/a115f-boot-test/ZineROM_OneUI7_A115F-Port-A057F.zip
- **SHA-256:** `29384d92ba37f6603cf0dfe08eec027e4049e3781414ffc9d197479b3388e2e0`
- **Size:** `1,842,620,087` bytes.

## Change log

1. Previous diagnostic attempt: added stock wait helper and libraries, but did not explicitly run it before the `/data` late mount. This was an incomplete diagnostic and did not prove or fix the ordering race.
2. Current change: add `scripts/patch_a115f_init.py`; invoke it from `target/a115f/patches/miscs/customize.sh`; add five regression tests in `tests/test_patch_a115f_init.py`.
3. Current behavior: FBE remains enabled. No `format data`, no vbmeta/bootloader/radio change, and no custom kernel replacement are part of this patch.
4. Safety correction: the config and ZIP generator now require the observed bootloader `A115FXXS6CWK2`; the validator and tests enforce this alongside an exclusive `SM-A115F` model guard.

## Next three actions

1. Have a tester use the linked runbook and flash only on `SM-A115F` with bootloader `A115FXXS6CWK2`; do not add patches or format data just for this test.
2. Record the exact downloaded ZIP SHA and the furthest stage reached: Samsung logo, ROM boot animation, Setup Wizard, or Recovery. Collect ADB logcat if reachable, otherwise `pstore/last_kmsg` from recovery.
3. Analyze whether `wait_for_keymaster` reached readiness and whether the QSEE/SCM and vold/FBE errors persist. Select the next change only after those logs; disabling FBE remains a last-resort diagnostic.

## Safety status

The patch leaves FBE enabled and does not modify the bootloader, modem, physical PIT/partition boundaries, or stock Kernel. The installer does rewrite logical dynamic-partition metadata inside the existing `super` device; a wrong target or interrupted flash can still leave Android unbootable. Keep a verified stock restore package and recovery access available. The patch does not guarantee boot, and the separate Keymaster/QSEE failure may remain. Do not use this build on another model or bootloader build.

## References

[1]: https://source.android.com/docs/security/features/encryption/metadata "Android metadata encryption configuration and KeyMint readiness ordering"
[2]: https://android.googlesource.com/platform/system/core/+/master/init/README.md "AOSP init services, classes, and exec_start command"
[3]: https://android.googlesource.com/platform/system/vold/+/android-12.0.0_r1/Keymaster.cpp "AOSP Android 12 vold Keymaster wrapper"
[4]: https://android.googlesource.com/platform/system/core/+/refs/heads/main/init/property_service.cpp "AOSP androidboot property mapping"
