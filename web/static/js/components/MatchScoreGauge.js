/**
 * EduAtlas - MatchScoreGauge Component
 * Accessible circular SVG match score gauge with dynamic color tiering.
 */

(function () {
    'use strict';

    const MatchScoreGauge = {
        /**
         * Parses score into integer 0-100.
         * @param {number|string} score
         * @returns {number}
         */
        parseScore(score) {
            if (typeof score === 'number') {
                return Math.max(0, Math.min(100, Math.round(score)));
            }
            if (!score) return 75;
            const clean = String(score).replace(/[^0-9.]/g, '');
            const parsed = parseFloat(clean);
            if (isNaN(parsed)) return 75;
            if (parsed <= 4.0 && parsed > 0) {
                // GPA 4.0 scale conversion
                return Math.round((parsed / 4.0) * 100);
            }
            return Math.max(0, Math.min(100, Math.round(parsed)));
        },

        /**
         * @param {number} scoreNum
         * @returns {{ color: string, stroke: string, bg: string, label: string }}
         */
        getColorTier(scoreNum) {
            if (scoreNum >= 90) {
                return {
                    color: 'text-emerald-600 dark:text-emerald-400',
                    stroke: '#10b981',
                    bg: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
                    label: 'توافق استثنائي'
                };
            }
            if (scoreNum >= 80) {
                return {
                    color: 'text-blue-600 dark:text-blue-400',
                    stroke: '#3b82f6',
                    bg: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
                    label: 'توافق مرتفع'
                };
            }
            if (scoreNum >= 70) {
                return {
                    color: 'text-amber-600 dark:text-amber-400',
                    stroke: '#f59e0b',
                    bg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
                    label: 'توافق جيد'
                };
            }
            return {
                color: 'text-[#C86446]',
                stroke: '#c86446',
                bg: 'bg-[#C86446]/10 text-[#C86446] border-[#C86446]/20',
                label: 'توافق متوسط'
            };
        },

        /**
         * Renders an accessible circular SVG score gauge.
         * @param {number|string} score
         * @param {string} [customLabel]
         * @param {'sm'|'md'|'lg'} [size='md']
         * @returns {string} HTML string
         */
        render(score, customLabel = '', size = 'md') {
            const scoreNum = this.parseScore(score);
            const tier = this.getColorTier(scoreNum);
            const labelText = customLabel || tier.label;

            const dimensions = {
                sm: { size: 48, stroke: 4, radius: 19, text: 'text-xs', sub: 'text-[9px]' },
                md: { size: 68, stroke: 5, radius: 27, text: 'text-sm font-black', sub: 'text-[10px]' },
                lg: { size: 92, stroke: 6.5, radius: 37, text: 'text-lg font-black', sub: 'text-xs' }
            };

            const cfg = dimensions[size] || dimensions.md;
            const circumference = 2 * Math.PI * cfg.radius;
            const strokeDashoffset = circumference - (scoreNum / 100) * circumference;

            return `
                <div class="match-score-gauge inline-flex flex-col items-center justify-center shrink-0" 
                     role="meter" 
                     aria-valuenow="${scoreNum}" 
                     aria-valuemin="0" 
                     aria-valuemax="100" 
                     aria-label="نسبة توافق الشروط: ${scoreNum}% - ${labelText}">
                    <div class="relative flex items-center justify-center" style="width: ${cfg.size}px; height: ${cfg.size}px;">
                        <svg class="transform -rotate-90" width="${cfg.size}" height="${cfg.size}" viewBox="0 0 ${cfg.size} ${cfg.size}">
                            <!-- Background Track -->
                            <circle cx="${cfg.size / 2}" cy="${cfg.size / 2}" r="${cfg.radius}" 
                                fill="transparent" 
                                stroke="currentColor" 
                                stroke-width="${cfg.stroke}" 
                                class="text-slate-200 dark:text-slate-800/80" />
                            <!-- Active Progress -->
                            <circle cx="${cfg.size / 2}" cy="${cfg.size / 2}" r="${cfg.radius}" 
                                fill="transparent" 
                                stroke="${tier.stroke}" 
                                stroke-width="${cfg.stroke}" 
                                stroke-linecap="round" 
                                stroke-dasharray="${circumference}" 
                                stroke-dashoffset="${strokeDashoffset}" 
                                class="transition-all duration-700 ease-out" />
                        </svg>
                        <div class="absolute inset-0 flex flex-col items-center justify-center text-center font-latin">
                            <span class="${cfg.text} ${tier.color} leading-none tabular-nums font-black">${scoreNum}%</span>
                            <span class="${cfg.sub} text-slate-400 font-sans mt-0.5 hidden sm:block">توافق</span>
                        </div>
                    </div>
                    ${size !== 'sm' ? `<span class="mt-1 text-[11px] font-bold ${tier.color} truncate max-w-[90px] text-center">${labelText}</span>` : ''}
                </div>
            `;
        },

        /**
         * Renders an accessible compact inline pill badge with score.
         * @param {number|string} score
         * @param {string} [customLabel]
         * @returns {string} HTML string
         */
        renderBadge(score, customLabel = '') {
            const scoreNum = this.parseScore(score);
            const tier = this.getColorTier(scoreNum);
            const labelText = customLabel || tier.label;

            return `
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-[11px] font-bold ${tier.bg}"
                      role="meter" aria-valuenow="${scoreNum}" aria-valuemin="0" aria-valuemax="100" aria-label="توافق الشروط ${scoreNum}%">
                    <span class="w-1.5 h-1.5 rounded-full" style="background-color: ${tier.stroke}"></span>
                    <span class="font-latin font-black">${scoreNum}%</span>
                    <span>${labelText}</span>
                </span>
            `;
        }
    };

    window.MatchScoreGauge = MatchScoreGauge;
})();
