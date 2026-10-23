# Flashing the A115F boot-first test ZIP

The first test ZIP must not depend on decrypted `/data`. A115F recovery may show encrypted or randomly named files even when the ROM ZIP itself is valid. Keep the ZIP on a microSD card or USB-OTG drive, or use ADB sideload from a computer.

## Safety and prerequisites

This procedure is for `SM-A115F` only. Keep the complete stock `A115FXXS6CWK2` package and a working Download Mode path available. Unlocking the bootloader and formatting data can erase the phone. Back up personal data first. Do not flash the ZIP on an A115M, A115U, M11, or another A115 variant.

The A11 Snapdragon TWRP guidance documents the following sequence: unlock the bootloader, disable AVB with `vbmeta_disabled.tar`, flash the A11 TWRP TAR through Odin, disable encryption with the recovery `multidisabler`, and format data when required. See the original A11 recovery thread before using any recovery or vbmeta file:

https://xdaforums.com/t/recovery-unofficial-twrp-for-galaxy-a11-snapdragon.4197085/page-2

## Recommended first-test sequence

1. Boot the phone to Download Mode and confirm that the model shown is `SM-A115F`. Do not continue if it shows another model.
2. Confirm that the bootloader is unlocked. Samsung normally performs a data wipe during the unlock process.
3. Flash an A115F-compatible `vbmeta_disabled.tar` in Odin's AP slot. Do not use a vbmeta file from A52s, A73, A05s, or another model.
4. Flash an A115F-compatible TWRP/OrangeFox TAR in Odin's AP slot. Boot directly to recovery after Odin completes; do not allow stock Android to boot first if the recovery guide warns that stock recovery may be restored.
5. In recovery, check whether `/data` is readable. If it is encrypted, do not spend time trying to browse internal storage. Use microSD, USB-OTG, or ADB sideload.
6. If the recovery build provides an A115F-compatible `multidisabler`, run it from recovery Terminal or flash the matching utility recommended by the recovery maintainer. Do not use a random multidisabler from another device.
7. If recovery or the multidisabler requires it, use **Wipe → Format Data**, type `yes`, and reboot back into recovery. This erases user data and is not the same as an ordinary cache wipe.
8. Reconnect the external storage or USB cable after rebooting recovery. Encryption changes can make the storage disappear until recovery restarts.
9. Flash the ZineROM ZIP from one of these methods:

### Method A — ADB sideload (preferred when `/data` is encrypted)

On the computer, from the folder containing the ZIP:

```bash
adb sideload ZineROM_OneUI7_A115F-Port-A057F.zip
```

In recovery choose **Advanced → ADB Sideload → Swipe to Start** first. The ZIP is streamed directly to recovery and does not need to be copied to encrypted internal storage.

### Method B — microSD or USB-OTG

Copy the ZIP to a FAT32/exFAT microSD card or USB-OTG drive. In recovery choose **Install**, select the external storage, and flash the ZIP. If recovery cannot mount the external device, use ADB sideload instead.

10. Do not flash any Live Blur, AI, camera, audio, repartitioner, or random vendor patch after the first test. The boot-first ZIP keeps the current logical partition layout, does not rewrite super metadata, and is only intended to test the boot chain, display/touch, ADB, and SystemServer. Google Play Services is omitted in this test build to fit the existing product partition.
11. After installation, reboot system and wait several minutes on the first boot. If it loops, return to recovery and collect the logs in `BOOT_LOGGING.md` before changing anything else.

## Why this ZIP should not format data automatically

A recovery ZIP that formats data automatically can destroy the user's backup and can make diagnosis harder. The A115F boot-first installer does not resize or repartition super and does not automatically format data; data formatting remains a deliberate manual recovery step after a backup.

## If the phone shows “System has been destroyed” or “System Broken”

Stop and do not repeatedly reboot. Return to Download Mode, restore the matching stock A115F package, and verify that the recovery/vbmeta files were for `SM-A115F`. That message is a boot-chain/AVB or partition mismatch until proven otherwise; it is not fixed by copying a donor vendor or by adding Live Blur libraries.
