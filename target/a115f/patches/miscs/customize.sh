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

LOG "A115F boot-first patch stage: no extra blobs or properties applied"
