# EduAtlas Design System — رسام الخرائط الحديث (Modern Cartographer)
**نظام التصميم والهوية البصرية الشاملة — الإصدار v3.0 (Direction B: Modern Cartographer)**

---

## 🧭 1. فلسفة التصميم (Design Philosophy)

يقوم نظام تصميم **EduAtlas — رسام الخرائط الحديث (Modern Cartographer)** على استعارة بصرية متقدمة: **رحلة الطالب نحو منحة أحلامه هي رحلة استكشاف ملاحية ورسم خرائط المستقبل عبر أدوات رقمية فائقة الذكاء والدقة**.

يستهدف النظام شريحة الطلاب والباحثين الشباب (18-30 سنة) الذين يتطلعون لواجهة تقنية متطورة، فائقة السرعة، توحي بالدقة والاحترافية والذكاء الاصطناعي، وتبدد تشتت البحث عن المنح من خلال:

1. **العمق الكوني والتقني (Obsidian & Cyber Violet):** خلفيات داكنة عميقة (`#0C0A17`, `#18142C`) وخلفيات نهارية فائقة النقاء (`#F8F9FD`) تبرز محتوى المنح والبيانات بوضوح بصري استثنائي.
2. **إشارات الملاحة بالليزر (Laser Mint Accent):** الأخضر النعناعي الفسفوري (`#10E599`) للأزرار الأساسية، مؤشرات التوافق الأكاديمي، ونقاط الرادار الملاحي النشطة.
3. **نبض الذكاء الاصطناعي (Electric Purple & Indigo):** درجات البنفسجي والنيلي الكهربائي (`#7C3AED`, `#818CF8`) لتمثيل قدرات محرك Gemini والمستشار الأكاديمي الذكي.
4. **الخطوط الطبوغرافية الرقمية (Digital Topographic Contours & Laser Grids):** خطوط كنتورية دقيقة وشبكات ملاحية خفيفة في الخلفيات تعزز هوية "رسم الخرائط" دون تشويش على النصوص.

---

## 🎨 2. منظومة الألوان (Color Tokens & WCAG Contrast)

### أ) لوحة الألوان الأساسية (Core Color Tokens)

| الرمز (Token) | الاسم الشائع | القيمة (Light) | القيمة (Dark) | الوظيفة الدلالية | نسبة التباين (Contrast) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `--ea-canvas` | Canvas Background | `#F8F9FD` (Pure Frost) | `#0C0A17` (Deep Obsidian) | خلفية الصفحة العامة | 18.5:1 (AAA) |
| `--ea-surface` | Card Surface | `#FFFFFF` (Pure White) | `#18142C` (Cyber Midnight) | بطاقات المنح والنوافذ المنبثقة | 15.2:1 (AAA) |
| `--ea-surface-subtle` | Subtle Surface | `#EEF1FA` (Cool Ice) | `#231D3E` (Subtle Violet) | حقول الإدخال، القوائم المنسدلة | 12.4:1 (AAA) |
| `--ea-brand-primary` | Brand Primary | `#6D28D9` (Electric Purple 700) | `#7C3AED` (Electric Purple 600) | الهيدر، الروابط، الأيقونات الثانوية | 11.2:1 على الخلفيات الفاتحة |
| `--ea-brand-accent` | Brand Accent (CTA) | `#059669` (Emerald 600) | `#10E599` (Laser Mint) | أزرار الحث على اتخاذ إجراء، نقاط الرادار | 5.8:1 (AA Compliant) |
| `--ea-brand-accent-hover` | Accent Hover | `#047857` | `#34D399` | حالات التحويم (Hover States) | 6.2:1 |
| `--ea-brand-ai` | AI Advisor Pulse | `#7C3AED` (Violet) | `#818CF8` (Cyber Indigo) | رسائل وواجهات مستشار الذكاء الاصطناعي | 7.4:1 على الأسطح الداكنة |

### ب) ألوان الحالات والبيانات (Semantic Status Tokens)

