/* ================================================
   CADS Insight Bot — Script
   ================================================ */

class CADSInsightBot {
    constructor() {
        this.conversationHistory = [];
        this.isTyping = false;
        this.currentChatId = null;

        this.initElements();
        this.initEventListeners();
        this.initMarkdown();
        this.initTheme();
        this.setDynamicGreeting();

        // Clear saved history on fresh server load
        localStorage.removeItem('lexara-chats');
        this.startNewChat(false);
    }

    // ---- DOM References ----
    initElements() {
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.welcomeSection = document.getElementById('welcomeSection');
        this.themeToggle = document.getElementById('themeToggle');
        this.dynamicGreeting = document.getElementById('dynamicGreeting');
        this.shareChatBtn = document.getElementById('shareChatBtn');
        this.conversationHistoryContainer = document.getElementById('conversationHistory');

        // Sidebar / mobile
        this.sidebar = document.getElementById('sidebar');
        this.sidebarOverlay = document.getElementById('sidebarOverlay');
        this.mobileMenuBtn = document.getElementById('mobileMenuBtn');

        // Quick actions
        this.quickActionBtns = document.querySelectorAll('.quick-action-btn');

        // Modal
        this.dataframeModal = document.getElementById('dataframeModal');
        this.dataframeModalContent = document.getElementById('dataframeModalContent');
        this.modalDownloadBtn = document.getElementById('modalDownloadBtn');
        this.modalCloseBtn = document.getElementById('modalCloseBtn');
        this._lastModalRows = [];
    }

