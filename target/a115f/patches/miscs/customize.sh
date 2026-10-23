# Boot-first target cleanup. The current A11 stock extraction contains an empty
# directory literally named `""` under /vendor/lib with no fs_config or SELinux
# context entry; e2fsdroid cannot label it when assembling vendor.img. Remove only
# this empty directory from the generated work tree, never from extracted firmware.
A11_QUOTED_VENDOR_DIR="$WORK_DIR/vendor/lib/\"\""
if [ -d "$A11_QUOTED_VENDOR_DIR" ] && [ ! -L "$A11_QUOTED_VENDOR_DIR" ] \
    && [ -z "$(find "$A11_QUOTED_VENDOR_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    LOG "Removing empty malformed target artifact /vendor/lib/\"\""
    DELETE_FROM_WORK_DIR "vendor" 'lib/""'
elif [ -e "$A11_QUOTED_VENDOR_DIR" ] || [ -L "$A11_QUOTED_VENDOR_DIR" ]; then
    LOGW "Preserving unexpected or non-empty target path /vendor/lib/\"\""
fi

SYSTEM_EXT_MAPPING="$WORK_DIR/system/system/system_ext/etc/selinux/mapping/31.0.cil"
if [ -f "$SYSTEM_EXT_MAPPING" ]; then
    for A11_POLICY_ATTR in perf_prop_31_0 qb_id_prop_31_0; do
        if grep -Fq "(expandtypeattribute ($A11_POLICY_ATTR) true)" "$SYSTEM_EXT_MAPPING" \
            && grep -Fq "(typeattributeset $A11_POLICY_ATTR (" "$SYSTEM_EXT_MAPPING" \
            && ! grep -Eq "^\(typeattribute[[:space:]]+$A11_POLICY_ATTR\)$" "$SYSTEM_EXT_MAPPING"; then
            sed -i "0,/^(expandtypeattribute /s//(typeattribute $A11_POLICY_ATTR)\\n&/" "$SYSTEM_EXT_MAPPING"
            LOG "Added missing compatibility typeattribute $A11_POLICY_ATTR to system_ext policy mapping"
        fi
    done
fi

LOG "A115F boot-first patch stage: no extra blobs or properties applied"
