# ملاحظات تعطل استيراد firmware لـA115F

## نتيجة أول تشغيل للـworkflow

في GitHub Actions run `40117738481` نجح تنزيل واستخراج firmware المانح A05s، بما في ذلك `system` و`product` و`system_ext`. ثم توقف استيراد target A115F قبل استخراج أقسامه: حاول importer طلب `SM-A115F/INS` من Samsung FUS، وأعادت أداة Samloader-rs الخطأ `Info request invalid`، ثم انتهى الـjob برمز 101.[1] لم يبدأ `make_rom.sh`، ولم يُنشأ ZIP، ولم يحدث اختبار إقلاع.

كشف التدقيق أن `scripts/import_samfw_firmware.sh` كان يثبت `TARGET_CSC="INS"` داخليًا بدل قراءة `TARGET_FIRMWARE` من إعداد الهدف؛ لذلك كان يتجاهل قيمة CSC الموجودة في config. أُزيل هذا التجاوز: importer يقرأ الموديل والمنطقة وAP من `TARGET_FIRMWARE`، ثم يتحقق من تطابق الموديل مع `TARGET_ASSERT_MODEL` وتطابق AP مع tuple المثبت.

## تحقق metadata من Samsung FUS

نُزّلت أداة Samloader-rs 2.2.0 بالـSHA-256 المثبت نفسه في workflow. استعلام `check-update` لا ينزّل firmware، وأعطى النتيجتين التاليتين:

- `SM-A115F/INS`: فشل Samloader في تحليل `history.xml`؛ لا يثبت هذا وحده أن firmware غير موجود.
- `SM-A115F/MWD`: أعاد من FUS tuple كاملًا يطابق الإعداد حرفيًا: `A115FXXS6CWK2/A115FOJM6CWK1/A115FXXS6CWK1/A115FXXS6CWK2`.[2]

لذلك يستخدم config الآن MWD **كمنطقة مصدر لتنزيل حزمة A115F فقط**. سجلات الهاتف ما زالت تسجل sales code `INS`؛ لن تتغير قيمة الهاتف ولن يُفلش ملف CSC الخاص بـMWD. لا يزال تنزيل الحزمة الكاملة، فحص محتوياتها وMD5، واستخراج أقسام target مطلوبة لإثبات أن المصدر صالح فعليًا.

يعرض SamFrew إصدار `A115FXXS6CWK2` ضمن MWD مع CSC `A115FOJM6CWK1`، بينما تعرض صفحة SamFW الإقليم PNG للإصدار نفسه لكن CSC مختلفًا `A115FPNG6CWK1`.[3][4] هذه فهارس طرف ثالث؛ اعتمد اختيار MWD على استجابة FUS metadata المطابقة، لا على أسماء المناطق وحدها.

الـfeeds العامة `version.xml` لـFUS أعادت HTTP 403 من Akamai لهذه البيئة في محاولات INS وMWD وPNG وEGY.[5][6][7][8] هذا الحجب لا يدل على عدم وجود firmware؛ اختبار `check-update` عبر Samloader-rs هو الذي أعطى نتيجة MWD أعلاه.

## ما بقي قبل اختبار الإقلاع

يلزم تشغيل workflow بعد التعديل ليتحقق من تنزيل archive من MWD، ومطابقة AP/CSC/CP/BL والـOdin MD5، واستخراج كل target-side partitions مع boot/DTBO، ثم تمرير firmware-layout validator. بعد ذلك فقط يمكن بناء ZIP وتشغيل ZIP validator. لا توجد حتى الآن حزمة ZIP أو نتيجة اختبار على الهاتف، ولا يوجد ادعاء بأن الروم وصل للـboot animation.

## المراجع

[1]: https://github.com/nova-arch008/ZineROM-a11q/actions/runs/40117738481 "سجل أول بناء A115F الفاشل عند FUS"
[2]: https://github.com/topjohnwu/samloader-rs/releases/tag/2.2.0 "Samloader-rs 2.2.0 المستخدم لاستعلام FUS"
[3]: https://samfrew.com/download/Galaxy__A11____/6nm4/MWD/A115FXXS6CWK2/A115FOJM6CWK1 "فهرس firmware SM-A115F لمنطقة MWD"
[4]: https://samfw.com/firmware/SM-A115F/PNG/A115FXXS6CWK2 "فهرس firmware SM-A115F لمنطقة PNG"
[5]: https://fota-cloud-dn.ospserver.net/firmware/INS/SM-A115F/version.xml "Samsung FUS version feed لـINS"
[6]: https://fota-cloud-dn.ospserver.net/firmware/MWD/SM-A115F/version.xml "Samsung FUS version feed لـMWD"
[7]: https://fota-cloud-dn.ospserver.net/firmware/PNG/SM-A115F/version.xml "Samsung FUS version feed لـPNG"
[8]: https://fota-cloud-dn.ospserver.net/firmware/EGY/SM-A115F/version.xml "Samsung FUS version feed لـEGY"
