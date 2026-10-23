if [ ! -f "$WORK_DIR/system/system/lib64/libbluetooth_jni.so" ]; then
    LOG_STEP_IN "- Extracting libbluetooth_jni.so from com.android.btservices.apex"

    APEX="$WORK_DIR/system/system/apex/com.android.btservices.apex"
    if [ ! -f "$APEX" ]; then
        LOG "- Bluetooth APEX is not present; skipping optional library patch"
        LOG_STEP_OUT
        return 0
    fi

    [ -d "$TMP_DIR" ] && EVAL "rm -rf \"$TMP_DIR\""
    mkdir -p "$TMP_DIR"

    if ! unzip -q -j "$APEX" "apex_payload.img" -d "$TMP_DIR"; then
        LOG "- A73 Bluetooth APEX has no unpackable payload; skipping optional library patch"
        rm -rf "$TMP_DIR"
        LOG_STEP_OUT
        return 0
    fi

    if ! sudo -n true &> /dev/null; then
        LOG "\033[0;33m! Asking user for sudo password\033[0m"
        if ! sudo -v 2> /dev/null; then
            ABORT "Root permissions are required to unpack APEX image"
        fi
    fi

    mkdir -p "$TMP_DIR/tmp_out"
    if ! sudo mount -o ro "$TMP_DIR/apex_payload.img" "$TMP_DIR/tmp_out"; then
        LOG "- Could not mount Bluetooth APEX payload; skipping optional library patch"
        rm -rf "$TMP_DIR"
        LOG_STEP_OUT
        return 0
    fi
    if [ ! -f "$TMP_DIR/tmp_out/lib64/libbluetooth_jni.so" ]; then
        sudo umount "$TMP_DIR/tmp_out" || true
        LOG "- Bluetooth library is absent from A73 APEX; skipping optional patch"
        rm -rf "$TMP_DIR"
        LOG_STEP_OUT
        return 0
    fi
    if ! sudo cat "$TMP_DIR/tmp_out/lib64/libbluetooth_jni.so" > "$WORK_DIR/system/system/lib64/libbluetooth_jni.so"; then
        sudo umount "$TMP_DIR/tmp_out" || true
        rm -rf "$TMP_DIR"
        LOG "- Could not extract Bluetooth library; skipping optional patch"
        LOG_STEP_OUT
        return 0
    fi

    EVAL "sudo umount \"$TMP_DIR/tmp_out\""
    rm -rf "$TMP_DIR"

    SET_METADATA "system" "system/lib64/libbluetooth_jni.so" 0 0 644 "u:object_r:system_lib_file:s0"

    LOG_STEP_OUT
fi

# https://github.com/3arthur6/BluetoothLibraryPatcher/blob/master/hexpatch.sh#L12
if [ "$SOURCE_API_LEVEL" -eq 33 ]; then
    HEX_PATCH "$WORK_DIR/system/system/lib64/libbluetooth_jni.so" \
        "6804003528008052" "2a00001428008052"
elif [ "$SOURCE_API_LEVEL" -eq 34 ]; then
    HEX_PATCH "$WORK_DIR/system/system/lib64/libbluetooth_jni.so" \
        "6804003528008052" "2b00001428008052"
elif [ "$SOURCE_API_LEVEL" -eq 35 ]; then
    HEX_PATCH "$WORK_DIR/system/system/lib64/libbluetooth_jni.so" \
        "480500352800805228" "530100142800805228"
elif [ "$SOURCE_API_LEVEL" -eq 36 ]; then
    HEX_PATCH "$WORK_DIR/system/system/lib64/libbluetooth_jni.so" \
        "00122a0140395f01086b00020054" "00122a0140395f01086bde030014"
fi
