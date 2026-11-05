/**
 * EduAtlas - SkeletonLoader Component
 * High-fidelity shimmering skeleton placeholders for async perceived performance.
 */

(function () {
    'use strict';

    const SkeletonLoader = {
        /**
         * Renders scholarship card skeletons.
         * @param {number} [count=3]
         * @returns {string} HTML string
         */
        renderCards(count = 3) {
            let html = '';
            for (let i = 0; i < count; i++) {
                html += `
                    <div class="sp-card p-6 flex flex-col justify-between border border-slate-200/80 dark:border-slate-800/80 animate-pulse space-y-4" role="status" aria-label="جاري تحميل المنحة...">
                        <div class="space-y-3">
                            <!-- Header: Badge & Score Gauge -->
                            <div class="flex items-center justify-between">
                                <div class="h-6 w-24 sp-skeleton rounded-lg"></div>
                                <div class="w-12 h-12 sp-skeleton rounded-full"></div>
                            </div>

                            <!-- Title & Subtitle -->
                            <div class="space-y-2">
                                <div class="h-5 w-4/5 sp-skeleton rounded-md"></div>
                                <div class="h-3.5 w-1/2 sp-skeleton rounded-md"></div>
                            </div>

                            <!-- Degree Tags -->
                            <div class="flex items-center gap-2 pt-1">
                                <div class="h-5 w-20 sp-skeleton rounded-lg"></div>
                                <div class="h-5 w-16 sp-skeleton rounded-lg"></div>
                            </div>

                            <!-- Highlights Box -->
                            <div class="p-3.5 rounded-xl border border-slate-200/60 dark:border-slate-800/60 bg-slate-100/50 dark:bg-slate-900/40 space-y-2">
                                <div class="h-4 w-3/4 sp-skeleton rounded"></div>
                                <div class="h-3 w-full sp-skeleton rounded"></div>
                                <div class="h-3 w-5/6 sp-skeleton rounded"></div>
                            </div>
                        </div>

                        <!-- Actions Footer -->
                        <div class="pt-4 border-t border-slate-200/70 dark:border-slate-800/70 space-y-2">
                            <div class="grid grid-cols-2 gap-2">
                                <div class="h-9 sp-skeleton rounded-xl"></div>
                                <div class="h-9 sp-skeleton rounded-xl"></div>
                            </div>
                            <div class="h-10 sp-skeleton rounded-xl"></div>
                        </div>
                    </div>
                `;
            }
            return html;
        },

        /**
         * Renders dashboard stats cards skeleton.
         * @returns {string} HTML string
         */
        renderStats() {
            return `
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" role="status" aria-label="جاري تحميل الإحصائيات...">
                    ${[1, 2, 3, 4].map(() => `
                        <div class="sp-card p-5 space-y-3 animate-pulse border border-slate-200/80 dark:border-slate-800/80">
                            <div class="flex items-center justify-between">
                                <div class="h-3.5 w-24 sp-skeleton rounded"></div>
                                <div class="w-5 h-5 sp-skeleton rounded-full"></div>
                            </div>
                            <div class="h-6 w-32 sp-skeleton rounded-md"></div>
                        </div>
                    `).join('')}
                </div>
            `;
        },

        /**
         * Renders comparison table skeleton rows.
         * @param {number} [rows=4]
         * @returns {string} HTML string
         */
        renderTableRows(rows = 4) {
            let html = '';
            for (let i = 0; i < rows; i++) {
                html += `
                    <tr class="animate-pulse border-b border-slate-200/60 dark:border-slate-800/60">
                        <td class="p-4"><div class="h-4 w-36 sp-skeleton rounded"></div></td>
                        <td class="p-4"><div class="h-4 w-20 sp-skeleton rounded"></div></td>
                        <td class="p-4"><div class="h-4 w-24 sp-skeleton rounded"></div></td>
                        <td class="p-4"><div class="h-8 w-12 sp-skeleton rounded-full mx-auto"></div></td>
                        <td class="p-4"><div class="h-4 w-20 sp-skeleton rounded"></div></td>
                        <td class="p-4"><div class="h-4 w-24 sp-skeleton rounded"></div></td>
                        <td class="p-4"><div class="h-4 w-20 sp-skeleton rounded"></div></td>
                        <td class="p-4"><div class="h-4 w-24 sp-skeleton rounded"></div></td>
                        <td class="p-4"><div class="h-4 w-16 sp-skeleton rounded"></div></td>
                        <td class="p-4"><div class="h-4 w-20 sp-skeleton rounded"></div></td>
                        <td class="p-4"><div class="h-8 w-24 sp-skeleton rounded-xl"></div></td>
                    </tr>
                `;
            }
            return html;
        }
    };

    window.SkeletonLoader = SkeletonLoader;
})();
