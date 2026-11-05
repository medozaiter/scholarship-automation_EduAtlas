# EduAtlas Design System — «الباحث الدافئ» (Warm Scholar)
**نظام التصميم الرقمي والهوية البصرية لمنصة استكشاف المنح الأكاديمية EduAtlas v2.5**

---

## 🌿 1. الرؤية والفلسفة التصميمية (Design Philosophy)

يقوم نظام تصميم **EduAtlas** على استعارة محورية: **«رحلة الطالب نحو المنحة هي رحلة استكشاف ملاحية وجغرافية»**.
في كثير من الأحيان، يعاني الطلاب في سن 18-30 عاماً من "رهبة التقديم" (Application Anxiety) والخوف من البيروقراطية أو الرفض. لذلك، تم اختيار اتجاه **«الباحث الدافئ — Warm Scholar»** لتحويل تجربة المنصة من مجرد قاعدة بيانات جافة إلى **دفتر استكشاف ميداني مهدئ وملهم (Field Expedition Journal)** يجمع بين:

1. **الوقار الأكاديمي:** عبر درجات الأخضر النباتي والغابي العميق (Forest Botanical).
2. **الدفء الإنساني:** عبر خلفيات تحاكي الورق المعتق الفاخر (Warm Parchment / Cream).
3. **وضوح البوصلة والخطوة التالية:** عبر اللون البرتقالي المحروق (Terracotta Clay) كنقطة ارتكاز للإجراءات الحاسمة (CTAs).
4. **التضاريس كمعيار للتقدم:** خطوط كنتور طبوغرافية رقيقة (Topographic Contours) تمثل تدرجات متطلبات القبول وصعود قمة الهدف.

---

## 🎨 2. مصفوفة الألوان والرموز (Color Tokens & WCAG Contrast)

### أ) لوحة الألوان الأساسية (Core Tokens)

| الرمز (Token) | اسم اللون | القيمة النهارية (Light) | القيمة الليلية (Dark) | الدور الوظيفي | نسبة التباين (Contrast) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `--ea-color-canvas` | الخلفية العامة | `#F8F6F0` (Parchment) | `#101612` (Obsidian Pine) | خلفية الصفحة والجسم الرئيسي | 16.2:1 (AAA) |
| `--ea-color-surface` | أسطح الكروت | `#FFFFFF` (Pure Parchment) | `#19241E` (Dark Forest) | بطاقات المنح والنوافذ المنبثقة | 13.5:1 (AAA) |
| `--ea-color-surface-subtle` | أسطح فرعية | `#EFECE2` (Oat Cream) | `#22322A` (Muted Pine) | حقول الإدخال والشريط الجانبي | 10.8:1 (AAA) |
| `--ea-color-primary` | الأخضر الأكاديمي | `#1F4232` (Forest 700) | `#2E654D` (Sage 500) | العناوين الرئيسية والهيدر | 12.1:1 على الفاتح |
| `--ea-color-accent` | التراكوتا الملاحية | `#C25438` (Terracotta 600) | `#DC6843` (Clay 500) | أزرار الإجراء الأساسية (CTAs) | 5.4:1 (AA Compliant) |
| `--ea-color-accent-hover` | تراكوتا متفاعلة | `#A63F26` | `#E87B57` | حالة التمرير (Hover States) | 6.8:1 |
| `--ea-color-ai` | الذكاء الاصطناعي | `#D98858` (Warm Ochre) | `#F3A88E` (Soft Ochre) | شارات ومحادثات Gemini | 7.1:1 على الداكن |

### ب) ألوان الحالات والنتائج (Semantic Status Colors)

