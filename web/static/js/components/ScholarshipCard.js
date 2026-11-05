/**
 * EduAtlas - ScholarshipCard Component
 * Reusable, accessible scholarship opportunity card and compact row presentation.
 */

(function () {
    'use strict';

    /**
     * @param {unknown} str
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

    const ScholarshipCard = {
        /**
         * Computes days left until deadline.
         * @param {string} deadlineStr
         * @returns {{ label: string, isUrgent: boolean }}
         */
        getDeadlineStatus(deadlineStr) {
            if (!deadlineStr) return { label: 'مفتوح الآن', isUrgent: false };
            const cleanDate = deadlineStr.match(/\d{4}-\d{2}-\d{2}/);
            if (cleanDate) {
                const target = new Date(cleanDate[0]).getTime();
                const now = new Date().getTime();
                const diffDays = Math.ceil((target - now) / (1000 * 60 * 60 * 24));
                if (diffDays < 0) return { label: 'انتهى التقديم', isUrgent: false };
                if (diffDays <= 7) return { label: `باقي ${diffDays} أيام فقط!`, isUrgent: true };
                if (diffDays <= 30) return { label: `باقي ${diffDays} يوماً`, isUrgent: false };
                return { label: deadlineStr, isUrgent: false };
            }
            return { label: deadlineStr, isUrgent: false };
        },

        /**
         * Renders degree badges.
         * @param {Scholarship} s
         * @returns {string} HTML string
         */
        renderDegreeBadges(s) {
            const degrees = s.target_degrees || [];
            const degText = ((s.degree || '') + ' ' + degrees.join(' ')).toLowerCase();
            let badges = '';

            const isBachelor = degText.includes('bachelor') || degText.includes('بكالوريوس') || degText.includes('undergraduate') || degText.includes('كافة المراحل');
            const isMaster = degText.includes('master') || degText.includes('ماجستير') || degText.includes('دراسات عليا') || degText.includes('كافة المراحل');
            const isPhd = degText.includes('phd') || degText.includes('دكتوراه') || degText.includes('doctorate') || degText.includes('كافة المراحل');

            if (isBachelor) {
                badges += `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-[10px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"><i data-lucide="graduation-cap" class="w-3 h-3"></i> بكالوريوس</span>`;
            }
            if (isMaster) {
                badges += `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-[10px] font-bold bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20"><i data-lucide="scroll" class="w-3 h-3"></i> ماجستير</span>`;
            }
            if (isPhd) {
                badges += `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-[10px] font-bold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20"><i data-lucide="microscope" class="w-3 h-3"></i> دكتوراه</span>`;
            }

            if (!badges) {
                badges = `<span class="sp-badge sp-badge-neutral text-[10px]">${escapeHtml(s.degree || 'كافة المراحل')}</span>`;
            }
            return badges;
        },

        /**
         * Renders a full scholarship card.
         * @param {Scholarship} s
         * @param {Object} [options]
         * @param {boolean} [options.isSaved=false]
         * @returns {string} HTML string
         */
        render(s, options = {}) {
            const isSaved = options.isSaved || s.is_saved || false;
            const deadlineInfo = this.getDeadlineStatus(s.deadline || s.deadline_display || '');
            const gaugeHtml = window.MatchScoreGauge
                ? window.MatchScoreGauge.render(s.matchScore || s.match_score || 90, s.matchLabel || '', 'md')
                : `<span class="sp-badge sp-badge-info font-latin font-bold">${escapeHtml(s.matchScore || '90%')}</span>`;

            const link = s.link && s.link !== '#' ? s.link : 'https://future.utoronto.ca/pearson/';
            const institution = s.institution || s.university || s.country;
            const safeId = escapeHtml(s.id);
            const safeName = escapeHtml(s.name);

            // Funding badge
            const isFullyFunded = (s.funding || s.coverage || '').includes('100%') || (s.funding || '').includes('كامل');
            const fundingBadge = isFullyFunded
                ? `<span class="sp-badge sp-badge-success text-[10px]"><i data-lucide="check-circle-2" class="w-3 h-3"></i> تمويل كامل 100%</span>`
                : `<span class="sp-badge sp-badge-info text-[10px]">إعفاء دراسي جزئي</span>`;

            // Language Requirement Tag
            const langReq = s.language_req || 'شهادة لغة معتمدة';
            const hasNoIelts = langReq.toLowerCase().includes('بدون') || langReq.toLowerCase().includes('جامعية');
            const langBadge = hasNoIelts
                ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"><i data-lucide="check" class="w-2.5 h-2.5"></i> شهادة جامعية مقبولة</span>`
                : `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"><i data-lucide="file-check" class="w-2.5 h-2.5"></i> ${escapeHtml(langReq)}</span>`;

            const bookmarkBtnClass = isSaved
                ? 'sp-btn-secondary border-emerald-500/40 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10'
                : 'sp-btn-secondary text-slate-700 dark:text-slate-300 hover:text-blue-600';

            const bookmarkBtnText = isSaved
                ? `<i data-lucide="bookmark-check" class="w-3.5 h-3.5 text-emerald-500"></i><span>محفوظة بالمتابعة</span>`
                : `<i data-lucide="bookmark" class="w-3.5 h-3.5 text-blue-500"></i><span>حفظ وتنبيه</span>`;

            return `
                <article id="scholarship-card-${safeId}" 
                         class="sp-card p-6 flex flex-col justify-between sp-card-hover group border border-slate-200/80 dark:border-slate-800/80 relative"
                         role="article" 
                         aria-labelledby="card-title-${safeId}">
                    <div>
                        <!-- Top Row: Status Badges & Match Gauge -->
                        <div class="flex items-start justify-between gap-3 mb-3">
                            <div class="flex flex-wrap items-center gap-1.5">
                                <span class="sp-badge ${escapeHtml(s.statusClass || 'sp-badge-success')} text-[10px]">
                                    ${escapeHtml(s.status || 'مفتوح حالياً')}
                                </span>
                                ${fundingBadge}
                            </div>
                            <div class="shrink-0 -mt-1">
                                ${gaugeHtml}
                            </div>
                        </div>

                        <!-- Title & Institution -->
                        <h3 id="card-title-${safeId}" class="text-base sm:text-lg font-bold text-slate-900 dark:text-white mb-1 group-hover:text-blue-500 transition-colors leading-snug">
                            ${safeName}
                        </h3>
                        <p class="text-xs text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                            <i data-lucide="map-pin" class="w-3.5 h-3.5 text-blue-500 shrink-0"></i>
                            <span class="truncate">${escapeHtml(s.country)} · ${escapeHtml(institution)}</span>
                        </p>

                        <!-- Degree Badges -->
                        <div class="flex flex-wrap items-center gap-1.5 mb-3">
                            ${this.renderDegreeBadges(s)}
                        </div>

                        <!-- Highlights Box -->
                        <div class="sp-subcard p-3 rounded-xl text-xs mb-3 space-y-2 border border-slate-200/60 dark:border-slate-800/60 bg-slate-50/60 dark:bg-slate-900/40">
                            <div class="flex items-center justify-between gap-2">
                                <div class="${deadlineInfo.isUrgent ? 'text-rose-600 dark:text-rose-400' : 'text-amber-600 dark:text-amber-400'} font-bold flex items-center gap-1.5 text-xs">
                                    <i data-lucide="calendar" class="w-3.5 h-3.5 shrink-0"></i>
                                    <span>الموعد النهائي: ${escapeHtml(deadlineInfo.label)}</span>
                                </div>
                            </div>
                            <div class="text-[11px] leading-relaxed flex items-start gap-1.5 text-slate-600 dark:text-slate-300">
                                <i data-lucide="shield-check" class="w-3.5 h-3.5 text-emerald-500 mt-0.5 shrink-0"></i>
                                <span class="line-clamp-2">${escapeHtml(s.coverage || 'تغطية دراسية وسكن وبدل معيشة')}</span>
                            </div>
                            <div class="pt-1 border-t border-slate-200/40 dark:border-slate-800/40 flex items-center gap-2">
                                ${langBadge}
                            </div>
                        </div>
                    </div>

                    <!-- Action Controls -->
                    <div class="space-y-2 pt-3 border-t border-slate-200 dark:border-slate-800">
                        <div class="grid grid-cols-2 gap-2">
                            <!-- Bookmark Action -->
                            <button type="button" 
                                    onclick="DashboardApp.toggleBookmark('${safeId}', '${safeName}', this)" 
                                    class="${bookmarkBtnClass} py-2 text-xs font-bold flex items-center justify-center gap-1.5 transition-all"
                                    title="حفظ المنحة وتفعيل تذكيرات المواعيد">
                                ${bookmarkBtnText}
                            </button>

                            <!-- SOP Document Studio Trigger -->
                            <button type="button" 
                                    onclick="DashboardApp.openSopStudio('${safeId}', '${safeName}')" 
                                    class="sp-btn-secondary py-2 text-xs font-bold flex items-center justify-center gap-1.5 text-blue-600 dark:text-blue-400 hover:border-blue-500/50"
                                    title="صياغة خطاب الدافع المخصص لهذه المنحة">
                                <i data-lucide="file-pen" class="w-3.5 h-3.5 text-blue-500"></i>
                                <span>خطاب الدافع</span>
                            </button>
                        </div>

                        <div class="grid grid-cols-2 gap-2">
                            <!-- Advisor Consultation -->
                            <button type="button" 
                                    onclick="DashboardApp.askAdvisor('${safeId}', '${safeName}')" 
                                    class="sp-btn-secondary py-2 text-xs font-bold flex items-center justify-center gap-1.5 text-slate-700 dark:text-slate-300 hover:border-blue-500/50"
                                    title="استشارة المستشار الذكي حول متطلبات القبول">
                                <i data-lucide="sparkles" class="w-3.5 h-3.5 text-indigo-500"></i>
                                <span>استشر الذكاء</span>
                            </button>

                            <!-- Direct Portal Link -->
                            <a href="${escapeHtml(link)}" 
                               target="_blank" 
                               rel="noopener noreferrer" 
                               class="sp-btn-primary py-2 text-xs font-bold flex items-center justify-center gap-1.5 shadow-xs hover:shadow-md transition-all" 
                               title="الانتقال إلى بوابة التقديم الرسمية المعتمدة">
                                <span>قدّم الآن</span>
                                <i data-lucide="arrow-up-right" class="w-3.5 h-3.5"></i>
                            </a>
                        </div>
                    </div>
                </article>
            `;
        }
    };

    window.ScholarshipCard = ScholarshipCard;
})();
