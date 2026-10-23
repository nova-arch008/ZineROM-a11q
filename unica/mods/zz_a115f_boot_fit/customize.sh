# Keep this cleanup last so optional ROM mods cannot re-add removed apps.
# The A115F boot-first profile preserves core UI and framework; GmsCore is
# temporarily omitted so product.img fits the stock product logical partition.
if [ "$TARGET_CODENAME" != "a115f" ]; then
    LOG "Skipping A115F boot-first space profile for $TARGET_CODENAME"
    return 0
fi

LOG "Applying A115F boot-first optional-app trim (no super/PIT resizing)"
while IFS='|' read -r PARTITION RELATIVE_PATH; do
    [ -n "$PARTITION" ] || continue
    ITEM_PATH="$WORK_DIR/$PARTITION/$RELATIVE_PATH"
    if [ -e "$ITEM_PATH" ] || [ -L "$ITEM_PATH" ]; then
        LOG "- Removing optional app /$PARTITION/$RELATIVE_PATH"
        DELETE_FROM_WORK_DIR "$PARTITION" "$RELATIVE_PATH"
    fi
done <<'A115F_BOOT_FIRST_REMOVE_LIST'
product|app/Chrome
product|app/YouTube
product|app/Maps
product|app/Gmail2
product|app/SpeechServicesByGoogle
product|priv-app/AndroidSystemIntelligence
product|priv-app/GoogleRestore
product|priv-app/PrivateComputeServices
product|priv-app/Messages
product|priv-app/Velvet
product|priv-app/Phonesky
product|priv-app/GmsCore
system|system/priv-app/SamsungSmartSuggestions
system|system/priv-app/SamSungCamera
system|system/priv-app/OneDrive_Samsung_v3
system|system/priv-app/AREmoji
system|system/priv-app/TalkbackSE
system|system/priv-app/Routines
system|system/priv-app/SamsungIntelliVoiceServices
system|system/priv-app/SamsungAccount
system|system/app/SmartCapture
system|system/priv-app/SamsungMessages
system|system/priv-app/DressRoom
system|system/priv-app/SamsungContacts
system|system/priv-app/SamsungCloudClient
system|system/priv-app/PhotoEditor_Lite
system|system/app/SmartManager_v6_DeviceSecurity
system|system/priv-app/DynamicLockscreen
system|system/priv-app/CallAssistant
system|system/app/SamsungWeather
system|system/priv-app/Crane
system|system/priv-app/GameHome
system|system/priv-app/SecMyFiles2020
system|system/priv-app/ShareLive
system|system/priv-app/ThemeStore
system|system/app/StickerCenter
system|system/priv-app/GalaxyApps_OPEN
system|system/priv-app/SamsungGallery2018
system|system/app/SamsungTTSVoice_vi_VN_f00
A115F_BOOT_FIRST_REMOVE_LIST

LOG "A115F boot-first space profile applied; GMS core omitted to fit existing product partition"
