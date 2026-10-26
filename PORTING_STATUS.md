# حالة مشروع One UI 7 على Galaxy A11 (SM-A115F)

**آخر تحديث:** 2026-10-26، 13:10 +03:00
**الفرع البعيد:** `manus/a115f-vendor-fingerprint`
**نسخة المصدر التي بُنيت واختُبرت في CI:** `190586c39cd86057887d7ae84a4631761ace7c54`
**الجهاز المستهدف:** Samsung Galaxy A11 `SM-A115F`، Snapdragon 450، Binary 6 فقط (`A115FXXS6CWK2`)
**النظام الأساسي:** Android 12 / One UI 4 Core vendor؛ المانح SM-A057F / One UI 7 / Android 15.

## الخلاصة التنفيذية

اكتمل تدقيق ساكن من سبعة مجالات مستقلة، وبُنيت نسخة المصدر الموجودة على commit `190586c` بنجاح في GitHub Actions. نجحت اختبارات المشروع الـ60، واكتمل بناء ROM، واجتاز ZIP فحوص البنية وحارس الطراز والـ bootloader وسعة dynamic partitions.

هذا **لا يثبت أن الروم وصل إلى الشعار أو Setup Wizard**. لكن أحدث المرفقات تتضمن سجل محاولة Android (`androidboot.boot_recovery=0`) ثم فشل `enablefilecrypto`/`K00R` وإعادة تشغيل init إلى Recovery. لا يظهر فيه هل `wait_for_keymaster` نُفّذ، ولا SHA-256 للحزمة المجربة.

**لم تُفلش أي أجهزة، ولم يُنشر Release جديد، ولم تُجرَ تغييرات مدمرة.** التعليمات الأخيرة تشترط موافقة صريحة قبل أي نشر أو إجراء تدميري؛ لذلك لم أستبدل ملف الـ Release العام بحزمة CI الأحدث.

## مؤشرات التقدم المبنية على الأدلة

- **تغطية التدقيق الساكن:** 7 من 7 مجالات مخططة = **100% من نطاق التدقيق الذي أُجري**؛ لا يعني ذلك اكتمال كل توافقات التشغيل.
- **اختبارات وبناء commit `190586c`:** **نجاح CI**؛ 60/60 اختبارًا، بناء كامل، وفحوص ZIP ناجحة.
- **مرحلة التشغيل المثبتة:** سجل Android يصل إلى محاولة تهيئة FBE ثم يعيد التشغيل إلى Recovery؛ لم يثبت الوصول إلى شعار Samsung أو Boot Animation أو Setup Wizard. لا يمكن ربطه بعد بـ ZIP محدد.
- **تقييم الجاهزية لأول إقلاع:** لا يمكن استخراج نسبة احتمال موثوقة من السجل. السبب المباشر المسجل للعودة إلى Recovery هو FBE `K00R`، مع QSEE SCM failures سابقة؛ هوية الحزمة ونتيجة helper لا تزالان مجهولتين.

## أحدث المرفقات: ما تثبته وما لا تثبته

1. `pasted_content.txt` سجل TWRP ويعرض Android Rescue Party reason `--reason=enablefilecrypto_failedK00R`؛ ليس مجرد تعليمات.
2. `pasted_content_2.txt` السابق كان سجل Recovery، لكن المرفق الأحدث بتاريخ 2026-10-26 (1,609 سطرًا) هو سجل kernel/init من محاولة Android: command line يحتوي `androidboot.boot_recovery=0` للطراز `SM-A115F` والـ bootloader `A115FXXS6CWK2`.
3. التسلسل الأحدث يسجل عدة إخفاقات `qseecomd` بـ `scm_call` function `0x72000206` قرب 12.66–12.69 ثانية؛ ثم `security.fbe.fail_cause ... K00R` قرب 13.27 ثانية، وفشل `cryptfs enablefilecrypto` قرب 13.81 ثانية. عند 14.23 ثانية يعيد init تشغيل الجهاز إلى Recovery. لا يظهر panic صريح في نهاية الالتقاط.
4. سجل TWRP اللاحق (`pasted_content.txt`) يعرض Android Rescue Party reason `--reason=enablefilecrypto_failedK00R`، بما يتوافق مع فشل FBE المسجل أثناء محاولة Android.
5. لا يظهر نص `wait_for_keymaster` أو `exec_start` في السجل المتاح؛ لذلك لا يمكن تأكيد أن حاجز الترتيب نُفذ أو أن helper نجح. كما لا يوجد اسم/ SHA-256 للحزمة التي أنتجت السجل، فلا يمكن ربطه قطعًا بـ Release أو CI artifact.

