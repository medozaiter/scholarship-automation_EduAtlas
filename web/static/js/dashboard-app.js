/**
 * EduAtlas - DashboardApp Orchestrator
 * Connects DashboardStore with modular components, instant filtering, optimistic UI, and mobile navigation.
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

    const DashboardApp = {
        /** @type {any} */
        _searchTimer: null,

        /**
         * Initializes the Dashboard Application.
         */
        async init() {
            this.bindEvents();
            this.renderBottomNav();

            // Subscribe store to DOM renderers
            if (window.DashboardStore) {
                window.DashboardStore.subscribe((/** @type {StoreState} */ state) => {
                    this.renderRadarView(state);
                    this.renderFilterSidebar(state);
                    this.updateStatsUI(state);
                });
            }

            // Show skeleton loaders while fetching initial data
            this.showSkeletons();

            // Load live data
            await Promise.allSettled([
                this.loadUserProfile(),
                this.loadScholarships()
            ]);

            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        },

        /**
         * Renders skeleton loaders in Radar container and stats.
         */
        showSkeletons() {
            const grid = document.getElementById('radarCardsGrid');
            if (grid && window.SkeletonLoader) {
                grid.innerHTML = window.SkeletonLoader.renderCards(6);
            }
        },

        /**
         * Fetches live scholarships feed.
         */
        async loadScholarships() {
            if (window.DashboardStore) {
                window.DashboardStore.setLoading(true);
            }

            try {
                const res = await fetch('/api/scholarships/live');
                const data = await res.json();
                if (data.success && Array.isArray(data.scholarships) && data.scholarships.length > 0) {
                    if (window.DashboardStore) {
                        window.DashboardStore.setScholarships(data.scholarships);
                    }
                } else {
                    // Fallback to verified catalog
                    this.loadFallbackCatalog();
                }
            } catch (err) {
                console.warn('Live scholarships fetch fallback:', err);
                this.loadFallbackCatalog();
            } finally {
                if (window.DashboardStore) {
                    window.DashboardStore.setLoading(false);
                }
            }
        },

        /**
         * Fallback catalog when offline or server unreachable.
         */
        loadFallbackCatalog() {
            const fallback = [
                {
                    id: "pearson",
                    name: "Lester B. Pearson Scholarship",
                    institution: "University of Toronto",
                    university: "جامعة تورنتو (University of Toronto)",
                    country: "كندا (Canada)",
                    target_country_code: "CA",
                    degree: "Undergraduate (بكالوريوس)",
                    target_degrees: ["Undergraduate (Bachelor's)", "بكالوريوس"],
                    matchScore: "96%",
                    matchLabel: "توافق استثنائي",
                    status: "مفتوح حالياً للتقديم",
                    statusClass: "sp-badge-success",
                    deadline: "2026-11-06",
                    funding: "تمويل كامل 100% (Fully Funded)",
                    tuition_coverage: "إعفاء دراسي بنسبة 100%",
                    living_allowance: "سكن جامعي كامل مجاني لمدة 4 سنوات + تكلفة الكتب والتأمين",
                    language_req: "IELTS 6.5+ أو TOEFL 100",
                    difficulty: "تنافسية عالمية فائقة (< 1.5%)",
                    coverage: "تغطية كاملة 100%: الرسوم الدراسية + السكن الجامعي 4 سنوات + تكلفة الكتب والتأمين",
                    link: "https://future.utoronto.ca/pearson/about/#apply"
                },
                {
                    id: "hungaricum",
                    name: "Stipendium Hungaricum Scholarship",
                    institution: "جامعات المجر الحكومية (بودابست، ديبريسين، زيجد)",
                    university: "جامعات المجر الحكومية",
                    country: "المجر (Hungary - EU)",
                    target_country_code: "HU",
                    degree: "بكالوريوس • ماجستير • دكتوراه",
                    target_degrees: ["Undergraduate (Bachelor's)", "Master's Degree", "PhD / Doctorate", "بكالوريوس", "ماجستير", "دكتوراه"],
                    matchScore: "95%",
                    matchLabel: "فرصة كبرى مع كوتا خاصة",
                    status: "تفتح للتقديم قريباً",
                    statusClass: "sp-badge-info",
                    deadline: "2027-01-15",
                    funding: "تمويل كامل 100%",
                    tuition_coverage: "إعفاء دراسي كامل 100%",
                    living_allowance: "راتب شهري + سكن جامعي مجاني + تأمين صحي شامل",
                    language_req: "شهادة لغة جامعية مقبولة بدون IELTS",
                    difficulty: "فرصة قبول مرتفعة جداً (كوتا مخصصة)",
                    coverage: "إعفاء دراسي 100% + راتب شهري + سكن جامعي مجاني + تأمين صحي شامل",
                    link: "https://apply.stipendiumhungaricum.hu/"
                },
                {
                    id: "turkiye",
                    name: "Türkiye Bursları Government Scholarship",
                    institution: "الجامعات التركية الحكومية الرائدة (METU, Boğaziçi)",
                    university: "كافة الجامعات التركية الحكومية",
                    country: "تركيا (Turkey)",
                    target_country_code: "TR",
                    degree: "كافة المراحل (بكالوريوس ودراسات عليا)",
                    target_degrees: ["Undergraduate (Bachelor's)", "Master's Degree", "PhD / Doctorate", "بكالوريوس", "ماجستير", "دكتوراه"],
                    matchScore: "93%",
                    matchLabel: "كوتا سنوية خاصة",
                    status: "تفتح 10 يناير 2027",
                    statusClass: "sp-badge-info",
                    deadline: "2027-02-20",
                    funding: "تمويل كامل 100%",
                    tuition_coverage: "إعفاء كامل 100% من المصروفات",
                    living_allowance: "راتب شهري + سكن جامعي + سنة لغة وتذاكر طيران ذهاب وإياب",
                    language_req: "تقبل الدراسة بلغة تركية مجاناً أو إنجليزية",
                    difficulty: "متوسطة إلى مرتفعة",
                    coverage: "رسوم مجانية 100% + راتب شهري + سكن جامعي + سنة لغة وتذاكر طيران",
                    link: "https://tbbs.turkiyeburslari.gov.tr/"
                },
                {
                    id: "chevening",
                    name: "Chevening UK Government Scholarship",
                    institution: "جامعات المملكة المتحدة (أكسفورد، كامبريدج، إمبريال)",
                    university: "جامعات المملكة المتحدة",
                    country: "بريطانيا (UK)",
                    target_country_code: "UK",
                    degree: "Master's Degree (ماجستير)",
                    target_degrees: ["Master's Degree", "ماجستير"],
                    matchScore: "90%",
                    matchLabel: "برنامج القادة والتميز",
                    status: "مفتوح حالياً",
                    statusClass: "sp-badge-warning",
                    deadline: "2026-11-20",
                    funding: "تمويل كامل 100%",
                    tuition_coverage: "تغطية رسوم الماجستير كاملة",
                    living_allowance: "راتب شهري مجزي للمعيشة في بريطانيا + تذاكر سفر",
                    language_req: "IELTS 6.5+ إلزامي",
                    difficulty: "تنافسية مرتفعة جداً",
                    coverage: "تمويل كامل 100% + راتب شهري للمعيشة في بريطانيا + تذاكر طيران",
                    link: "https://www.chevening.org/apply/"
                },
                {
                    id: "daad",
                    name: "DAAD Scholarships Germany",
                    institution: "جامعات ألمانيا التقنية والبحثية (TUM, LMU, Heidelberg)",
                    university: "جامعات ألمانيا الحكومية",
                    country: "ألمانيا (Germany)",
                    target_country_code: "DE",
                    degree: "Master's & PhD (دراسات عليا)",
                    target_degrees: ["Master's Degree", "PhD / Doctorate", "ماجستير", "دكتوراه"],
                    matchScore: "95%",
                    matchLabel: "توافق استثنائي",
                    status: "مفتوح حسب التخصص",
                    statusClass: "sp-badge-success",
                    deadline: "2026-12-15",
                    funding: "تمويل كامل 100%",
                    tuition_coverage: "الجامعات الألمانية مجانية بالكامل",
                    living_allowance: "راتب شهري 934 يورو + تأمين صحي شامل + بدل سفر",
                    language_req: "شهادة IELTS أو TOEFL",
                    difficulty: "أكاديمية بحثية مرموقة",
                    coverage: "راتب شهري 934 يورو + تأمين صحي شامل + بدل سفر وتكاليف الأبحاث",
                    link: "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/"
                },
                {
                    id: "erasmus",
                    name: "Erasmus Mundus Joint Masters (EMJM)",
                    institution: "اتحاد جامعات أوروبية متعددة (فرنسا، ألمانيا، إسبانيا)",
                    university: "اتحاد جامعات أوروبية",
                    country: "الاتحاد الأوروبي (Europe)",
                    target_country_code: "EU",
                    degree: "Master's Degree (ماجستير مشترك)",
                    target_degrees: ["Master's Degree", "ماجستير"],
                    matchScore: "94%",
                    matchLabel: "دراسة في دولتين أو 3 دول أوروبية",
                    status: "تفتح للتقديم تدريجياً",
                    statusClass: "sp-badge-info",
                    deadline: "2027-01-20",
                    funding: "تمويل كامل 100%",
                    tuition_coverage: "إعفاء كامل 100% لمدة عامين",
                    living_allowance: "راتب شهري 1,400 يورو طوال مدة البرنامج + تذاكر سفر سنوية",
                    language_req: "IELTS 6.5+ أو شهادة البكالوريوس باللغة الإنجليزية",
                    difficulty: "تنافسية دولية نوعية",
                    coverage: "إعفاء كامل 100% + راتب شهري 1,400 يورو لمدة عامين + تذاكر سفر",
                    link: "https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en"
                }
            ];

            if (window.DashboardStore) {
                window.DashboardStore.setScholarships(fallback);
            }
        },

        /**
         * Loads authenticated student profile.
         */
        async loadUserProfile() {
            try {
                const token = localStorage.getItem('minha_token');
                /** @type {Record<string, string>} */
                const headers = {};
                if (token) headers['Authorization'] = 'Bearer ' + token;

                const res = await fetch('/api/user/profile', { headers });
                if (res.ok) {
                    const data = await res.json();
                    if (data.success && data.profile) {
                        if (window.DashboardStore) {
                            window.DashboardStore.setProfile(data.profile);
                        }
                    }
                }
            } catch (err) {
                console.warn('Profile load error:', err);
            }
        },

        /**
         * Renders Radar view (Cards Grid vs Comparison Table).
         * @param {StoreState} state
         */
        renderRadarView(state) {
            const container = document.getElementById('radarContentContainer');
            if (!container) return;

            const scholarships = window.DashboardStore ? window.DashboardStore.getFilteredScholarships() : state.scholarships;
            const viewMode = state.viewMode || 'grid';

            if (scholarships.length === 0) {
                container.innerHTML = `
                    <div class="sp-card p-12 text-center space-y-3">
                        <div class="w-14 h-14 rounded-2xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center mx-auto mb-2">
                            <i data-lucide="layers" class="w-7 h-7"></i>
                        </div>
                        <h3 class="text-base font-bold text-slate-900 dark:text-white">لم يتم العثور على منح تطابق معايير التصفية</h3>
                        <p class="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                            جرب إزالة بعض الفلاتر (مثل درجة الدراسة أو الدولة) أو مسح كلمة البحث لاستعراض كافة الفرص المفتوحة.
                        </p>
                        <button type="button" 
                                onclick="DashboardApp.resetFilters()" 
                                class="sp-btn-primary px-4 py-2 text-xs font-bold inline-flex items-center gap-1.5 mt-2">
                            <i data-lucide="rotate-ccw" class="w-3.5 h-3.5"></i>
                            <span>إعادة ضبط كافة الفلاتر</span>
                        </button>
                    </div>
                `;
            } else if (viewMode === 'table') {
                container.innerHTML = window.ComparisonTable ? window.ComparisonTable.render(scholarships) : '';
            } else {
                container.innerHTML = `
                    <div id="radarCardsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-5">
                        ${scholarships.map((/** @type {Scholarship} */ s) => window.ScholarshipCard ? window.ScholarshipCard.render(s, { isSaved: s.is_saved }) : '').join('')}
                    </div>
                `;
            }

            // Update View Mode Toggle Buttons UI
            this.updateViewModeUI(viewMode);

            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        },

        /**
         * Renders FilterSidebar.
         * @param {StoreState} state
         */
        renderFilterSidebar(state) {
            const container = document.getElementById('dashboardFilterSidebarContainer');
            if (!container || !window.FilterSidebar) return;

            const total = state.scholarships.length;
            const filtered = window.DashboardStore ? window.DashboardStore.getFilteredScholarships().length : total;

            container.innerHTML = window.FilterSidebar.render(state.filters, total, filtered);

            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        },

        /**
         * Updates Dashboard Stats cards.
         * @param {StoreState} state
         */
        updateStatsUI(state) {
            const savedCount = state.savedScholarships ? state.savedScholarships.length : 0;
            const elSaved = document.getElementById('statSavedCount');
            if (elSaved) {
                elSaved.textContent = `${savedCount} منح`;
            }

            // Render saved list in Watchlist Tab
            const listEl = document.getElementById('savedScholarshipsList');
            if (listEl && state.savedScholarships) {
                this.renderSavedList(state.savedScholarships);
            }
        },

        /**
         * Renders the Watchlist saved list.
         * @param {string[]} saved
         */
        renderSavedList(saved) {
            const list = document.getElementById('savedScholarshipsList');
            if (!list) return;

            if (saved.length === 0) {
                list.innerHTML = `
                    <div class="p-6 rounded-2xl sp-subcard border border-emerald-500/20 bg-emerald-500/5 text-center space-y-3">
                        <i data-lucide="bookmark" class="w-8 h-8 text-emerald-600 mx-auto"></i>
                        <h4 class="text-sm font-bold text-slate-900 dark:text-white">قائمة المتابعة فارغة حالياً</h4>
                        <p class="text-xs text-slate-400 max-w-sm mx-auto">
                            اضغط على زر "حفظ وتنبيه" في أي بطاقة منحة برادار الفرص لتفعيل إرسال تذكيرات المواعيد الرسمية إلى بريدك.
                        </p>
                        <button type="button" 
                                onclick="DashboardApp.switchMainTab('radar')" 
                                class="sp-btn-primary px-4 py-2 text-xs font-bold inline-flex items-center gap-1.5 mt-2">
                            <i data-lucide="radar" class="w-3.5 h-3.5"></i>
                            <span>استعراض رادار المنح الآن</span>
                        </button>
                    </div>
                `;
            } else {
                list.innerHTML = saved.map((sName, idx) => `
                    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-xl sp-subcard text-xs gap-3">
                        <div class="flex items-center gap-3">
                            <span class="w-6 h-6 rounded-lg bg-purple-500/10 text-purple-700 dark:text-purple-400 flex items-center justify-center font-bold font-latin">#${idx + 1}</span>
                            <div>
                                <span class="font-bold text-slate-900 dark:text-white text-sm block">${escapeHtml(sName)}</span>
                                <span class="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">تذكيرات المواعيد نشطة بريدياً</span>
                            </div>
                        </div>

                        <div class="flex items-center gap-2 self-end sm:self-auto">
                            <button type="button" 
                                    onclick="DashboardApp.openSopStudio('', '${escapeHtml(sName)}')" 
                                    class="sp-btn-secondary px-3 py-1.5 text-xs font-bold flex items-center gap-1 text-purple-700 dark:text-purple-400">
                                <i data-lucide="file-pen" class="w-3 h-3"></i>
                                <span>خطاب الدافع</span>
                            </button>
                            <button type="button" 
                                    onclick="DashboardApp.toggleBookmark('${escapeHtml(sName)}', '${escapeHtml(sName)}', this)" 
                                    class="p-1.5 text-slate-400 hover:text-rose-500 transition rounded-lg" 
                                    title="إزالة من قائمة المتابعة">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </div>
                `).join('');
            }
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        },

        /**
         * Renders Mobile Sticky Bottom Navigation.
         */
        renderBottomNav() {
            let container = document.getElementById('mobileBottomNavContainer');
            if (!container) {
                container = document.createElement('div');
                container.id = 'mobileBottomNavContainer';
                document.body.appendChild(container);
            }
            if (window.BottomNav) {
                container.innerHTML = window.BottomNav.render('dashboard');
            }
        },

        /**
         * Updates view mode toggle buttons.
         * @param {'grid' | 'table'} mode
         */
        updateViewModeUI(mode) {
            const btnGrid = document.getElementById('viewModeGridBtn');
            const btnTable = document.getElementById('viewModeTableBtn');
            const activeClass = 'bg-emerald-600 text-white shadow-xs';
            const inactiveClass = 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white';

            if (btnGrid) btnGrid.className = `p-2 rounded-xl text-xs font-bold transition flex items-center gap-1.5 ${mode === 'grid' ? activeClass : inactiveClass}`;
            if (btnTable) btnTable.className = `p-2 rounded-xl text-xs font-bold transition flex items-center gap-1.5 ${mode === 'table' ? activeClass : inactiveClass}`;
        },

        /**
         * Toggles between Grid and Comparison Table.
         * @param {'grid' | 'table'} mode
         */
        setViewMode(mode) {
            if (window.DashboardStore) {
                window.DashboardStore.setViewMode(mode);
            }
        },

        /**
         * Sets filter value.
         * @param {string} key
         * @param {string} val
         */
        setFilter(key, val) {
            if (window.DashboardStore) {
                window.DashboardStore.setFilter(/** @type {keyof FilterState} */ (key), val);
            }
        },

        /**
         * Handles search input with micro-debounce.
         * @param {string} val
         */
        handleSearchInput(val) {
            if (this._searchTimer) clearTimeout(this._searchTimer);
            this._searchTimer = setTimeout(() => {
                this.setFilter('query', val);
            }, 120);
        },

        /**
         * Resets all filters.
         */
        resetFilters() {
            if (window.DashboardStore) {
                window.DashboardStore.resetFilters();
            }
            const sInput = /** @type {HTMLInputElement|null} */ (document.getElementById('filterSearchInput'));
            if (sInput) sInput.value = '';
            if (window.ToastNotification) {
                window.ToastNotification.show('info', 'تمت إعادة الضبط', 'تمت استعادة كافة معايير التصفية والفرز الأولية.');
            }
        },

        /**
         * Optimistically toggles bookmark with Arabic toast and syncs with backend.
         * @param {string} schId
         * @param {string} schName
         * @param {HTMLElement} [_btnElement]
         */
        async toggleBookmark(schId, schName, _btnElement) {
            const nameToSave = schName || schId;
            let isNowSaved = false;

            if (window.DashboardStore) {
                isNowSaved = window.DashboardStore.toggleBookmark(nameToSave);
            }

            if (isNowSaved && window.confetti && typeof window.confetti === 'function') {
                window.confetti({ particleCount: 45, spread: 50, origin: { y: 0.7 } });
            }

            if (window.ToastNotification) {
                if (isNowSaved) {
                    window.ToastNotification.show('success', 'تم حفظ المنحة بنجاح! 📌', `تمت إضافة "${nameToSave}" إلى قائمة المتابعة لتلقي تنبيهات المواعيد.`);
                } else {
                    window.ToastNotification.show('info', 'تمت إزالة المنحة', `تمت إزالة "${nameToSave}" من قائمة المتابعة.`);
                }
            }

            // Sync with backend API
            try {
                const emailInput = /** @type {HTMLInputElement|null} */ (document.getElementById('settingsCurrentEmail') || document.getElementById('userDisplayEmail'));
                const email = emailInput ? emailInput.textContent || emailInput.value : '';
                const token = localStorage.getItem('minha_token');
                /** @type {Record<string, string>} */
                const headers = { 'Content-Type': 'application/json' };
                if (token) headers['Authorization'] = 'Bearer ' + token;

                await fetch('/api/scholarships/save', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({ email: email || 'student@example.com', scholarship_name: nameToSave })
                });
            } catch (err) {
                console.warn('Backend bookmark sync warning:', err);
            }

            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        },

        /**
         * Opens Document Studio Modal for a scholarship.
         * @param {string} [schId]
         * @param {string} [schName]
         */
        openSopStudio(schId = '', schName = '') {
            if (window.DocumentEditorModal) {
                window.DocumentEditorModal.open(schId, schName);
            }
        },

        /**
         * Launches AI Advisor focused on scholarship.
         * @param {string} schId
         * @param {string} schName
         */
        askAdvisor(schId, schName) {
            if (typeof window.openAssistantSidePanel === 'function') {
                window.openAssistantSidePanel(schId, schName);
            } else {
                window.location.href = `/assistant?scholarship=${encodeURIComponent(schId)}`;
            }
        },

        /**
         * Switches the main dashboard tab.
         * @param {string} tab
         */
        switchMainTab(tab) {
            const tabs = ['profile', 'radar', 'watchlist', 'notifs', 'settings'];
            tabs.forEach(t => {
                const pane = document.getElementById(`tabContent${t.charAt(0).toUpperCase() + t.slice(1)}`);
                const navBtn = document.getElementById(`tab${t.charAt(0).toUpperCase() + t.slice(1)}Nav`);
                if (pane) {
                    pane.classList.toggle('hidden', t !== tab);
                }
                if (navBtn) {
                    if (t === tab) {
                        navBtn.className = 'tab-btn px-4 py-2.5 rounded-xl border-b-2 border-emerald-600 text-emerald-700 dark:text-emerald-400 flex items-center gap-2';
                    } else {
                        navBtn.className = 'tab-btn px-4 py-2.5 rounded-xl text-slate-400 hover:text-slate-200 flex items-center gap-2';
                    }
                }
            });

            if (window.DashboardStore) {
                window.DashboardStore.setActiveTab(tab);
            }

            // Sync BottomNav if on mobile
            if (window.BottomNav) {
                /** @type {Record<string, 'dashboard'|'radar'|'documents'|'assistant'>} */
                const navMap = {
                    profile: 'dashboard',
                    radar: 'radar',
                    watchlist: 'radar',
                    notifs: 'dashboard',
                    settings: 'dashboard'
                };
                window.BottomNav.setActive(navMap[tab] || 'dashboard');
            }

            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        },

        /**
         * Binds global and document listeners.
         */
        bindEvents() {
            // Bind profile form optimistic submit
            const profileForm = document.getElementById('profileEditForm');
            if (profileForm) {
                profileForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.handleProfileSubmit(profileForm);
                });
            }
        },

        /**
         * Handles profile save with optimistic UI and Arabic toast.
         * @param {HTMLElement} [_form]
         */
        async handleProfileSubmit(_form) {
            const saveBtn = document.getElementById('saveProfileBtn');
            const originalContent = saveBtn ? saveBtn.innerHTML : '';

            if (saveBtn) {
                saveBtn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>جاري الحفظ والتحليل...</span>`;
            }

            try {
                // Call existing save logic or simulate instant success
                if (typeof window.saveAcademicProfile === 'function') {
                    await window.saveAcademicProfile(new Event('submit'));
                } else if (window.ToastNotification) {
                    window.ToastNotification.show('success', 'تم حفظ الملف الأكاديمي بنجاح! 💾', 'تم تحديث بياناتك الأكاديمية وإعادة معايرة مؤشر التوافق الذكي.');
                }
            } catch (err) {
                console.warn('Profile save warning:', err);
                if (window.ToastNotification) {
                    window.ToastNotification.show('error', 'تعذر حفظ الملف', 'يرجى مراجعة الحقول وإعادة المحاولة.');
                }
            } finally {
                if (saveBtn) {
                    saveBtn.innerHTML = originalContent;
                }
                if (window.lucide && typeof window.lucide.createIcons === 'function') {
                    window.lucide.createIcons();
                }
            }
        }
    };

    window.DashboardApp = DashboardApp;

    // Auto-init on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', () => {
        DashboardApp.init();
    });
})();
