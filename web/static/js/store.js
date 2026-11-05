/**
 * EduAtlas - Centralized Reactive State Store
 * Manages scholarships, instant client-side filtering, sorting, bookmarks, and user profile.
 */

(function () {
    'use strict';

    const initialFilters = {
        degree: 'all',
        funding: 'all',
        country: 'all',
        language: 'all',
        query: '',
        sortBy: 'match'
    };

    /** @type {StoreState} */
    const state = {
        scholarships: [],
        savedScholarships: [],
        profile: null,
        filters: { ...initialFilters },
        viewMode: /** @type {'grid' | 'table'} */ (localStorage.getItem('ea_radar_view') || 'grid'),
        activeTab: 'profile',
        isLoading: false
    };

    /** @type {Array<(state: StoreState) => void>} */
    const listeners = [];

    const DashboardStore = {
        /**
         * Returns immutable copy of the state.
         * @returns {StoreState}
         */
        getState() {
            return {
                ...state,
                scholarships: [...state.scholarships],
                savedScholarships: [...state.savedScholarships],
                filters: { ...state.filters }
            };
        },

        /**
         * Subscribes a listener function to state changes.
         * @param {(state: StoreState) => void} fn
         * @returns {() => void} Unsubscribe function
         */
        subscribe(fn) {
            listeners.push(fn);
            return () => {
                const idx = listeners.indexOf(fn);
                if (idx > -1) listeners.splice(idx, 1);
            };
        },

        /**
         * Emits state change to all listeners.
         */
        emit() {
            const current = this.getState();
            listeners.forEach(fn => {
                try {
                    fn(current);
                } catch (e) {
                    console.error('Store listener error:', e);
                }
            });
        },

        /**
         * Updates scholarship listings.
         * @param {Scholarship[]} list
         */
        setScholarships(list) {
            state.scholarships = list;
            this.emit();
        },

        /**
         * Sets loading flag.
         * @param {boolean} loading
         */
        setLoading(loading) {
            state.isLoading = loading;
            this.emit();
        },

        /**
         * Updates a specific filter key and value.
         * @param {keyof FilterState} key
         * @param {string} value
         */
        setFilter(key, value) {
            state.filters[key] = value;
            this.emit();
        },

        /**
         * Resets all filters to initial state.
         */
        resetFilters() {
            state.filters = { ...initialFilters };
            this.emit();
        },

        /**
         * Sets view mode (grid vs table).
         * @param {'grid' | 'table'} mode
         */
        setViewMode(mode) {
            state.viewMode = mode;
            localStorage.setItem('ea_radar_view', mode);
            this.emit();
        },

        /**
         * Sets active tab.
         * @param {string} tab
         */
        setActiveTab(tab) {
            state.activeTab = tab;
            this.emit();
        },

        /**
         * Sets user profile.
         * @param {any} profile
         */
        setProfile(profile) {
            state.profile = profile;
            if (profile && Array.isArray(profile.saved_scholarships)) {
                state.savedScholarships = [...profile.saved_scholarships];
            }
            this.emit();
        },

        /**
         * Optimistically toggles saving a scholarship to watchlist.
         * @param {string} scholarshipName
         * @returns {boolean} New saved state
         */
        toggleBookmark(scholarshipName) {
            const cleanName = scholarshipName.trim();
            const idx = state.savedScholarships.indexOf(cleanName);
            const isNowSaved = idx === -1;

            if (isNowSaved) {
                state.savedScholarships.push(cleanName);
            } else {
                state.savedScholarships.splice(idx, 1);
            }

            // Sync scholarships is_saved flag
            state.scholarships = state.scholarships.map(s => {
                if (s.name === cleanName || s.id === cleanName) {
                    return { ...s, is_saved: isNowSaved };
                }
                return s;
            });

            this.emit();
            return isNowSaved;
        },

        /**
         * Helper to parse match score as number.
         * @param {Scholarship} s
         * @returns {number}
         */
        _parseMatchScore(s) {
            const raw = s.matchScore || s.match_score || s.admission_probability || 90;
            const parsed = parseFloat(String(raw).replace(/[^0-9.]/g, ''));
            return isNaN(parsed) ? 90 : parsed;
        },

        /**
         * Helper to parse deadline date.
         * @param {Scholarship} s
         * @returns {number} Timestamp
         */
        _parseDeadline(s) {
            const raw = s.deadline || s.deadline_display || '';
            const match = raw.match(/\d{4}-\d{2}-\d{2}/);
            if (match) return new Date(match[0]).getTime();
            return 9999999999999;
        },

        /**
         * Computes instant client-side filtered and sorted scholarships list.
         * @returns {Scholarship[]}
         */
        getFilteredScholarships() {
            const { degree, funding, country, language, query, sortBy } = state.filters;
            const savedList = state.savedScholarships;

            let result = state.scholarships.filter(s => {
                // Degree filter
                if (degree !== 'all') {
                    const targetDegrees = Array.isArray(s.target_degrees) ? s.target_degrees.join(' ').toLowerCase() : '';
                    const degText = ((s.degree || '') + ' ' + targetDegrees + ' ' + (s.name || '')).toLowerCase();

                    if (degree === 'bachelor' && !(degText.includes('bachelor') || degText.includes('undergraduate') || degText.includes('بكالوريوس') || degText.includes('كافة المراحل'))) {
                        return false;
                    }
                    if (degree === 'master' && !(degText.includes('master') || degText.includes('ماجستير') || degText.includes('دراسات عليا') || degText.includes('كافة المراحل'))) {
                        return false;
                    }
                    if (degree === 'phd' && !(degText.includes('phd') || degText.includes('doctorate') || degText.includes('دكتوراه') || degText.includes('دراسات عليا') || degText.includes('كافة المراحل'))) {
                        return false;
                    }
                }

                // Funding filter
                if (funding !== 'all') {
                    const fundText = ((s.funding || '') + ' ' + (s.coverage || '')).toLowerCase();
                    const isFully = fundText.includes('100%') || fundText.includes('كامل') || fundText.includes('fully');
                    if (funding === 'fully' && !isFully) return false;
                    if (funding === 'partial' && isFully) return false;
                }

                // Country filter
                if (country !== 'all') {
                    const cText = ((s.country || '') + ' ' + (s.target_country_code || '')).toLowerCase();
                    if (!cText.includes(country.toLowerCase())) return false;
                }

                // Language requirement filter
                if (language !== 'all') {
                    const langText = (s.language_req || '').toLowerCase();
                    const hasNoIelts = langText.includes('بدون') || langText.includes('جامعية') || langText.includes('مقبولة');
                    if (language === 'none' && !hasNoIelts) return false;
                    if (language === 'ielts' && hasNoIelts) return false;
                }

                // Text Search query
                if (query) {
                    const q = query.trim().toLowerCase();
                    const haystack = [
                        s.name,
                        s.university,
                        s.institution,
                        s.country,
                        s.coverage,
                        s.description
                    ].join(' ').toLowerCase();
                    if (!haystack.includes(q)) return false;
                }

                return true;
            });

            // Map saved status
            result = result.map(s => ({
                ...s,
                is_saved: savedList.includes(s.name) || savedList.includes(s.id)
            }));

            // Sorting
            result.sort((a, b) => {
                if (sortBy === 'match') {
                    return this._parseMatchScore(b) - this._parseMatchScore(a);
                }
                if (sortBy === 'deadline') {
                    return this._parseDeadline(a) - this._parseDeadline(b);
                }
                if (sortBy === 'name') {
                    return (a.name || '').localeCompare(b.name || '', 'ar');
                }
                return 0;
            });

            return result;
        }
    };

    window.DashboardStore = DashboardStore;
})();
