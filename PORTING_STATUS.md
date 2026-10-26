# حالة مشروع One UI 7 على Galaxy A11 (SM-A115F)

**آخر تحديث:** 2026-10-26، 13:10 +03:00
**الفرع البعيد:** `manus/a115f-vendor-fingerprint`
**نسخة المصدر التي بُنيت واختُبرت في CI:** `190586c39cd86057887d7ae84a4631761ace7c54`
**الجهاز المستهدف:** Samsung Galaxy A11 `SM-A115F`، Snapdragon 450، Binary 6 فقط (`A115FXXS6CWK2`)
**النظام الأساسي:** Android 12 / One UI 4 Core vendor؛ المانح SM-A057F / One UI 7 / Android 15.

## الخلاصة التنفيذية

اكتمل تدقيق ساكن من سبعة مجالات مستقلة، وبُنيت نسخة المصدر الموجودة على commit `190586c` بنجاح في GitHub Actions. نجحت اختبارات المشروع الـ60، واكتمل بناء ROM، واجتاز ZIP فحوص البنية وحارس الطراز والـ bootloader وسعة dynamic partitions.

هذا **لا يثبت أن الروم أقلع على الهاتف**. المرفق الأخير ليس سجل محاولة ROM: الملف الأول تعليمات تدقيق، والثاني سجل kernel أثناء Recovery كما يثبت `androidboot.boot_recovery=1`. لا يتضمن المرفق الثاني سجل `logcat` من Android، ولا يثبت أن حاجز Keymaster نُفّذ في محاولة الإقلاع، ولا يحدد سبب bootloop الروم.

**لم تُفلش أي أجهزة، ولم يُنشر Release جديد، ولم تُجرَ تغييرات مدمرة.** التعليمات الأخيرة تشترط موافقة صريحة قبل أي نشر أو إجراء تدميري؛ لذلك لم أستبدل ملف الـ Release العام بحزمة CI الأحدث.

## مؤشرات التقدم المبنية على الأدلة

- **تغطية التدقيق الساكن:** 7 من 7 مجالات مخططة = **100% من نطاق التدقيق الذي أُجري**؛ لا يعني ذلك اكتمال كل توافقات التشغيل.
- **اختبارات وبناء commit `190586c`:** **نجاح CI**؛ 60/60 اختبارًا، بناء كامل، وفحوص ZIP ناجحة.
- **إثبات الإقلاع على الجهاز لهذا الـ ZIP:** **0 من 3 مراحل تشغيل مؤكدة** (شعار الجهاز، Boot Animation، Setup Wizard). هذا عدّ للأدلة المتوفرة، **وليس احتمالًا مقدرًا لنجاح الروم**.
- **تقييم الجاهزية لأول إقلاع:** غير قابل للتقدير كنسبة احتمالية قبل ربط SHA-256 لحزمة مختبرة بسجل محاولة ROM حقيقي. لا يوجد حتى الآن إثبات أن النسخة الحالية وصلت للشعار أو Setup Wizard.

## أحدث المرفقات: ما تثبته وما لا تثبته

1. `pasted_content.txt` مكوّن من تعليمات لإجراء التدقيق الشامل؛ **ليس سجل جهاز**.
2. `pasted_content_2.txt` سجل kernel/init بطول 1,577 سطرًا. يحتوي سطر kernel command line على `androidboot.boot_recovery=1`، ويذكر init أن first-stage mount تم تخطيه بسبب Recovery، ثم يصل إلى second-stage init. ينتهي عند نحو 23.27 ثانية من وقت kernel من دون panic/reboot cause ظاهر.
3. يظهر في سجل Recovery خطأ `scm_call` بالمعرّف `0x42000c16` مع فشل إسناد ذاكرة (`hyp_assign_phys`, `-5`) ورسائل QSEECOM. هذه ملاحظات من سياق Recovery، ولا تثبت أنها سبب فشل ROM. وهي مختلفة عن المعرّف `0x72000206` الذي ورد في سجل أقدم، ولا يجوز دمجها كأنها الخطأ نفسه.
4. لا يظهر في هذه المرفقات `wait_for_keymaster` أو `exec_start` أو `vold` أو `K00R` أو فشل `enablefilecrypto` أو سجل Android userspace يحدد أول fatal error. لذلك نتيجة محاولة ROM الأخيرة غير محسومة من المرفقات الحالية.

## نتائج تدقيق المكونات السبعة

