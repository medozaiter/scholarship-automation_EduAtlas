/**
 * EduAtlas - MatchScoreGauge Component
 * Refined Palette: Emerald Green (Exceptional Match), Purple (High Match), Amber (Moderate / Caution)
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
            if (scoreNum >= 88) {
                return {
                    color: 'text-emerald-700 dark:text-emerald-300 font-bold',
                    stroke: '#059669',
                    bg: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20',
                    label: 'توافق استثنائي'
                };
            }
            if (scoreNum >= 75) {
                return {
                    color: 'text-purple-700 dark:text-purple-300 font-bold',
                    stroke: '#7C3AED',
                    bg: 'bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/20',
                    label: 'توافق مرتفع'
                };
            }
            return {
                color: 'text-amber-800 dark:text-amber-300 font-bold',
                stroke: '#D97706',
                bg: 'bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-500/20',
                label: 'بحاجة لمستندات'
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
                                class="text-purple-100 dark:text-slate-800" />
                            <!-- Progress Ring -->
                            <circle cx="${cfg.size / 2}" cy="${cfg.size / 2}" r="${cfg.radius}" 
                                fill="transparent" 
                                stroke="${tier.stroke}" 
                                stroke-width="${cfg.stroke}" 
                                stroke-dasharray="${circumference}" 
                                stroke-dashoffset="${strokeDashoffset}" 
                                stroke-linecap="round" 
                                class="transition-all duration-700 ease-out" />
                        </svg>
                        <div class="absolute inset-0 flex flex-col items-center justify-center text-center">
                            <span class="${cfg.text} ${tier.color} font-latin font-black leading-none">${scoreNum}%</span>
                        </div>
                    </div>
                    <span class="${cfg.sub} font-bold text-slate-500 dark:text-slate-400 mt-1">${labelText}</span>
                </div>
            `;
        }
    };

    window.MatchScoreGauge = MatchScoreGauge;
})();
