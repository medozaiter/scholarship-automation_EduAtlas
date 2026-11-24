/**
 * EduAtlas — warm-scholar.js
 * Vanilla JS micro-interactions for instant search, compass gauge & mobile drawer
 */

(function () {
  'use strict';

  // ===================================================================
  // 1. THEME MANAGER (DARK / LIGHT PARCHMENT)
  // ===================================================================
  window.toggleEduAtlasTheme = function (explicitMode) {
    let shouldBeDark;
    if (explicitMode === 'dark') {
      shouldBeDark = true;
    } else if (explicitMode === 'light') {
      shouldBeDark = false;
    } else {
      shouldBeDark = !document.documentElement.classList.contains('dark');
    }

    if (shouldBeDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }

    const newTheme = shouldBeDark ? 'dark' : 'light';
    try {
      localStorage.setItem('theme', newTheme);
      localStorage.theme = newTheme;
    } catch(_e) {}

    updateThemeToggleIcons();

    try {
      window.dispatchEvent(new CustomEvent('themechange', { detail: { isDark: shouldBeDark, theme: newTheme } }));
    } catch(_e) {}
  };

  function updateThemeToggleIcons() {
    const isDark = document.documentElement.classList.contains('dark');
    
    // 1. Update all navbar toggle buttons
    const mainIcon = document.getElementById('themeIcon');
    if (mainIcon) {
      mainIcon.innerHTML = isDark
        ? '<svg class="w-4 h-4 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'
        : '<svg class="w-4 h-4 text-slate-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    }

    const navBtn = document.getElementById('themeToggleBtn');
    if (navBtn) {
      navBtn.title = isDark ? "التبديل إلى الوضع النهاري (فاتح)" : "التبديل إلى الوضع الليلي (داكن)";
      navBtn.setAttribute('aria-label', isDark ? "التبديل إلى الوضع النهاري" : "التبديل إلى الوضع الليلي");
    }

    // 2. Update all mobile drawer theme tiles
    const drawerBtns = document.querySelectorAll('.ea-drawer-theme-btn, #drawerThemeToggleBtn');
    drawerBtns.forEach(btn => {
      const textEl = btn.querySelector('.ea-drawer-theme-text');
      const iconEl = btn.querySelector('.ea-drawer-theme-icon');
      if (textEl) {
        textEl.textContent = isDark ? "الوضع النهاري (فاتح)" : "الوضع الليلي (داكن)";
      }
      if (iconEl) {
        iconEl.innerHTML = isDark
          ? '<svg class="w-4 h-4 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'
          : '<svg class="w-4 h-4 text-slate-600 dark:text-slate-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
      }
    });

    const icons = document.querySelectorAll('.ea-theme-toggle-icon');
    icons.forEach(icon => {
      icon.setAttribute('data-lucide', isDark ? 'sun' : 'moon');
    });

    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      try { window.lucide.createIcons(); } catch(_e) {}
    }
  }

  // Universal aliases
  window.toggleTheme = window.toggleEduAtlasTheme;
  window.updateThemeButton = updateThemeToggleIcons;
  window.updateThemeIcon = updateThemeToggleIcons;

  // Sync on DOM loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateThemeToggleIcons);
  } else {
    updateThemeToggleIcons();
  }

  // ===================================================================
  // 2. INSTANT SEARCH DEBOUNCE ENGINE
  // ===================================================================
  /**
   * @param {Function} func
   * @param {number} wait
   * @returns {(...args: any[]) => void}
   */
  function debounce(func, wait) {
    /** @type {any} */
    let timeout;
    /**
     * @this {any}
     * @param {...any} args
     */
    return function (...args) {
      clearTimeout(timeout);
      const self = this;
      timeout = setTimeout(() => func.apply(self, args), wait);
    };
  }

  /**
   * @param {string} inputSelector
   * @param {string} itemsSelector
   * @param {((query: string) => void) | null | undefined} [onSearchCallback]
   */
  window.setupInstantScholarshipSearch = function (inputSelector, itemsSelector, onSearchCallback) {
    const input = document.querySelector(inputSelector);
    if (!input) return;

    const handleSearch = debounce(
      /** @param {string} [query] */
      function (query) {
      const q = (query || '').trim().toLowerCase();
      
      // Update URL search param seamlessly without reload
      const url = new URL(window.location.href);
      if (q) {
        url.searchParams.set('q', q);
      } else {
        url.searchParams.delete('q');
      }
      window.history.replaceState({}, '', url);

      if (typeof onSearchCallback === 'function') {
        onSearchCallback(q);
        return;
      }

      // Default client-side filter
      const cards = /** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll(itemsSelector));
      let matchedCount = 0;
      cards.forEach(card => {
        const text = (card.innerText || '').toLowerCase();
        if (!q || text.includes(q)) {
          card.style.display = '';
          matchedCount++;
        } else {
          card.style.display = 'none';
        }
      });

      const emptyEl = document.getElementById('searchEmptyState');
      if (emptyEl) {
        emptyEl.style.display = (matchedCount === 0) ? 'flex' : 'none';
      }
    }, 250);

    input.addEventListener('input', (e) => {
      const target = /** @type {HTMLInputElement | null} */ (e.target);
      handleSearch(target ? target.value : '');
    });
  };

  // ===================================================================
  // 3. COMPASS GAUAGE ANIMATION
  // ===================================================================
  /**
   * @param {number} scorePercent
   * @param {string} circleSelector
   * @param {string} textSelector
   */
  window.animateCompassGauge = function (scorePercent, circleSelector, textSelector) {
    const circle = /** @type {SVGCircleElement | null} */ (document.querySelector(circleSelector));
    const textEl = /** @type {HTMLElement | null} */ (document.querySelector(textSelector));
    if (!circle) return;

    const radius = circle.r.baseVal.value || 42;
    const circumference = 2 * Math.PI * radius;
    circle.style.strokeDasharray = `${circumference}`;

    const offset = circumference - (Math.min(100, Math.max(0, scorePercent)) / 100) * circumference;
    
    // Smooth frame transition
    setTimeout(() => {
      circle.style.strokeDashoffset = `${offset}`;
    }, 50);

    if (textEl) {
      let current = 0;
      const stepTime = 15;
      const totalSteps = 40;
      const increment = scorePercent / totalSteps;
      const timer = setInterval(() => {
        current += increment;
        if (current >= scorePercent) {
          current = scorePercent;
          clearInterval(timer);
        }
        textEl.textContent = `${Math.round(current)}%`;
      }, stepTime);
    }
  };

  // ===================================================================
  // 4. MOBILE NAVIGATION DRAWER
  // ===================================================================
  /**
   * @param {boolean} [open]
   */
  window.toggleEduAtlasDrawer = function (open) {
    const drawer = document.getElementById('eaMobileDrawer');
    const backdrop = document.getElementById('eaMobileBackdrop');
    if (!drawer) return;

    const willOpen = (typeof open === 'boolean') ? open : drawer.classList.contains('translate-x-full');

    if (willOpen) {
      drawer.classList.remove('translate-x-full');
      if (backdrop) {
        backdrop.classList.remove('opacity-0', 'pointer-events-none');
        backdrop.classList.add('opacity-100');
      }
      document.body.style.overflow = 'hidden';
    } else {
      drawer.classList.add('translate-x-full');
      if (backdrop) {
        backdrop.classList.remove('opacity-100');
        backdrop.classList.add('opacity-0', 'pointer-events-none');
      }
      document.body.style.overflow = '';
    }
  };

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      window.toggleEduAtlasDrawer?.(false);
    }
  });

  // Auto-init on DOM loaded
  document.addEventListener('DOMContentLoaded', () => {
    updateThemeToggleIcons();

    // Ensure World-Class SaaS Engine is loaded and active
    if (!window.SaaSEngine && !document.querySelector('script[src*="saas-engine.js"]')) {
      const s = document.createElement('script');
      s.src = '/static/js/saas-engine.js';
      s.defer = true;
      document.head.appendChild(s);
    }
  });
})();