| المجال | ما تم التحقق منه | ما يزال غير محسوم |
|---|---|---|
| Kernel / boot / DTB / DTBO | الحزمة مبنية على مدخلات boot المستهدفة لـ A115F؛ مقارنة kernel وramdisk المعبّأين مع stock موثقة في التدقيق. النواة المستعملة stock A115F وليست kernel مخصصًا جرى بناؤه لهذا المشروع. | لم يُفك DTB/DTBO ويُتحقق مستقلًا من جدول overlays واختيار اللوحة لهذه الحزمة على الجهاز. لا يوجد boot test مطابق لـ SHA الحالي. donor A057F يستخدم boot-image layout أحدث، ولذلك لا ينبغي استبدال صور boot المستهدفة بصور المانح. |
| Partition map / updater / fstab | قيمة super الفيزيائية في الإعدادات `4,324,327,424` بايت، ومجموعة `qti_dynamic_partitions` حدها `4,320,133,120` بايت. يذكر CI أن payload المجموعة `4,055,482,368` بايت، ضمن الحد. الـ updater يحرس `SM-A115F` و`A115FXXS6CWK2` ولا يحتوي أمر format data بحسب الفاحص. | الـ updater يعيد تكوين logical-partition metadata داخل super؛ قبول recovery الفعلي ومسارات by-name وخصائص recovery لم تُختبر على الجهاز. لا تغيّر PIT أو الأقسام الفيزيائية. |
| Firmware / image assembly | الإعداد يثبت tuple هدف A115F `A115FXXS6CWK2/A115FOJM6CWK1/A115FXXS6CWK1/A115FXXS6CWK2`، ويبني system/vendor/product/odm مع ملفات boot المستهدفة. CI أنشأ ZIP صالحًا. | لا يوجد في التقرير hash موثّق لملف firmware archive الأصلي يربطه تشفيريًا بكل ملفات الاستخراج. وُجدت ملاحظة استخراجية: ملف `system_ext/etc/aconfig_flags.pb` لدى المانح حجمه صفر وبعض أدلة fs_config فارغة؛ target يدمج system_ext مع system، لذا هذه ملاحظة تحتاج متابعة وليست عطلًا مثبتًا. |
| HAL / VINTF / ABI / FBE | vendor الهدف من جيل Android 12: SDK/VNDK 31، ويحتوي Keymaster HIDL 3.0/4.0 بنسخ ARM32. fstab الهدف يضبط `/data` على F2FS و`fileencryption=ice`. تم استيراد helper ومكتبات KeyMint/Keystore2 ذات 32-bit ضمن تشخيص الترتيب. | Android 15 donor أعلى API (35) ويقدم مصفوفات AIDL KeyMint، مقابل HIDL قديم في vendor. وجود المداخل لا يثبت وحده رفض VINTF، لكن لا توجد نتيجة `checkvintf` للمزيج النهائي؛ أداة `checkvintf` غير متاحة في بيئة التدقيق. نجاح QSEE/TEE وإنشاء مفتاح FBE وفتح `/data` غير مثبت. |
| Init / SELinux / permissions | patcher `scripts/patch_a115f_init.py` fail-closed وidempotent، ويُدرج `exec_start wait_for_keymaster` قبل `mount_all ... --late`. ملف workdir السابق أظهر الترتيب والـ helper labels/permissions المنقولة من stock. التغيير موجود في المصدر ودخل بناء commit الحالي. | لا يوجد log من ROM يثبت تنفيذ الخدمة، readiness، السماح عبر SELinux، أو نجاح Keymaster/QSEE؛ ترتيب المصدر لا يساوي نجاح runtime. |
| Build / tests / CI | GitHub Actions run [40233035076](https://github.com/nova-arch008/ZineROM-a11q/actions/runs/40233035076) على SHA `190586c…` انتهى **success**. `Ran 60 tests` ثم `OK`. بناء ROM اكتمل، وفاحص ZIP أكد 22 عنصرًا، حارس `a115f / SM-A115F / A115FXXS6CWK2`، تغطية payload/transfer-list لأقسام odm/product/system/vendor، وسعة المجموعة. SHA-256 لحزمة ROM الناتجة: `18f579c0758134d4e5db6bf81d437f27403f7dcdf9d4586321944dd82993c3e5`. | خطوة fingerprint audit في workflow معلّمة `continue-on-error: true`، لذلك نجاح الـ job وحده لا يجعلها gate إلزامية. فاحص ZIP ساكن ولا يحاكي التفليش أو الإقلاع. لم تُجرَ مقارنة clean repeat-build مضبوطة. |
| Tester bootloop / stage | تم تصنيف أحدث مرفق كسجل Recovery لا كسجل محاولة ROM؛ لم تُعرف منه مرحلة ROM أو أول fatal error. | نحتاج اسم/Hash ZIP الذي جُرّب، وهل دخل Recovery تلقائيًا أم يدويًا، وlogcat/dmesg/pstore ملتقطًا من محاولة ROM نفسها. السجل الأقدم عن FBE لا يحمل هوية ZIP يمكن ربطها بهذه المحاولة. |

## التنفيذ المحفوظ في GitHub

التغييرات البرمجية والاختبارات موجودة في الفرع البعيد `manus/a115f-vendor-fingerprint` داخل commit `190586c39cd86057887d7ae84a4631761ace7c54`. شملت: استيراد ملفات Keymaster المطلوبة، إضافة حاجز init قبل mount `/data`، حارس Binary 6 الصارم، validator واختبارات، وربط الفرع ببناء GitHub Actions.

### نتيجة CI وحزمة البناء

- Run: [GitHub Actions #40233035076](https://github.com/nova-arch008/ZineROM-a11q/actions/runs/40233035076)
- النتيجة: success؛ job `build (a115f)` انتهى بنجاح.
- SHA-256 لملف ROM ZIP الناتج عن هذا الـ run: `18f579c0758134d4e5db6bf81d437f27403f7dcdf9d4586321944dd82993c3e5`.
- اسم artifact في Actions: `ZineROM_OneUI7_A115F-Port-A057F-7`؛ حجم أرشيف Artifact الخارجي `1,837,883,911` بايت، وdigest الخارجي `7888e2f9df50001bfcf1fe32a0ca9116ceca88c8c4cee7182e438cfabaae2184`. تاريخ الانتهاء المعلن: 2027-01-23.
- هذا الـ Action artifact **ليس Release عامًا**. الإصدار العام السابق بقي كما هو، SHA-256 `29384d92ba37f6603cf0dfe08eec027e4049e3781414ffc9d197479b3388e2e0`. لم أرفع حزمة CI الجديدة إلى Release لأن ذلك يتطلب موافقتك الصريحة وفق التعليمات الأخيرة.

## أكبر الموانع حسب الأولوية

1. **P0 — ربط نتيجة التيستر بالحزمة الصحيحة:** لا نملك SHA-256 للحزمة التي جُرّبت أو log من إقلاع ROM مطابق لها. المرفق الحالي لا يثبت bootloop ROM.
2. **P0 — تجربة الجهاز غير مثبتة:** لا يوجد دليل لهذا الإصدار على الشعار أو Boot Animation أو Setup Wizard؛ ولا يوجد سبب reboot مؤكد في أحدث سجل.
3. **P1 — VINTF/runtime security:** لا يوجد `checkvintf` للمزيج النهائي أو دليل runtime على تسجيل Keymaster/Keystore2 أو نجاح QSEE/FBE.
4. **P1 — مخاطرة recovery/super:** إعادة كتابة dynamic-partition metadata مرتبة ساكنًا لكنها غير مختبرة على recovery الجهاز؛ لا PIT ولا تغييرات فيزيائية مسموحة.
5. **P2 — سلامة provenance/reproducibility:** أضف لاحقًا hash SHA-256 موثقًا لملف firmware archive وسجل build provenance؛ MD5 الداخلي في Samsung/Odin مفيد لاكتشاف التلف لكنه ليس إثبات provenance تشفيريًا قويًا.

## خطة العمل المرتبة

1. **من دون لمس الهاتف:** حفظ اسم الحزمة وSHA-256 وتاريخ الاختبار، والتحقق هل اختُبر Release القديم (`29384d…`) أم Artifact CI الحالي (`18f579…`).
2. **تحديد سياق السجل:** طلب سجل محاولة ROM لا Recovery. إذا دخل Recovery فقط، جمع `last_kmsg` و`/sys/fs/pstore/*` و`/cache/recovery/last_log` و`last_install` مع إبقاء سجلات recovery منفصلة.
3. **مراجعة ساكنة قبل أي محاولة جديدة:** توفير/بناء `checkvintf` صالح ومقارنة manifests/matrices النهائية، وفحص DTBO overlay IDs/compatibles وprovenance firmware وملفات payload بعد فكها، ثم تسجيل النتائج في هذا الملف.
4. **اختبار عتادي مشروط:** لا يتم هنا. يلزم موافقتك المنفصلة وإثبات مسار استعادة stock، والطراز SM-A115F وBinary 6. لا format data ولا تغيير PIT/bootloader/modem ولا تعطيل دائم لـ FBE.
5. **اختيار الإصلاح التالي من دليل السجل:** إن ثبت وصول محاولة ROM إلى late-fs، نتحقق من trace تنفيذ helper ثم Keymaster/Keystore2/QSEE وvold/fscrypt؛ وإن كانت الرسالة VINTF أو linker أو init fatal، يعالج السبب المحدد بدل إضافة تغييرات عشوائية.
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
