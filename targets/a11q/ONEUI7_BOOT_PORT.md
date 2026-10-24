# One UI 7 boot port — Samsung Galaxy A11 SM-A115F

This branch is intended for an experimental One UI 7 / Android 15 port for `SM-A115F` only. The requested milestone is to reach the boot animation and remain there without a bootloop; this is not a claim of a stable ROM or complete device support.

## Actual local state

The earlier statement that the exact A115F stock-package gate was satisfied locally was incorrect and is withdrawn. The inspected workspace contains an A05s donor Odin archive under `out/odin/SM-A057F_TUR`, but it contains no A115F target archive, no extracted A115F `vendor`/`odm`/`super`/`boot`/`dtbo` images, no assembled target work directory, and no flashable ROM ZIP. The donor firmware also has not been freshly revalidated during this audit.

The target config and importer now pin firmware to `SM-A115F/INS/A115FXXS6CWK2`, matching the sales code in the supplied device logs. Availability of this exact historical INS FUS tuple has not yet been verified locally. The importer must download and validate the exact AP/CSC/CP/BL components before building; if the exact tuple is unavailable, stop and resolve the firmware pin rather than substituting EGY or another A115 variant.

## Correct hardware/framework split

The intended split is A05s One UI 7 system/product as a framework donor, with **all A115F hardware-facing files** coming from the exact SM-A115F firmware: boot/kernel, DTBO, vendor, and every non-system logical partition needed by the target layout, including ODM and any vendor/ODM/system DLKM partitions that the target `super` actually contains. Do not transplant A05s vendor, kernel, DTBO, modem, PIT, or EFS to the A11.

The A05s page from Samsung identifies a Snapdragon 680 processor, whereas this repository's A115F config describes the target as Snapdragon 450/Adreno 506. They are different hardware platforms, so “porting the full vendor” means adapting and validating the A115F vendor stack against the donor framework—not replacing it with A05s drivers. Android documents VINTF manifests as the device's supplied interfaces and framework compatibility matrices as the framework's requirements; those must be reconciled rather than inferred from file presence ([Android VINTF documentation](https://source.android.com/docs/core/architecture/vintf), [Samsung Galaxy A05s specifications](https://www.samsung.com/ph/smartphones/galaxy-a/galaxy-a05s-light-green-128gb-sm-a057flggphl/)).

## Build gates

1. Verify the device's exact target CSC/build and obtain the matching official A115F package. Record its archive and Odin payload hashes.
2. Extract the A115F super inventory, vendor-side partition trees, `fs_config`/`file_context`, boot and DTBO. The new firmware-layout check must confirm the configured super group/size, every target-side logical partition, a target VINTF manifest, and a declared Keymaster/KeyMint HAL.
3. Compare the Android 15 framework compatibility requirements against the A115F vendor manifest/services and review fstab, encryption, Keymaster/TEE and SELinux. Passing inventory checks alone does not prove compatibility.
4. Package every target-side partition listed by the target `super` metadata, while replacing only the donor system/product components and applying the configured `system_ext` merge. The ZIP validator must reject missing target partition payloads or a group-size mismatch.
5. Build and statically validate the ZIP, then test it only on the exact SM-A115F with a recoverable stock path. Boot-animation success requires a real device observation and logs; a generated ZIP is not evidence of boot success.

The current local environment is not at those gates. No firmware download, ROM build, or device flash was performed in this continuation.