    // ---- Event Listeners ----
    initEventListeners() {
        // Send
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        this.messageInput.addEventListener('input', () => {
            this.autoResize();
            this.toggleSend();
        });

        // New chat
        this.newChatBtn.addEventListener('click', () => this.startNewChat());

        // Quick actions
        this.quickActionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const prompt = btn.getAttribute('data-prompt') || '';
                if (prompt) {
                    this.messageInput.value = prompt;
                    this.autoResize();
                    this.toggleSend();
                    this.messageInput.focus();
                }
            });
        });

        // Theme
        this.themeToggle.addEventListener('click', () => this.toggleTheme());

        // Share
        this.shareChatBtn.addEventListener('click', () => this.copyChatToClipboard());

        // Mobile sidebar
        if (this.mobileMenuBtn) {
            this.mobileMenuBtn.addEventListener('click', () => this.toggleMobileSidebar());
        }
        if (this.sidebarOverlay) {
            this.sidebarOverlay.addEventListener('click', () => this.closeMobileSidebar());
        }
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) this.closeMobileSidebar();
        });

        // Modal
        if (this.modalCloseBtn) {
            this.modalCloseBtn.addEventListener('click', () => {
                if (this.dataframeModal) this.dataframeModal.style.display = 'none';
            });
        }
        if (this.modalDownloadBtn) {
            this.modalDownloadBtn.addEventListener('click', () => this.downloadModalCSV());
        }

        // Initial state
        this.toggleSend();
    }

    // ---- Markdown ----
    initMarkdown() {
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                highlight: (code, lang) => {
                    if (lang && hljs.getLanguage(lang)) {
                        try { return hljs.highlight(code, { language: lang }).value; } catch (_) {}
                    }
                    return hljs.highlightAuto(code).value;
                },
                breaks: true,
                gfm: true
            });
        }
    }

    // ---- Theme ----
    initTheme() {
        const saved = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', saved);
    }
    toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
    }

    // ---- Mobile Sidebar ----
    toggleMobileSidebar() {
        this.sidebar.classList.toggle('mobile-open');
        this.sidebarOverlay.classList.toggle('active');
    }
    closeMobileSidebar() {
        this.sidebar.classList.remove('mobile-open');
        this.sidebarOverlay.classList.remove('active');
    }

    // ---- Greeting ----
    setDynamicGreeting() {
        if (!this.dynamicGreeting) return;
        const h = new Date().getHours();
        let g = 'Hello there!';
        if (h >= 5 && h < 12) g = 'Good morning! 👋';
        else if (h >= 12 && h < 17) g = 'Good afternoon! ☀️';
        else if (h >= 17 && h < 22) g = 'Good evening! 🌆';
        else g = 'Hey there, night owl! 🌙';
        this.dynamicGreeting.textContent = g;
    }

    // ---- Input Helpers ----
    autoResize() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }
    toggleSend() {
        this.sendButton.disabled = !this.messageInput.value.trim() || this.isTyping;
    }

    hideWelcome() {
        if (this.welcomeSection) this.welcomeSection.style.display = 'none';
    }
    showWelcome() {
        if (this.welcomeSection) this.welcomeSection.style.display = 'flex';
    }

    // ---- Send Message ----
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        if (!this.currentChatId) this.startNewChat(false);
        this.hideWelcome();
        this.addUserMessage(message);

        this.messageInput.value = '';
        this.autoResize();
        this.toggleSend();
        this.showTyping();

        try {
            const response = await this.sendToBackend(message);
            this.hideTyping();
            this.addAssistantMessage(response.response);
            this.saveCurrentChat();
        } catch (error) {
            this.hideTyping();
            this.addErrorMessage(error.message);
        }
    }

    async sendToBackend(message) {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                conversation_history: this.conversationHistory
            })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP error ${res.status}`);
        }
        return await res.json();
    }

    // ---- Messages ----
    addUserMessage(message) {
        this.conversationHistory.push({ role: 'user', content: message });
        this.chatMessages.appendChild(this.createMessage('user', message));
        this.scrollToBottom();
    }
    addAssistantMessage(message) {
        this.conversationHistory.push({ role: 'assistant', content: message });
        this.chatMessages.appendChild(this.createMessage('assistant', message));
        this.scrollToBottom();
    }
    addErrorMessage(error) {
        const el = this.createMessage('assistant', `Sorry, I encountered an error: ${error}. Please try again.`);
        el.classList.add('error-message');
        this.chatMessages.appendChild(el);
        this.scrollToBottom();
    }

    createMessage(role, content) {
        const msg = document.createElement('div');
        msg.className = `message ${role}-message`;

        // Avatar
        const avatarWrap = document.createElement('div');
        avatarWrap.className = 'msg-avatar';
        const avatar = document.createElement('div');
        if (role === 'user') {
            avatar.className = 'avatar-user';
            avatar.textContent = 'U';
        } else {
            avatar.className = 'avatar-bot';
            avatar.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7l10 5 10-5-10-5z" fill="currentColor" opacity="0.3"/><path d="M2 17l10 5 10-5" stroke="currentColor" stroke-width="2"/><path d="M2 12l10 5 10-5" stroke="currentColor" stroke-width="2"/></svg>';
        }
        avatarWrap.appendChild(avatar);

        // Body
        const body = document.createElement('div');
        body.className = 'msg-body';

        if (role === 'assistant') {
            if (typeof marked !== 'undefined') {
                body.innerHTML = marked.parse(content);
                body.querySelectorAll('pre code').forEach(block => hljs.highlightBlock(block));
            } else {
                body.innerHTML = this.parseBasicMarkdown(content);
            }
            this.attachRunButtons(body);
        } else {
            const span = document.createElement('span');
            span.textContent = content;
            body.appendChild(span);
        }

        msg.appendChild(avatarWrap);
        msg.appendChild(body);
        return msg;
    }

    attachRunButtons(bodyEl) {
        const self = this;
        bodyEl.querySelectorAll('pre code').forEach(codeEl => {
            try {
                const pre = codeEl.parentElement;
                const codeText = codeEl.textContent || '';
                const langClass = (codeEl.className || '').toLowerCase();
                const isSQL = langClass.includes('language-sql') || codeText.trim().toLowerCase().startsWith('select');
                if (!isSQL) return;

                const wrapper = document.createElement('div');
                wrapper.className = 'code-block-wrapper';
                pre.parentNode.replaceChild(wrapper, pre);
                wrapper.appendChild(pre);

                // Auto-run SQL and show inline results immediately
                self._autoRunSQL(codeText, wrapper);
            } catch (e) {
                console.error('Error auto-running SQL:', e);
            }
        });
    }

    async _autoRunSQL(sql, wrapperEl) {
        // Insert a loading placeholder right after the code block
        const placeholder = document.createElement('div');
        placeholder.className = 'inline-result-loading';
        placeholder.innerHTML = `
            <div class="inline-result-spinner"></div>
            <span>Fetching results…</span>
        `;
        wrapperEl.appendChild(placeholder);
        this.scrollToBottom();

        try {
            const res = await fetch('/api/run_sql', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sql })
            });
            placeholder.remove();

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                this._renderInlineError(wrapperEl, err.detail || `HTTP ${res.status}`);
            } else {
                const data = await res.json();
                this._renderInlineTable(wrapperEl, data.rows || []);
            }
        } catch (err) {
            placeholder.remove();
            this._renderInlineError(wrapperEl, String(err));
        }
        this.scrollToBottom();
    }

    _renderInlineError(wrapperEl, msg) {
        const el = document.createElement('div');
        el.className = 'inline-result-error';
        el.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                <path d="M12 8v4M12 16h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span>${String(msg)}</span>
        `;
        wrapperEl.appendChild(el);
    }

    _renderInlineTable(wrapperEl, rows) {
        const container = document.createElement('div');
        container.className = 'inline-result-container';

        if (!Array.isArray(rows) || rows.length === 0) {
            container.innerHTML = `
                <div class="inline-result-empty">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                        <rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" stroke-width="1.5"/>
                        <path d="M3 9h18M9 21V9" stroke="currentColor" stroke-width="1.5"/>
                    </svg>
                    <span>Query returned 0 rows</span>
                </div>`;
            wrapperEl.appendChild(container);
            return;
        }

        const cols = Object.keys(rows[0]);
        let filteredRows = [...rows];
        let sortCol = null;
        let sortAsc = true;
        let searchQuery = '';
        let currentPage = 1;
        const pageSize = 10;

        // ── Header bar ──────────────────────────────────────────
        const headerBar = document.createElement('div');
        headerBar.className = 'irt-header';

        const metaInfo = document.createElement('div');
        metaInfo.className = 'irt-meta';

        const searchBox = document.createElement('div');
        searchBox.className = 'irt-search';
        searchBox.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <circle cx="11" cy="11" r="8" stroke="currentColor" stroke-width="2"/>
                <path d="M21 21l-4.35-4.35" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <input type="text" placeholder="Search results…" class="irt-search-input"/>
        `;

        const actions = document.createElement('div');
        actions.className = 'irt-actions';
        const csvBtn = document.createElement('button');
        csvBtn.className = 'irt-btn';
        csvBtn.innerHTML = `
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                <path d="M12 3v12M8 11l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M20 21H4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            Download CSV
        `;
        actions.appendChild(csvBtn);

        headerBar.appendChild(metaInfo);
        headerBar.appendChild(searchBox);
        headerBar.appendChild(actions);

        // ── Table wrapper ────────────────────────────────────────
        const tableWrap = document.createElement('div');
        tableWrap.className = 'irt-table-wrap';

        const table = document.createElement('table');
        table.className = 'irt-table';

        const thead = document.createElement('thead');
        const theadRow = document.createElement('tr');
        cols.forEach(col => {
            const th = document.createElement('th');
            th.innerHTML = `<span class="irt-th-text">${col}</span><span class="irt-sort-icon">↕</span>`;
            th.dataset.col = col;
            th.addEventListener('click', () => {
                if (sortCol === col) sortAsc = !sortAsc;
                else { sortCol = col; sortAsc = true; }
                thead.querySelectorAll('th').forEach(t => t.classList.remove('sorted-asc', 'sorted-desc'));
                th.classList.add(sortAsc ? 'sorted-asc' : 'sorted-desc');
                currentPage = 1;
                render();
            });
            theadRow.appendChild(th);
        });
        thead.appendChild(theadRow);

        const tbody = document.createElement('tbody');
        table.appendChild(thead);
        table.appendChild(tbody);
        tableWrap.appendChild(table);

        // ── Pagination bar ───────────────────────────────────────
        const pagination = document.createElement('div');
        pagination.className = 'irt-pagination';

        // ── Assemble ─────────────────────────────────────────────
        container.appendChild(headerBar);
        container.appendChild(tableWrap);
        container.appendChild(pagination);
        wrapperEl.appendChild(container);

        // ── Render function ──────────────────────────────────────
        const render = () => {
            // Filter
            filteredRows = rows.filter(r =>
                !searchQuery ||
                cols.some(c => String(r[c] == null ? '' : r[c]).toLowerCase().includes(searchQuery))
            );
            // Sort
            if (sortCol) {
                filteredRows.sort((a, b) => {
                    const av = a[sortCol], bv = b[sortCol];
                    if (av == null && bv == null) return 0;
                    if (av == null) return 1;
                    if (bv == null) return -1;
                    const isNum = !isNaN(av) && !isNaN(bv);
                    if (isNum) return sortAsc ? av - bv : bv - av;
                    return sortAsc ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
                });
            }
            // Paginate
            const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
            if (currentPage > totalPages) currentPage = totalPages;
            const start = (currentPage - 1) * pageSize;
            const pageRows = filteredRows.slice(start, start + pageSize);

            // Update meta
            metaInfo.innerHTML = `
                <span class="irt-count">
                    <strong>${filteredRows.length.toLocaleString()}</strong> row${filteredRows.length !== 1 ? 's' : ''}
                    ${filteredRows.length !== rows.length ? `<span class="irt-filtered">(filtered from ${rows.length.toLocaleString()})</span>` : ''}
                </span>
                <span class="irt-cols">${cols.length} col${cols.length !== 1 ? 's' : ''}</span>
            `;

            // Build rows
            tbody.innerHTML = '';
            pageRows.forEach((r, ri) => {
                const tr = document.createElement('tr');
                tr.className = ri % 2 === 0 ? 'irt-row-even' : 'irt-row-odd';
                cols.forEach(c => {
                    const td = document.createElement('td');
                    const val = r[c];
                    if (val === null || val === undefined) {
                        td.innerHTML = '<span class="irt-null">NULL</span>';
                    } else {
                        const str = String(val);
                        if (searchQuery && str.toLowerCase().includes(searchQuery)) {
                            td.innerHTML = str.replace(
                                new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
                                '<mark class="irt-highlight">$1</mark>'
                            );
                        } else {
                            td.textContent = str;
                        }
                    }
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });

            // Pagination controls
            pagination.innerHTML = '';
            if (totalPages > 1) {
                const info = document.createElement('span');
                info.className = 'irt-page-info';
                info.textContent = `Page ${currentPage} / ${totalPages}`;

                const prevBtn = document.createElement('button');
                prevBtn.className = 'irt-page-btn';
                prevBtn.textContent = '‹ Prev';
                prevBtn.disabled = currentPage === 1;
                prevBtn.addEventListener('click', () => { currentPage--; render(); });

                const nextBtn = document.createElement('button');
                nextBtn.className = 'irt-page-btn';
                nextBtn.textContent = 'Next ›';
                nextBtn.disabled = currentPage === totalPages;
                nextBtn.addEventListener('click', () => { currentPage++; render(); });

                pagination.appendChild(prevBtn);
                pagination.appendChild(info);
                pagination.appendChild(nextBtn);
            }
        };

        // ── Search handler ───────────────────────────────────────
        const searchInput = searchBox.querySelector('.irt-search-input');
        searchInput.addEventListener('input', () => {
            searchQuery = searchInput.value.trim().toLowerCase();
            currentPage = 1;
            render();
        });

        // ── CSV download ─────────────────────────────────────────
        csvBtn.addEventListener('click', () => {
            const data = filteredRows.length ? filteredRows : rows;
            const lines = [cols.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')];
            data.forEach(r => {
                lines.push(cols.map(c => `"${String(r[c] == null ? '' : r[c]).replace(/"/g, '""')}"`).join(','));
            });
            const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `result_${new Date().toISOString().slice(0,19).replace(/[T:]/g,'-')}.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        });

        render();
    }

    parseBasicMarkdown(text) {
        return text
            .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    // ---- Typing ----
    showTyping() {
        this.isTyping = true;
        this.typingIndicator.style.display = 'block';
        this.toggleSend();
        this.scrollToBottom();
    }
    hideTyping() {
        this.isTyping = false;
        this.typingIndicator.style.display = 'none';
        this.toggleSend();
    }

    scrollToBottom() {
        requestAnimationFrame(() => {
            const container = this.chatMessages.parentElement;
            container.scrollTop = container.scrollHeight;
        });
    }

    // ---- Modal ----
    showModalWithData(rows) {
        if (!this.dataframeModal || !this.dataframeModalContent) return;
        this.dataframeModalContent.innerHTML = '';
        this._lastModalRows = rows;

        if (!Array.isArray(rows) || rows.length === 0) {
            this.dataframeModalContent.innerHTML = '<p style="color:var(--text-secondary);padding:12px;">No rows returned</p>';
        } else {
            const cols = Object.keys(rows[0]);
            const table = document.createElement('table');
            const thead = document.createElement('thead');
            const hr = document.createElement('tr');
            cols.forEach(c => {
                const th = document.createElement('th');
                th.textContent = c;
                hr.appendChild(th);
            });
            thead.appendChild(hr);
            const tbody = document.createElement('tbody');
            rows.forEach(r => {
                const tr = document.createElement('tr');
                cols.forEach(c => {
                    const td = document.createElement('td');
                    td.textContent = r[c] === null || r[c] === undefined ? '' : String(r[c]);
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
            table.appendChild(thead);
            table.appendChild(tbody);
            this.dataframeModalContent.appendChild(table);
        }
        this.dataframeModal.style.display = 'flex';
    }

    showModalError(msg) {
        if (!this.dataframeModal || !this.dataframeModalContent) return;
        this.dataframeModalContent.innerHTML = `<div style="color:#ef4444;padding:16px;font-size:14px;">Error: ${String(msg)}</div>`;
        this.dataframeModal.style.display = 'flex';
    }

    downloadModalCSV() {
        const rows = this._lastModalRows || [];
        if (!rows.length) return;
        const cols = Object.keys(rows[0]);
        const lines = [cols.map(c => `"${String(c).replace(/"/g,'""')}"`).join(',')];
        rows.forEach(row => {
            lines.push(cols.map(c => `"${String(row[c] == null ? '' : row[c]).replace(/"/g,'""')}"`).join(','));
        });
        const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `query_result_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }

    // ---- Copy Chat ----
    copyChatToClipboard() {
        if (!this.conversationHistory || this.conversationHistory.length === 0) {
            this.showTooltip(this.shareChatBtn, 'Nothing to copy!');
            return;
        }
        let text = 'CADS Insight Bot Conversation\n============================\n\n';
        this.conversationHistory.forEach(item => {
            const prefix = item.role === 'user' ? 'You: ' : 'Bot: ';
            text += prefix + item.content + '\n\n';
        });
        navigator.clipboard.writeText(text.trim()).then(() => {
            this.showTooltip(this.shareChatBtn, 'Copied!');
        }).catch(() => {
            this.showTooltip(this.shareChatBtn, 'Failed!');
        });
    }

    showTooltip(el, text) {
        const orig = el.getAttribute('title');
        el.setAttribute('title', text);
        el.style.borderColor = '#34d399';
        el.style.color = '#34d399';
        setTimeout(() => {
            el.setAttribute('title', orig || '');
            el.style.borderColor = '';
            el.style.color = '';
        }, 2000);
    }

    // ---- Chat History (localStorage) ----
    saveCurrentChat() {
        if (!this.currentChatId || this.conversationHistory.length === 0) return;
        const allChats = this.getAllChats();
        const chatData = {
            id: this.currentChatId,
            timestamp: new Date().toISOString(),
            messages: this.conversationHistory
        };
        const idx = allChats.findIndex(c => c.id === this.currentChatId);
        if (idx > -1) allChats[idx] = chatData;
        else allChats.unshift(chatData);
        localStorage.setItem('lexara-chats', JSON.stringify(allChats));
        this.renderChatHistory();
    }

    getAllChats() {
        try {
            return JSON.parse(localStorage.getItem('lexara-chats') || '[]');
        } catch { return []; }
    }

    renderChatHistory() {
        if (!this.conversationHistoryContainer) return;
        const allChats = this.getAllChats();
        this.conversationHistoryContainer.innerHTML = '';
        if (allChats.length === 0) return;

        const groups = this.groupByTime(allChats);
        for (const [label, chats] of Object.entries(groups)) {
            const section = document.createElement('div');
            section.className = 'history-section';
            const h3 = document.createElement('h3');
            h3.textContent = label;
            section.appendChild(h3);

            chats.forEach(chat => {
                const item = document.createElement('div');
                item.className = `chat-history-item${chat.id === this.currentChatId ? ' active' : ''}`;
                item.innerHTML = `
                    <div class="chat-icon">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <span>${this.getChatTitle(chat.messages)}</span>
                `;
                item.addEventListener('click', () => this.loadChat(chat.id));
                section.appendChild(item);
            });
            this.conversationHistoryContainer.appendChild(section);
        }
    }

    groupByTime(chats) {
        const groups = {};
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
        const week = new Date(today); week.setDate(today.getDate() - 7);

        chats.forEach(chat => {
            const d = new Date(chat.timestamp);
            let label;
            if (d >= today) label = 'Today';
            else if (d >= yesterday) label = 'Yesterday';
            else if (d >= week) label = 'Previous 7 Days';
            else label = 'Older';
            if (!groups[label]) groups[label] = [];
            groups[label].push(chat);
        });
        return groups;
    }

    getChatTitle(messages) {
        if (messages.length > 0 && messages[0].role === 'user') {
            const t = messages[0].content;
            return t.length > 35 ? t.substring(0, 35) + '...' : t;
        }
        return 'New Chat';
    }

    loadChat(chatId) {
        const chat = this.getAllChats().find(c => c.id === chatId);
        if (!chat) return;
        this.currentChatId = chatId;
        this.conversationHistory = chat.messages;
        this.chatMessages.innerHTML = '';
        if (this.conversationHistory.length > 0) {
            this.hideWelcome();
            this.conversationHistory.forEach(item => {
                this.chatMessages.appendChild(this.createMessage(item.role, item.content));
            });
            this.scrollToBottom();
        } else {
            this.showWelcome();
        }
        this.renderChatHistory();
        this.closeMobileSidebar();
    }

    startNewChat(clear = true) {
        this.currentChatId = `chat-${Date.now()}`;
        this.conversationHistory = [];
        if (clear) this.chatMessages.innerHTML = '';
        this.showWelcome();
        this.messageInput.value = '';
        this.autoResize();
        this.toggleSend();
        this.renderChatHistory();
        this.closeMobileSidebar();
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.cadsBot = new CADSInsightBot();
});