```css
:root {
  /* Success - فرص قبول عالية ومتطلبات مستوفاة */
  --ea-success-bg: rgba(62, 126, 85, 0.12);
  --ea-success-border: rgba(62, 126, 85, 0.35);
  --ea-success-text: #1E663B;

  /* Warning - مواعيد تقترب (أقل من 30 يوماً) */
  --ea-warning-bg: rgba(217, 119, 6, 0.12);
  --ea-warning-border: rgba(217, 119, 6, 0.35);
  --ea-warning-text: #B45309;

  /* Danger - مواعيد عاجلة جداً (أقل من 7 أيام) أو أوراق ناقصة */
  --ea-danger-bg: rgba(194, 65, 43, 0.12);
  --ea-danger-border: rgba(194, 65, 43, 0.35);
  --ea-danger-text: #B91C1C;

  /* Contour Stroke - خطوط التضاريس الخلفية */
  --ea-contour-stroke: rgba(31, 66, 50, 0.08);
}

html.dark {
  --ea-success-bg: rgba(74, 173, 115, 0.16);
  --ea-success-border: rgba(74, 173, 115, 0.4);
  --ea-success-text: #6EE7B7;

  --ea-warning-bg: rgba(245, 158, 11, 0.16);
  --ea-warning-border: rgba(245, 158, 11, 0.4);
  --ea-warning-text: #FCD34D;

  --ea-danger-bg: rgba(239, 68, 68, 0.18);
  --ea-danger-border: rgba(239, 68, 68, 0.42);
  --ea-danger-text: #FCA5A5;

  --ea-contour-stroke: rgba(220, 104, 67, 0.15);
}
```

---

## 🔤 3. نظام الطباعة والتجاوب (Typography Scale)

* **الخط العربي الأساسي:** `IBM Plex Sans Arabic` لمتن النصوص والبطاقات + `Cairo` للعناوين الملاحية الكبرى.
* **الخط اللاتيني:** `Plus Jakarta Sans` لأسماء الجامعات والمصطلحات الدولية والأرقام.
* **الأرقام والأكواد:** `JetBrains Mono` للنسب المئوية والتواريخ وجداول الحساب.

### سلم الأحجام المتجاوبة (Fluid Modular Scale عبر `clamp`):

```css
/* Fluid Typography Scale */
--ea-font-display: clamp(2rem, 1.6rem + 2vw, 3.25rem);    /* 32px -> 52px */
--ea-font-h1:      clamp(1.65rem, 1.35rem + 1.5vw, 2.5rem);/* 26px -> 40px */
--ea-font-h2:      clamp(1.35rem, 1.15rem + 1vw, 1.85rem); /* 21px -> 30px */
--ea-font-h3:      clamp(1.15rem, 1rem + 0.6vw, 1.45rem);   /* 18px -> 23px */
--ea-font-body:    clamp(0.95rem, 0.9rem + 0.2vw, 1.05rem); /* 15px -> 17px */
--ea-font-sm:      clamp(0.825rem, 0.8rem + 0.15vw, 0.9rem);/* 13px -> 14.5px */
--ea-font-xs:      0.75rem;                                  /* 12px ثابت كحد أدنى */

/* Line Heights */
--ea-lh-heading: 1.3;
--ea-lh-body:    1.7;  /* مريح جداً للقراءة العربية الممتدة */
```

---

## 📐 4. شبكة المسافات والارتفاع والحركة (Spacing, Elevation & Motion)

### شبكة المسافات (8pt Grid System)
`--ea-space-1: 4px;` | `--ea-space-2: 8px;` | `--ea-space-3: 12px;` | `--ea-space-4: 16px;` | `--ea-space-6: 24px;` | `--ea-space-8: 32px;` | `--ea-space-12: 48px;` | `--ea-space-16: 64px;`

### استعارة الطبقات التضاريسية (Topographic Elevation)
* **المستوى 1 (سطح الخريطة):** حواف منحنية بنعومة `border-radius: 16px` مع إطار دقيق `1px solid var(--ea-border-subtle)`.
* **المستوى 2 (تضاريس بارزة عند التحويم):** 
  `box-shadow: 0 10px 25px -5px rgba(20, 41, 31, 0.08), 0 0 0 1px rgba(194, 84, 56, 0.2); transform: translateY(-3px);`
* **المستوى 3 (البوصلة العائمة):**
  `box-shadow: 0 20px 35px -8px rgba(194, 84, 56, 0.25);`

### الحركة والانتقال (Motion Curves)
* **استجابة الضغط الفوري:** `150ms ease-out`
* **فتح النوافذ والبطاقات:** `250ms cubic-bezier(0.16, 1, 0.3, 1)`
* **حركة إبرة البوصلة:** `800ms cubic-bezier(0.34, 1.56, 0.64, 1)` (Spring Effect)

---

## 🧩 5. كتالوج المكونات المعيارية (Component Catalog)

