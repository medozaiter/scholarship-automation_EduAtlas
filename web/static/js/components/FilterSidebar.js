/**
 * EduAtlas - FilterSidebar Component
 * Instant, accessible client-side filtering and sorting controller without page reloads.
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

    const FilterSidebar = {
        /**
         * Renders the FilterSidebar HTML.
         * @param {FilterState} state
         * @param {number} totalCount
         * @param {number} filteredCount
         * @returns {string} HTML string
         */
        render(state, totalCount, filteredCount) {
            const countries = [
                { id: 'all', name: 'كافة الدول' },
                { id: 'Canada', name: 'كندا (Canada)' },
                { id: 'Hungary', name: 'المجر (Hungary)' },
                { id: 'Turkey', name: 'تركيا (Turkey)' },
                { id: 'UK', name: 'بريطانيا (UK)' },
                { id: 'Germany', name: 'ألمانيا (Germany)' },
                { id: 'Europe', name: 'الاتحاد الأوروبي' },
                { id: 'South Korea', name: 'كوريا الجنوبية' },
                { id: 'USA', name: 'الولايات المتحدة' }
            ];

            const activeFiltersCount = (state.degree !== 'all' ? 1 : 0) +
                                      (state.funding !== 'all' ? 1 : 0) +
                                      (state.country !== 'all' ? 1 : 0) +
                                      (state.language !== 'all' ? 1 : 0) +
                                      (state.query ? 1 : 0);

            return `
                <aside class="sp-card p-5 border border-slate-200/80 dark:border-slate-800/80 space-y-5" aria-label="فلاتر تصفية وفرز المنح">
                    <!-- Header with Filter Counter & Reset -->
                    <div class="flex items-center justify-between pb-3 border-b border-slate-200/80 dark:border-slate-800/80">
                        <div class="flex items-center gap-2">
                            <i data-lucide="filter" class="w-4 h-4 text-blue-500"></i>
                            <h3 class="text-sm font-bold text-slate-900 dark:text-white">تصفية وفرز الفرص</h3>
                            ${activeFiltersCount > 0 ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-600 text-white font-latin">${activeFiltersCount}</span>` : ''}
                        </div>

                        ${activeFiltersCount > 0 ? `
                            <button type="button" 
                                    onclick="DashboardApp.resetFilters()" 
                                    class="text-[11px] text-blue-600 dark:text-blue-400 hover:underline font-bold flex items-center gap-1">
                                <i data-lucide="rotate-ccw" class="w-3 h-3"></i>
                                <span>إعادة ضبط</span>
                            </button>
                        ` : ''}
                    </div>

                    <!-- Instant Search -->
                    <div class="space-y-1.5">
                        <label for="filterSearchInput" class="block text-xs font-bold text-slate-700 dark:text-slate-300">البحث الفوري</label>
                        <div class="relative">
                            <i data-lucide="search" class="w-3.5 h-3.5 text-slate-400 absolute top-1/2 -translate-y-1/2 right-3 pointer-events-none"></i>
                            <input type="text" 
                                   id="filterSearchInput" 
                                   value="${escapeHtml(state.query || '')}" 
                                   oninput="DashboardApp.handleSearchInput(this.value)" 
                                   placeholder="ابحث باسم المنحة، الجامعة، أو الدولة..." 
                                   class="sp-input text-xs py-2 pr-9 pl-3 w-full">
                        </div>
                    </div>

                    <!-- 1. Degree Level Filter -->
                    <div class="space-y-2">
                        <label class="block text-xs font-bold text-slate-700 dark:text-slate-300">المرحلة الدراسية</label>
                        <div class="grid grid-cols-2 gap-1.5 text-xs font-bold">
                            <button type="button" 
                                    onclick="DashboardApp.setFilter('degree', 'all')" 
                                    class="p-2 rounded-xl border text-center transition ${state.degree === 'all' ? 'bg-blue-600 text-white border-blue-600 shadow-xs' : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'}">
                                كافة المراحل
                            </button>
                            <button type="button" 
                                    onclick="DashboardApp.setFilter('degree', 'bachelor')" 
                                    class="p-2 rounded-xl border text-center transition flex items-center justify-center gap-1 ${state.degree === 'bachelor' ? 'bg-blue-600 text-white border-blue-600 shadow-xs' : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'}">
                                <i data-lucide="graduation-cap" class="w-3.5 h-3.5"></i>
                                <span>بكالوريوس</span>
                            </button>
                            <button type="button" 
                                    onclick="DashboardApp.setFilter('degree', 'master')" 
                                    class="p-2 rounded-xl border text-center transition flex items-center justify-center gap-1 ${state.degree === 'master' ? 'bg-blue-600 text-white border-blue-600 shadow-xs' : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'}">
                                <i data-lucide="scroll" class="w-3.5 h-3.5"></i>
                                <span>ماجستير</span>
                            </button>
                            <button type="button" 
                                    onclick="DashboardApp.setFilter('degree', 'phd')" 
                                    class="p-2 rounded-xl border text-center transition flex items-center justify-center gap-1 ${state.degree === 'phd' ? 'bg-blue-600 text-white border-blue-600 shadow-xs' : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'}">
                                <i data-lucide="microscope" class="w-3.5 h-3.5"></i>
                                <span>دكتوراه</span>
                            </button>
                        </div>
                    </div>

                    <!-- 2. Funding Type Filter -->
                    <div class="space-y-2">
                        <label class="block text-xs font-bold text-slate-700 dark:text-slate-300">نوع التمويل المالي</label>
                        <div class="flex flex-col gap-1.5 text-xs font-bold">
                            <button type="button" 
                                    onclick="DashboardApp.setFilter('funding', 'all')" 
                                    class="p-2 rounded-xl border text-right transition flex items-center justify-between ${state.funding === 'all' ? 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border-blue-500' : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'}">
                                <span>كافة أنواع التمويل</span>
                                <span class="w-2 h-2 rounded-full ${state.funding === 'all' ? 'bg-blue-500' : 'bg-transparent'}"></span>
                            </button>
                            <button type="button" 
                                    onclick="DashboardApp.setFilter('funding', 'fully')" 
                                    class="p-2 rounded-xl border text-right transition flex items-center justify-between ${state.funding === 'fully' ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border-emerald-500' : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'}">
                                <span>تمويل كامل 100% (Fully Funded)</span>
                                <span class="w-2 h-2 rounded-full ${state.funding === 'fully' ? 'bg-emerald-500' : 'bg-transparent'}"></span>
                            </button>
                            <button type="button" 
                                    onclick="DashboardApp.setFilter('funding', 'partial')" 
                                    class="p-2 rounded-xl border text-right transition flex items-center justify-between ${state.funding === 'partial' ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 border-amber-500' : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'}">
                                <span>إعفاء دراسي جزئي / رسوم</span>
                                <span class="w-2 h-2 rounded-full ${state.funding === 'partial' ? 'bg-amber-500' : 'bg-transparent'}"></span>
                            </button>
                        </div>
                    </div>

                    <!-- 3. Country Filter -->
                    <div class="space-y-1.5">
                        <label for="filterCountrySelect" class="block text-xs font-bold text-slate-700 dark:text-slate-300">الدولة المستهدفة</label>
                        <select id="filterCountrySelect" 
                                onchange="DashboardApp.setFilter('country', this.value)" 
                                class="sp-input text-xs w-full font-semibold">
                            ${countries.map(c => `
                                <option value="${escapeHtml(c.id)}" ${state.country === c.id ? 'selected' : ''}>
                                    ${escapeHtml(c.name)}
                                </option>
                            `).join('')}
                        </select>
                    </div>

                    <!-- 4. Language Requirement Filter -->
                    <div class="space-y-1.5">
                        <label for="filterLanguageSelect" class="block text-xs font-bold text-slate-700 dark:text-slate-300">متطلبات اللغة الإنجليزية</label>
                        <select id="filterLanguageSelect" 
                                onchange="DashboardApp.setFilter('language', this.value)" 
                                class="sp-input text-xs w-full font-semibold">
                            <option value="all" ${state.language === 'all' ? 'selected' : ''}>كافة الشروط اللغوية</option>
                            <option value="none" ${state.language === 'none' ? 'selected' : ''}>بدون IELTS / شهادة لغة جامعية</option>
                            <option value="ielts" ${state.language === 'ielts' ? 'selected' : ''}>IELTS أو TOEFL إلزامي</option>
                        </select>
                    </div>

                    <!-- 5. Sort By Option -->
                    <div class="space-y-1.5 pt-2 border-t border-slate-200/80 dark:border-slate-800/80">
                        <label for="filterSortSelect" class="block text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                            <i data-lucide="arrow-up-down" class="w-3.5 h-3.5 text-blue-500"></i>
                            <span>ترتيب النتائج حسب:</span>
                        </label>
                        <select id="filterSortSelect" 
                                onchange="DashboardApp.setFilter('sortBy', this.value)" 
                                class="sp-input text-xs w-full font-bold">
                            <option value="match" ${state.sortBy === 'match' ? 'selected' : ''}>الأعلى توافقاً مع ملفي (Match Score)</option>
                            <option value="deadline" ${state.sortBy === 'deadline' ? 'selected' : ''}>الأقرب موعداً نهائياً (Nearest Deadline)</option>
                            <option value="name" ${state.sortBy === 'name' ? 'selected' : ''}>الاسم أبجدياً (A-Z)</option>
                        </select>
                    </div>

                    <!-- Results Count Badge -->
                    <div class="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-700 dark:text-blue-300 text-xs font-bold flex items-center justify-between">
                        <span>النتائج المطابقة:</span>
                        <span class="font-latin text-sm">${filteredCount} / ${totalCount}</span>
                    </div>
                </aside>
            `;
        }
    };

    window.FilterSidebar = FilterSidebar;
})();
