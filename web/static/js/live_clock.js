/**
 * EduAtlas - Live Real-Time Date & Clock Engine
 * Updates date and time dynamically every second across all platform pages.
 */
(function () {
    'use strict';

    const ARABIC_DAYS = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
    const ARABIC_MONTHS = [
        'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
        'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
    ];

    function getFormattedDateTime(now = new Date()) {
        const dayName = ARABIC_DAYS[now.getDay()];
        const day = now.getDate();
        const monthName = ARABIC_MONTHS[now.getMonth()];
        const year = now.getFullYear();

        const fullDateArabic = `${dayName}، ${day} ${monthName} ${year}`;
        const shortDateArabic = `${day} ${monthName} ${year}`;

        let hours = now.getHours();
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        const period = hours >= 12 ? 'م' : 'ص';
        const hours12 = hours % 12 || 12;
        const formattedHours = String(hours12).padStart(2, '0');

        const time12WithSec = `${formattedHours}:${minutes}:${seconds} ${period}`;
        const time12Compact = `${formattedHours}:${minutes} ${period}`;
        const time24 = `${String(now.getHours()).padStart(2, '0')}:${minutes}:${seconds}`;

        return {
            fullDateArabic,
            shortDateArabic,
            time12WithSec,
            time12Compact,
            time24,
            iso: now.toISOString()
        };
    }

    function updateAllClockElements() {
        const dt = getFormattedDateTime();

        // 1. Full Date Elements
        const dateElements = document.querySelectorAll(
            '#liveCurrentDate, .live-current-date, .liveDrawerDate, [data-live-date]'
        );
        dateElements.forEach(el => {
            if (el.textContent !== dt.fullDateArabic) {
                el.textContent = dt.fullDateArabic;
                el.setAttribute('title', dt.fullDateArabic);
            }
        });

        // 2. Full Live Time Elements (HH:MM:SS AM/PM)
        const timeElements = document.querySelectorAll(
            '#liveCurrentTime, .live-current-time, .liveDrawerTime, [data-live-time]'
        );
        timeElements.forEach(el => {
            if (el.textContent !== dt.time12WithSec) {
                el.textContent = dt.time12WithSec;
                el.setAttribute('title', `الوقت المحلي: ${dt.time12WithSec}`);
            }
        });

        // 3. Compact Live Time Elements (HH:MM AM/PM)
        const compactElements = document.querySelectorAll(
            '#liveCompactTime, .liveCompactTime, [data-live-compact-time]'
        );
        compactElements.forEach(el => {
            if (el.textContent !== dt.time12Compact) {
                el.textContent = dt.time12Compact;
            }
        });
    }

    function initClock() {
        updateAllClockElements();
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            try {
                window.lucide.createIcons();
            } catch (_e) {}
        }
    }

    // Initialize immediately
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initClock);
    } else {
        initClock();
    }

    // Update dynamically every second (1000ms)
    setInterval(updateAllClockElements, 1000);

    // Refresh immediately when tab gains visibility (prevents freeze on background tab wakeup)
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) {
            updateAllClockElements();
        }
    });

    // Expose utility globally
    window.EduAtlasClock = {
        getDateTime: getFormattedDateTime,
        update: updateAllClockElements
    };
})();
