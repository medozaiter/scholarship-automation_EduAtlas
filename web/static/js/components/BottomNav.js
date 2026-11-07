/**
 * EduAtlas - BottomNav Component
 * Mobile-First Sticky Bottom Navigation Bar for quick switching between
 * Dashboard, Radar, Document Studio, and AI Assistant (360px-768px).
 */

(function () {
    'use strict';

    const BottomNav = {
        /**
         * @typedef {'dashboard' | 'radar' | 'documents' | 'assistant'} NavTab
         */
        currentTab: 'dashboard',

        /**
         * Renders the sticky bottom navigation HTML.
         * @param {NavTab} [activeTab='dashboard']
         * @returns {string} HTML string
         */
        render(activeTab = 'dashboard') {
            this.currentTab = activeTab;

            const tabs = [
                {
                    id: 'dashboard',
                    label: 'لوحة التحكم',
                    icon: 'layout-dashboard',
                    onClick: "DashboardApp.switchMainTab('profile')"
                },
                {
                    id: 'radar',
                    label: 'رادار المنح',
                    icon: 'radar',
                    onClick: "DashboardApp.switchMainTab('radar')"
                },
                {
                    id: 'documents',
                    label: 'استوديو الوثائق',
                    icon: 'file-pen',
                    onClick: "DashboardApp.openSopStudio()"
                },
                {
                    id: 'assistant',
                    label: 'المستشار الذكي',
                    icon: 'sparkles',
                    onClick: "DashboardApp.toggleAssistantSidePanel(true)"
                }
            ];

            return `
                <nav id="mobileStickyBottomNav" 
                     class="fixed bottom-0 inset-x-0 z-50 md:hidden bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl border-t border-slate-200/80 dark:border-slate-800/80 shadow-[0_-8px_30px_rgba(0,0,0,0.12)] px-2 py-1.5 transition-all duration-200 safe-bottom-area"
                     aria-label="شريط التنقل السفلي السريع للجوال">
                    <div class="flex items-center justify-around max-w-lg mx-auto">
                        ${tabs.map(t => {
                            const isActive = this.currentTab === t.id;
                            const activeClass = isActive
                                ? 'text-emerald-700 dark:text-emerald-400 font-black'
                                : 'text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:hover:text-white';
                            const activePill = isActive
                                ? '<span class="absolute top-0.5 inset-x-3 h-0.5 rounded-full bg-emerald-600 dark:bg-emerald-400"></span>'
                                : '';

                            return `
                                <button type="button" 
                                        onclick="${t.onClick}; BottomNav.setActive('${t.id}')" 
                                        id="bottomNavBtn_${t.id}"
                                        class="relative flex-1 py-1 px-1 flex flex-col items-center justify-center gap-1 rounded-xl transition-all duration-150 active:scale-95 ${activeClass}">
                                    ${activePill}
                                    <div class="relative flex items-center justify-center w-7 h-7 rounded-lg ${isActive ? 'bg-emerald-500/10' : ''}">
                                        <i data-lucide="${t.icon}" class="w-4 h-4"></i>
                                    </div>
                                    <span class="text-[10px] leading-none tracking-tight">${t.label}</span>
                                </button>
                            `;
                        }).join('')}
                    </div>
                </nav>
            `;
        },

        /**
         * Sets active tab state and updates button classes.
         * @param {NavTab} tab
         */
        setActive(tab) {
            this.currentTab = tab;
            const tabIds = ['dashboard', 'radar', 'documents', 'assistant'];
            tabIds.forEach(id => {
                const btn = document.getElementById(`bottomNavBtn_${id}`);
                if (!btn) return;
                const isActive = id === tab;
                if (isActive) {
                    btn.className = 'relative flex-1 py-1 px-1 flex flex-col items-center justify-center gap-1 rounded-xl transition-all duration-150 active:scale-95 text-emerald-700 dark:text-emerald-400 font-black';
                } else {
                    btn.className = 'relative flex-1 py-1 px-1 flex flex-col items-center justify-center gap-1 rounded-xl transition-all duration-150 active:scale-95 text-slate-500 dark:text-slate-400 font-medium hover:text-slate-900 dark:hover:text-white';
                }
            });
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        }
    };

    window.BottomNav = BottomNav;
})();