```css
:root {
  /* Success - توافق ممتاز / مؤهل */
  --ea-success-bg: rgba(16, 229, 153, 0.12);
  --ea-success-border: rgba(16, 229, 153, 0.35);
  --ea-success-text: #059669;

  /* Warning - اقتراب الموعد النهائي / بحاجة لوثائق */
  --ea-warning-bg: rgba(251, 191, 36, 0.12);
  --ea-warning-border: rgba(251, 191, 36, 0.35);
  --ea-warning-text: #D97706;

  /* Danger - منتهية الصلاحية / غير مؤهل */
  --ea-danger-bg: rgba(239, 68, 68, 0.12);
  --ea-danger-border: rgba(239, 68, 68, 0.35);
  --ea-danger-text: #DC2626;

  /* Topographic & HUD Glows */
  --ea-contour-glow: rgba(124, 58, 237, 0.08);
  --ea-laser-glow: rgba(16, 229, 153, 0.25);
}

html.dark {
  --ea-success-bg: rgba(16, 229, 153, 0.15);
  --ea-success-border: rgba(16, 229, 153, 0.40);
  --ea-success-text: #10E599;

  --ea-warning-bg: rgba(251, 191, 36, 0.15);
  --ea-warning-border: rgba(251, 191, 36, 0.40);
  --ea-warning-text: #FBBF24;

  --ea-danger-bg: rgba(239, 68, 68, 0.15);
  --ea-danger-border: rgba(239, 68, 68, 0.40);
  --ea-danger-text: #F87171;

  --ea-contour-glow: rgba(16, 229, 153, 0.14);
}
```

---

## 🔤 3. نظام الطباعة (Typography Scale)

تعتمد المنصة على خطوط هندسية عصرية تجمع بين الفخامة وقابلية القراءة على الشاشات العالية الدقة:
- **العناوين والنصوص العربية:** `Cairo` (للأرقام والعناوين الكبيرة) + `IBM Plex Sans Arabic` (للنصوص والفقرات).
- **العناوين اللاتينية والعلامة التجارية:** `Plus Jakarta Sans` و `Inter`.
- **الأرقام التقنية، نسب التوافق وتواريخ الانتهاء:** `JetBrains Mono` و `ui-monospace`.

### مقياس الأحجام (Modular Typography Scale - Base 16px)

| النمط | الحجم (CSS clamp) | الوزن | Line Height | الاستخدام |
| :--- | :--- | :--- | :--- | :--- |
| `Display Hero` | `clamp(2.25rem, 4vw, 3.75rem)` | 800 / 900 | 1.15 | عنوان البطل في الصفحة الرئيسية |
| `Heading 1 (H1)` | `clamp(1.75rem, 3vw, 2.5rem)` | 800 | 1.25 | عناوين الصفحات الرئيسية |
| `Heading 2 (H2)` | `clamp(1.35rem, 2vw, 1.85rem)` | 700 | 1.30 | عناوين أقسام الرادار والمحرك |
| `Heading 3 (H3)` | `1.15rem` (18.4px) | 700 | 1.40 | عناوين بطاقات المنح |
| `Body Large` | `1.05rem` (16.8px) | 500 / 600 | 1.60 | مقدمات المقالات ورسائل AI |
| `Body Regular` | `0.9375rem` (15px) | 400 / 500 | 1.65 | النصوص العامة والشروحات |
| `Caption / Meta` | `0.75rem` (12px) | 500 / 600 | 1.40 | المواعيد النهائية، الشارات، التلميحات |

---

## 📐 4. مقياس المسافات والزوايا (Spacing, Radii & Elevations)

### نظام المسافات (8-Point Grid)
- `spacing-1`: `4px` | `spacing-2`: `8px` | `spacing-3`: `12px` | `spacing-4`: `16px`
- `spacing-6`: `24px` | `spacing-8`: `32px` | `spacing-12`: `48px` | `spacing-16`: `64px`

### الحواف والزوايا (Border Radii)
- `radius-sm`: `6px` (للشارات الصغيرة والمؤشرات)
- `radius-md`: `10px` (للأزرار وحقول الإدخال)
- `radius-lg`: `14px` (للبطاقات الفرعية والقوائم المنسدلة)
- `radius-xl`: `20px` (لبطاقات المنح ولوحات التحكم)
- `radius-2xl`: `28px` (للنوافذ المنبثقة وصناديق الحوار)

