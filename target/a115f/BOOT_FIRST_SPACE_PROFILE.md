# A115F boot-first space profile

The A115F recovery reports a physical `super` size of 4,324,327,424 bytes, while both stock logical-partition metadata slots advertise 4,399,824,896 bytes. The recovery's dynamic-partition updater rejects this 72 MiB geometry mismatch. The port must not try to enlarge `super`, flash a PIT, or rewrite that metadata blindly.

The boot-first installer keeps the stock logical partition extents and skips `update_dynamic_partitions`. It first preflights that all existing logical partitions can be mapped, then writes only images that fit within the verified stock extents: system 3,315,875,840 bytes, vendor 575,578,112 bytes, product 397,549,568 bytes, and odm 4,349,952 bytes. The builder aborts if any image exceeds its configured extent.

`unica/mods/zz_a115f_boot_fit` runs last and only for target codename `a115f`. In addition to the existing optional-app trim, this boot-first profile temporarily removes product `GmsCore` so the product image fits its current 397,549,568-byte extent. A trial ext4 image without GmsCore is 312,815,616 bytes, leaving about 81 MiB. SystemUI, launcher, keyboard, Settings, telephony, and the core framework remain. Google Play Services is intentionally absent in this first-boot test package and may be revisited after a successful boot.

This is not a repartitioner. The installer does not alter the partition table, super size, PIT, or logical-partition metadata. If any mapped partition cannot be opened in recovery, the installer must stop before writing images. Do not flash a repartitioner intended for another device.
