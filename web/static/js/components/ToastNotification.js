/**
 * EduAtlas - ToastNotification Component
 * Accessible, modern glassmorphism toast system with optimistic UI support.
 */

(function () {
    'use strict';

    /**
     * @typedef {'success' | 'error' | 'info' | 'loading'} ToastType
     */

    const ICONS = {
        success: `<div class="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-500 dark:text-emerald-400 flex items-center justify-center shrink-0 border border-emerald-500/30">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
        </div>`,
        error: `<div class="w-8 h-8 rounded-xl bg-rose-500/20 text-rose-500 dark:text-rose-400 flex items-center justify-center shrink-0 border border-rose-500/30">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        </div>`,
        info: `<div class="w-8 h-8 rounded-xl bg-purple-500/20 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0 border border-purple-500/30">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
        </div>`,
        loading: `<div class="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0 border border-emerald-500/30">
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
        </div>`
    };

    const ToastNotification = {
        /**
         * @returns {HTMLElement}
         */
        getContainer() {
            let container = document.getElementById('toastContainer');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toastContainer';
                container.className = 'fixed top-5 left-1/2 -translate-x-1/2 z-[9999] pointer-events-none flex flex-col items-center gap-2 max-w-md w-full px-4';
                document.body.appendChild(container);
            }
            return container;
        },

        /**
         * @param {string} str
         * @returns {string}
         */
        escapeHtml(str) {
            if (str === null || str === undefined) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        },

        /**
         * Shows a toast notification.
         * @param {ToastType} type
         * @param {string} title
         * @param {string} message
         * @param {number} [duration=4500]
         * @returns {HTMLElement}
         */
        show(type, title, message, duration = 4500) {
            const container = this.getContainer();

            const toast = document.createElement('div');
            toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
            toast.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');

            const borderColors = {
                success: 'border-emerald-500/40 shadow-emerald-500/10',
                error: 'border-rose-500/40 shadow-rose-500/10',
                info: 'border-purple-500/40 shadow-purple-500/10',
                loading: 'border-emerald-500/40 shadow-emerald-500/10'
            };

            const borderClass = borderColors[type] || borderColors.info;

            toast.className = `pointer-events-auto w-full p-4 rounded-2xl shadow-2xl border backdrop-blur-xl flex items-start gap-3.5 transform transition-all duration-300 ease-out translate-y-[-20px] opacity-0 bg-slate-900/95 text-white ${borderClass}`;

            const iconHtml = ICONS[type] || ICONS.info;

            toast.innerHTML = `
                ${iconHtml}
                <div class="flex-1 text-right min-w-0">
                    <h4 class="text-xs sm:text-sm font-extrabold text-white mb-0.5 truncate">${this.escapeHtml(title)}</h4>
                    <p class="text-[11px] sm:text-xs text-slate-300 leading-relaxed font-medium break-words">${this.escapeHtml(message)}</p>
                </div>
                <button type="button" aria-label="إغلاق التنبيه" class="text-slate-400 hover:text-white transition text-xs p-1 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-400">
                    ✕
                </button>
            `;

            const closeBtn = toast.querySelector('button');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    this.dismiss(toast);
                });
            }

            container.appendChild(toast);

            requestAnimationFrame(() => {
                toast.classList.remove('translate-y-[-20px]', 'opacity-0');
            });

            if (type !== 'loading' && duration > 0) {
                const timer = setTimeout(() => {
                    this.dismiss(toast);
                }, duration);

                // Pause on hover
                toast.addEventListener('mouseenter', () => clearTimeout(timer));
                toast.addEventListener('mouseleave', () => {
                    setTimeout(() => this.dismiss(toast), 1500);
                });
            }

            // Expose dismiss method on the element
            const toastWithDismiss = /** @type {HTMLElement & { dismiss?: () => void }} */ (toast);
            toastWithDismiss.dismiss = () => this.dismiss(toast);
            return toast;
        },

        /**
         * Dismiss a toast with transition.
         * @param {HTMLElement} toast
         */
        dismiss(toast) {
            if (!toast || !toast.parentElement) return;
            toast.classList.add('translate-y-[-10px]', 'opacity-0');
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, 300);
        },

        /**
         * Helper for Optimistic UI updates with instant feedback.
         * @template T
         * @param {() => Promise<T>} actionPromise
         * @param {Object} options
         * @param {() => void} [options.onOptimistic]
         * @param {(error: unknown) => void} [options.onRollback]
         * @param {string} [options.loadingTitle]
         * @param {string} [options.loadingMessage]
         * @param {string} options.successTitle
         * @param {string} options.successMessage
         * @param {string} [options.errorTitle]
         * @param {string} [options.errorMessage]
         * @returns {Promise<T>}
         */
        async optimistic(actionPromise, options) {
            if (typeof options.onOptimistic === 'function') {
                try {
                    options.onOptimistic();
                } catch (e) {
                    console.error('Optimistic state update failed:', e);
                }
            }

            let loadingToast = null;
            if (options.loadingTitle) {
                loadingToast = this.show('loading', options.loadingTitle, options.loadingMessage || 'جاري المعالجة...', 0);
            }

            try {
                const result = await actionPromise();
                if (loadingToast) this.dismiss(loadingToast);
                this.show('success', options.successTitle, options.successMessage);
                return result;
            } catch (err) {
                if (loadingToast) this.dismiss(loadingToast);
                if (typeof options.onRollback === 'function') {
                    try {
                        options.onRollback(err);
                    } catch (e) {
                        console.error('Rollback failed:', e);
                    }
                }
                const errDetail = err && typeof err === 'object' && 'message' in err ? String(err.message) : '';
                this.show(
                    'error',
                    options.errorTitle || 'تعذرت العملية',
                    options.errorMessage || (errDetail ? `حدث خطأ: ${errDetail}` : 'يرجى إعادة المحاولة.')
                );
                throw err;
            }
        }
    };

    window.ToastNotification = ToastNotification;
    window.showToast = function (type, title, message, duration) {
        return ToastNotification.show(/** @type {ToastType} */ (type), title, message, duration);
    };
})();
