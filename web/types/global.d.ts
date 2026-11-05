// Global ambient type declarations for frontend scripts and modular components

declare global {
    interface LucideStatic {
        createIcons: (options?: Record<string, unknown>) => void;
    }

    interface MarkedStatic {
        parse: (markdown: string) => string;
    }

    interface ConfettiOptions {
        particleCount?: number;
        spread?: number;
        origin?: { x?: number; y?: number };
        colors?: string[];
    }

    type ConfettiFunction = (options?: ConfettiOptions) => void;

    interface Scholarship {
        id: string;
        name: string;
        university?: string;
        institution?: string;
        country: string;
        target_country_code?: string;
        degree?: string;
        target_degrees?: string[];
        target_majors?: string[];
        min_gpa_percent?: number;
        min_gpa_4?: number;
        matchScore?: string | number;
        match_score?: string | number;
        admission_probability?: string;
        matchLabel?: string;
        status?: string;
        statusClass?: string;
        deadline?: string;
        deadline_display?: string;
        coverage?: string;
        funding?: string;
        tuition_coverage?: string;
        living_allowance?: string;
        language_req?: string;
        difficulty?: string;
        competitiveness?: string;
        application_complexity?: string;
        link?: string;
        description?: string;
        requirements?: string;
        quota_palestine?: boolean;
        is_saved?: boolean;
    }

    interface FilterState {
        degree: string;
        funding: string;
        country: string;
        language: string;
        query: string;
        sortBy: string;
    }

    interface StoreState {
        scholarships: Scholarship[];
        savedScholarships: string[];
        profile: any;
        filters: FilterState;
        viewMode: 'grid' | 'table';
        activeTab: string;
        isLoading: boolean;
    }

    interface ToastOptions {
        duration?: number;
        action?: {
            text: string;
            onClick: () => void;
        };
    }

    interface Window {
        lucide?: LucideStatic;
        marked?: MarkedStatic;
        confetti?: ConfettiFunction;
        theme?: string;

        // Modular components & store
        DashboardStore?: any;
        ScholarshipCard?: any;
        MatchScoreGauge?: any;
        FilterSidebar?: any;
        DocumentEditorModal?: any;
        ToastNotification?: any;
        ComparisonTable?: any;
        SkeletonLoader?: any;
        BottomNav?: any;
        DashboardApp?: any;

        // Legacy / template helpers
        showToast?: (type: string, title: string, message: string, duration?: number) => HTMLElement | null;
        switchMainTab?: (tab: string) => void;
        toggleTheme?: () => void;
        updateThemeButton?: () => void;
        openDocumentStudioModal?: (scholarshipId?: string) => void;
        closeDocumentStudioModal?: () => void;
        openAssistantSidePanel?: (schId?: string, schName?: string) => void;
        toggleAssistantSidePanel?: (force?: boolean) => void;
        quickMarkAllRead?: (e?: Event) => Promise<void>;
        quickMarkSingleRead?: (id: string, e?: Event) => Promise<void>;
        filterDropdownNotifs?: (category: string, e?: Event) => void;
        toggleUnifiedNotifDropdown?: (e?: Event) => void;
        triggerMyReport?: () => void;
        saveAcademicProfile?: (e?: Event) => Promise<void>;
        escapeHTML?: (str: unknown) => string;
    }

    const lucide: LucideStatic | undefined;
    const marked: MarkedStatic | undefined;
    const confetti: ConfettiFunction | undefined;
}

export {};
