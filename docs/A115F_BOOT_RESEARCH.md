# تدقيق إقلاع ZineROM لـGalaxy A11 SM-A115F

الحالة في 2026-10-25: هذا عمل تشخيصي خاص، وليس إصدار ROM صالحًا للتفليش بعد.

## ما تم حفظه على GitHub

المستودع الخاص: `nova-arch008/ZineROM-a11q`، فرع العمل: `manus/a115f-vendor-fingerprint`.

- commit `71c59c21`: وسّع تدقيق firmware ليبحث بشكل recursive عن خصائص VNDK وملفات APEX، وأتاح تشغيل `audit_only` دون بناء ROM.
- commit `a80a2ffb`: فصل إعداد بصمة donor عن إعداد هدف A115F وأدخل اختبار regression.
- اختبارات Python الحالية و`bash -n` و`git diff --check` نجحت محليًا.

نجح تشغيل التشخيص الخاص رقم [40132773279](https://github.com/nova-arch008/ZineROM-a11q/actions/runs/40132773279). هذا التشغيل نزّل firmware وفكّه وفحصه؛ وتخطى صراحةً خطوات بناء ROM والتحقق من ZIP والرفع.

## البصمة

وجد الفحص في DEX الخاص بـ`framework.jar` من donor Galaxy A05s القيمة `google_touch_side,settings=3`. ملف A115F يحدد `rear,settings=0`. وكان config المصدر العام يصرّح خطأً عن `rear,settings=0` أيضًا، ولذلك لم يكن patch الحالي يرى اختلافًا بين نوع المستشعرين ولا يشغّل مسار التحويل.

تم تعديل `unica/configs/qssi.sh` إلى `SOURCE_FP_SENSOR_CONFIG="google_touch_side,settings=3"` مع الإبقاء على `TARGET_FP_SENSOR_CONFIG="rear,settings=0"` في ملف A115F. بذلك يستطيع patch استبدال إعداد donor side بإعداد الهدف rear في framework. كما كشف vendor الرسمي لـA115F خدمات fingerprint في VINTF/init ومكونات Egistec وFocaltech وSilead. هذه أدلة على وجود تكامل vendor قابل للفحص، وليست إثباتًا بأن البصمة ستعمل في ROM قبل بناء ناجح واختبار الجهاز.

## العائق الحالي: VNDK

يعلن `vendor/build.prop` الرسمي لـA115F `ro.vndk.version=31`، لكن شجرة firmware المستخرجة لا تحتوي ملفًا من نوع `com.android.vndk*.apex`. بالمقابل يحتوي donor A05s على `system_ext/apex/com.android.vndk.v33.apex`. شرط البناء في target patch يرفض الاستبدال عندما لا يوجد APEX v31، وقد أظهر التشغيل السابق فشلًا عند هذا التحقق.

توثيق AOSP يبين أن VNDK APEX يركب باسم `com.android.vndk.v${ro.vndk.version}` وأن إصدار المكتبات يتبع قيمة الخاصية [1]. ولدى AOSP تعريف بناء وsnapshot مفتوحان لـVNDK31 على Android 12 QPR3 [2] [3]؛ لكن لم يُنشأ APEX منها بعد. لا نعيد تسمية v33 إلى v31، ولا نغير قيمة vendor إلى 33، لأن ذلك لا يضمن توافق ABI وقد يجعل سبب الفشل أصعب في التشخيص.

## الحالة والخطوة التالية

لم يُنجز حتى الآن بناء ROM كامل بعد إصلاح إعداد بصمة المصدر، ولم يُنتج أو يُرفع ZIP جديد، ولم يتم اختبار الإقلاع أو البصمة على الهاتف. الخطوة السابقة لأي إعادة بناء هي إعداد VNDK31 صحيح من مصدر AOSP والتحقق من payload/manifest/signing/paths، أو إثبات مصدر آخر متوافق؛ بعد ذلك يعاد البناء على فرع خاص، مع حفظ logs، ومن دون نشر ZIP عام قبل نجاح التحقق والاختبار.

## المصادر

[1]: https://source.android.com/docs/core/architecture/vndk "Android VNDK overview and VNDK APEX versioning"
[2]: https://android.googlesource.com/platform/packages/modules/vndk/+/refs/heads/android12-qpr3-release/apex/Android.bp "AOSP Android 12 QPR3 VNDK APEX build definition"
[3]: https://android.googlesource.com/platform/prebuilts/vndk/v31/+/refs/heads/android12-qpr3-release/ "AOSP Android 12 QPR3 VNDK31 snapshot"
[4]: https://android.googlesource.com/platform/build/soong/+/refs/heads/android12-qpr3-release/apex/vndk.go "AOSP Soong implementation for VNDK APEX"
