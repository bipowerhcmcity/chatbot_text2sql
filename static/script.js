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

            if (response.table) {
                try {
                    const tableData = Array.isArray(response.table) ? response.table : (response.table.rows || []);
                    if (Array.isArray(tableData) && tableData.length > 0) this.showModalWithData(tableData);
                } catch (e) { console.error('Failed to render table:', e); }
            }

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

                const btn = document.createElement('button');
                btn.textContent = '▶ Run';
                btn.className = 'inline-run-sql-btn';
                wrapper.appendChild(btn);

                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const orig = btn.textContent;
                    btn.textContent = 'Running...';
                    btn.disabled = true;
                    try {
                        const res = await fetch('/api/run_sql', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ sql: codeText })
                        });
                        if (!res.ok) {
                            const err = await res.json().catch(() => ({}));
                            self.showModalError(err.detail || `HTTP ${res.status}`);
                        } else {
                            const data = await res.json();
                            self.showModalWithData(data.rows || []);
                        }
                    } catch (err) {
                        self.showModalError(String(err));
                    } finally {
                        btn.textContent = orig;
                        btn.disabled = false;
                    }
                });
            } catch (e) {
                console.error('Error attaching run button:', e);
            }
        });
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
