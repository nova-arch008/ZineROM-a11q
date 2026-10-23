# A115F boot-first space profile

The official SM-A115F firmware metadata reports a 4,324,327,424-byte `super` partition and a 4,320,133,120-byte `qti_dynamic_partitions` group containing `system`, `vendor`, `product`, and `odm`. The untrimmed A05s donor build required 6,998,220,800 bytes, so the installer correctly refuses to generate a package that cannot fit the target's verified stock layout.

`unica/mods/zz_a115f_boot_fit` runs last and only for target codename `a115f`. It removes optional donor applications to fit the target group without changing the partition table, `super` size, or PIT. It retains the core framework, SystemUI, launcher, keyboard, Settings, telephony, and Google Play Services. Optional apps removed by this first-boot profile can be restored or replaced in a later port iteration after the first boot is confirmed.

The profile is intentionally conservative about device-level partition changes: do not increase `TARGET_SUPER_GROUP_SIZE` beyond the official target metadata and do not flash a repartitioning/PIT package as part of this port.
