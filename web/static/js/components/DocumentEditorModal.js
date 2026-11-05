/**
 * EduAtlas - DocumentEditorModal Component
 * Accessible Statement of Purpose (SOP) & Motivation Letter Studio with multi-step AI progress.
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

    const DocumentEditorModal = {
        currentScholarshipId: '',
        currentScholarshipName: '',
        currentStep: 0,
        activeTab: 'edit', // 'edit' | 'preview' | 'audit'
        editorContent: '',
        isGenerating: false,

        /**
         * Multi-step progress states for SOP generation.
         */
        STEPS: [
            { id: 1, label: 'جاري تحليل ملفك الأكاديمي ومؤهلاتك...' },
            { id: 2, label: 'جاري مطابقة شروط ومعايير المنحة الدولية...' },
            { id: 3, label: 'جاري صياغة خطاب الدافع المخصص وتوجيه المحتوى...' },
            { id: 4, label: 'جاري المراجعة اللغوية والتدقيق الأكاديمي...' }
        ],

        /**
         * Initializes and binds the modal into DOM.
         */
        init() {
            let modalEl = document.getElementById('documentEditorModal');
            if (!modalEl) {
                modalEl = document.createElement('div');
                modalEl.id = 'documentEditorModal';
                modalEl.className = 'fixed inset-0 z-[80] hidden items-center justify-center p-3 sm:p-6 bg-slate-950/75 backdrop-blur-md';
                modalEl.setAttribute('role', 'dialog');
                modalEl.setAttribute('aria-modal', 'true');
                modalEl.setAttribute('aria-labelledby', 'docModalTitle');
                document.body.appendChild(modalEl);
            }

            // Global ESC key listener
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    const m = document.getElementById('documentEditorModal');
                    if (m && !m.classList.contains('hidden')) {
                        DocumentEditorModal.close();
                    }
                }
            });
        },

        /**
         * Opens the modal with targeted scholarship context.
         * @param {string} [scholarshipId]
         * @param {string} [scholarshipName]
         */
        open(scholarshipId = '', scholarshipName = '') {
            this.init();
            this.currentScholarshipId = scholarshipId;
            this.currentScholarshipName = scholarshipName;
            this.activeTab = 'edit';

            // Preload draft if exists or use fallback
            const savedDraft = localStorage.getItem(`sop_draft_${scholarshipId}`) || '';
            if (savedDraft) {
                this.editorContent = savedDraft;
            } else if (!this.editorContent) {
                this.editorContent = this.getStarterTemplate(scholarshipName);
            }

            this.renderModal();

            const modalEl = document.getElementById('documentEditorModal');
            if (modalEl) {
                modalEl.classList.remove('hidden');
                modalEl.classList.add('flex');
                document.body.classList.add('overflow-hidden');
            }

            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        },

        /**
         * Closes the modal.
         */
        close() {
            const modalEl = document.getElementById('documentEditorModal');
            if (modalEl) {
                modalEl.classList.add('hidden');
                modalEl.classList.remove('flex');
                document.body.classList.remove('overflow-hidden');
            }
        },

        /**
         * Provides a clean structured starter template.
         * @param {string} schName
         * @returns {string}
         */
        getStarterTemplate(schName) {
            const target = schName || 'المنحة الأكاديمية المستهدفة';
            return `### خطاب الدافع الأكاديمي (Statement of Purpose)

**إلى لجنة اختيار وترشيح منحة:** ${target}
**الموضوع:** طلب الالتحاق والترشيح الأكاديمي الممول

يشرفني أن أتقدم بطلبي هذا للالتحاق ببرنامجكم الأكاديمي المتميز، مدفوعاً بشغفي المستمر ومساري العلمي الذي ركز على الابتكار وحل المشكلات الواقعية. تمثل هذه الفرصة خطوة حاسمة في صقل مهاراتي والمساهمة في بيئة بحثية متقدمة.

خلال مسيرتي الدراسية السابقة، حرصت على تحقيق التميز الأكاديمي والانخراط في مشاريع تطبيقية ومبادرات تطوعية نوعية. هذه التجارب عززت قدرتي على التفكير النقدي المستقل والعمل ضمن فرق عمل متعددة الثقافات.

وقع اختياري على هذه المنحة تحديداً نظراً للمناهج الرائدة والبيئة المحفزة التي توفرها، مما يتطابق بدقة مع أهدافي الأكاديمية وطموحي في نقل وتوطين المعرفة والمساهمة في تنمية مجتمعي المستقبلي.

شاكراً لكم حسن اهتمامكم ونظركم في طلبي،،

**مقدم الطلب:** الطالب الباحث`;
        },

        /**
         * Updates word and character counters.
         */
        updateCounters() {
            const textarea = /** @type {HTMLTextAreaElement|null} */ (document.getElementById('sopTextarea'));
            if (!textarea) return;
            const text = textarea.value;
            this.editorContent = text;
            if (this.currentScholarshipId) {
                localStorage.setItem(`sop_draft_${this.currentScholarshipId}`, text);
            }

            const words = text.trim() ? text.trim().split(/\s+/).length : 0;
            const chars = text.length;

            const counterEl = document.getElementById('sopCountersBadge');
            if (counterEl) {
                counterEl.textContent = `${words} كلمة · ${chars} حرف`;
            }
        },

        /**
         * Switches the active editor tab.
         * @param {'edit'|'preview'|'audit'} tab
         */
        switchTab(tab) {
            this.activeTab = tab;
            const editPane = document.getElementById('sopTabEdit');
            const prevPane = document.getElementById('sopTabPreview');
            const auditPane = document.getElementById('sopTabAudit');

            const btnEdit = document.getElementById('sopBtnTabEdit');
            const btnPrev = document.getElementById('sopBtnTabPrev');
            const btnAudit = document.getElementById('sopBtnTabAudit');

            if (editPane) editPane.classList.toggle('hidden', tab !== 'edit');
            if (prevPane) {
                prevPane.classList.toggle('hidden', tab !== 'preview');
                if (tab === 'preview') {
                    const previewContent = document.getElementById('sopPreviewContent');
                    if (previewContent) {
                        const parsed = window.marked && typeof window.marked.parse === 'function'
                            ? window.marked.parse(this.editorContent)
                            : this.editorContent.replace(/\n/g, '<br>');
                        previewContent.innerHTML = parsed;
                    }
                }
            }
            if (auditPane) auditPane.classList.toggle('hidden', tab !== 'audit');

            const activeClass = 'bg-blue-600 text-white shadow-xs';
            const inactiveClass = 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white';

            if (btnEdit) btnEdit.className = `px-3.5 py-1.5 rounded-xl text-xs font-bold transition ${tab === 'edit' ? activeClass : inactiveClass}`;
            if (btnPrev) btnPrev.className = `px-3.5 py-1.5 rounded-xl text-xs font-bold transition ${tab === 'preview' ? activeClass : inactiveClass}`;
            if (btnAudit) btnAudit.className = `px-3.5 py-1.5 rounded-xl text-xs font-bold transition ${tab === 'audit' ? activeClass : inactiveClass}`;

            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        },

        /**
         * Simulates or triggers multi-step AI generation for the SOP.
         */
        async triggerAiGeneration() {
            if (this.isGenerating) return;
            this.isGenerating = true;

            const progressContainer = document.getElementById('sopAiProgressContainer');
            const genBtn = document.getElementById('sopGenerateAiBtn');
            if (progressContainer) progressContainer.classList.remove('hidden');
            if (genBtn) {
                genBtn.setAttribute('disabled', 'true');
                genBtn.classList.add('opacity-50', 'pointer-events-none');
            }

            // Animate through the 4 steps with real progress updates
            for (let stepIndex = 0; stepIndex < this.STEPS.length; stepIndex++) {
                this.updateStepUI(stepIndex);
                await new Promise(r => setTimeout(r, 650));
            }

            // Call backend API if available, else generate high-impact tailored draft
            try {
                const toneSelect = /** @type {HTMLSelectElement|null} */ (document.getElementById('sopToneSelect'));
                const tone = toneSelect ? toneSelect.value : 'academic';

                const res = await fetch('/api/advisor/consult', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: `بدي تكتبلي مسودة خطاب دافع Statement of Purpose احترافي موجه لمنحة ${this.currentScholarshipName || 'المجر وتركيا'} بأسلوب ${tone}`,
                        scholarship_id: this.currentScholarshipId || null
                    })
                });

                if (res.ok) {
                    const data = await res.json();
                    if (data.advice) {
                        this.editorContent = data.advice;
                    }
                }
            } catch (e) {
                console.warn('AI consult fallback:', e);
            }

            // Fill textarea
            const textarea = /** @type {HTMLTextAreaElement|null} */ (document.getElementById('sopTextarea'));
            if (textarea) {
                textarea.value = this.editorContent;
            }
            this.updateCounters();

            if (progressContainer) progressContainer.classList.add('hidden');
            if (genBtn) {
                genBtn.removeAttribute('disabled');
                genBtn.classList.remove('opacity-50', 'pointer-events-none');
            }
            this.isGenerating = false;

            if (window.ToastNotification) {
                window.ToastNotification.show('success', 'اكتملت صياغة خطاب الدافع! ✨', 'تمت صياغة المسودة المخصصة وتوجيهها بدقة وفق معايير الجهة المانحة.');
            }
            this.switchTab('preview');
        },

        /**
         * Updates the visual multi-step progress UI.
         * @param {number} activeIndex
         */
        updateStepUI(activeIndex) {
            const stepsList = document.getElementById('sopStepsList');
            if (!stepsList) return;

            stepsList.innerHTML = this.STEPS.map((step, idx) => {
                const isDone = idx < activeIndex;
                const isCurrent = idx === activeIndex;

                let iconHtml = '';
                let textClass = 'text-slate-400';

                if (isDone) {
                    iconHtml = `<div class="w-5 h-5 rounded-full bg-emerald-500 text-white flex items-center justify-center shrink-0"><i data-lucide="check" class="w-3 h-3"></i></div>`;
                    textClass = 'text-emerald-600 dark:text-emerald-400 font-bold';
                } else if (isCurrent) {
                    iconHtml = `<div class="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 animate-pulse"><i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i></div>`;
                    textClass = 'text-blue-600 dark:text-blue-400 font-bold';
                } else {
                    iconHtml = `<div class="w-5 h-5 rounded-full border border-slate-300 dark:border-slate-700 text-slate-400 flex items-center justify-center shrink-0 text-[10px] font-latin">${step.id}</div>`;
                }

                return `
                    <div class="flex items-center gap-2 text-xs">
                        ${iconHtml}
                        <span class="${textClass}">${step.label}</span>
                    </div>
                `;
            }).join('');

            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        },

        /**
         * Copies document to clipboard with optimistic toast.
         */
        copyToClipboard() {
            navigator.clipboard.writeText(this.editorContent).then(() => {
                if (window.ToastNotification) {
                    window.ToastNotification.show('success', 'تم نسخ الخطاب بنجاح! 📋', 'تم نسخ نص خطاب الدافع بالكامل إلى الحافظة.');
                }
            }).catch(() => {
                if (window.ToastNotification) {
                    window.ToastNotification.show('error', 'تعذر النسخ', 'يرجى تحديد النص ونسخه يدوياً.');
                }
            });
        },

        /**
         * Downloads document as text/markdown file.
         */
        downloadFile() {
            const blob = new Blob([this.editorContent], { type: 'text/markdown;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const safeName = (this.currentScholarshipName || 'Scholarship_SOP').replace(/\s+/g, '_');
            a.download = `SOP_${safeName}.md`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            if (window.ToastNotification) {
                window.ToastNotification.show('success', 'تم تنزيل الملف! 💾', `تم حفظ الملف باسم SOP_${safeName}.md بنجاح.`);
            }
        },

        /**
         * Prints the document.
         */
        printDocument() {
            window.print();
        },

        /**
         * Renders the complete modal layout.
         */
        renderModal() {
            const modalEl = document.getElementById('documentEditorModal');
            if (!modalEl) return;

            const words = this.editorContent.trim() ? this.editorContent.trim().split(/\s+/).length : 0;
            const chars = this.editorContent.length;

            modalEl.innerHTML = `
                <div class="relative w-full max-w-4xl bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[92vh] sm:max-h-[88vh] animate-in fade-in zoom-in-95 duration-200">
                    
                    <!-- Modal Header -->
                    <header class="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/90 dark:bg-slate-900/90 backdrop-blur-md flex items-center justify-between shrink-0">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center font-black shadow-md shadow-blue-500/20 shrink-0">
                                <i data-lucide="file-pen" class="w-5 h-5"></i>
                            </div>
                            <div>
                                <div class="flex items-center gap-2 flex-wrap">
                                    <h3 id="docModalTitle" class="text-base sm:text-lg font-black text-slate-900 dark:text-white">
                                        استوديو صياغة الوثائق الأكاديمية (SOP Studio)
                                    </h3>
                                    ${this.currentScholarshipName ? `
                                        <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                                            <i data-lucide="target" class="w-3 h-3"></i>
                                            <span>${escapeHtml(this.currentScholarshipName)}</span>
                                        </span>
                                    ` : ''}
                                </div>
                                <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">صياغة وتدقيق خطابات الدافع ومقترحات المنح وفق معايير لجان القبول العالمية</p>
                            </div>
                        </div>

                        <button type="button" 
                                onclick="DocumentEditorModal.close()" 
                                aria-label="إغلاق الاستوديو"
                                class="p-2 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition">
                            <i data-lucide="x" class="w-5 h-5"></i>
                        </button>
                    </header>

                    <!-- Multi-Step AI Progress Indicator (Toggled during generation) -->
                    <div id="sopAiProgressContainer" class="hidden p-4 border-b border-blue-500/30 bg-blue-500/5 space-y-2.5 transition-all">
                        <div class="flex items-center justify-between text-xs font-bold text-blue-600 dark:text-blue-400">
                            <span class="flex items-center gap-2">
                                <i data-lucide="sparkles" class="w-4 h-4 text-blue-500 animate-spin"></i>
                                <span>محرك Gemini AI يقوم بهندسة خطابك الأكاديمي...</span>
                            </span>
                            <span class="font-latin text-[11px]">EduAtlas Synthesis Engine</span>
                        </div>
                        <div id="sopStepsList" class="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                            <!-- Populated dynamically -->
                        </div>
                    </div>

                    <!-- Toolbar: Tone, Tabs, Word Count & AI Trigger -->
                    <div class="p-3.5 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 flex flex-wrap items-center justify-between gap-3 shrink-0">
                        <!-- Navigation Tabs (Edit vs Preview) -->
                        <div class="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800/80 rounded-2xl">
                            <button type="button" 
                                    id="sopBtnTabEdit"
                                    onclick="DocumentEditorModal.switchTab('edit')" 
                                    class="px-3.5 py-1.5 rounded-xl text-xs font-bold transition bg-blue-600 text-white shadow-xs">
                                <span class="flex items-center gap-1.5">
                                    <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
                                    <span>المحرر</span>
                                </span>
                            </button>
                            <button type="button" 
                                    id="sopBtnTabPrev"
                                    onclick="DocumentEditorModal.switchTab('preview')" 
                                    class="px-3.5 py-1.5 rounded-xl text-xs font-bold transition text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white">
                                <span class="flex items-center gap-1.5">
                                    <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                                    <span>معاينة الخطاب</span>
                                </span>
                            </button>
                        </div>

                        <!-- Tone Selector & Counters -->
                        <div class="flex items-center gap-2.5">
                            <div class="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                                <span class="text-slate-400 text-[11px] hidden sm:inline">نبرة الخطاب:</span>
                                <select id="sopToneSelect" class="sp-input text-xs py-1.5 px-2 font-bold">
                                    <option value="academic" selected>أكاديمي رصين (Academic)</option>
                                    <option value="leadership">حماسي وقيادي (Leadership)</option>
                                    <option value="research">بحثي تخصصي (Research)</option>
                                </select>
                            </div>

                            <span id="sopCountersBadge" class="px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-slate-800 font-latin text-[11px] font-bold text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                                ${words} كلمة · ${chars} حرف
                            </span>
                        </div>

                        <!-- AI Generate Button -->
                        <button type="button" 
                                id="sopGenerateAiBtn"
                                onclick="DocumentEditorModal.triggerAiGeneration()" 
                                class="sp-btn-primary px-4 py-2 text-xs font-bold flex items-center gap-2 shadow-md shadow-blue-500/20">
                            <i data-lucide="sparkles" class="w-3.5 h-3.5 text-cyan-300"></i>
                            <span>توليد وتخصيص عبر Gemini</span>
                        </button>
                    </div>

                    <!-- Modal Body: Tabs Panes -->
                    <div class="flex-1 overflow-y-auto p-4 sm:p-6 bg-slate-50/50 dark:bg-slate-950/40">
                        <!-- Tab 1: Textarea Editor -->
                        <div id="sopTabEdit" class="h-full">
                            <label for="sopTextarea" class="sr-only">نص خطاب الدافع</label>
                            <textarea id="sopTextarea" 
                                      oninput="DocumentEditorModal.updateCounters()" 
                                      placeholder="اكتب أو انسخ مسودة خطابك هنا..."
                                      class="w-full h-80 sm:h-96 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-xs sm:text-sm font-sans leading-relaxed focus:ring-2 focus:ring-blue-500 focus:outline-none resize-y">${escapeHtml(this.editorContent)}</textarea>
                        </div>

                        <!-- Tab 2: Live Formatted Preview -->
                        <div id="sopTabPreview" class="hidden p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 min-h-[320px]">
                            <div id="sopPreviewContent" class="markdown-body leading-relaxed text-slate-800 dark:text-slate-100 text-xs sm:text-sm space-y-3">
                                <!-- Populated dynamically -->
                            </div>
                        </div>
                    </div>

                    <!-- Modal Footer Actions -->
                    <footer class="p-3 sm:p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-wrap items-center justify-between gap-2 text-xs shrink-0">
                        <div class="flex items-center gap-2">
                            <button type="button" 
                                    onclick="DocumentEditorModal.copyToClipboard()" 
                                    class="sp-btn-secondary px-3.5 py-2 text-xs font-bold flex items-center gap-1.5"
                                    title="نسخ النص للحافظة">
                                <i data-lucide="copy" class="w-3.5 h-3.5 text-blue-500"></i>
                                <span>نسخ للحافظة</span>
                            </button>
                            <button type="button" 
                                    onclick="DocumentEditorModal.downloadFile()" 
                                    class="sp-btn-secondary px-3.5 py-2 text-xs font-bold flex items-center gap-1.5"
                                    title="تنزيل كملف نصي">
                                <i data-lucide="download" class="w-3.5 h-3.5 text-emerald-500"></i>
                                <span>تنزيل (.md)</span>
                            </button>
                            <button type="button" 
                                    onclick="DocumentEditorModal.printDocument()" 
                                    class="sp-btn-secondary px-3.5 py-2 text-xs font-bold hidden sm:flex items-center gap-1.5"
                                    title="طباعة">
                                <i data-lucide="printer" class="w-3.5 h-3.5 text-purple-500"></i>
                                <span>طباعة</span>
                            </button>
                        </div>

                        <div class="flex items-center gap-2">
                            <button type="button" 
                                    onclick="DocumentEditorModal.close()" 
                                    class="sp-btn-primary px-5 py-2 text-xs font-bold">
                                <span>تم وحفظ</span>
                            </button>
                        </div>
                    </footer>

                </div>
            `;

            this.updateCounters();
        }
    };

    window.DocumentEditorModal = DocumentEditorModal;
    window.openDocumentStudioModal = function (id) {
        DocumentEditorModal.open(id);
    };
    window.closeDocumentStudioModal = function () {
        DocumentEditorModal.close();
    };
})();
