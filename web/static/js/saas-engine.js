/**
 * EduAtlas & ScholarPilot AI — saas-engine.js
 * High-Performance Modern SaaS Animation & Interaction Engine
 * Inspired by Linear, Stripe, Framer, Notion & Apple
 */

(function () {
  'use strict';

  // Check user motion preference
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ===================================================================
  // 1. TOP SCROLL PROGRESS INDICATOR
  // ===================================================================
  function initScrollProgress() {
    if (prefersReducedMotion) return;

    let progressBar = document.getElementById('saasScrollProgress');
    if (!progressBar) {
      progressBar = document.createElement('div');
      progressBar.id = 'saasScrollProgress';
      progressBar.setAttribute('aria-hidden', 'true');
      document.body.prepend(progressBar);
    }

    let ticking = false;
    function updateProgress() {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? Math.min(1, Math.max(0, scrollTop / docHeight)) : 0;
      progressBar.style.transform = `scaleX(${progress})`;
      ticking = false;
    }

    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(updateProgress);
        ticking = true;
      }
    }, { passive: true });

    updateProgress();
  }

  // ===================================================================
  // 2. PARALLAX & NAVBAR DYNAMIC SCROLLED STATE
  // ===================================================================
  function initParallaxAndNavbar() {
    const navbars = document.querySelectorAll('.sp-sticky-nav, header');
    let ticking = false;

    function onScroll() {
      const scrollY = window.pageYOffset || document.documentElement.scrollTop;

      // Update CSS variable for parallax backgrounds
      if (!prefersReducedMotion) {
        document.documentElement.style.setProperty('--scroll-y', `${scrollY}`);
      }

      // Navbar glassmorphism scrolled depth
      const isScrolled = scrollY > 15;
      navbars.forEach(nav => {
        if (isScrolled) {
          nav.classList.add('scrolled');
        } else {
          nav.classList.remove('scrolled');
        }
      });

      ticking = false;
    }

    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(onScroll);
        ticking = true;
      }
    }, { passive: true });

    onScroll();
  }

  // ===================================================================
  // 3. SCROLL-TRIGGERED REVEAL OBSERVER
  // ===================================================================
  function initScrollReveals() {
    if (prefersReducedMotion) {
      document.querySelectorAll('.reveal-on-scroll').forEach(el => {
        el.classList.add('is-revealed');
      });
      return;
    }

    if (!('IntersectionObserver' in window)) {
      document.querySelectorAll('.reveal-on-scroll').forEach(el => {
        el.classList.add('is-revealed');
      });
      return;
    }

    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          observer.unobserve(entry.target);
        }
      });
    }, {
      root: null,
      threshold: 0.1,
      rootMargin: '0px 0px -40px 0px'
    });

    // Auto-discover cards and sections if not explicitly tagged
    const candidates = document.querySelectorAll('.reveal-on-scroll, .fade-up-card, .sp-card, .scholarship-card');
    candidates.forEach((el, index) => {
      if (!el.classList.contains('reveal-on-scroll')) {
        el.classList.add('reveal-on-scroll');
      }
      revealObserver.observe(el);
    });

    // Expose dynamic observer for dynamically injected cards (e.g. search filter results)
    window.observeNewSaaSElements = function (container) {
      const root = container || document;
      const newItems = root.querySelectorAll('.reveal-on-scroll, .sp-card, .scholarship-card');
      newItems.forEach(item => {
        if (!item.classList.contains('is-revealed')) {
          item.classList.add('reveal-on-scroll');
          revealObserver.observe(item);
        }
      });
    };
  }

  // ===================================================================
  // 4. ANIMATED STATISTICS COUNTERS
  // ===================================================================
  function animateValue(obj, start, end, duration, prefix, suffix) {
    if (prefersReducedMotion) {
      obj.textContent = `${prefix}${end}${suffix}`;
      return;
    }

    let startTimestamp = null;
    const isDecimals = String(end).includes('.');

    function step(timestamp) {
      if (!startTimestamp) startTimestamp = timestamp;
      const elapsed = timestamp - startTimestamp;
      const progress = Math.min(elapsed / duration, 1);
      // Cubic ease out: 1 - Math.pow(1 - progress, 3)
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const current = start + (end - start) * easeProgress;

      obj.textContent = `${prefix}${isDecimals ? current.toFixed(1) : Math.round(current)}${suffix}`;

      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        obj.textContent = `${prefix}${end}${suffix}`;
      }
    }

    window.requestAnimationFrame(step);
  }

  function initAnimatedCounters() {
    const counterElements = document.querySelectorAll('.saas-stat-num, [data-counter-target]');
    if (counterElements.length === 0) return;

    if (!('IntersectionObserver' in window)) {
      counterElements.forEach(el => {
        const target = el.getAttribute('data-counter-target') || el.textContent;
        el.textContent = target;
      });
      return;
    }

    const counterObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          observer.unobserve(el);

          const rawText = el.getAttribute('data-counter-target') || el.textContent.trim();
          // Extract numeric value, prefix and suffix
          const match = rawText.match(/^([^\d]*)([\d,.]+)(.*)$/);
          if (match) {
            const prefix = match[1] || '';
            const num = parseFloat(match[2].replace(/,/g, ''));
            const suffix = match[3] || '';
            if (!isNaN(num)) {
              animateValue(el, 0, num, 1600, prefix, suffix);
            }
          }
        }
      });
    }, { threshold: 0.2 });

    counterElements.forEach(el => counterObserver.observe(el));
  }

  // ===================================================================
  // 5. INTERACTIVE MOUSE-FOLLOW SPOTLIGHT (STRIPE / LINEAR STYLE)
  // ===================================================================
  function initMouseSpotlight() {
    if (prefersReducedMotion) return;
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

    function handleCardMouseMove(e) {
      const card = e.currentTarget;
      const rect = card.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      card.style.setProperty('--mouse-x', `${x.toFixed(1)}%`);
      card.style.setProperty('--mouse-y', `${y.toFixed(1)}%`);
    }

    function attachCardSpotlight(root) {
      const cards = (root || document).querySelectorAll('.sp-card, .ea-card, .saas-card');
      cards.forEach(card => {
        if (!card.dataset.spotlightBound) {
          card.addEventListener('mousemove', handleCardMouseMove, { passive: true });
          card.dataset.spotlightBound = 'true';
        }
      });
    }

    attachCardSpotlight(document);
    window.attachSaaSSpotlights = attachCardSpotlight;
  }

  // ===================================================================
  // 6. HORIZONTAL SCROLLING SHOWCASE (DRAG TO SCROLL & BUTTON CONTROLS)
  // ===================================================================
  function initHorizontalShowcase() {
    const sliders = document.querySelectorAll('.saas-horizontal-scroll');

    sliders.forEach(slider => {
      let isDown = false;
      let startX;
      let scrollLeft;
      let isDragging = false;

      slider.addEventListener('mousedown', (e) => {
        isDown = true;
        isDragging = false;
        slider.style.cursor = 'grabbing';
        slider.style.userSelect = 'none';
        slider.style.scrollSnapType = 'none'; // Temporarily disable snap during active drag
        startX = e.pageX - slider.offsetLeft;
        scrollLeft = slider.scrollLeft;
      });

      window.addEventListener('mouseup', () => {
        if (!isDown) return;
        isDown = false;
        slider.style.cursor = 'grab';
        slider.style.removeProperty('user-select');
        slider.style.scrollSnapType = 'x mandatory';
      });

      slider.addEventListener('mousemove', (e) => {
        if (!isDown) return;
        e.preventDefault();
        const x = e.pageX - slider.offsetLeft;
        const walk = (x - startX) * 1.5;
        if (Math.abs(walk) > 5) {
          isDragging = true;
        }
        slider.scrollLeft = scrollLeft - walk;
      });

      // Prevent accidental link click if the user was dragging
      slider.addEventListener('click', (e) => {
        if (isDragging) {
          e.preventDefault();
          e.stopPropagation();
        }
      }, true);
    });

    // Arrow button controls
    document.querySelectorAll('[data-scroll-prev]').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-scroll-prev');
        const target = document.getElementById(targetId);
        if (target) {
          target.scrollBy({ left: -320, behavior: 'smooth' });
        }
      });
    });

    document.querySelectorAll('[data-scroll-next]').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-scroll-next');
        const target = document.getElementById(targetId);
        if (target) {
          target.scrollBy({ left: 320, behavior: 'smooth' });
        }
      });
    });
  }

  // ===================================================================
  // 7. SMOOTH INTERNAL ANCHOR NAVIGATION
  // ===================================================================
  function initSmoothAnchors() {
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a[href^="#"]');
      if (!link) return;

      const href = link.getAttribute('href');
      if (!href || href === '#' || href === '#!') return;

      const targetEl = document.querySelector(href);
      if (targetEl) {
        e.preventDefault();
        const headerOffset = 80;
        const elementPosition = targetEl.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

        window.scrollTo({
          top: offsetPosition,
          behavior: prefersReducedMotion ? 'auto' : 'smooth'
        });

        // Set focus for accessibility without jump
        targetEl.setAttribute('tabindex', '-1');
        targetEl.focus({ preventScroll: true });
      }
    });
  }

  // ===================================================================
  // 8. AUTO-INITIALIZATION ON DOM READY
  // ===================================================================
  function initSaaSWorldClass() {
    initScrollProgress();
    initParallaxAndNavbar();
    initScrollReveals();
    initAnimatedCounters();
    initMouseSpotlight();
    initHorizontalShowcase();
    initSmoothAnchors();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSaaSWorldClass);
  } else {
    initSaaSWorldClass();
  }

  // Expose API for external components
  window.SaaSEngine = {
    init: initSaaSWorldClass,
    refreshReveals: initScrollReveals,
    refreshSpotlights: initMouseSpotlight
  };

})();
