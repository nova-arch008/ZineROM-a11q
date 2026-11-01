# ملاحظات تعطل استيراد وبناء firmware لـA115F

## 1. فشل FUS الأول وإصلاح مصدر التنزيل

في أول GitHub Actions run (`40117738481`) نجح تنزيل واستخراج firmware المانح A05s، ثم حاول importer طلب `SM-A115F/INS` من Samsung FUS. أعادت أداة Samloader-rs الخطأ `Info request invalid` ولم يبدأ `make_rom.sh`.

كان `scripts/import_samfw_firmware.sh` يثبت `TARGET_CSC="INS"` بدل قراءة إعداد target. أُزيل hardcode وصار importer يقرأ الموديل والمنطقة وAP من `TARGET_FIRMWARE` ويتحقق من تطابقه مع `TARGET_ASSERT_MODEL` والـtuple الكامل.

استعلام metadata-only عبر Samloader-rs 2.2.0 أعاد من `SM-A115F/MWD` الـtuple التالي المطابق للإعداد:

`A115FXXS6CWK2/A115FOJM6CWK1/A115FXXS6CWK1/A115FXXS6CWK2`

تُستخدم MWD فقط كمصدر لتنزيل حزمة SM-A115F المطابقة. سجلات الهاتف تبقى INS ولا يجري تفليش CSC الخاص بـMWD.

## 2. نتيجة استيراد A115F وفشل بناء ROM

في CI run `40120489519`:

- نُزّلت حزمة A115F من MWD، وطابقت أسماء payloads مكونات AP/CSC/CP/BL المثبتة.
- تحقق embedded MD5 لخمسة ملفات Odin: AP وBL وCP وCSC وHOME_CSC.
- استُخرجت صور kernel/DTBO وvendor/ODM وDLKM المطلوبة؛ اجتاز `validate_a115f_firmware_layout.py` فحص الحجم الفيزيائي لـ`super`، المجموعة، partition inventory، manifests وخدمات Keymaster/KeyMint وFBE declarations.
- بدأ `make_rom.sh` لكنه توقف في `unica/patches/stock_blobs/customize.sh` عند نسخ `system/saiv`، برسالة: `File not found: out/fw/SM-A115F_MWD/system/saiv`.

### السبب والإصلاح

كان importer يطلب من `extract_fw.sh` أقسام `odm` وDLKM و`vendor` فقط للهدف، بينما patch العام `stock_blobs` يستخدم أيضًا شجرة `system` الأصلية كمصدر لملفات stock. لا يعني هذا أن `system/saiv` غير موجود في firmware نفسه؛ كانت صورة target `system` ببساطة غير مستخرجة.

الإصلاح الحالي:

1. إضافة `system.img` إلى قائمة استخراج target، واعتبار `system` و`vendor` مخرجات مطلوبة مع ملفات `fs_config` و`file_context`.
2. جعل validator يتطلب شجرة target `system` غير الفارغة وmetadata الخاصة بها، وتشغيل layout validation كاملًا قبل إعادة استخدام cache قديم.
3. جعل استبدال SAIV مشروطًا بوجود `system/saiv` في الشجرة المستخرجة. عند غيابه تُحذف نسخة donor-only ويُسجل التخطي بدل فشل build.
4. إضافة اختبارات regression للحالتين: وجود SAIV الهدف وغيابه.

نجحت **47 وحدة اختبار محلية**، وفحوص Python/Bash و`git diff --check`. هذه فحوص ثابتة وليست ZIP أو إثبات إقلاع. يجب تشغيل Workflow جديد لأن الإضافة إلى target `system` تزيد استهلاك المساحة والوقت، وللتأكد من أن بقية stock-blob patches تكتمل.

## رؤية ملف البناء

المستودع `nova-arch008/ZineROM-a11q` عام. ووفق توثيق GitHub، تنزيل artifacts متاح لمن لديه صلاحية قراءة المستودع؛ لذلك اسم الخطوة “private artifact” وحده لا يجعل الملف خاصًا. عُدّل workflow ليطلب من GitHub قيمة `.private` ويرفع artifact فقط إذا ثبت أن المستودع خاص، مع fail-closed إذا تعذر التحقق. في وضع المستودع الحالي سيُبنى ZIP ويُفحص على runner، لكن لن يُرفع artifact قابل للتنزيل. تغيير خصوصية المستودع أو وضع رابط عام يحتاج قرارًا منفصلًا، ولن يحدث تلقائيًا.

## ما بقي

لا يوجد ZIP flashable ناتج ولا اختبار على الجهاز. بعد CI الجديد، يجب أن ينجح بناء الحزمة ومدقق ZIP أولًا. ثم يلزم اختبار clean flash على جهاز SM-A115F احتياطي أو قابل للاستعادة، وجمع `logcat -b all` و`pstore/last_kmsg` إذا لم يصل إلى boot animation. سبب FBE `K00R` لا يزال غير محسوم؛ اجتياز الفحوص الثابتة لا يثبت توافق Keymaster/TEE أثناء التشغيل.

## المراجع

[1]: https://github.com/nova-arch008/ZineROM-a11q/actions/runs/40117738481 "سجل فشل طلب FUS الأول"
[2]: https://github.com/nova-arch008/ZineROM-a11q/actions/runs/40120489519 "سجل استيراد target وفشل stock_blobs"
[3]: https://github.com/topjohnwu/samloader-rs/releases/tag/2.2.0 "Samloader-rs 2.2.0 المستخدم لاستعلام FUS"
[4]: https://samfrew.com/download/Galaxy__A11____/6nm4/MWD/A115FXXS6CWK2/A115FOJM6CWK1 "فهرس firmware SM-A115F لمنطقة MWD"
[5]: https://samfw.com/firmware/SM-A115F/PNG/A115FXXS6CWK2 "فهرس firmware SM-A115F للإقليم PNG"
[6]: https://docs.github.com/actions/managing-workflow-runs/downloading-workflow-artifacts "GitHub: صلاحية تنزيل workflow artifacts"
[7]: https://docs.github.com/rest/actions/artifacts "GitHub REST API: صلاحية الوصول إلى artifacts"