### أ) أزرار الإجراءات (Action Buttons)

```html
<!-- Primary CTA (البوصلة التراكوتا) -->
<button class="ea-btn-primary">
  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <circle cx="12" cy="12" r="10"/>
    <polygon points="12 4 15 12 12 10 9 12" fill="currentColor"/>
  </svg>
  <span>ابدأ بوصلة التقديم</span>
</button>

<!-- Secondary Button (الأخضر الأكاديمي الهادئ) -->
<button class="ea-btn-secondary">
  <span>استعراض كل المنح</span>
</button>
```

### ب) بطاقة المنحة الذكية (The Canonical Scholarship Card)

```html
<article class="ea-scholarship-card">
  <!-- رأس البطاقة -->
  <div class="ea-card-header">
    <div class="ea-country-flag">🇬🇧</div>
    <div class="ea-university-info">
      <span class="ea-country-name">المملكة المتحدة • جامعة أكسفورد</span>
      <h3 class="ea-scholarship-title">منحة تشيفنينغ البريطانية (Chevening)</h3>
    </div>
    <div class="ea-match-badge ea-match-high">
      <span>توافق 94%</span>
    </div>
  </div>

  <p class="ea-scholarship-desc">
    تمويل حكومي شامل لدرجة الماجستير لمدة عام في المملكة المتحدة لقادة المستقبل.
  </p>

  <!-- شريط القياس السريع -->
  <div class="ea-card-metrics">
    <div>
      <span class="ea-metric-label">التغطية</span>
      <span class="ea-metric-value">تمويل كامل 100%</span>
    </div>
    <div>
      <span class="ea-metric-label">الدرجة</span>
      <span class="ea-metric-value">ماجستير</span>
    </div>
    <div>
      <span class="ea-metric-label">الموعد النهائي</span>
      <span class="ea-metric-value ea-text-warning">28 يوماً متبقية</span>
    </div>
  </div>

  <!-- الأزرار -->
  <div class="ea-card-actions">
    <button class="ea-btn-primary ea-btn-sm">احسب فرصة قبولك</button>
    <button class="ea-btn-outline ea-btn-sm">استشر رادار AI</button>
  </div>
</article>
```

### ج) مؤشر بوصلة القبول الدائري (Acceptance Compass Gauge)

```html
<div class="ea-gauge-wrapper">
  <svg class="ea-gauge-svg" viewBox="0 0 100 100">
    <circle cx="50" cy="50" r="42" class="ea-gauge-track"/>
    <circle cx="50" cy="50" r="42" class="ea-gauge-fill" style="stroke-dashoffset: 40;"/>
  </svg>
  <div class="ea-gauge-center">
    <span class="ea-gauge-score">88%</span>
    <span class="ea-gauge-label">فرصة مرتفعة</span>
  </div>
</div>
```

---

## ⚖️ 6. إرشادات الاستخدام الموصى بها (Do & Don't)

| ✅ ما يجب فعله (Do) | ❌ ما يجب تجنبه (Don't) |
| :--- | :--- |
| **استخدام لغة دافئة ومطمئنة:** «فرصتك واعدة، وتحتاج لتعزيز نقطتين» | **لغة الصدمة والرفض القاطع:** «نسبة قبولك ضعيفة ومرفوضة» |
| **استخدام التراكوتا `#DC6843` فقط للأزرار الحيوية:** مثل التقديم والحساب | **الإفراط في اللون التراكوتا:** لا تجعل خلفيات الأقسام برتقالية |
| **الحفاظ على الخطوط الكنتورية خفيفة الشفافية:** 8% إلى 15% كحد أقصى | **رسم خطوط كنتور فاقعة أو كثيفة:** تشتت القراءة وتجهد العين |
| **دعم التباين المريح للنصوص الطويلة:** استخدام line-height لا يقل عن 1.65 | **استخدام خطوط مضغوطة جداً:** تصعّب قراءة الحركات والنقاط |
| **توفير حالة فارغة (Empty State) تشجع على المحاولة:** مع زر لتوسيع الفلاتر | **عرض شاشة فارغة دون أي رسالة أو توجيه للطالب** |

---
**EduAtlas Design System © 2026 — Designed for Academic Explorers Worldwide.**
