# One UI 7 boot port — Samsung Galaxy A11 SM-A115F

This branch is intended for an experimental One UI 7 / Android 15 port for `SM-A115F` only. The requested milestone is to reach the boot animation and remain there without a bootloop; this is not a claim of a stable ROM or complete device support.

## Actual local state

The current local workspace contains no extracted firmware or flashable ZIP. CI run `40120489519` did download the exact A115F target package, verify all five embedded Odin MD5 trailers, extract the configured target vendor-side partitions and pass the firmware-layout gate. The generated files were temporary runner data and are no longer in this checkout.

The supplied device logs report sales code `INS`, but the first CI attempt showed that the importer hardcoded an INS FUS lookup and Samloader could not parse its history response. A metadata-only Samloader-rs 2.2.0 query for `SM-A115F/MWD` returned the exact pinned tuple `A115FXXS6CWK2/A115FOJM6CWK1/A115FXXS6CWK1/A115FXXS6CWK2`; CI subsequently downloaded and validated that target package. MWD is only the source region; it does not change the phone sales code, and no MWD CSC tar is flashed.

## Correct hardware/framework split

The intended split is A05s One UI 7 system/product as a framework donor, with **all A115F hardware-facing files** coming from the exact SM-A115F firmware: boot/kernel, DTBO, vendor, and every non-donor logical partition needed by the target layout, including ODM and any vendor/ODM/system DLKM partitions actually listed by `super`. The A115F `system` partition is also extracted as a source-only input for selected stock blobs; it is not flashed as the donor system. Do not transplant A05s vendor, kernel, DTBO, modem, PIT, or EFS to the A11.

The A05s page from Samsung identifies a Snapdragon 680 processor, whereas this repository's A115F config describes the target as Snapdragon 450/Adreno 506. They are different hardware platforms, so “porting the full vendor” means adapting and validating the A115F vendor stack against the donor framework—not replacing it with A05s drivers. Android documents VINTF manifests as the device's supplied interfaces and framework compatibility matrices as the framework's requirements; those must be reconciled rather than inferred from file presence ([Android VINTF documentation](https://source.android.com/docs/core/architecture/vintf), [Samsung Galaxy A05s specifications](https://www.samsung.com/ph/smartphones/galaxy-a/galaxy-a05s-light-green-128gb-sm-a057flggphl/)).

## Build gates

1. Confirm the physical device is `SM-A115F` and record its sales code/build. Retrieve the A115F package through MWD only because FUS metadata resolves there to the exact pinned AP/CSC/CP/BL tuple; do not flash the regional CSC tar. Record archive and Odin payload hashes.
2. Extract the A115F super inventory, source-only target `system`, vendor-side partition trees, `fs_config`/`file_context`, boot and DTBO. The firmware-layout check confirms the configured super group/size, every target-side logical partition, a target VINTF manifest, and a declared Keymaster/KeyMint HAL.
3. Compare the Android 15 framework compatibility requirements against the A115F vendor manifest/services and review fstab, encryption, Keymaster/TEE and SELinux. Passing inventory checks alone does not prove compatibility.
4. Package every target-side partition listed by the target `super` metadata, while replacing only the donor system/product components and applying the configured `system_ext` merge. The ZIP validator must reject missing target partition payloads or a group-size mismatch.
5. Build and statically validate the ZIP, then test it only on the exact SM-A115F with a recoverable stock path. Boot-animation success requires a real device observation and logs; a generated ZIP is not evidence of boot success.

The first remote workflow failed before importing target firmware because the importer hardcoded INS. Run `40120489519` later downloaded/validated the exact A115F package and passed the target firmware-layout gate, but ROM assembly stopped because target `system` had not been extracted for the shared stock-blob patch. The current change adds that extraction and guards optional SAIV copying; a fresh CI run is required. No ROM ZIP has been built, and no device flash or boot test has occurred.
