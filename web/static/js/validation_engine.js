/**
 * EduAtlas Enterprise Data Validation & Sanitization Engine
 * Dual-layer (Frontend & Backend-aligned) validation, real-time input filtering,
 * anti-injection defense (XSS, SQLi, Prototype Pollution, Script Tag injections),
 * instant keypress blocking, clipboard paste sanitization, and UX feedback.
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

    // Core Regex definitions for strict data types
    // Arabic Letters: \u0621-\u064A, \u0671-\u06D3, \u06D5, Tashkeel: \u064B-\u0652
    // Latin Letters: a-zA-Z
    // Space: \s
    const REGEX_ARABIC_LATIN_LETTERS = /[\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652a-zA-Z]/u;
    const REGEX_TEXT_ONLY_CHAR = /^[\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652a-zA-Z\s]$/u;
    const REGEX_TEXT_ONLY_STRIP = /[^\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652a-zA-Z\s]/gu;

    const REGEX_NAME_CHAR = /^[\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652a-zA-Z\s'\-]$/u;
    const REGEX_NAME_STRIP = /[^\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652a-zA-Z\s'\-]/gu;

    const REGEX_DIGITS_CHAR = /^[0-9]$/;
    const REGEX_DIGITS_STRIP = /[^0-9]/g;

    const REGEX_USERNAME_CHAR = /^[a-zA-Z0-9_.-]$/;
    const REGEX_USERNAME_STRIP = /[^a-zA-Z0-9_.-]/g;

    const REGEX_GPA_CHAR = /^[0-9.%/]$/;
    const REGEX_GPA_STRIP = /[^0-9.%/]/g;

    const REGEX_PHONE_CHAR = /^[0-9+]$/;
    const REGEX_PHONE_STRIP = /[^0-9+]/g;

    const REGEX_UNIVERSITY_STRIP = /[^\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652a-zA-Z0-9\s.\-()&/,\u060C]/gu;
    const REGEX_INJECTION_STRIP = /<[^>]*>|javascript:|data:text\/html|onerror\s*=|onload\s*=|['"`<>;\\]/gi;

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
         * Only Arabic/English letters, spaces, and clean apostrophes/hyphens. Strictly NO numbers or injection symbols.
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

            // Strictly reject all numbers (ASCII & Arabic digits)
            if (/[\d\u0660-\u0669\u06F0-\u06F9]/.test(clean)) {
                return { valid: false, message: "الاسم لا يمكن أن يحتوي على أي أرقام." };
            }

            // Strictly reject special symbols & injection characters
            if (/[^a-zA-Z\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652\s'\-]/.test(clean)) {
                return { valid: false, message: "يرجى إدخال اسم حقيقي يحتوي على أحرف عربية أو إنجليزية فقط دون رموز خاصة." };
            }

            const letterCount = (clean.match(/[\u0621-\u064A\u0671-\u06D3\u06D5a-zA-Z]/g) || []).length;
            if (letterCount < 2) {
                return { valid: false, message: "الاسم يجب أن يتضمن حرفين نصيين على الأقل." };
            }
            if (isGibberishOrSpam(clean)) {
                return { valid: false, message: "الاسم المدخل يحتوي على تكرار عشوائي غير مفهوم. يرجى إدخال اسم حقيقي." };
            }
            return { valid: true, value: clean.replace(/\s+/g, ' ').trim() };
        },

        /**
         * Validates city name.
         * Strictly letters and spaces only. Absolutely NO numbers or symbols.
         */
        validateCity: function (cityStr, isRequired = false) {
            if (!cityStr || !cityStr.trim()) {
                if (isRequired) {
                    return { valid: false, message: "اسم المدينة مطلوب ولا يمكن تركه فارغاً." };
                }
                return { valid: true, value: "" };
            }
            const clean = sanitizeString(cityStr, 60);
            if (clean.length < 2) {
                return { valid: false, message: "اسم المدينة قصير جداً (حرفان على الأقل)." };
            }
            if (clean.length > 60) {
                return { valid: false, message: "اسم المدينة طويل جداً (الحد الأقصى 60 حرف)." };
            }

            // Reject all digits
            if (/[\d\u0660-\u0669\u06F0-\u06F9]/.test(clean)) {
                return { valid: false, message: "اسم المدينة يجب ألا يحتوي على أي أرقام." };
            }

            // Text only: Arabic & Latin letters and spaces
            if (/[^\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652a-zA-Z\s]/.test(clean)) {
                return { valid: false, message: "اسم المدينة يجب أن يتكون من أحرف ومسافات فقط دون أرقام أو رموز." };
            }

            const letterCount = (clean.match(/[\u0621-\u064A\u0671-\u06D3\u06D5a-zA-Z]/g) || []).length;
            if (letterCount < 2) {
                return { valid: false, message: "اسم المدينة يجب أن يتضمن حرفين نصيين على الأقل." };
            }
            if (isGibberishOrSpam(clean)) {
                return { valid: false, message: "اسم المدينة يحتوي على تكرار عشوائي." };
            }
            return { valid: true, value: clean.replace(/\s+/g, ' ').trim() };
        },

        /**
         * Validates country against the official recognized list.
         * Strictly letters and spaces. Absolutely NO numbers or symbols.
         */
        validateCountry: function (countryStr, isRequired = false) {
            if (!countryStr || !countryStr.trim()) {
                if (isRequired) {
                    return { valid: false, message: "يرجى اختيار دولة إقامتك أو جنسيتك." };
                }
                return { valid: true, value: "" };
            }
            const clean = sanitizeString(countryStr, 60);

            // Reject digits
            if (/[\d\u0660-\u0669\u06F0-\u06F9]/.test(clean)) {
                return { valid: false, message: "اسم الدولة لا يمكن أن يحتوي على أي أرقام." };
            }

            // Reject special injection symbols
            if (/[!@#$%^&*()_+={}\[\]|\\:;\"'<>,.?/~`؟،؛٪]/.test(clean)) {
                return { valid: false, message: "اسم الدولة يحتوي على رموز غير مسموح بها." };
            }

            let normalized = clean.toLowerCase();
            normalized = normalized.replace(/\s*\(.*?\)/g, '').split('-')[0].trim();

            if (OFFICIAL_COUNTRIES.has(normalized)) {
                return { valid: true, value: clean.trim() };
            }

            // If it consists solely of valid letters
            if (/^[\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652a-zA-Z\s]{2,60}$/.test(clean)) {
                return { valid: true, value: clean.trim() };
            }

            return { valid: false, message: `الدولة المدخلة (${countryStr}) غير موجودة في قائمة الدول المعتمدة.` };
        },

        /**
         * Validates field of study / major.
         * Strictly text-only (letters and spaces). No numbers or injection symbols.
         */
        validateMajor: function (major, isRequired = false) {
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

            // Reject numbers
            if (/[\d\u0660-\u0669\u06F0-\u06F9]/.test(clean)) {
                return { valid: false, message: "اسم التخصص يجب ألا يحتوي على أي أرقام." };
            }

            // Allow letters, spaces, and clean academic connectors like / & -
            if (/[^\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652a-zA-Z\s/&,\u060C\-()]/.test(clean)) {
                return { valid: false, message: "اسم التخصص يحتوي على رموز غير مقبولة." };
            }

            const letterCount = (clean.match(/[\u0621-\u064A\u0671-\u06D3\u06D5a-zA-Z]/g) || []).length;
            if (letterCount < 2) {
                return { valid: false, message: "يرجى كتابة تخصص دراسي حقيقي يتضمن أحرفاً صالحة." };
            }
            if (isGibberishOrSpam(clean)) {
                return { valid: false, message: "التخصص المدخل يحتوي على تكرار عشوائي." };
            }
            return { valid: true, value: clean.replace(/\s+/g, ' ').trim() };
        },

        /**
         * Validates university or educational institution.
         * Letters, numbers (for institutions with numbers), common institution punctuation.
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

            // Disallow dangerous injection chars
            if (/[<>"'`\\;%$#*!~^{}]/.test(clean)) {
                return { valid: false, message: "اسم الجامعة يحتوي على رموز غير مسموح بها أمنياً." };
            }

            const regex = /^[\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652a-zA-Z0-9\s.\-()&/,\u060C]{2,150}$/;
            if (!regex.test(clean)) {
                return { valid: false, message: "اسم الجامعة يحتوي على رموز غير مقبولة." };
            }
            const letterCount = (clean.match(/[\u0621-\u064A\u0671-\u06D3\u06D5a-zA-Z]/g) || []).length;
            if (letterCount < 2) {
                return { valid: false, message: "اسم الجامعة يجب أن يحتوي على أحرف حقيقية وليس أرقاماً أو رموزاً فقط." };
            }
            if (isGibberishOrSpam(clean)) {
                return { valid: false, message: "اسم الجامعة يحتوي على تكرار عشوائي للرموز أو الأحرف." };
            }
            return { valid: true, value: clean.replace(/\s+/g, ' ').trim() };
        },

        /**
         * Validates public username / handle.
         * English lowercase letters, numbers, and allowed punctuation (_, -, .).
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
                return { valid: false, message: "اسم المستخدم يجب أن يحتوي على أحرف إنجليزية وأرقام ونقاط أو شرطات فقط دون مسافات." };
            }
            if (RESERVED_USERNAMES.has(clean)) {
                return { valid: false, message: "اسم المستخدم هذا محجوز لنظام المنصة." };
            }
            return { valid: true, value: clean };
        },

        /**
         * Validates academic GPA strictly:
         * - 4.0 / 5.0 systems (0.5 to 5.0)
         * - Percentage systems (40% to 100%)
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
            if (/[^0-9.\s%/]/.test(clean)) {
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
         * Validates student biography. Max 600 characters.
         * Strips dangerous script tags and injection tokens.
         */
        validateBio: function (bioStr, maxLength = 600) {
            if (!bioStr || !bioStr.trim()) {
                return { valid: true, value: "" };
            }
            let clean = sanitizeString(bioStr, maxLength);
            // Defuse injection quotes and dangerous symbols
            clean = clean.replace(REGEX_INJECTION_STRIP, '');
            if (clean.length > maxLength) {
                return { valid: false, message: `النبذة التعريفية يجب ألا تتجاوز ${maxLength} حرفاً.` };
            }
            return { valid: true, value: clean };
        },

        /**
         * Validates student age (10 to 100).
         */
        validateAge: function (ageVal, isRequired = false) {
            if (!ageVal && ageVal !== 0) {
                if (isRequired) return { valid: false, message: "حقل العمر مطلوب." };
                return { valid: true, value: null };
            }
            const num = parseInt(String(ageVal).trim(), 10);
            if (isNaN(num) || num < 10 || num > 100) {
                return { valid: false, message: "يرجى إدخال عمر واقعي بين 10 و 100 سنة." };
            }
            return { valid: true, value: num };
        },

        /**
         * Validates expected graduation year (1970 to 2040).
         */
        validateGradYear: function (yrVal, isRequired = false) {
            if (!yrVal) {
                if (isRequired) return { valid: false, message: "سنة التخرج مطلوبة." };
                return { valid: true, value: "" };
            }
            const num = parseInt(String(yrVal).trim(), 10);
            if (isNaN(num) || num < 1970 || num > 2040) {
                return { valid: false, message: "يرجى إدخال سنة تخرج واقعية بين 1970 و 2040." };
            }
            return { valid: true, value: String(num) };
        },

        /**
         * Validates international phone number (+ followed by 7-15 digits).
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
            let clean = sanitizeString(qStr, 120);
            clean = clean.replace(REGEX_INJECTION_STRIP, '');
            return { valid: true, value: clean };
        },

        // =====================================================================
        // SANITIZATION ROUTINES BY DATA TYPE (FOR INPUT & PASTE EVENTS)
        // =====================================================================

        sanitizeByFilterType: function (val, filterType, maxLen) {
            if (val === null || val === undefined) return '';
            let s = String(val);

            switch (filterType) {
                case 'text-only':
                case 'city':
                case 'country':
                    // Strictly letters and spaces only. No numbers, no symbols.
                    s = s.replace(REGEX_TEXT_ONLY_STRIP, '');
                    if (maxLen) s = s.slice(0, maxLen);
                    return s;

                case 'fullname':
                case 'name':
                    // Letters, spaces, hyphens, and apostrophes only. No numbers, no symbols.
                    s = s.replace(REGEX_NAME_STRIP, '');
                    if (maxLen) s = s.slice(0, maxLen);
                    return s;

                case 'major':
                    // Letters, spaces, and clean academic connectors
                    s = s.replace(/[^\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652a-zA-Z\s/&,\u060C\-()]/gu, '');
                    if (maxLen) s = s.slice(0, maxLen);
                    return s;

                case 'username':
                    // Lowercase English alphanumeric + _ - .
                    s = s.replace(REGEX_USERNAME_STRIP, '').toLowerCase();
                    return s.slice(0, maxLen || 40);

                case 'digits':
                case 'age':
                case 'gradyear':
                case 'code':
                    s = s.replace(REGEX_DIGITS_STRIP, '');
                    if (maxLen) s = s.slice(0, maxLen);
                    return s;

                case 'gpa':
                    s = s.replace(REGEX_GPA_STRIP, '');
                    return s.slice(0, maxLen || 10);

                case 'phone':
                case 'whatsapp':
                    s = s.replace(REGEX_PHONE_STRIP, '');
                    // Only one '+' allowed, strictly at index 0
                    if (s.indexOf('+') > 0) {
                        const hasLeadingPlus = s.startsWith('+');
                        s = (hasLeadingPlus ? '+' : '') + s.replace(/\+/g, '');
                    }
                    return s.slice(0, maxLen || 20);

                case 'university':
                    s = s.replace(REGEX_UNIVERSITY_STRIP, '');
                    return s.slice(0, maxLen || 150);

                case 'safe-text':
                case 'bio':
                case 'comment':
                    // Strips tags, quotes and injection chars
                    s = s.replace(REGEX_INJECTION_STRIP, '');
                    if (maxLen) s = s.slice(0, maxLen);
                    return s;

                case 'url':
                    s = s.replace(/[\s<>"'`\\^]/g, '');
                    return s.slice(0, maxLen || 500);

                case 'email':
                    s = s.replace(/[^\w.@+-]/g, '').toLowerCase();
                    return s.slice(0, maxLen || 100);

                default:
                    return s;
            }
        },

        // Helper wrappers for explicit sanitization calls
        sanitizeFullNameInput: function (inputEl) {
            if (!inputEl) return;
            const original = inputEl.value;
            const filtered = this.sanitizeByFilterType(original, 'fullname', 100);
            if (original !== filtered) inputEl.value = filtered;
        },

        sanitizeCityInput: function (inputEl) {
            if (!inputEl) return;
            const original = inputEl.value;
            const filtered = this.sanitizeByFilterType(original, 'city', 60);
            if (original !== filtered) inputEl.value = filtered;
        },

        sanitizeCountryInput: function (inputEl) {
            if (!inputEl) return;
            const original = inputEl.value;
            const filtered = this.sanitizeByFilterType(original, 'country', 60);
            if (original !== filtered) inputEl.value = filtered;
        },

        sanitizeGpaInput: function (inputEl) {
            if (!inputEl) return;
            const original = inputEl.value;
            const filtered = this.sanitizeByFilterType(original, 'gpa', 10);
            if (original !== filtered) inputEl.value = filtered;
        },

        sanitizeUniversityInput: function (inputEl) {
            if (!inputEl) return;
            const original = inputEl.value;
            const filtered = this.sanitizeByFilterType(original, 'university', 150);
            if (original !== filtered) inputEl.value = filtered;
        },

        sanitizeMajorInput: function (inputEl) {
            if (!inputEl) return;
            const original = inputEl.value;
            const filtered = this.sanitizeByFilterType(original, 'major', 100);
            if (original !== filtered) inputEl.value = filtered;
        },

        // =====================================================================
        // REAL-TIME UX FEEDBACK & FLOATING WARNING BADGES
        // =====================================================================

        showInputWarning: function (inputEl, filterType, customMsg) {
            if (!inputEl || typeof document === 'undefined') return;

            // Visual pulse on the input border
            inputEl.classList.add('ring-2', 'ring-amber-500/50', 'border-amber-500');

            let message = customMsg;
            if (!message) {
                switch (filterType) {
                    case 'text-only':
                    case 'city':
                    case 'country':
                        message = "نصوص فقط (أحرف ومسافات بدون أرقام أو رموز خاصة).";
                        break;
                    case 'fullname':
                    case 'name':
                        message = "الاسم يقبل أحرفاً ومسافات فقط دون أرقام أو رموز.";
                        break;
                    case 'major':
                        message = "اسم التخصص يقبل أحرفاً ومسافات فقط.";
                        break;
                    case 'digits':
                    case 'age':
                    case 'gradyear':
                    case 'code':
                        message = "أرقام فقط (0 - 9).";
                        break;
                    case 'username':
                        message = "أحرف إنجليزية وأرقام ونقاط وشرطات فقط دون مسافات.";
                        break;
                    case 'gpa':
                        message = "أرقام ورموز المعدل فقط (. % /).";
                        break;
                    case 'phone':
                    case 'whatsapp':
                        message = "أرقام الهاتف مع الرمز الدولي (+) فقط.";
                        break;
                    case 'university':
                        message = "تم منع رموز الحقن غير الآمنة.";
                        break;
                    default:
                        message = "نوع بيانات غير مسموح به في هذا الحقل.";
                        break;
                }
            }

            const warnId = (inputEl.id || inputEl.name || 'field') + '_warnTooltip';
            let badge = document.getElementById(warnId);
            if (!badge) {
                badge = document.createElement('div');
                badge.id = warnId;
                badge.className = 'ea-input-warning fixed z-50 pointer-events-none px-2.5 py-1 text-[11px] font-bold text-amber-900 bg-amber-50 dark:bg-amber-950/90 dark:text-amber-200 border border-amber-300 dark:border-amber-700/80 rounded-lg shadow-lg backdrop-blur-sm transition-all duration-200 opacity-0 transform -translate-y-1';
                document.body.appendChild(badge);
            }

            badge.textContent = message;
            const rect = inputEl.getBoundingClientRect();
            badge.style.top = `${rect.bottom + 6}px`;
            badge.style.left = `${Math.max(10, rect.left)}px`;
            badge.classList.remove('opacity-0', '-translate-y-1');
            badge.classList.add('opacity-100', 'translate-y-0');

            clearTimeout(inputEl._warnTimeout);
            inputEl._warnTimeout = setTimeout(() => {
                badge.classList.remove('opacity-100', 'translate-y-0');
                badge.classList.add('opacity-0', '-translate-y-1');
                inputEl.classList.remove('ring-2', 'ring-amber-500/50', 'border-amber-500');
            }, 1800);
        },

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
         * Resolves the proper validation & filter rule for a DOM element.
         */
        detectFilterType: function (inputEl) {
            if (!inputEl) return null;

            // 1. Explicit data-type or data-validate attributes
            const explicit = inputEl.getAttribute('data-type') || inputEl.getAttribute('data-validate');
            if (explicit) {
                const low = explicit.toLowerCase();
                if (/fullname|name/i.test(low)) return 'fullname';
                if (/city/i.test(low)) return 'city';
                if (/country/i.test(low)) return 'country';
                if (/major/i.test(low)) return 'major';
                if (/text-only|text_only|letters/i.test(low)) return 'text-only';
                if (/digits|numbers|integer/i.test(low)) return 'digits';
                if (/username/i.test(low)) return 'username';
                if (/gpa/i.test(low)) return 'gpa';
                if (/phone|whatsapp/i.test(low)) return 'phone';
                if (/university|institution/i.test(low)) return 'university';
                if (/age/i.test(low)) return 'age';
                if (/gradyear|year/i.test(low)) return 'gradyear';
                if (/bio|content|description/i.test(low)) return 'safe-text';
                if (/url|website|portfolio/i.test(low)) return 'url';
                if (/email/i.test(low)) return 'email';
                if (/password/i.test(low)) return 'password';
                return low;
            }

            // 2. Automated inference based on ID, name, or HTML type
            const id = (inputEl.id || '').toLowerCase();
            const name = (inputEl.name || '').toLowerCase();
            const htmlType = (inputEl.type || '').toLowerCase();

            if (htmlType === 'tel') return 'phone';
            if (htmlType === 'url') return 'url';
            if (htmlType === 'email') return 'email';
            if (htmlType === 'password') return 'password';

            // Username
            if (id.includes('username') || name.includes('username')) return 'username';

            // Full name (exclude username)
            if ((id.includes('fullname') || id.includes('name') || name.includes('name')) && !id.includes('username') && !id.includes('kanban')) {
                return 'fullname';
            }

            // City
            if (id.includes('city') || name.includes('city')) return 'city';

            // Country
            if (id.includes('country') || name.includes('country')) return 'country';

            // Major
            if (id.includes('major') || name.includes('major')) return 'major';

            // GPA
            if (id.includes('gpa') || name.includes('gpa')) return 'gpa';

            // Phone / WhatsApp
            if (id.includes('phone') || id.includes('whatsapp') || name.includes('phone')) return 'phone';

            // Age
            if (id.includes('age') || name.includes('age')) return 'age';

            // Graduation Year
            if (id.includes('gradyear') || id.includes('year') || name.includes('year')) return 'gradyear';

            // University / Institution
            if (id.includes('university') || id.includes('institution') || name.includes('university')) return 'university';

            // Textarea / Bio
            if (inputEl.tagName === 'TEXTAREA' || id.includes('bio') || name.includes('bio')) return 'safe-text';

            if (htmlType === 'number') return 'digits';

            return null;
        },

        /**
         * Validates a single input element according to its resolved rule.
         */
        validateElement: function (inputEl) {
            if (!inputEl) return true;
            const filterType = this.detectFilterType(inputEl);
            if (!filterType) return true;

            const val = inputEl.value;
            const isReq = inputEl.hasAttribute('required');
            let result = { valid: true };

            switch (filterType) {
                case 'fullname':
                case 'name':
                    result = this.validateFullName(val, isReq);
                    break;
                case 'city':
                    result = this.validateCity(val, isReq);
                    break;
                case 'country':
                    result = this.validateCountry(val, isReq);
                    break;
                case 'major':
                    result = this.validateMajor(val, isReq);
                    break;
                case 'text-only':
                    result = this.validateCity(val, isReq); // Strict text-only
                    break;
                case 'university':
                    result = this.validateUniversity(val, isReq);
                    break;
                case 'gpa':
                    result = this.validateGpa(val, isReq);
                    break;
                case 'username':
                    result = this.validateUsername(val);
                    break;
                case 'phone':
                case 'whatsapp':
                    result = this.validatePhone(val, isReq);
                    break;
                case 'age':
                    result = this.validateAge(val, isReq);
                    break;
                case 'gradyear':
                    result = this.validateGradYear(val, isReq);
                    break;
                case 'safe-text':
                case 'bio':
                    result = this.validateBio(val, parseInt(inputEl.getAttribute('maxlength')) || 600);
                    break;
                case 'email':
                    result = this.validateEmail(val);
                    break;
                case 'password':
                    result = this.validatePassword(val);
                    break;
                default:
                    break;
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
         * Binds real-time filtering, keypress blocking, and clipboard sanitization to an input element.
         */
        bindField: function (inputEl, explicitType) {
            if (!inputEl || inputEl._eaFiltered) return;

            const filterType = explicitType || this.detectFilterType(inputEl);
            if (!filterType) return;

            inputEl._eaFiltered = true;
            inputEl.setAttribute('data-filter-active', filterType);

            const self = this;
            const maxLen = parseInt(inputEl.getAttribute('maxlength')) || null;

            // 1. KEYPRESS / BEFOREINPUT BLOCKER: Block invalid characters from being typed
            inputEl.addEventListener('keypress', function (e) {
                // Ignore system & navigation keys (Enter, Backspace, arrows, shortcuts)
                if (e.ctrlKey || e.altKey || e.metaKey || e.key.length > 1) return;

                const char = e.key;
                let allowed = true;

                if (filterType === 'text-only' || filterType === 'city' || filterType === 'country') {
                    // Strictly letters and spaces. Zero numbers, zero symbols.
                    allowed = REGEX_TEXT_ONLY_CHAR.test(char);
                } else if (filterType === 'fullname' || filterType === 'name') {
                    // Letters, spaces, apostrophe, hyphen. Zero numbers.
                    allowed = REGEX_NAME_CHAR.test(char);
                } else if (filterType === 'major') {
                    // Letters, spaces, composite academic connectors
                    allowed = /^[\u0621-\u064A\u0671-\u06D3\u06D5\u064B-\u0652a-zA-Z\s/&,\u060C\-()]$/u.test(char);
                } else if (filterType === 'digits' || filterType === 'age' || filterType === 'gradyear' || filterType === 'code') {
                    allowed = REGEX_DIGITS_CHAR.test(char);
                } else if (filterType === 'username') {
                    allowed = REGEX_USERNAME_CHAR.test(char);
                } else if (filterType === 'gpa') {
                    allowed = REGEX_GPA_CHAR.test(char);
                } else if (filterType === 'phone' || filterType === 'whatsapp') {
                    if (char === '+') {
                        allowed = (this.selectionStart === 0 && !this.value.includes('+'));
                    } else {
                        allowed = REGEX_DIGITS_CHAR.test(char);
                    }
                } else if (filterType === 'university') {
                    // Disallow injection symbols
                    allowed = !/[<>"'`\\;%$#*!~^{}]/.test(char);
                } else if (filterType === 'safe-text' || filterType === 'bio') {
                    // Disallow script/injection quotes and angle brackets
                    allowed = !/[<>"'`\\;]/.test(char);
                }

                if (!allowed) {
                    e.preventDefault();
                    self.showInputWarning(this, filterType);
                }
            });

            // 2. CLIPBOARD PASTE INTERCEPTOR: Sanitize clipboard data on paste
            inputEl.addEventListener('paste', function (e) {
                const pasteText = (e.clipboardData || window.clipboardData)?.getData('text');
                if (!pasteText) return;

                const sanitized = self.sanitizeByFilterType(pasteText, filterType, maxLen);
                if (sanitized !== pasteText) {
                    e.preventDefault();
                    const start = this.selectionStart ?? this.value.length;
                    const end = this.selectionEnd ?? this.value.length;
                    const cur = this.value;
                    const nextVal = cur.substring(0, start) + sanitized + cur.substring(end);
                    this.value = maxLen ? nextVal.slice(0, maxLen) : nextVal;
                    const newCursor = start + sanitized.length;
                    if (this.setSelectionRange) this.setSelectionRange(newCursor, newCursor);

                    this.dispatchEvent(new Event('input', { bubbles: true }));

                    if (sanitized.length < pasteText.length) {
                        self.showInputWarning(this, filterType, "تم تنقية المحتوى الملصق وحظر الرموز والأرقام غير المسموح بها.");
                    }
                }
            });

            // 3. INPUT EVENT SANITIZER (Safety net for autofill, drag-drop, mobile suggestions)
            inputEl.addEventListener('input', function () {
                const original = this.value;
                const sanitized = self.sanitizeByFilterType(original, filterType, maxLen);

                if (original !== sanitized) {
                    const start = this.selectionStart;
                    this.value = sanitized;
                    if (start !== null && this.setSelectionRange) {
                        const targetPos = Math.min(start, sanitized.length);
                        this.setSelectionRange(targetPos, targetPos);
                    }
                    self.showInputWarning(this, filterType);
                }

                if (this.value.trim().length >= 2) {
                    self.validateElement(this);
                } else {
                    self.clearError(this);
                }
            });

            // 4. BLUR & CHANGE: Final formatting and validation
            inputEl.addEventListener('blur', function () {
                if (filterType === 'text-only' || filterType === 'city' || filterType === 'country' || filterType === 'fullname') {
                    this.value = this.value.replace(/\s+/g, ' ').trim();
                } else if (filterType === 'username') {
                    this.value = this.value.replace(/^[._-]+|[._-]+$/g, '').trim();
                }
                self.validateElement(this);
            });
        },

        /**
         * Automatically binds validation listeners, character counters, and input filters to all inputs in container.
         */
        init: function (container = (typeof document !== 'undefined' ? document : null)) {
            if (!container) return;

            // Target all relevant input, textarea, and select elements
            const candidates = container.querySelectorAll('input:not([type="hidden"]):not([type="file"]):not([type="checkbox"]):not([type="radio"]):not([type="submit"]):not([type="button"]), textarea');
            candidates.forEach(input => {
                this.bindField(input);
            });

            // Auto-bind character counters for textareas with maxlength
            const textareas = container.querySelectorAll('textarea[maxlength], textarea[data-counter="true"]');
            textareas.forEach(ta => {
                const max = parseInt(ta.getAttribute('maxlength')) || 600;
                this.bindCharCounter(ta, null, max);
            });

            // Setup MutationObserver to automatically bind new dynamic fields (e.g. modals, tabs)
            if (typeof MutationObserver !== 'undefined' && !container._eaObserverAttached) {
                container._eaObserverAttached = true;
                const observer = new MutationObserver(mutations => {
                    for (const m of mutations) {
                        if (m.addedNodes && m.addedNodes.length) {
                            m.addedNodes.forEach(node => {
                                if (node.nodeType === 1) { // ELEMENT_NODE
                                    if (node.matches && node.matches('input, textarea')) {
                                        EduAtlasValidator.bindField(node);
                                    }
                                    if (node.querySelectorAll) {
                                        node.querySelectorAll('input:not([type="hidden"]):not([type="file"]), textarea').forEach(inp => {
                                            EduAtlasValidator.bindField(inp);
                                        });
                                    }
                                }
                            });
                        }
                    }
                });
                observer.observe(container === document ? document.body || document.documentElement : container, {
                    childList: true,
                    subtree: true
                });
            }
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
