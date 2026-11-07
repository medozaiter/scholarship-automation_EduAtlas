/**
 * EduAtlas Enterprise Data Validation & Sanitization Engine
 * Dual-layer (Frontend & Backend-aligned) validation, real-time sanitization,
 * spam/gibberish defense, character counters, layout protection, and instant UX feedback.
 */

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.EduAtlasValidator = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    // Official recognized country catalogue (Arabic & English & Common forms)
    const OFFICIAL_COUNTRIES = new Set([
        "palestine", "فلسطين", "دولة فلسطين",
        "jordan", "الأردن", "المملكة الأردنية الهاشمية",
        "lebanon", "لبنان",
        "syria", "سوريا",
        "saudi arabia", "السعودية", "المملكة العربية السعودية",
        "united arab emirates", "الإمارات", "uae",
        "qatar", "قطر",
        "kuwait", "الكويت",
        "oman", "عمان", "سلطنة عمان",
        "bahrain", "البحرين",
        "yemen", "اليمن",
        "iraq", "العراق",
        "egypt", "مصر", "جمهورية مصر العربية",
        "morocco", "المغرب",
        "algeria", "الجزائر",
        "tunisia", "تونس",
        "libya", "ليبيا",
        "sudan", "السودان",
        "mauritania", "موريتانيا",
        "somalia", "الصومال",
        "djibouti", "جيبوتي",
        "comoros", "جزر القمر",
        "united kingdom", "uk", "بريطانيا", "المملكة المتحدة",
        "germany", "ألمانيا",
        "france", "فرنسا",
        "italy", "إيطاليا",
        "spain", "إسبانيا",
        "turkey", "تركيا",
        "hungary", "المجر", "هنغاريا",
        "netherlands", "هولندا",
        "sweden", "السويد",
        "switzerland", "سويسرا",
        "norway", "النرويج",
        "poland", "بولندا",
        "belgium", "بلجيكا",
        "austria", "النمسا",
        "ireland", "أيرلندا", "ايرلندا",
        "czech republic", "التشيك",
        "portugal", "البرتغال",
        "greece", "اليونان",
        "cyprus", "قبرص",
        "romania", "رومانيا",
        "russia", "روسيا",
        "united states", "usa", "us", "أمريكا", "الولايات المتحدة",
        "canada", "كندا",
        "brazil", "البرازيل",
        "argentina", "الأرجنتين",
        "japan", "اليابان",
        "south korea", "korea", "كوريا الجنوبية", "كوريا",
        "china", "الصين",
        "malaysia", "ماليزيا",
        "singapore", "سنغافورة",
        "indonesia", "إندونيسيا",
        "india", "الهند",
        "pakistan", "باكستان",
        "australia", "أستراليا",
        "new zealand", "نيوزيلندا",
        "south africa", "جنوب أفريقيا",
        "international", "دولي", "دولة أخرى", "any"
    ]);

    const RESERVED_USERNAMES = new Set([
        "admin", "administrator", "api", "dashboard", "assistant", "notifications",
        "profile", "settings", "logout", "login", "register", "null", "undefined",
        "user", "root", "scholarpilot", "eduatlas", "help", "support", "about", "terms", "privacy", "static"
    ]);

    /**
     * Anti-gibberish, anti-spam, and keyboard-smash analyzer.
     */
    function isGibberishOrSpam(text) {
        if (!text) return false;
        const clean = String(text).trim();

        // 1. 4 or more identical consecutive characters (e.g. aaaa, 9999, !!!)
        if (/(.)\1{3,}/.test(clean)) return true;

        // 2. Short repeated patterns (2-6 chars) repeated 3+ times (e.g. testtesttest, abcabcabc)
        if (/(.{2,6})\1{2,}/i.test(clean)) return true;

        // 3. Excessive consecutive punctuation (3 or more)
        if (/([!@#$%^&*()_+=\[\]{};:'"\\|,.<>/?~`\u060C\u061F\u061B\-])\1{2,}/.test(clean)) return true;

        return false;
    }

    /**
     * Strips dangerous script tags, invisible characters, and malicious payload markers.
     */
    function sanitizeString(str, maxLength) {
        if (!str) return '';
        let clean = String(str)
            .replace(/[\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFEFF]/g, '') // BiDi / Trojan Source
            .replace(/<[^>]*>/g, '') // HTML tags
            .replace(/javascript:/gi, '')
            .replace(/data:text\/html/gi, '')
            .replace(/onerror\s*=/gi, '')
            .replace(/onload\s*=/gi, '')
            .trim();

        if (maxLength && clean.length > maxLength) {
            clean = clean.substring(0, maxLength);
        }
        return clean;
    }

    const EduAtlasValidator = {
        /**
         * Validates student full name.
         * Only Arabic/English letters, spaces, hyphens, and apostrophes. 2-100 chars.
         */
        validateFullName: function (name, isRequired = true) {
            if (!name || !name.trim()) {
                if (isRequired) {
                    return { valid: false, message: "الاسم الكامل مطلوب ولا يمكن تركه فارغاً." };
                }
                return { valid: true, value: "" };
            }
            const clean = sanitizeString(name, 100);
            if (clean.length < 2) {
                return { valid: false, message: "الاسم قصير جداً (حرفان على الأقل)." };
            }
            if (clean.length > 100) {
                return { valid: false, message: "الاسم طويل جداً (الحد الأقصى 100 حرف)." };
            }
            const regex = /^[\u0600-\u06FFa-zA-Z\s\.\-']{2,100}$/;
            if (!regex.test(clean)) {
                return { valid: false, message: "يرجى إدخال اسم حقيقي يحتوي على أحرف عربية أو إنجليزية فقط دون أرقام أو رموز خاصة." };
            }
            const letterCount = (clean.match(/[\u0600-\u06FFa-zA-Z]/g) || []).length;
            if (letterCount < 2) {
                return { valid: false, message: "الاسم يجب أن يتضمن حرفين نصيين على الأقل." };
            }
            if (isGibberishOrSpam(clean)) {
                return { valid: false, message: "الاسم المدخل يحتوي على تكرار عشوائي غير مفهوم. يرجى إدخال اسم حقيقي." };
            }
            return { valid: true, value: clean };
        },

        /**
         * Validates university or educational institution.
         * Letters, numbers, common punctuation, 2-150 chars.
         */
        validateUniversity: function (univ, isRequired = false) {
            if (!univ || !univ.trim()) {
                if (isRequired) {
                    return { valid: false, message: "اسم الجامعة أو المؤسسة التعليمية مطلوب." };
                }
                return { valid: true, value: "" };
            }
            const clean = sanitizeString(univ, 150);
            if (clean.length < 2) {
                return { valid: false, message: "اسم المؤسسة قصير جداً (حرفان على الأقل)." };
            }
            if (clean.length > 150) {
                return { valid: false, message: "اسم المؤسسة طويل جداً (الحد الأقصى 150 حرف)." };
            }
            const regex = /^[\u0600-\u06FFa-zA-Z0-9\s\.\-/,()&\u060C]{2,150}$/;
            if (!regex.test(clean)) {
                return { valid: false, message: "اسم الجامعة يحتوي على رموز غير مقبولة." };
            }
            const letterCount = (clean.match(/[\u0600-\u06FFa-zA-Z]/g) || []).length;
            if (letterCount < 2) {
                return { valid: false, message: "اسم الجامعة يجب أن يحتوي على أحرف حقيقية وليس أرقاماً أو رموزاً فقط." };
            }
            if (isGibberishOrSpam(clean)) {
                return { valid: false, message: "اسم الجامعة يحتوي على تكرار عشوائي للرموز أو الأحرف." };
            }
            return { valid: true, value: clean };
        },

        /**
         * Validates field of study / major.
         * 2 to 100 characters.
         */
        validateMajor: function (major, isRequired = true) {
            if (!major || !major.trim()) {
                if (isRequired) {
                    return { valid: false, message: "التخصص الدراسي مطلوب." };
                }
                return { valid: true, value: "" };
            }
            const clean = sanitizeString(major, 100);
            if (clean.length < 2) {
                return { valid: false, message: "اسم التخصص قصير جداً (حرفان على الأقل)." };
            }
            if (clean.length > 100) {
                return { valid: false, message: "اسم التخصص طويل جداً (الحد الأقصى 100 حرف)." };
            }
            const letterCount = (clean.match(/[\u0600-\u06FFa-zA-Z]/g) || []).length;
            if (letterCount < 2) {
                return { valid: false, message: "يرجى كتابة تخصص دراسي حقيقي يتضمن أحرفاً صالحة." };
            }
            if (isGibberishOrSpam(clean)) {
                return { valid: false, message: "التخصص المدخل يحتوي على تكرار عشوائي." };
            }
            return { valid: true, value: clean };
        },

        /**
         * Validates academic GPA strictly:
         * - 4.0 / 5.0 systems (0.5 to 5.0)
         * - Percentage systems (40% to 100%)
         * - Rejects 333333, 999999, -999, abc, @@@@.
         */
        validateGpa: function (gpaStr, isRequired = true) {
            if (!gpaStr || !gpaStr.trim()) {
                if (isRequired) {
                    return { valid: false, message: "حقل المعدل التراكمي مطلوب." };
                }
                return { valid: true, value: "85%" };
            }
            const clean = String(gpaStr).trim();
            if (clean.length > 10) {
                return { valid: false, message: "المعدل المدخل طويل جداً وغير منطقي." };
            }

            const acceptedTerms = ["امتياز", "جيد جدا", "جيد جداً", "ممتاز", "جيد", "مقبول"];
            if (acceptedTerms.includes(clean)) {
                return { valid: true, value: clean };
            }

            // Reject letters and symbol spam
            if (/[a-zA-Z\u0600-\u06FF]/.test(clean)) {
                return { valid: false, message: "حقل المعدل يجب أن يحتوي على أرقام فقط (مثال: 3.75 أو 88.5%)." };
            }
            if (/[^0-9\.\s%/]/.test(clean)) {
                return { valid: false, message: "حقل المعدل يحتوي على رموز غير مقبولة." };
            }

            // 1. Explicit slash scale e.g. 3.75/4 or 4.5/5
            const slashMatch = clean.match(/^([0-5](?:\.\d{1,2})?)\s*\/\s*([45](?:\.0)?)$/);
            if (slashMatch) {
                const val = parseFloat(slashMatch[1]);
                const scale = parseFloat(slashMatch[2]);
                if (val >= 0.5 && val <= scale) {
                    return { valid: true, value: `${val}/${scale}` };
                }
                if (val < 0.5) {
                    return { valid: false, message: `المعدل (${val}) منخفض جداً وغير واقعي.` };
                }
                return { valid: false, message: `المعدل (${val}/${scale}) غير منطقي. يجب ألا يتجاوز ${scale}.` };
            }

            // 2. Percentage with '%' e.g. 85.5% or 95%
            if (clean.includes('%')) {
                const pctMatch = clean.match(/^(\d{1,3}(?:\.\d{1,2})?)\s*%$/);
                if (pctMatch) {
                    const val = parseFloat(pctMatch[1]);
                    if (val >= 40.0 && val <= 100.0) {
                        return { valid: true, value: `${val}%` };
                    }
                    return { valid: false, message: `المعدل المئوي (${val}%) خارج النطاق المقبول. يجب أن يكون بين 40% و 100%.` };
                }
                return { valid: false, message: "صيغة النسبة المئوية غير صحيحة (مثال: 88.5%)." };
            }

            // 3. Numeric value without symbol
            const numMatch = clean.match(/^(\d{1,3}(?:\.\d{1,2})?)$/);
            if (numMatch) {
                const val = parseFloat(numMatch[1]);
                if (val >= 0.5 && val <= 5.0) {
                    const scale = val > 4.0 ? 5 : 4;
                    return { valid: true, value: `${val}/${scale}` };
                }
                if (val >= 40.0 && val <= 100.0) {
                    return { valid: true, value: `${val}%` };
                }
                return { valid: false, message: `المعدل (${val}) خارج النطاق المقبول (0.5 إلى 4.0 أو 40% إلى 100%).` };
            }

            return { valid: false, message: "صيغة المعدل غير صحيحة. أدخل قيمة بنظام 4.0 (مثال: 3.75) أو نسبة مئوية (مثال: 85%)." };
        },

        /**
         * Validates country against the official recognized list.
         */
        validateCountry: function (countryStr, isRequired = true) {
            if (!countryStr || !countryStr.trim()) {
                if (isRequired) {
                    return { valid: false, message: "يرجى اختيار دولة إقامتك أو جنسيتك." };
                }
                return { valid: true, value: "Palestine" };
            }
            let clean = String(countryStr).trim().toLowerCase();
            clean = clean.replace(/\s*\(.*?\)/g, '').split('-')[0].trim();

            if (OFFICIAL_COUNTRIES.has(clean)) {
                return { valid: true, value: countryStr.trim() };
            }
            return { valid: false, message: `الدولة المدخلة (${countryStr}) غير موجودة في قائمة الدول المعتمدة.` };
        },

        /**
         * Validates RFC 5322 compliant email address.
         */
        validateEmail: function (emailStr) {
            if (!emailStr || !emailStr.trim()) {
                return { valid: false, message: "البريد الإلكتروني مطلوب ولا يمكن تركه فارغاً." };
            }
            const clean = String(emailStr).trim().toLowerCase();
            if (clean.length > 100) {
                return { valid: false, message: "البريد الإلكتروني طويل جداً (الحد الأقصى 100 حرف)." };
            }
            if (/\s/.test(clean)) {
                return { valid: false, message: "البريد الإلكتروني لا يمكن أن يحتوي على مسافات." };
            }
            const regex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
            if (!regex.test(clean)) {
                return { valid: false, message: "يرجى إدخال عنوان بريد إلكتروني صالح (مثال: student@example.com)." };
            }
            return { valid: true, value: clean };
        },

        /**
         * Validates international phone number (+ or 00 followed by 7-15 digits).
         */
        validatePhone: function (phoneStr, isRequired = false) {
            if (!phoneStr || !phoneStr.trim()) {
                if (isRequired) {
                    return { valid: false, message: "رقم الهاتف مطلوب." };
                }
                return { valid: true, value: "" };
            }
            const clean = String(phoneStr).replace(/[\s\-\(\)]/g, '').trim();
            if (!/^(\+|00)?[0-9]{7,15}$/.test(clean)) {
                return { valid: false, message: "رقم الهاتف غير صحيح. يجب أن يتكون من 7 إلى 15 رقماً مع رمز الدولة الدولي (مثال: +970590000000)." };
            }
            return { valid: true, value: clean };
        },

        /**
         * Validates student biography. Max 600 characters.
         */
        validateBio: function (bioStr, maxLength = 600) {
            if (!bioStr || !bioStr.trim()) {
                return { valid: true, value: "" };
            }
            const clean = sanitizeString(bioStr, maxLength);
            if (clean.length > maxLength) {
                return { valid: false, message: `النبذة التعريفية يجب ألا تتجاوز ${maxLength} حرفاً.` };
            }
            return { valid: true, value: clean };
        },

        /**
         * Validates public username / handle.
         */
        validateUsername: function (usernameStr) {
            if (!usernameStr || !usernameStr.trim()) {
                return { valid: false, message: "اسم المستخدم مطلوب." };
            }
            const clean = String(usernameStr).trim().toLowerCase();
            if (clean.length < 3) {
                return { valid: false, message: "اسم المستخدم قصير جداً (الحد الأدنى 3 أحرف)." };
            }
            if (clean.length > 40) {
                return { valid: false, message: "اسم المستخدم طويل جداً (الحد الأقصى 40 حرف)." };
            }
            if (!/^[a-z0-9][a-z0-9_\-\.]{1,38}[a-z0-9]$/.test(clean)) {
                return { valid: false, message: "اسم المستخدم يجب أن يحتوي على أحرف إنجليزية وأرقام وشرطات دون مسافات." };
            }
            if (RESERVED_USERNAMES.has(clean)) {
                return { valid: false, message: "اسم المستخدم هذا محجوز لنظام المنصة." };
            }
            return { valid: true, value: clean };
        },

        /**
         * Validates password strength (8+ chars, letters + numbers).
         */
        validatePassword: function (passwordStr) {
            if (!passwordStr) {
                return { valid: false, message: "كلمة المرور مطلوبة." };
            }
            if (passwordStr.length < 8) {
                return { valid: false, message: "كلمة المرور يجب ألا تقل عن 8 أحرف." };
            }
            if (passwordStr.length > 128) {
                return { valid: false, message: "كلمة المرور طويلة جداً (الحد الأقصى 128 حرف)." };
            }
            if (!/[a-zA-Z]/.test(passwordStr)) {
                return { valid: false, message: "كلمة المرور يجب أن تحتوي على حرف واحد على الأقل." };
            }
            if (!/[0-9]/.test(passwordStr)) {
                return { valid: false, message: "كلمة المرور يجب أن تحتوي على رقم واحد على الأقل." };
            }
            return { valid: true, value: passwordStr };
        },

        /**
         * Validates search queries (max 120 chars, defuses script injections).
         */
        validateSearchQuery: function (qStr) {
            if (!qStr) return { valid: true, value: "" };
            const clean = sanitizeString(qStr, 120);
            return { valid: true, value: clean };
        },

        // =====================================================================
        // REAL-TIME INPUT SANITIZERS (BLOCK JUNK DURING TYPING/PASTE)
        // =====================================================================

        sanitizeFullNameInput: function (inputEl) {
            if (!inputEl) return;
            const original = inputEl.value;
            // Allow Arabic/English letters, spaces, hyphens, and single quotes
            const filtered = original.replace(/[^\u0600-\u06FFa-zA-Z\s\.\-']/g, '').slice(0, 100);
            if (original !== filtered) {
                inputEl.value = filtered;
            }
        },

        sanitizeGpaInput: function (inputEl) {
            if (!inputEl) return;
            const original = inputEl.value;
            // Allowed: digits, '.', '%', '/'
            let filtered = original.replace(/[^0-9.%/]/g, '').slice(0, 10);
            if (original !== filtered) {
                inputEl.value = filtered;
            }
        },

        sanitizeUniversityInput: function (inputEl) {
            if (!inputEl) return;
            const original = inputEl.value;
            // Allowed: Arabic/English letters, digits, spaces, dots, hyphens, slashes, commas, parentheses, &
            let filtered = original.replace(/[^\u0600-\u06FFa-zA-Z0-9\s\.\-/,\u060C()&]/g, '').slice(0, 150);
            if (original !== filtered) {
                inputEl.value = filtered;
            }
        },

        sanitizeMajorInput: function (inputEl) {
            if (!inputEl) return;
            const original = inputEl.value;
            let filtered = original.replace(/[^\u0600-\u06FFa-zA-Z0-9\s\.\-&,/\u060C()]/g, '').slice(0, 100);
            if (original !== filtered) {
                inputEl.value = filtered;
            }
        },

        // =====================================================================
        // DOM UX & REAL-TIME INTERACTION HELPERS
        // =====================================================================

        showError: function (inputEl, errorMsg) {
            if (!inputEl) return;
            inputEl.classList.add('border-rose-500', 'focus:border-rose-500', 'ring-2', 'ring-rose-500/20');
            inputEl.classList.remove('border-slate-200', 'dark:border-slate-800');
            inputEl.setAttribute('aria-invalid', 'true');

            const errorId = (inputEl.id || inputEl.name || 'field') + 'Error';
            let errEl = document.getElementById(errorId);
            if (!errEl) {
                errEl = document.createElement('p');
                errEl.id = errorId;
                errEl.className = 'ea-validation-error text-[11px] text-rose-500 font-bold mt-1.5 flex items-center gap-1 transition-all duration-200';
                if (inputEl.parentNode) {
                    inputEl.parentNode.appendChild(errEl);
                }
            }
            errEl.textContent = errorMsg;
            errEl.classList.remove('hidden');
        },

        clearError: function (inputEl) {
            if (!inputEl) return;
            inputEl.classList.remove('border-rose-500', 'focus:border-rose-500', 'ring-2', 'ring-rose-500/20');
            inputEl.classList.add('border-slate-200', 'dark:border-slate-800');
            inputEl.setAttribute('aria-invalid', 'false');

            const errorId = (inputEl.id || inputEl.name || 'field') + 'Error';
            const errEl = document.getElementById(errorId);
            if (errEl) {
                errEl.textContent = '';
                errEl.classList.add('hidden');
            }
        },

        bindCharCounter: function (textareaEl, counterEl, maxLength = 600) {
            if (!textareaEl) return;
            if (!counterEl) {
                counterEl = document.getElementById(textareaEl.id + 'Counter');
                if (!counterEl && textareaEl.parentNode) {
                    counterEl = document.createElement('div');
                    counterEl.id = textareaEl.id + 'Counter';
                    counterEl.className = 'text-[11px] font-mono text-slate-400 mt-1 text-left';
                    textareaEl.parentNode.appendChild(counterEl);
                }
            }
            if (!counterEl) return;

            const update = () => {
                const count = textareaEl.value.length;
                counterEl.textContent = `${count} / ${maxLength}`;
                if (count >= maxLength) {
                    counterEl.className = 'text-[11px] font-mono text-rose-500 font-bold mt-1 text-left';
                } else if (count >= maxLength * 0.9) {
                    counterEl.className = 'text-[11px] font-mono text-amber-500 font-semibold mt-1 text-left';
                } else {
                    counterEl.className = 'text-[11px] font-mono text-slate-400 mt-1 text-left';
                }
            };
            textareaEl.addEventListener('input', update);
            update();
        },

        /**
         * Validates a single input element according to its data-validate or type attribute.
         */
        validateElement: function (inputEl) {
            if (!inputEl) return true;
            const type = inputEl.getAttribute('data-validate') || inputEl.type || inputEl.id;
            const val = inputEl.value;
            const isReq = inputEl.hasAttribute('required');

            let result = { valid: true };

            if (/fullname|name/i.test(type)) {
                result = this.validateFullName(val, isReq);
            } else if (/univ/i.test(type)) {
                result = this.validateUniversity(val, isReq);
            } else if (/major/i.test(type)) {
                result = this.validateMajor(val, isReq);
            } else if (/gpa/i.test(type)) {
                result = this.validateGpa(val, isReq);
            } else if (/country/i.test(type)) {
                result = this.validateCountry(val, isReq);
            } else if (/email/i.test(type)) {
                result = this.validateEmail(val);
            } else if (/phone|whatsapp/i.test(type)) {
                result = this.validatePhone(val, isReq);
            } else if (/username/i.test(type)) {
                result = this.validateUsername(val);
            } else if (/password/i.test(type)) {
                result = this.validatePassword(val);
            } else if (/bio/i.test(type)) {
                result = this.validateBio(val, parseInt(inputEl.getAttribute('maxlength')) || 600);
            }

            if (!result.valid) {
                this.showError(inputEl, result.message);
                return false;
            } else {
                this.clearError(inputEl);
                return true;
            }
        },

        /**
         * Automatically binds validation listeners and character counters to all form inputs in container.
         */
        init: function (container = document) {
            const inputs = container.querySelectorAll('[data-validate]');
            inputs.forEach(input => {
                const rule = input.getAttribute('data-validate');

                input.addEventListener('input', () => {
                    if (rule === 'fullname') this.sanitizeFullNameInput(input);
                    if (rule === 'gpa') this.sanitizeGpaInput(input);
                    if (rule === 'university') this.sanitizeUniversityInput(input);
                    if (rule === 'major') this.sanitizeMajorInput(input);
                    if (input.value.trim().length >= 2) {
                        this.validateElement(input);
                    } else {
                        this.clearError(input);
                    }
                });

                input.addEventListener('blur', () => {
                    this.validateElement(input);
                });
            });

            // Auto-bind character counters for textareas with maxlength
            const textareas = container.querySelectorAll('textarea[maxlength], textarea[data-counter="true"]');
            textareas.forEach(ta => {
                const max = parseInt(ta.getAttribute('maxlength')) || 600;
                this.bindCharCounter(ta, null, max);
            });
        }
    };

    // Auto-init on DOMContentLoaded if in browser
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => EduAtlasValidator.init());
        } else {
            EduAtlasValidator.init();
        }
    }

    return EduAtlasValidator;
}));