### الظلال والتوهج (Elevations & Glows)
- `shadow-sm`: `0 1px 3px rgba(12, 10, 23, 0.08)`
- `shadow-md`: `0 4px 14px -2px rgba(12, 10, 23, 0.12), 0 2px 6px -1px rgba(12, 10, 23, 0.06)`
- `shadow-glow-mint`: `0 0 20px -3px rgba(16, 229, 153, 0.35)`
- `shadow-glow-purple`: `0 0 25px -4px rgba(124, 58, 237, 0.35)`

---

## 🧩 5. كتالوج المكونات (Component Catalog)

### أ) شريط التنقل الملاحي (Sticky Nav)
```html
<header class="ea-navbar sp-sticky-nav">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
    <!-- الشعار الملاحي -->
    <a href="/" class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#6D28D9] via-[#7C3AED] to-[#4C1D95] border border-violet-400/30 flex items-center justify-center text-white shadow-md shadow-violet-950/30">
        <svg class="w-6 h-6 text-[#10E599]" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="42" stroke="currentColor" stroke-width="7" stroke-opacity="0.35" fill="none"/>
          <polygon points="50,16 60,50 50,43 40,50" fill="#10E599"/>
          <polygon points="50,84 60,50 50,57 40,50" fill="#EDE9FE"/>
          <circle cx="50" cy="50" r="6" fill="#10E599"/>
        </svg>
      </div>
      <div>
        <span class="text-lg font-black text-[#130E26] dark:text-white font-latin">Edu<span class="text-[#10E599]">Atlas</span> AI</span>
      </div>
    </a>
  </div>
</header>
```

### ب) بطاقة المنحة الذكية (Scholarship Card)
```html
<article class="ea-card group hover:border-[#10E599]/40 p-6 flex flex-col justify-between">
  <div>
    <div class="flex items-start justify-between gap-3 mb-3">
      <span class="ea-badge-match">
        <span class="w-2 h-2 rounded-full bg-[#10E599] animate-pulse"></span>
        تطابق 94%
      </span>
      <span class="text-xs font-mono text-slate-400">ينتهي: 15 مارس</span>
    </div>
    <h3 class="text-lg font-bold text-slate-900 dark:text-white group-hover:text-[#10E599] transition-colors">
      منحة إيراسموس موندوس للدراسات العليا
    </h3>
    <p class="text-sm text-slate-600 dark:text-slate-300 mt-2 line-clamp-2">
      تمويل كامل يشمل الرسوم الدراسية، بدل السكن، وتأمين السفر للجامعات الشريكة في الاتحاد الأوروبي.
    </p>
  </div>
  <div class="mt-5 pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
    <span class="text-sm font-bold text-[#7C3AED] dark:text-[#A78BFA]">تمويل كامل (Full Ride)</span>
    <button class="ea-btn-primary text-xs px-4 py-2">
      استكشف المسار
    </button>
  </div>
</article>
```

---

## 🚫 6. إرشادات الاستخدام (Do / Don't)

- ✅ **افعل (Do):**
  - استخدم أخضر الليزر (`#10E599`) فقط كنقطة تركيز وجذب أساسية (CTAs، نسب التطابق، البوصلة).
  - احرص على تباين النص مع الخلفيات بدرجة WCAG AA على الأقل في كلا الوضعين (النهاري والليلي).
  - احتفظ بظل الكنتور الطبوغرافي الرقمي في خلفيات البطاقات والهيدر كعلامة مميزة.
  - استخدم خط الأرقام `JetBrains Mono` أو الأرقام اللاتينية داخل الشارات والإحصائيات.

- ❌ **لا تفعل (Don't):**
  - لا تفرط في استخدام الأخضر الفسفوري كنصوص فقرات أو خلفيات كاملة تسبب إجهاداً للعين.
  - لا تخلط بين درجات الأخضر العشبي القديم مع أخضر الليزر النعناعي الحديث.
  - لا تكسر التسلسل الهرمي للبطاقات (العنوان، الجامعة، نسبة التطابق، الإجراء).
