/**
 * EduAtlas - ComparisonTable Component
 * 11-column scholarship comparison table for desktop, automatically converted into
 * touch-friendly swipeable cards or collapsible accordions on mobile devices (360px-768px).
 */

(function () {
    'use strict';

    /**
     * @param {string} str
     * @returns {string}
     */
    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    const ComparisonTable = {
        /**
         * @typedef {'accordion' | 'swipeable'} MobileViewMode
         */
        currentMobileMode: 'accordion',

        /**
         * Renders the complete responsive comparison section.
         * @param {Scholarship[]} scholarships
         * @returns {string} HTML string
         */
        render(scholarships) {
            if (!scholarships || scholarships.length === 0) {
                return `
                    <div class="sp-card p-10 text-center space-y-3">
                        <div class="w-12 h-12 rounded-2xl bg-blue-500/10 text-blue-500 flex items-center justify-center mx-auto">
                            <i data-lucide="layers" class="w-6 h-6"></i>
                        </div>
                        <h4 class="text-sm font-bold text-slate-900 dark:text-white">لا توجد منح للمقارنة حالياً</h4>
                        <p class="text-xs text-slate-400">يرجى تعديل الفلاتر أو تفعيل البحث لعرض المنح في جدول المقارنة.</p>
                    </div>
                `;
            }

            return `
                <div class="space-y-4">
                    <!-- Mobile View Switcher (Visible on Mobile 360px-768px only) -->
                    <div class="flex lg:hidden items-center justify-between p-3 rounded-xl bg-slate-100 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-xs">
                        <span class="font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                            <i data-lucide="sliders-horizontal" class="w-3.5 h-3.5 text-blue-500"></i>
                            <span>طريقة العرض في الجوال:</span>
                        </span>
                        <div class="flex items-center gap-1">
                            <button type="button" 
                                    onclick="ComparisonTable.switchMobileMode('accordion')" 
                                    id="compModeAccordionBtn"
                                    class="px-2.5 py-1 rounded-lg text-[11px] font-bold transition ${this.currentMobileMode === 'accordion' ? 'bg-blue-600 text-white shadow-xs' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'}">
                                قائمة أكورديون
                            </button>
                            <button type="button" 
                                    onclick="ComparisonTable.switchMobileMode('swipeable')" 
                                    id="compModeSwipeBtn"
                                    class="px-2.5 py-1 rounded-lg text-[11px] font-bold transition ${this.currentMobileMode === 'swipeable' ? 'bg-blue-600 text-white shadow-xs' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'}">
                                بطاقات سحب
                            </button>
                        </div>
                    </div>

                    <!-- 1. Desktop 11-Column Table (Hidden on small screens < 1024px) -->
                    <div class="hidden lg:block overflow-x-auto rounded-2xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900 shadow-sm">
                        <table class="w-full text-right text-xs border-collapse">
                            <thead>
                                <tr class="border-b border-slate-200 dark:border-slate-800 bg-slate-50/90 dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 font-bold sticky top-0 z-10">
                                    <th class="p-3.5 whitespace-nowrap min-w-[200px]">1. المنحة والمؤسسة</th>
                                    <th class="p-3.5 whitespace-nowrap min-w-[110px]">2. الدولة</th>
                                    <th class="p-3.5 whitespace-nowrap min-w-[120px]">3. المرحلة</th>
                                    <th class="p-3.5 whitespace-nowrap min-w-[100px] text-center">4. التوافق</th>
                                    <th class="p-3.5 whitespace-nowrap min-w-[110px]">5. نوع التمويل</th>
                                    <th class="p-3.5 whitespace-nowrap min-w-[150px]">6. الراتب والمعيشة</th>
                                    <th class="p-3.5 whitespace-nowrap min-w-[130px]">7. الرسوم الدراسية</th>
                                    <th class="p-3.5 whitespace-nowrap min-w-[130px]">8. شرط اللغة</th>
                                    <th class="p-3.5 whitespace-nowrap min-w-[130px]">9. التنافسية</th>
                                    <th class="p-3.5 whitespace-nowrap min-w-[120px]">10. الموعد النهائي</th>
                                    <th class="p-3.5 whitespace-nowrap min-w-[140px] text-center">11. الإجراءات</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
                                ${this.renderDesktopRows(scholarships)}
                            </tbody>
                        </table>
                    </div>

                    <!-- 2. Mobile Container: Accordions or Swipeable Deck (Visible on screens < 1024px) -->
                    <div class="lg:hidden" id="mobileComparisonContainer">
                        ${this.currentMobileMode === 'accordion' ? this.renderMobileAccordions(scholarships) : this.renderMobileSwipeable(scholarships)}
                    </div>
                </div>
            `;
        },

        /**
         * Renders desktop table rows.
         * @param {Scholarship[]} scholarships
         * @returns {string}
         */
        renderDesktopRows(scholarships) {
            return scholarships.map((s, _idx) => {
                const institution = s.institution || s.university || s.country;
                const link = s.link && s.link !== '#' ? s.link : 'https://future.utoronto.ca/pearson/';
                const scoreNum = window.MatchScoreGauge ? window.MatchScoreGauge.parseScore(s.matchScore || s.match_score || 90) : 90;
                const scoreTier = window.MatchScoreGauge ? window.MatchScoreGauge.getColorTier(scoreNum) : { color: 'text-emerald-500', stroke: '#10b981' };

                const isFully = (s.funding || s.coverage || '').includes('100%') || (s.funding || '').includes('كامل');
                const fundingBadge = isFully
                    ? `<span class="sp-badge sp-badge-success text-[10px] py-0.5">تمويل 100%</span>`
                    : `<span class="sp-badge sp-badge-info text-[10px] py-0.5">إعفاء جزئي</span>`;

                return `
                    <tr class="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors">
                        <!-- 1. Name & Institution -->
                        <td class="p-3.5">
                            <div class="font-bold text-slate-900 dark:text-white leading-snug">${escapeHtml(s.name)}</div>
                            <div class="text-[11px] text-slate-400 mt-0.5">${escapeHtml(institution)}</div>
                        </td>

                        <!-- 2. Country -->
                        <td class="p-3.5 whitespace-nowrap text-slate-700 dark:text-slate-300">
                            <span class="inline-flex items-center gap-1 font-medium">
                                <i data-lucide="map-pin" class="w-3 h-3 text-blue-500"></i>
                                <span>${escapeHtml(s.country)}</span>
                            </span>
                        </td>

                        <!-- 3. Degree -->
                        <td class="p-3.5 text-[11px]">
                            <span class="sp-badge sp-badge-neutral">${escapeHtml(s.degree || 'بكالوريوس')}</span>
                        </td>

                        <!-- 4. Match Score Gauge -->
                        <td class="p-3.5 text-center whitespace-nowrap font-latin font-bold">
                            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[11px] ${scoreTier.color} border-slate-200 dark:border-slate-800">
                                <span class="w-1.5 h-1.5 rounded-full" style="background-color: ${scoreTier.stroke}"></span>
                                <span>${scoreNum}%</span>
                            </span>
                        </td>

                        <!-- 5. Funding Type -->
                        <td class="p-3.5 whitespace-nowrap">
                            ${fundingBadge}
                        </td>

                        <!-- 6. Living Allowance -->
                        <td class="p-3.5 text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed max-w-[180px]">
                            ${escapeHtml(s.living_allowance || s.coverage || 'راتب شهري وسكن')}
                        </td>

                        <!-- 7. Tuition -->
                        <td class="p-3.5 text-[11px] text-slate-600 dark:text-slate-400 whitespace-nowrap">
                            ${escapeHtml(s.tuition_coverage || 'إعفاء 100%')}
                        </td>

                        <!-- 8. Language -->
                        <td class="p-3.5 text-[11px] text-slate-600 dark:text-slate-400">
                            ${escapeHtml(s.language_req || 'شهادة إتقان لغة')}
                        </td>

                        <!-- 9. Competitiveness -->
                        <td class="p-3.5 text-[11px]">
                            <span class="text-amber-600 dark:text-amber-400 font-semibold">${escapeHtml(s.difficulty || s.competitiveness || 'عالي')}</span>
                        </td>

                        <!-- 10. Deadline -->
                        <td class="p-3.5 whitespace-nowrap text-[11px] font-latin font-bold text-slate-800 dark:text-slate-200">
                            <span class="flex items-center gap-1">
                                <i data-lucide="calendar" class="w-3 h-3 text-amber-500"></i>
                                <span>${escapeHtml(s.deadline || s.deadline_display || 'مفتوح')}</span>
                            </span>
                        </td>

                        <!-- 11. Actions -->
                        <td class="p-3.5 text-center whitespace-nowrap">
                            <div class="flex items-center justify-center gap-1.5">
                                <button type="button" 
                                        onclick="DashboardApp.openSopStudio('${escapeHtml(s.id)}', '${escapeHtml(s.name)}')" 
                                        class="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/40 transition" 
                                        title="صياغة خطاب الدافع (SOP)">
                                    <i data-lucide="file-pen" class="w-3.5 h-3.5"></i>
                                </button>
                                <button type="button" 
                                        onclick="DashboardApp.toggleBookmark('${escapeHtml(s.id)}', '${escapeHtml(s.name)}', this)" 
                                        class="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:text-emerald-500 transition" 
                                        title="حفظ وتنبيه">
                                    <i data-lucide="bookmark" class="w-3.5 h-3.5"></i>
                                </button>
                                <a href="${escapeHtml(link)}" 
                                   target="_blank" 
                                   rel="noopener noreferrer" 
                                   class="sp-btn-primary px-2.5 py-1 text-[11px] font-bold flex items-center gap-1" 
                                   title="قدّم الآن">
                                    <span>قدّم</span>
                                    <i data-lucide="arrow-up-right" class="w-3 h-3"></i>
                                </a>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        },

        /**
         * Renders Mobile Collapsible Accordions (11 criteria neatly organized per card).
         * @param {Scholarship[]} scholarships
         * @returns {string}
         */
        renderMobileAccordions(scholarships) {
            return `
                <div class="space-y-3">
                    ${scholarships.map((s, idx) => {
                        const institution = s.institution || s.university || s.country;
                        const link = s.link && s.link !== '#' ? s.link : 'https://future.utoronto.ca/pearson/';
                        const scoreNum = window.MatchScoreGauge ? window.MatchScoreGauge.parseScore(s.matchScore || s.match_score || 90) : 90;
                        const scoreTier = window.MatchScoreGauge ? window.MatchScoreGauge.getColorTier(scoreNum) : { color: 'text-emerald-500', stroke: '#10b981' };

                        return `
                            <details class="sp-card border border-slate-200 dark:border-slate-800 rounded-2xl group transition-all" ${idx === 0 ? 'open' : ''}>
                                <summary class="p-4 list-none cursor-pointer flex items-center justify-between gap-3 select-none">
                                    <div class="flex items-center gap-2.5 min-w-0">
                                        <span class="w-6 h-6 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-latin font-black flex items-center justify-center shrink-0">
                                            ${idx + 1}
                                        </span>
                                        <div class="min-w-0">
                                            <h4 class="text-xs sm:text-sm font-bold text-slate-900 dark:text-white truncate">${escapeHtml(s.name)}</h4>
                                            <p class="text-[11px] text-slate-400 truncate">${escapeHtml(s.country)} · ${escapeHtml(institution)}</p>
                                        </div>
                                    </div>

                                    <div class="flex items-center gap-2 shrink-0">
                                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-latin font-bold ${scoreTier.color} border-slate-200 dark:border-slate-800">
                                            <span class="w-1.5 h-1.5 rounded-full" style="background-color: ${scoreTier.stroke}"></span>
                                            <span>${scoreNum}%</span>
                                        </span>
                                        <i data-lucide="chevron-down" class="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform"></i>
                                    </div>
                                </summary>

                                <!-- Expanded 11-Criteria Breakdown -->
                                <div class="px-4 pb-4 pt-1 border-t border-slate-100 dark:border-slate-800/80 text-xs space-y-2.5">
                                    <div class="grid grid-cols-2 gap-2 text-[11px] pt-1">
                                        <div class="p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800">
                                            <span class="text-slate-400 block mb-0.5">3. المرحلة الدراسية:</span>
                                            <span class="font-bold text-slate-800 dark:text-slate-200">${escapeHtml(s.degree || 'بكالوريوس')}</span>
                                        </div>
                                        <div class="p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800">
                                            <span class="text-slate-400 block mb-0.5">5. التمويل المالي:</span>
                                            <span class="font-bold text-emerald-600 dark:text-emerald-400">${escapeHtml(s.funding || 'تمويل كامل 100%')}</span>
                                        </div>
                                        <div class="p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800">
                                            <span class="text-slate-400 block mb-0.5">6. الراتب الشهري:</span>
                                            <span class="font-bold text-slate-800 dark:text-slate-200">${escapeHtml(s.living_allowance || 'راتب وسكن مجاني')}</span>
                                        </div>
                                        <div class="p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800">
                                            <span class="text-slate-400 block mb-0.5">7. الرسوم الدراسية:</span>
                                            <span class="font-bold text-slate-800 dark:text-slate-200">${escapeHtml(s.tuition_coverage || 'إعفاء 100%')}</span>
                                        </div>
                                        <div class="p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800">
                                            <span class="text-slate-400 block mb-0.5">8. شرط اللغة:</span>
                                            <span class="font-bold text-slate-800 dark:text-slate-200">${escapeHtml(s.language_req || 'شهادة إتقان')}</span>
                                        </div>
                                        <div class="p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800">
                                            <span class="text-slate-400 block mb-0.5">9. التنافسية:</span>
                                            <span class="font-bold text-amber-600 dark:text-amber-400">${escapeHtml(s.difficulty || 'عالي')}</span>
                                        </div>
                                    </div>

                                    <div class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300 flex items-center justify-between text-xs font-bold">
                                        <span class="flex items-center gap-1.5">
                                            <i data-lucide="calendar" class="w-3.5 h-3.5"></i>
                                            <span>10. الموعد النهائي:</span>
                                        </span>
                                        <span class="font-latin">${escapeHtml(s.deadline || s.deadline_display || 'مفتوح')}</span>
                                    </div>

                                    <!-- 11. Actions Row -->
                                    <div class="pt-2 flex items-center gap-2">
                                        <button type="button" 
                                                onclick="DashboardApp.openSopStudio('${escapeHtml(s.id)}', '${escapeHtml(s.name)}')" 
                                                class="sp-btn-secondary flex-1 py-2 text-xs font-bold flex items-center justify-center gap-1 text-blue-600 dark:text-blue-400">
                                            <i data-lucide="file-pen" class="w-3.5 h-3.5"></i>
                                            <span>صياغة خطاب الدافع</span>
                                        </button>
                                        <button type="button" 
                                                onclick="DashboardApp.toggleBookmark('${escapeHtml(s.id)}', '${escapeHtml(s.name)}', this)" 
                                                class="sp-btn-secondary p-2 text-xs font-bold" title="حفظ وتنبيه">
                                            <i data-lucide="bookmark" class="w-3.5 h-3.5 text-blue-500"></i>
                                        </button>
                                        <a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer" class="sp-btn-primary px-4 py-2 text-xs font-bold flex items-center gap-1">
                                            <span>قدّم الآن</span>
                                            <i data-lucide="arrow-up-right" class="w-3 h-3"></i>
                                        </a>
                                    </div>
                                </div>
                            </details>
                        `;
                    }).join('')}
                </div>
            `;
        },

        /**
         * Renders Mobile Swipeable Card Deck.
         * @param {Scholarship[]} scholarships
         * @returns {string}
         */
        renderMobileSwipeable(scholarships) {
            return `
                <div class="flex overflow-x-auto snap-x snap-mandatory gap-4 pb-4 px-1" style="-webkit-overflow-scrolling: touch;">
                    ${scholarships.map((s, idx) => {
                        const institution = s.institution || s.university || s.country;
                        const link = s.link && s.link !== '#' ? s.link : 'https://future.utoronto.ca/pearson/';
                        const scoreNum = window.MatchScoreGauge ? window.MatchScoreGauge.parseScore(s.matchScore || s.match_score || 90) : 90;

                        return `
                            <div class="snap-center shrink-0 w-[85vw] max-w-[340px] sp-card p-5 border border-slate-200 dark:border-slate-800 rounded-3xl space-y-3 shadow-md flex flex-col justify-between">
                                <div>
                                    <div class="flex items-center justify-between text-xs font-bold mb-2">
                                        <span class="w-6 h-6 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 font-latin flex items-center justify-center">${idx + 1}/${scholarships.length}</span>
                                        ${window.MatchScoreGauge ? window.MatchScoreGauge.renderBadge(scoreNum) : `<span class="sp-badge sp-badge-info">${scoreNum}%</span>`}
                                    </div>
                                    <h4 class="text-sm font-bold text-slate-900 dark:text-white mb-1 line-clamp-2">${escapeHtml(s.name)}</h4>
                                    <p class="text-[11px] text-slate-400 flex items-center gap-1 mb-2">
                                        <i data-lucide="map-pin" class="w-3 h-3 text-blue-500"></i>
                                        <span>${escapeHtml(s.country)} · ${escapeHtml(institution)}</span>
                                    </p>

                                    <div class="space-y-1.5 text-[11px] p-3 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800">
                                        <div class="flex justify-between">
                                            <span class="text-slate-400">التمويل:</span>
                                            <span class="font-bold text-emerald-600 dark:text-emerald-400">${escapeHtml(s.funding || 'تمويل 100%')}</span>
                                        </div>
                                        <div class="flex justify-between">
                                            <span class="text-slate-400">الموعد:</span>
                                            <span class="font-bold text-amber-600 dark:text-amber-400 font-latin">${escapeHtml(s.deadline || 'مفتوح')}</span>
                                        </div>
                                        <div class="flex justify-between">
                                            <span class="text-slate-400">شرط اللغة:</span>
                                            <span class="font-semibold text-slate-700 dark:text-slate-300 truncate max-w-[140px]">${escapeHtml(s.language_req || 'شهادة إتقان')}</span>
                                        </div>
                                    </div>
                                </div>

                                <div class="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                                    <div class="grid grid-cols-2 gap-2">
                                        <button type="button" 
                                                onclick="DashboardApp.openSopStudio('${escapeHtml(s.id)}', '${escapeHtml(s.name)}')" 
                                                class="sp-btn-secondary py-2 text-xs font-bold text-blue-600 dark:text-blue-400">
                                            خطاب الدافع
                                        </button>
                                        <button type="button" 
                                                onclick="DashboardApp.toggleBookmark('${escapeHtml(s.id)}', '${escapeHtml(s.name)}', this)" 
                                                class="sp-btn-secondary py-2 text-xs font-bold text-slate-700 dark:text-slate-300">
                                            حفظ وتنبيه
                                        </button>
                                    </div>
                                    <a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer" class="sp-btn-primary w-full py-2 text-xs font-bold text-center flex items-center justify-center gap-1.5">
                                        <span>قدّم الآن</span>
                                        <i data-lucide="arrow-up-right" class="w-3.5 h-3.5"></i>
                                    </a>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        },

        /**
         * Switches the mobile view mode and re-renders container.
         * @param {MobileViewMode} mode
         */
        switchMobileMode(mode) {
            this.currentMobileMode = mode;
            const container = document.getElementById('mobileComparisonContainer');
            if (container && window.DashboardStore) {
                const scholarships = window.DashboardStore.getFilteredScholarships();
                container.innerHTML = mode === 'accordion' ? this.renderMobileAccordions(scholarships) : this.renderMobileSwipeable(scholarships);
            }

            const btnAcc = document.getElementById('compModeAccordionBtn');
            const btnSwipe = document.getElementById('compModeSwipeBtn');
            if (btnAcc && btnSwipe) {
                if (mode === 'accordion') {
                    btnAcc.className = 'px-2.5 py-1 rounded-lg text-[11px] font-bold transition bg-blue-600 text-white shadow-xs';
                    btnSwipe.className = 'px-2.5 py-1 rounded-lg text-[11px] font-bold transition text-slate-600 dark:text-slate-400 hover:text-slate-900';
                } else {
                    btnSwipe.className = 'px-2.5 py-1 rounded-lg text-[11px] font-bold transition bg-blue-600 text-white shadow-xs';
                    btnAcc.className = 'px-2.5 py-1 rounded-lg text-[11px] font-bold transition text-slate-600 dark:text-slate-400 hover:text-slate-900';
                }
            }
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        }
    };

    window.ComparisonTable = ComparisonTable;
})();
