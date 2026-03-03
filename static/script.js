class LexaraAI {
    constructor() {
        this.conversationHistory = [];
        this.isTyping = false;
        this.currentChatId = null;
        
        this.initializeElements();
        this.setupEventListeners();
        this.setupMarkdown();
        this.setDynamicGreeting();
        this.loadChatHistoryFromStorage();
    }

    initializeElements() {
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.welcomeSection = document.getElementById('welcomeSection');
    this.quickActionCards = document.querySelectorAll('.quick-action-card');
    this.quickActionBtns = document.querySelectorAll('.quick-action-btn');
        this.themeToggle = document.getElementById('themeToggle');
        this.dynamicGreeting = document.getElementById('dynamicGreeting');
        this.shareChatBtn = document.getElementById('shareChatBtn');
        this.conversationHistoryContainer = document.getElementById('conversationHistory');
        this.sidebar = document.querySelector('.sidebar');
        this.setupMobileMenu();

    // Dataframe result elements (panel + table)
    this.dataframePanel = document.getElementById('dataframeResultPanel');
    this.dataframeTable = document.getElementById('dataframeTable');
    this.dataframeContainer = document.getElementById('dataframeContainer');
    this.dataframeTableWrapper = document.getElementById('dataframeTableWrapper');
    this.dataframeCloseBtn = document.getElementById('dataframeCloseBtn');
    this.dataframeDownloadBtn = document.getElementById('dataframeDownloadBtn');
    this.dataframeSearch = document.getElementById('dataframeSearch');
    this.dataframePageSize = document.getElementById('dataframePageSize');
    this.dataframeToggleBtn = document.getElementById('dataframeToggleBtn');
    this.dataframePrevBtn = document.getElementById('dataframePrevBtn');
    this.dataframeNextBtn = document.getElementById('dataframeNextBtn');
    this.dataframePageInfo = document.getElementById('dataframePageInfo');

    // Internal state for interactive table
    this.currentTableData = [];
    this.filteredTableData = [];
    this.sortColumn = null;
    this.sortDir = 'asc';
    this.page = 1;
    this.pageSize = parseInt(this.dataframePageSize ? this.dataframePageSize.value : 10, 10) || 10;
    this.dataframeCollapsed = false;
    this.searchQuery = '';
    }

    setupMobileMenu() {
        // Create mobile menu overlay
        this.mobileOverlay = document.createElement('div');
        this.mobileOverlay.className = 'sidebar-overlay';
        document.body.appendChild(this.mobileOverlay);

        // Mobile menu toggle functionality
        const chatHeaderBar = document.querySelector('.chat-header-bar');
        if (chatHeaderBar) {
            chatHeaderBar.addEventListener('click', (e) => {
                if (window.innerWidth <= 480 && e.target === chatHeaderBar) {
                    this.toggleMobileSidebar();
                }
            });
        }

        // Close sidebar when clicking overlay
        this.mobileOverlay.addEventListener('click', () => {
            this.closeMobileSidebar();
        });

        // Close sidebar when window is resized to larger screen
        window.addEventListener('resize', () => {
            if (window.innerWidth > 480) {
                this.closeMobileSidebar();
            }
        });
    }

    toggleMobileSidebar() {
        if (this.sidebar && this.mobileOverlay) {
            this.sidebar.classList.toggle('mobile-open');
            this.mobileOverlay.classList.toggle('active');
        }
    }

    closeMobileSidebar() {
        if (this.sidebar && this.mobileOverlay) {
            this.sidebar.classList.remove('mobile-open');
            this.mobileOverlay.classList.remove('active');
        }
    }

    setupEventListeners() {
        // Send button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Enter key to send message
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
            this.toggleSendButton();
        });

        // New chat button
        this.newChatBtn.addEventListener('click', () => this.startNewChat());


        // Quick action cards (legacy)
        this.quickActionCards.forEach(card => {
            card.addEventListener('click', () => {
                const prompt = card.getAttribute('data-prompt');
                this.handleQuickAction(prompt);
            });
        });

        // Quick action buttons (new)
        const quickActionPrompts = {
            'Summarize text': 'Summarize this text: ',
            'Get advice': 'I need advice about ',
            'Surprise me': 'Surprise me with something interesting',
            'Analyze data': 'Help me analyze this data: ',
            'Help me write': 'Help me write ',
            'More': 'Explain : '
        };
        this.quickActionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const key = btn.getAttribute('data-prompt');
                const prompt = quickActionPrompts[key] || '';
                if (prompt) {
                    this.handleQuickAction(prompt);
                }
            });
        });

        // Theme toggle
        this.themeToggle.addEventListener('click', () => this.toggleTheme());

        // Share chat button
        this.shareChatBtn.addEventListener('click', () => this.copyChatToClipboard());

        // Initial button state
        this.toggleSendButton();
        
        // Initialize theme
        this.initializeTheme();
        // Dataframe panel controls
        if (this.dataframeCloseBtn) {
            this.dataframeCloseBtn.addEventListener('click', () => this.hideDataframeResult());
        }
        if (this.dataframeDownloadBtn) {
            this.dataframeDownloadBtn.addEventListener('click', () => this.downloadDataframeCSV());
        }
        if (this.dataframeSearch) {
            this.dataframeSearch.addEventListener('input', (e) => {
                this.searchQuery = e.target.value || '';
                this.page = 1;
                this.renderDataframeTable();
            });
        }
        if (this.dataframePageSize) {
            this.dataframePageSize.addEventListener('change', (e) => {
                this.pageSize = parseInt(e.target.value, 10) || 10;
                this.page = 1;
                this.renderDataframeTable();
            });
        }
        if (this.dataframeToggleBtn) {
            this.dataframeToggleBtn.addEventListener('click', () => this.toggleCollapseDataframe());
        }
        if (this.dataframePrevBtn) {
            this.dataframePrevBtn.addEventListener('click', () => { if (this.page > 1) { this.page--; this.renderDataframeTable(); } });
        }
        if (this.dataframeNextBtn) {
            this.dataframeNextBtn.addEventListener('click', () => { this.page++; this.renderDataframeTable(); });
        }

        // SQL runner buttons (Run / Clear)
        this.sqlRunBtn = document.getElementById('sqlRunBtn');
        this.sqlClearBtn = document.getElementById('sqlClearBtn');
        this.dataframeModal = document.getElementById('dataframeModal');
        this.dataframeModalContent = document.getElementById('dataframeModalContent');
        this.modalDownloadBtn = document.getElementById('modalDownloadBtn');
        this.modalCloseBtn = document.getElementById('modalCloseBtn');


        if (this.modalCloseBtn) {
            this.modalCloseBtn.addEventListener('click', () => { if (this.dataframeModal) this.dataframeModal.style.display = 'none'; });
        }
        if (this.modalDownloadBtn) {
            this.modalDownloadBtn.addEventListener('click', () => { this.downloadModalCSV(); });
        }
    }

    /**
     * Show a dataframe-like result in the UI.
     * Accepts an array of objects (rows) or an empty array.
     */
    showDataframeResult(jsonArray) {
        if (!this.dataframePanel || !this.dataframeTable) return;

        // normalize input
        this.currentTableData = Array.isArray(jsonArray) ? jsonArray : [];
        this.searchQuery = '';
        if (this.dataframeSearch) this.dataframeSearch.value = '';
        this.sortColumn = null;
        this.sortDir = 'asc';
        this.page = 1;
        this.pageSize = parseInt(this.dataframePageSize ? this.dataframePageSize.value : 10, 10) || 10;

        // compute filtered data and render
        this.filteredTableData = this.currentTableData.slice();
        this.renderDataframeTable();

        // show panel
        // show panel but keep it collapsed by default (only header / toggle visible)
        this.dataframePanel.style.display = 'block';
        this.dataframeCollapsed = true;
        if (this.dataframeTableWrapper) this.dataframeTableWrapper.style.display = 'none';
        if (this.dataframeToggleBtn) this.dataframeToggleBtn.textContent = 'Show';
        if (this.dataframePanel.classList) this.dataframePanel.classList.add('collapsed');
        // hide all `.dataframe-controls` containers across the page (so only toggle remains visible)
        document.querySelectorAll('.dataframe-controls').forEach(el => {
            try { el.style.display = 'none'; } catch (e) {}
        });
        // hide footers as well
        document.querySelectorAll('.dataframe-footer').forEach(el => { try { el.style.display = 'none'; } catch (e) {} });
        setTimeout(() => {
            if (this.dataframePanel.scrollIntoView) this.dataframePanel.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }, 120);
    }

    hideDataframeResult() {
        if (!this.dataframePanel) return;
        this.dataframePanel.style.display = 'none';
    }

    renderDataframeTable() {
        // Apply search filter
        const q = (this.searchQuery || '').toString().toLowerCase().trim();
        if (q === '') {
            this.filteredTableData = this.currentTableData.slice();
        } else {
            this.filteredTableData = this.currentTableData.filter(row => {
                return Object.values(row).some(val => (val === null || val === undefined ? '' : String(val)).toLowerCase().includes(q));
            });
        }

        // Apply sorting
        if (this.sortColumn) {
            const col = this.sortColumn;
            const dir = this.sortDir === 'asc' ? 1 : -1;
            this.filteredTableData.sort((a, b) => {
                const va = a[col];
                const vb = b[col];
                if (va === vb) return 0;
                if (va === null || va === undefined) return -1 * dir;
                if (vb === null || vb === undefined) return 1 * dir;
                if (!isNaN(Number(va)) && !isNaN(Number(vb))) {
                    return (Number(va) - Number(vb)) * dir;
                }
                return String(va).localeCompare(String(vb)) * dir;
            });
        }

        // Pagination
        const totalRows = this.filteredTableData.length;
        const totalPages = Math.max(1, Math.ceil(totalRows / this.pageSize));
        if (this.page > totalPages) this.page = totalPages;
        const start = (this.page - 1) * this.pageSize;
        const end = start + this.pageSize;
        const pageSlice = this.filteredTableData.slice(start, end);

        // Build table
        this.dataframeTable.innerHTML = '';
        if (this.currentTableData.length === 0) {
            this.dataframeTable.innerHTML = '<tr><td>No rows returned</td></tr>';
            if (this.dataframePageInfo) this.dataframePageInfo.textContent = '0 / 0';
            return;
        }

        const cols = Object.keys(this.currentTableData[0]);
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        cols.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            th.style.textAlign = 'left';
            th.style.padding = '6px 8px';
            th.style.borderBottom = '1px solid rgba(0,0,0,0.08)';
            th.style.cursor = 'pointer';
            // sort indicator
            const indicator = document.createElement('span');
            indicator.style.marginLeft = '6px';
            if (this.sortColumn === col) indicator.textContent = this.sortDir === 'asc' ? '▲' : '▼';
            th.appendChild(indicator);
            th.addEventListener('click', () => this.sortByColumn(col));
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);

        const tbody = document.createElement('tbody');
        pageSlice.forEach(row => {
            const tr = document.createElement('tr');
            cols.forEach(col => {
                const td = document.createElement('td');
                const val = row[col] === null || row[col] === undefined ? '' : row[col];
                td.textContent = String(val);
                td.style.padding = '6px 8px';
                td.style.borderBottom = '1px solid rgba(0,0,0,0.04)';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        this.dataframeTable.appendChild(thead);
        this.dataframeTable.appendChild(tbody);

        // Update page info
        if (this.dataframePageInfo) this.dataframePageInfo.textContent = `${this.page} / ${totalPages}`;
        // Disable/Enable pagination buttons
        if (this.dataframePrevBtn) this.dataframePrevBtn.disabled = this.page <= 1;
        if (this.dataframeNextBtn) this.dataframeNextBtn.disabled = this.page >= totalPages;
    }

    // --- Modal helpers ---
    showModalWithData(rows) {
        if (!this.dataframeModal || !this.dataframeModalContent) return;
        // clear
        this.dataframeModalContent.innerHTML = '';

        if (!Array.isArray(rows) || rows.length === 0) {
            this.dataframeModalContent.innerHTML = '<p>No rows returned</p>';
        } else {
            const cols = Object.keys(rows[0]);
            const table = document.createElement('table');
            table.style.width = '100%';
            table.style.borderCollapse = 'collapse';
            const thead = document.createElement('thead');
            const hr = document.createElement('tr');
            cols.forEach(c => {
                const th = document.createElement('th');
                th.textContent = c;
                th.style.textAlign = 'left';
                th.style.padding = '6px 8px';
                th.style.borderBottom = '1px solid rgba(0,0,0,0.08)';
                hr.appendChild(th);
            });
            thead.appendChild(hr);
            const tbody = document.createElement('tbody');
            rows.forEach(r => {
                const tr = document.createElement('tr');
                cols.forEach(c => {
                    const td = document.createElement('td');
                    td.textContent = r[c] === null || r[c] === undefined ? '' : String(r[c]);
                    td.style.padding = '6px 8px';
                    td.style.borderBottom = '1px solid rgba(0,0,0,0.04)';
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
            table.appendChild(thead);
            table.appendChild(tbody);
            this.dataframeModalContent.appendChild(table);
            // save last modal rows for download
            this._lastModalRows = rows;
        }
        this.dataframeModal.style.display = 'flex';
    }

    showModalError(msg) {
        if (!this.dataframeModal || !this.dataframeModalContent) return;
        this.dataframeModalContent.innerHTML = `<div style="color:var(--text-primary); padding:12px;">Error: ${String(msg)}</div>`;
        this.dataframeModal.style.display = 'flex';
    }

    downloadModalCSV() {
        const rows = this._lastModalRows || [];
        if (!rows || rows.length === 0) return this.showTemporaryTooltip(this.modalDownloadBtn, 'No data');
        const cols = Object.keys(rows[0]);
        const lines = [];
        lines.push(cols.map(c => `"${String(c).replace(/"/g,'""')}"`).join(','));
        rows.forEach(row => {
            const line = cols.map(c => `"${String(row[c] === null || row[c] === undefined ? '' : row[c]).replace(/"/g,'""')}"`).join(',');
            lines.push(line);
        });
        const csvContent = lines.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', `sql_result_${new Date().toISOString().replace(/[:.]/g,'-')}.csv`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }

    sortByColumn(col) {
        if (this.sortColumn === col) {
            this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = col;
            this.sortDir = 'asc';
        }
        this.page = 1;
        this.renderDataframeTable();
    }

    toggleCollapseDataframe() {
        this.dataframeCollapsed = !this.dataframeCollapsed;
        if (this.dataframeTableWrapper) this.dataframeTableWrapper.style.display = this.dataframeCollapsed ? 'none' : 'block';
        if (this.dataframeToggleBtn) this.dataframeToggleBtn.textContent = this.dataframeCollapsed ? 'Show' : 'Hide';
        // toggle visibility of all `.dataframe-controls` containers
        document.querySelectorAll('.dataframe-controls').forEach(el => {
            try {
                el.style.display = this.dataframeCollapsed ? 'none' : 'flex';
            } catch (e) {}
        });
        // toggle footers
        document.querySelectorAll('.dataframe-footer').forEach(el => {
            try { el.style.display = this.dataframeCollapsed ? 'none' : ''; } catch (e) {}
        });
        if (this.dataframePanel && this.dataframePanel.classList) {
            if (this.dataframeCollapsed) {
                this.dataframePanel.classList.add('collapsed');
            } else {
                this.dataframePanel.classList.remove('collapsed');
            }
        }
    }

    // Convert currently shown (filtered) data to CSV and trigger download
    downloadDataframeCSV() {
        if (!this.currentTableData || this.currentTableData.length === 0) return;

        // Use filteredTableData if present, otherwise full data
        const rows = this.filteredTableData && this.filteredTableData.length > 0 ? this.filteredTableData : this.currentTableData;
        const cols = Object.keys(this.currentTableData[0]);
        const lines = [];
        lines.push(cols.map(c => `"${String(c).replace(/"/g,'""')}"`).join(','));
        rows.forEach(row => {
            const line = cols.map(c => `"${String(row[c] === null || row[c] === undefined ? '' : row[c]).replace(/"/g,'""')}"`).join(',');
            lines.push(line);
        });
        const csvContent = lines.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', `dataframe_result_${new Date().toISOString().replace(/[:.]/g,'-')}.csv`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }
    setupMarkdown() {
        // Configure marked for better rendering
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                highlight: function(code, lang) {
                    if (lang && hljs.getLanguage(lang)) {
                        try {
                            return hljs.highlight(code, { language: lang }).value;
                        } catch (__) {}
                    }
                    return hljs.highlightAuto(code).value;
                },
                breaks: true,
                gfm: true
            });
        }
    }

    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    toggleSendButton() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasText || this.isTyping;
    }

    handleQuickAction(prompt) {
        this.messageInput.value = prompt;
        this.autoResizeTextarea();
        this.toggleSendButton();
        this.messageInput.focus();
        this.saveCurrentChat();
    }

    hideWelcomeSection() {
        if (this.welcomeSection) {
            this.welcomeSection.style.display = 'none';
        }
    }

    showWelcomeSection() {
        if (this.welcomeSection) {
            this.welcomeSection.style.display = 'flex';
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        if (!this.currentChatId) {
            this.startNewChat(false); // Don't clear messages if it's the first message of a new session
        }

        // Hide welcome section on first message
        this.hideWelcomeSection();

        // Add user message to UI
        this.addUserMessage(message);
        
        // Clear input
        this.messageInput.value = '';
        this.autoResizeTextarea();
        this.toggleSendButton();

        // Show typing indicator
        this.showTypingIndicator();

        try {
            // Send message to backend
            const response = await this.sendToBackend(message);
            
            // Hide typing indicator
            this.hideTypingIndicator();
            
            // Add assistant response to UI
            this.addAssistantMessage(response.response);

            // If backend returned a table (array of row objects), render it
            if (response.table) {
                try {
                    // If response.table contains a dict with rows key, prefer that
                    const tableData = Array.isArray(response.table) ? response.table : (response.table.rows || []);
                    if (Array.isArray(tableData)) this.showDataframeResult(tableData);
                } catch (e) {
                    console.error('Failed to render dataframe result:', e);
                }
            }

            // Update conversation history
            this.conversationHistory = response.conversation_history;
            this.saveCurrentChat();
            
        } catch (error) {
            this.hideTypingIndicator();
            this.addErrorMessage(error.message);
        }
    }

    async sendToBackend(message) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                conversation_history: this.conversationHistory
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    addUserMessage(message) {
        const messageElement = this.createMessageElement('user', message);
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }

    addAssistantMessage(message) {
        const messageElement = this.createMessageElement('assistant', message);
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }

    addErrorMessage(error) {
        const messageElement = this.createMessageElement('assistant', 
            `I apologize, but I encountered an error: ${error}. Please try again.`);
        messageElement.classList.add('error-message');
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }

    createMessageElement(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        
        const avatar = document.createElement('div');
        if (role === 'user') {
            avatar.className = 'avatar user-avatar';
            avatar.innerHTML = `
                <img src="https://em-content.zobj.net/source/microsoft-teams/400/bust-in-silhouette_1f464.png" alt="User Avatar" width="18" height="18" style="border-radius: 50%; object-fit: cover;">
            `;
        } else {
            avatar.className = 'avatar lexara-avatar-small';
            avatar.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="2"/>
                    <path d="M12 2v20M2 12h20" stroke="currentColor" stroke-width="2"/>
                </svg>
            `;
        }
        
        avatarDiv.appendChild(avatar);

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        if (role === 'assistant') {
            // Parse markdown for assistant messages
            if (typeof marked !== 'undefined') {
                contentDiv.innerHTML = marked.parse(content);
                // Apply syntax highlighting to code blocks
                contentDiv.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightBlock(block);
                });
                // (run buttons are attached uniformly after markdown/plain rendering)
            } else {
                contentDiv.innerHTML = this.parseBasicMarkdown(content);
            }
            // Add Run button for SQL code blocks inside assistant messages (works for both marked and fallback)
            const self = this;
            contentDiv.querySelectorAll('pre code').forEach((codeEl) => {
                try {
                    const pre = codeEl.parentElement;
                    const codeText = codeEl.textContent || '';
                    const langClass = (codeEl.className || '').toLowerCase();
                    const looksLikeSQL = langClass.includes('language-sql') || codeText.trim().toLowerCase().startsWith('select');
                    if (!looksLikeSQL) return;

                    // wrap pre in a relative container so we can position the button
                    const wrapper = document.createElement('div');
                    wrapper.style.position = 'relative';
                    wrapper.style.display = 'block';
                    pre.parentNode.replaceChild(wrapper, pre);
                    wrapper.appendChild(pre);

                    const runBtn = document.createElement('button');
                    runBtn.textContent = 'Run';
                    runBtn.title = 'Run SQL';
                    runBtn.className = 'inline-run-sql-btn';
                    // style the button to appear top-right of the code block
                    runBtn.style.position = 'absolute';
                    runBtn.style.top = '8px';
                    runBtn.style.right = '8px';
                    runBtn.style.zIndex = '20';
                    runBtn.style.padding = '6px 8px';
                    runBtn.style.fontSize = '12px';
                    runBtn.style.borderRadius = '6px';
                    runBtn.style.border = '1px solid rgba(0,0,0,0.1)';
                    runBtn.style.background = 'rgba(0,0,0,0.6)';
                    runBtn.style.color = '#fff';

                    wrapper.appendChild(runBtn);

                    runBtn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        // show loading state
                        const originalText = runBtn.textContent;
                        runBtn.textContent = 'Running...';
                        runBtn.disabled = true;
                        try {
                            const sql = codeText;
                            const res = await fetch('/api/run_sql', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ sql })
                            });
                            if (!res.ok) {
                                const err = await res.json().catch(() => ({}));
                                const msg = err.detail || `HTTP ${res.status}`;
                                self.showModalError(msg);
                            } else {
                                const data = await res.json();
                                const rows = data.rows || [];
                                self.showModalWithData(rows);
                            }
                        } catch (err) {
                            console.error('Run SQL failed', err);
                            self.showModalError(String(err));
                        } finally {
                            runBtn.textContent = originalText;
                            runBtn.disabled = false;
                        }
                    });
                } catch (e) {
                    // ignore per-block errors
                    console.error('Error attaching run button to code block', e);
                }
            });
        } else {
            // Plain text for user messages
            const p = document.createElement('p');
            p.textContent = content;
            contentDiv.appendChild(p);
        }

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);

        return messageDiv;
    }

    parseBasicMarkdown(text) {
        // Basic markdown parsing fallback
        return text
            .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    showTypingIndicator() {
        this.isTyping = true;
        this.typingIndicator.style.display = 'block';
        this.toggleSendButton();
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.isTyping = false;
        this.typingIndicator.style.display = 'none';
        this.toggleSendButton();
    }

    scrollToBottom() {
        setTimeout(() => {
            const container = this.chatMessages.parentElement;
            container.scrollTop = container.scrollHeight;
        }, 100);
    }

    // Add smooth animations
    addRippleEffect(element, event) {
        const ripple = document.createElement('span');
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            transform: scale(0);
            animation: ripple 0.6s linear;
            pointer-events: none;
        `;
        
        element.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    // Theme Management Methods
    initializeTheme() {
        // Check for saved theme preference or default to 'light'
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.setTheme(savedTheme);
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        
        // Add a subtle animation class for smooth transition
        document.body.classList.add('theme-transitioning');
        setTimeout(() => {
            document.body.classList.remove('theme-transitioning');
        }, 300);
    }

    // Dynamic Greeting Based on Time
    setDynamicGreeting() {
        if (!this.dynamicGreeting) return;
        
        const now = new Date();
        const hour = now.getHours();
        let greeting = "Hello there!"; // fallback/default
        
        if (hour >= 5 && hour < 12) {
            greeting = "Good morning! 👋";
        } else if (hour >= 12 && hour < 17) {
            greeting = "Good afternoon! ☀️";
        } else if (hour >= 17 && hour < 22) {
            greeting = "Good evening! 🌆";
        } else if (hour >= 22 || hour < 5) {
            greeting = "Hey there, night owl! 🌙";
        }
        
        this.dynamicGreeting.textContent = greeting;
    }

    copyChatToClipboard() {
        if (this.conversationHistory.length === 0) {
            this.showTemporaryTooltip(this.shareChatBtn, 'Nothing to copy!');
            return;
        }

        let chatText = "Lexara AI Conversation\n";
        chatText += "========================\n\n";

        this.conversationHistory.forEach(item => {
            const prefix = item.role === 'user' ? 'You: ' : 'Lexara AI: ';
            chatText += prefix + item.content + '\n\n';
        });

        navigator.clipboard.writeText(chatText.trim()).then(() => {
            this.showTemporaryTooltip(this.shareChatBtn, 'Copied!');
        }).catch(err => {
            console.error('Failed to copy chat: ', err);
            this.showTemporaryTooltip(this.shareChatBtn, 'Failed to copy!');
        });
    }

    showTemporaryTooltip(element, text) {
        const originalTitle = element.getAttribute('title');
        element.setAttribute('title', text);

        const icon = element.querySelector('svg');
        if (!icon) return;
        
        const originalIconHTML = icon.innerHTML;
        // Checkmark icon
        icon.innerHTML = `<path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;

        element.style.borderColor = '#34d399'; // Green border for success
        element.style.color = '#34d399';

        setTimeout(() => {
            element.setAttribute('title', originalTitle);
            icon.innerHTML = originalIconHTML;
            element.style.borderColor = '';
            element.style.color = '';
        }, 2000);
    }

    // Local Storage Chat History Management
    saveCurrentChat() {
        if (!this.currentChatId || this.conversationHistory.length === 0) return;

        const allChats = this.getAllChatsFromStorage();
        const chatData = {
            id: this.currentChatId,
            timestamp: new Date().toISOString(),
            messages: this.conversationHistory
        };
        
        const existingChatIndex = allChats.findIndex(chat => chat.id === this.currentChatId);
        if (existingChatIndex > -1) {
            allChats[existingChatIndex] = chatData;
        } else {
            allChats.unshift(chatData);
        }

        localStorage.setItem('lexara-chats', JSON.stringify(allChats));
        this.renderChatHistoryList();
    }

    loadChatHistoryFromStorage() {
        this.renderChatHistoryList();
        const allChats = this.getAllChatsFromStorage();
        if (allChats.length > 0) {
            this.loadChat(allChats[0].id);
        } else {
            this.startNewChat(false);
        }
    }

    getAllChatsFromStorage() {
        try {
            const chats = localStorage.getItem('lexara-chats');
            return chats ? JSON.parse(chats) : [];
        } catch (e) {
            console.error("Error parsing chats from localStorage", e);
            return [];
        }
    }

    renderChatHistoryList() {
        if (!this.conversationHistoryContainer) return;

        const allChats = this.getAllChatsFromStorage();
        this.conversationHistoryContainer.innerHTML = '';

        if (allChats.length === 0) {
            this.conversationHistoryContainer.innerHTML = `
                <div class="history-placeholder">
                    <div class="chat-history-item">
                        <div class="chat-icon">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                        <span>No recent chats</span>
                    </div>
                </div>`;
            return;
        }

        const groupedChats = this.groupChatsByTime(allChats);

        for (const group in groupedChats) {
            const section = document.createElement('div');
            section.className = 'history-section';
            
            const title = document.createElement('h3');
            title.textContent = group;
            section.appendChild(title);

            groupedChats[group].forEach(chat => {
                const item = document.createElement('div');
                item.className = `chat-history-item ${chat.id === this.currentChatId ? 'active' : ''}`;
                item.dataset.chatId = chat.id;
                
                const icon = document.createElement('div');
                icon.className = 'chat-icon';
                icon.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
                
                const span = document.createElement('span');
                span.textContent = this.getChatTitle(chat.messages);

                item.appendChild(icon);
                item.appendChild(span);
                
                item.addEventListener('click', () => this.loadChat(chat.id));
                section.appendChild(item);
            });
            
            this.conversationHistoryContainer.appendChild(section);
        }
    }

    groupChatsByTime(chats) {
        const groups = {
            'Today': [],
            'Yesterday': [],
            'Previous 7 Days': [],
            'Previous 30 Days': [],
            'Older': []
        };

        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        const sevenDaysAgo = new Date(today);
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        const thirtyDaysAgo = new Date(today);
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

        chats.forEach(chat => {
            const chatDate = new Date(chat.timestamp);
            if (chatDate >= today) {
                groups['Today'].push(chat);
            } else if (chatDate >= yesterday) {
                groups['Yesterday'].push(chat);
            } else if (chatDate >= sevenDaysAgo) {
                groups['Previous 7 Days'].push(chat);
            } else if (chatDate >= thirtyDaysAgo) {
                groups['Previous 30 Days'].push(chat);
            } else {
                groups['Older'].push(chat);
            }
        });

        // Clean up empty groups
        for (const group in groups) {
            if (groups[group].length === 0) {
                delete groups[group];
            }
        }

        return groups;
    }

    getChatTitle(messages) {
        if (messages.length > 0 && messages[0].role === 'user') {
            return messages[0].content.substring(0, 30) + (messages[0].content.length > 30 ? '...' : '');
        }
        return 'New Chat';
    }

    loadChat(chatId) {
        const allChats = this.getAllChatsFromStorage();
        const chat = allChats.find(c => c.id === chatId);

        if (chat) {
            this.currentChatId = chatId;
            this.conversationHistory = chat.messages;
            this.chatMessages.innerHTML = '';
            
            if (this.conversationHistory.length > 0) {
                this.hideWelcomeSection();
                this.conversationHistory.forEach(item => {
                    const messageElement = this.createMessageElement(item.role, item.content);
                    this.chatMessages.appendChild(messageElement);
                });
                this.scrollToBottom();
            } else {
                if (this.welcomeSection) {
                    this.welcomeSection.style.display = 'flex';
                }
            }
            this.renderChatHistoryList();
            this.closeMobileSidebar(); // Close mobile sidebar when chat is loaded
        }
    }

    startNewChat(clearMessages = true) {
        this.currentChatId = `chat-${new Date().getTime()}`;
        this.conversationHistory = [];
        if (clearMessages) {
            this.chatMessages.innerHTML = '';
        }
        if (this.welcomeSection) {
            this.welcomeSection.style.display = 'flex';
        }
        this.messageInput.value = '';
        this.autoResizeTextarea();
        this.toggleSendButton();
        this.renderChatHistoryList();
        this.closeMobileSidebar(); // Close mobile sidebar when new chat is started
    }
}

// Add ripple animation CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    .quick-action-card, .new-chat-btn button, #sendButton {
        position: relative;
        overflow: hidden;
    }
`;
document.head.appendChild(style);

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Expose instance for interactive testing (e.g., showDataframeResult)
    window.lexaraAI = new LexaraAI();
});