**الاستنتاج:** لدينا الآن دليل على أن محاولة Android بدأت ووصلت لمسار Keymaster/FBE ثم أعادت التشغيل إلى Recovery بسبب فشل تهيئة file-based encryption. إخفاق QSEE يسبق ذلك زمنيًا، لكنه وحده لا يثبت السبب الجذري الكامل. يلزم ربط السجل بـ ZIP محدد ومعرفة نتيجة helper قبل اختيار تعديل جديد.

## نتائج تدقيق المكونات السبعة

| المجال | ما تم التحقق منه | ما يزال غير محسوم |
|---|---|---|
| Kernel / boot / DTB / DTBO | الحزمة مبنية على مدخلات boot المستهدفة لـ A115F؛ مقارنة kernel وramdisk المعبّأين مع stock موثقة في التدقيق. النواة المستعملة stock A115F وليست kernel مخصصًا جرى بناؤه لهذا المشروع. | لم يُفك DTB/DTBO ويُتحقق مستقلًا من جدول overlays واختيار اللوحة لهذه الحزمة على الجهاز. لا يوجد boot test مطابق لـ SHA الحالي. donor A057F يستخدم boot-image layout أحدث، ولذلك لا ينبغي استبدال صور boot المستهدفة بصور المانح. |
| Partition map / updater / fstab | قيمة super الفيزيائية في الإعدادات `4,324,327,424` بايت، ومجموعة `qti_dynamic_partitions` حدها `4,320,133,120` بايت. يذكر CI أن payload المجموعة `4,055,482,368` بايت، ضمن الحد. الـ updater يحرس `SM-A115F` و`A115FXXS6CWK2` ولا يحتوي أمر format data بحسب الفاحص. | الـ updater يعيد تكوين logical-partition metadata داخل super؛ قبول recovery الفعلي ومسارات by-name وخصائص recovery لم تُختبر على الجهاز. لا تغيّر PIT أو الأقسام الفيزيائية. |
| Firmware / image assembly | الإعداد يثبت tuple هدف A115F `A115FXXS6CWK2/A115FOJM6CWK1/A115FXXS6CWK1/A115FXXS6CWK2`، ويبني system/vendor/product/odm مع ملفات boot المستهدفة. CI أنشأ ZIP صالحًا. | لا يوجد في التقرير hash موثّق لملف firmware archive الأصلي يربطه تشفيريًا بكل ملفات الاستخراج. وُجدت ملاحظة استخراجية: ملف `system_ext/etc/aconfig_flags.pb` لدى المانح حجمه صفر وبعض أدلة fs_config فارغة؛ target يدمج system_ext مع system، لذا هذه ملاحظة تحتاج متابعة وليست عطلًا مثبتًا. |
| HAL / VINTF / ABI / FBE | vendor الهدف من جيل Android 12: SDK/VNDK 31، ويحتوي Keymaster HIDL 3.0/4.0 بنسخ ARM32. fstab الهدف يضبط `/data` على F2FS و`fileencryption=ice`. تم استيراد helper ومكتبات KeyMint/Keystore2 ذات 32-bit ضمن تشخيص الترتيب. | Android 15 donor أعلى API (35) ويقدم مصفوفات AIDL KeyMint، مقابل HIDL قديم في vendor. وجود المداخل لا يثبت وحده رفض VINTF، لكن لا توجد نتيجة `checkvintf` للمزيج النهائي؛ أداة `checkvintf` غير متاحة في بيئة التدقيق. نجاح QSEE/TEE وإنشاء مفتاح FBE وفتح `/data` غير مثبت. |
| Init / SELinux / permissions | patcher `scripts/patch_a115f_init.py` fail-closed وidempotent، ويُدرج `exec_start wait_for_keymaster` قبل `mount_all ... --late`. ملف workdir السابق أظهر الترتيب والـ helper labels/permissions المنقولة من stock. التغيير موجود في المصدر ودخل بناء commit الحالي. | لا يوجد log من ROM يثبت تنفيذ الخدمة، readiness، السماح عبر SELinux، أو نجاح Keymaster/QSEE؛ ترتيب المصدر لا يساوي نجاح runtime. |
| Build / tests / CI | GitHub Actions run [40233035076](https://github.com/nova-arch008/ZineROM-a11q/actions/runs/40233035076) على SHA `190586c…` انتهى **success**. `Ran 60 tests` ثم `OK`. بناء ROM اكتمل، وفاحص ZIP أكد 22 عنصرًا، حارس `a115f / SM-A115F / A115FXXS6CWK2`، تغطية payload/transfer-list لأقسام odm/product/system/vendor، وسعة المجموعة. SHA-256 لحزمة ROM الناتجة: `18f579c0758134d4e5db6bf81d437f27403f7dcdf9d4586321944dd82993c3e5`. | خطوة fingerprint audit في workflow معلّمة `continue-on-error: true`، لذلك نجاح الـ job وحده لا يجعلها gate إلزامية. فاحص ZIP ساكن ولا يحاكي التفليش أو الإقلاع. لم تُجرَ مقارنة clean repeat-build مضبوطة. |
| Tester bootloop / stage | السجل الأحدث يثبت محاولة Android بـ `boot_recovery=0`، ثم QSEE `0x72000206`، وFBE `K00R`، وفشل `enablefilecrypto`، وبعدها إعادة تشغيل init إلى Recovery. سجل TWRP اللاحق يؤكد Rescue Party بالسبب نفسه. | لا نملك SHA-256/اسم ZIP المجرب، ولا سجل init التفصيلي الذي يثبت تشغيل/نتيجة `wait_for_keymaster`. لا يثبت log وحده أن QSEE هو السبب الجذري الوحيد. |

## التنفيذ المحفوظ في GitHub

التغييرات البرمجية والاختبارات موجودة في الفرع البعيد `manus/a115f-vendor-fingerprint` داخل commit `190586c39cd86057887d7ae84a4631761ace7c54`. شملت: استيراد ملفات Keymaster المطلوبة، إضافة حاجز init قبل mount `/data`، حارس Binary 6 الصارم، validator واختبارات، وربط الفرع ببناء GitHub Actions.

### نتيجة CI وحزمة البناء

- آخر build: [GitHub Actions #40305496330](https://github.com/nova-arch008/ZineROM-a11q/actions/runs/40305496330)، على commit التوثيق `92a0510`؛ job `build (a115f)` انتهى بنجاح.
- أكدت السجلات `Ran 60 tests`, ونجاح فحوص ZIP والـ model/binary guard والتغطية والسعة.
- SHA-256 لملف ROM ZIP الناتج عن هذا الـ run: `e9b2d93c52dd21a25570e712f067692ee97d2e334876236bea258482f7914292`.
- اسم artifact في Actions: `ZineROM_OneUI7_A115F-Port-A057F-8`، بحجم خارجي `1,837,881,180` بايت. هذا الـ Action artifact **ليس Release عامًا** ولم يُختبر على الهاتف.
- الـ Release العام ما زال بالـ SHA-256 `29384d92ba37f6603cf0dfe08eec027e4049e3781414ffc9d197479b3388e2e0`. لم أرفع build 8 إلى Release.

## أكبر الموانع حسب الأولوية

1. **P0 — Keymaster/QSEE/FBE runtime:** أحدث سجل يثبت QSEE SCM errors `0x72000206` تسبق `K00R` وفشل `enablefilecrypto` وإعادة التشغيل إلى Recovery.
2. **P0 — ربط نتيجة التيستر بالحزمة الصحيحة:** لا نملك SHA-256/اسم ZIP الذي أنتج هذا السجل، ولا نعرف هل هو الـ Release العام أو artifact CI.
3. **P1 — التحقق من readiness barrier:** لم يظهر trace واضح لـ `wait_for_keymaster`/`exec_start`؛ نحتاج سجل init/logcat للمحاولة نفسها.
4. **P1 — VINTF/runtime security:** لا يوجد `checkvintf` للمزيج النهائي، ولا دليل على نجاح إنشاء مفتاح FBE رغم ظهور فشل QSEE/Keystore2.
5. **P1 — مخاطرة recovery/super:** إعادة كتابة dynamic-partition metadata مرتبة ساكنًا لكنها غير مختبرة على recovery الجهاز؛ لا PIT ولا تغييرات فيزيائية مسموحة.
6. **P2 — سلامة provenance/reproducibility:** أضف لاحقًا hash SHA-256 موثقًا لملف firmware archive وسجل build provenance؛ MD5 الداخلي في Samsung/Odin مفيد لاكتشاف التلف لكنه ليس إثبات provenance تشفيريًا قويًا.

## خطة العمل المرتبة

1. **تثبيت هوية التجربة:** احصل على اسم ZIP وSHA-256، وطابقه مع الـ Release العام (`29384d…`) أو artifact CI الأحدث (`e9b2d93c…` حسب سجل البناء).
2. **تحليل المسار دون لمس البيانات:** احتفظ بسجل Android الحالي منفصلًا عن سجل TWRP؛ لا تمسح `/data` ولا تعِد تقسيم الجهاز.
3. **فحص المصدر قبل أي patch:** تحقق من تعريف helper وإطلاقه ونتيجته، وخدمة Keymaster HIDL مقابل Keystore2، وسياسة SELinux، وQSEE/TA وsecure storage؛ لا تعدل FBE أو fstab تخمينًا.
4. **الدليل الناقص:** عند توفر ADB أثناء محاولة ROM، اجمع logcat/getprop قبل أن يعيد التشغيل؛ وإلا استخدم pstore/last_kmsg، واربطها بـ SHA ZIP المحدد.
5. **اختبار عتادي مشروط:** يلزم موافقتك المنفصلة ومسار استعادة stock مؤكد، وعلى SM-A115F Binary 6 فقط. لا format data ولا PIT/bootloader/modem ولا تعطيل دائم لـ FBE.
6. **Release:** لا تحديث أو نشر للحزمة الناتجة عن CI دون موافقتك الصريحة، ثم لا تُنشر إلا بعد إعادة التحقق من ZIP والحارس والـ SHA.

## المطلوب من الجهاز/التيستر

- SHA-256 واسم ZIP الذي تم تفليشه، ورقم build/التاريخ.
- هل Recovery فُتح يدويًا أم عاد إليه الهاتف تلقائيًا؟ وما آخر شاشة ظهرت: Samsung logo، Boot Animation، Setup Wizard، أم Recovery؟
- إن ظهر ADB أثناء محاولة ROM: `adb logcat -b all -v threadtime -d` و`getprop` و`dmesg`.
- إن لم يظهر ADB: من Recovery، وقبل أي مسح/تفليش، اجمع `/sys/fs/pstore/*` و`/proc/last_kmsg` و`/cache/recovery/last_log` و`last_install`، إضافة إلى Recovery `dmesg` و`logcat`.
- لا ترسل EFS/modem backups أو بيانات شخصية. لا تنفذ مسحًا أو تغييرًا فيزيائيًا بناءً على سجل Recovery الحالي.

## مصادر داخل المستودع

- `target/a115f/config.sh`
- `target/a115f/patches/miscs/customize.sh`
- `scripts/patch_a115f_init.py`
- `scripts/validate_a115f_zip.py`
- `scripts/validate_a115f_firmware_layout.py`
- `target/a115f/FLASHING_A115F.md`
- `target/a115f/BOOT_LOGGING.md`
- `target/a115f/BOOT_PROGRESS.md` (ملاحظات تاريخية؛ هذا الملف هو ملخص الحالة الأحدث)
