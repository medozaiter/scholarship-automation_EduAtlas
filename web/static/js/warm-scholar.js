/**
 * EduAtlas — warm-scholar.js
 * Vanilla JS micro-interactions for instant search, compass gauge & mobile drawer
 */

(function () {
  'use strict';

  // ===================================================================
  // 1. THEME MANAGER (DARK / LIGHT PARCHMENT)
  // ===================================================================
  window.toggleEduAtlasTheme = function () {
    const isDark = document.documentElement.classList.contains('dark');
    if (isDark) {
      document.documentElement.classList.remove('dark');
      localStorage.theme = 'light';
    } else {
      document.documentElement.classList.add('dark');
      localStorage.theme = 'dark';
    }
    updateThemeToggleIcons();
  };

  function updateThemeToggleIcons() {
    const isDark = document.documentElement.classList.contains('dark');
    const icons = document.querySelectorAll('.ea-theme-toggle-icon');
    icons.forEach(icon => {
      icon.setAttribute('data-lucide', isDark ? 'sun' : 'moon');
    });
    const mainIcon = document.getElementById('themeIcon');
    if (mainIcon) {
      mainIcon.innerHTML = isDark
        ? '<i data-lucide="sun" class="w-4 h-4 text-amber-400"></i>'
        : '<i data-lucide="moon" class="w-4 h-4 text-slate-600"></i>';
    }
    if (window.lucide && typeof lucide.createIcons === 'function') {
      try { lucide.createIcons(); } catch(e) {}
    }
  }

  // Universal aliases
  window.toggleTheme = window.toggleEduAtlasTheme;
  window.updateThemeButton = updateThemeToggleIcons;
  window.updateThemeIcon = updateThemeToggleIcons;

  // ===================================================================
  // 2. INSTANT SEARCH DEBOUNCE ENGINE
  // ===================================================================
  function debounce(func, wait) {
    let timeout;
    return function (...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }

  window.setupInstantScholarshipSearch = function (inputSelector, itemsSelector, onSearchCallback) {
    const input = document.querySelector(inputSelector);
    if (!input) return;

    const handleSearch = debounce(function (query) {
      const q = (query || '').trim().toLowerCase();
      
      // Update URL search param seamlessly without reload
      const url = new URL(window.location);
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
      const cards = document.querySelectorAll(itemsSelector);
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

    input.addEventListener('input', (e) => handleSearch(e.target.value));
  };

  // ===================================================================
  // 3. COMPASS GAUGE ANIMATION
  // ===================================================================
  window.animateCompassGauge = function (scorePercent, circleSelector, textSelector) {
    const circle = document.querySelector(circleSelector);
    const textEl = document.querySelector(textSelector);
    if (!circle) return;

    const radius = circle.r.baseVal.value || 42;
    const circumference = 2 * Math.PI * radius;
    circle.style.strokeDasharray = `${circumference}`;

    const offset = circumference - (Math.min(100, Math.max(0, scorePercent)) / 100) * circumference;
    
    // Smooth frame transition
    setTimeout(() => {
      circle.style.strokeDashoffset = offset;
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
      window.toggleEduAtlasDrawer(false);
    }
  });

  // Auto-init on DOM loaded
  document.addEventListener('DOMContentLoaded', () => {
    updateThemeToggleIcons();
  });
})();
