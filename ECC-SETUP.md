# إعداد ECC — دليل سريع

## شنو تنصب؟
- **ECC plugin** (`ecc@ecc`) — 71 agent، 311 skill، 97 أمر، و hooks
- **Rules** عامة بـ `.claude/rules/ecc/common/` (أسلوب الكود، الأمان، الاختبارات، git)

## التشغيل
1. افتح Claude Code داخل هذا المشروع
2. أول مرة راح يسألك يثق بالـ marketplace `ecc` → وافق
3. تأكد: `/plugin list` → لازم تشوف `ecc@ecc` مفعّل
4. إذا ما تنصب تلقائياً:
   ```
   /plugin marketplace add https://github.com/affaan-m/ECC
   /plugin install ecc@ecc
   ```

## أوامر مفيدة
- `/ecc:plan` — تخطيط قبل الكود
- `/ecc:tdd-workflow` — كتابة اختبارات أولاً
- `/ecc:code-review` — مراجعة الكود
- `/ecc:build-fix` — إصلاح أخطاء البناء
- `/ecc:configure-ecc` — تعديل الإعداد

## تخصيص
- قوة الـ hooks: غيّر `ECC_HOOK_PROFILE` بـ `.claude/settings.json` إلى `minimal` أو `strict`
- لغة المشروع: انسخ rules اللغة من ECC (مثلاً `rules/typescript`) إلى `.claude/rules/ecc/`

⚠️ لا تنصب ECC مرتين (plugin + install.sh) — يصير تكرار.
