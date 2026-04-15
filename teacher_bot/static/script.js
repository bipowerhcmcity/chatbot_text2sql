// ─── Teacher Bot Frontend Script ────────────────────────────

let uploadedQuestionsFile = null;
let currentJobId = null;
let currentResults = [];
let pollInterval = null;

// ─── Initialization ─────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    checkChatbot();
});

// ─── Chatbot Health Check ───────────────────────────────────

async function checkChatbot() {
    const url = document.getElementById('chatbotUrl').value;
    const statusEl = document.getElementById('chatbotStatus');
    const dot = statusEl.querySelector('.status-dot');
    const text = statusEl.querySelector('.status-text');

    dot.className = 'status-dot checking';
    text.textContent = 'Checking...';

    try {
        const response = await fetch('/api/check-chatbot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chatbot_api_url: url }),
        });
        const data = await response.json();

        if (data.is_healthy) {
            dot.className = 'status-dot online';
            text.textContent = 'Chatbot: Connected';
        } else {
            dot.className = 'status-dot offline';
            text.textContent = 'Chatbot: Offline';
        }
    } catch (err) {
        dot.className = 'status-dot offline';
        text.textContent = 'Chatbot: Error';
        console.error('Health check error:', err);
    }
}

// ─── File Upload ────────────────────────────────────────────

async function uploadQuestions() {
    const fileInput = document.getElementById('questionFile');
    const infoEl = document.getElementById('questionFileInfo');

    if (!fileInput.files.length) return;

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload-questions', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Upload failed');
        }

        const data = await response.json();
        uploadedQuestionsFile = data.file_path;

        infoEl.style.display = 'block';
        infoEl.innerHTML = `
            ✅ <strong>${data.filename}</strong><br>
            ${data.total_questions} questions loaded<br>
            ${Object.entries(data.validation.difficulty_distribution || {})
                .map(([k, v]) => `${k}: ${v}`)
                .join(' | ')}
        `;

        // Enable start button
        document.getElementById('startEvalBtn').disabled = false;

    } catch (err) {
        infoEl.style.display = 'block';
        infoEl.innerHTML = `❌ Error: ${err.message}`;
        infoEl.style.background = 'rgba(239, 68, 68, 0.1)';
        infoEl.style.color = '#ef4444';
    }
}

// ─── Start Batch Evaluation ─────────────────────────────────

async function startEvaluation() {
    if (!uploadedQuestionsFile) {
        alert('Please upload a Question List CSV first');
        return;
    }

    const btn = document.getElementById('startEvalBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Starting...';

    // Hide empty state, show progress
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('progressSection').style.display = 'block';

    // Reset previous results
    hideSections(['summaryCards', 'downloadSection', 'levelPerformance', 'errorDistribution', 'resultsTableSection']);

    const formData = new FormData();
    formData.append('questions_file', uploadedQuestionsFile);
    formData.append('chatbot_api_url', document.getElementById('chatbotUrl').value);
    formData.append('execute_and_compare', document.getElementById('executeCompare').checked);
    formData.append('use_llm_scoring', document.getElementById('useLlmScoring').checked);
    formData.append('use_llm_error_analysis', document.getElementById('useLlmErrors').checked);
    formData.append('generate_pdf', document.getElementById('generatePdf').checked);

    try {
        const response = await fetch('/api/evaluate-batch', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to start evaluation');
        }

        const data = await response.json();
        currentJobId = data.job_id;

        // Start polling for progress
        startPolling(currentJobId);

    } catch (err) {
        alert(`Error: ${err.message}`);
        btn.disabled = false;
        btn.textContent = '🚀 Start Evaluation';
    }
}

// ─── Poll Job Status ────────────────────────────────────────

function startPolling(jobId) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/job/${jobId}`);
            const data = await response.json();

            updateProgress(data);

            if (data.status === 'completed') {
                clearInterval(pollInterval);
                pollInterval = null;
                displayResults(data);
            } else if (data.status === 'failed') {
                clearInterval(pollInterval);
                pollInterval = null;
                document.getElementById('progressLabel').textContent = `❌ Failed: ${data.error || 'Unknown error'}`;
                document.getElementById('startEvalBtn').disabled = false;
                document.getElementById('startEvalBtn').textContent = '🚀 Start Evaluation';
            }
        } catch (err) {
            console.error('Polling error:', err);
        }
    }, 2000);
}

function updateProgress(data) {
    const progress = data.progress || {};
    const pct = progress.percentage || 0;
    const current = progress.current || 0;
    const total = progress.total || 0;

    document.getElementById('progressBar').style.width = `${pct}%`;
    document.getElementById('progressPercent').textContent = `${pct}%`;

    const statusMap = {
        'pending': '⏳ Pending...',
        'running': `🔄 Evaluating question ${current}/${total}`,
        'scoring': '📊 Scoring results...',
        'analyzing_errors': '🔍 Analyzing errors...',
        'generating_reports': '📝 Generating reports...',
    };

    document.getElementById('progressLabel').textContent = statusMap[data.status] || data.status;
    document.getElementById('progressDetail').textContent = progress.current_question || '';
}

// ─── Display Results ────────────────────────────────────────

function displayResults(data) {
    currentResults = data.results || [];
    const summary = data.summary || {};
    const errorDist = data.error_distribution || {};

    // Update progress bar to complete
    document.getElementById('progressBar').style.width = '100%';
    document.getElementById('progressPercent').textContent = '100%';
    document.getElementById('progressLabel').textContent = '✅ Evaluation Complete!';
    document.getElementById('progressDetail').textContent = '';

    // Re-enable start button
    document.getElementById('startEvalBtn').disabled = false;
    document.getElementById('startEvalBtn').textContent = '🚀 Start Evaluation';

    // Show summary cards
    document.getElementById('summaryCards').style.display = 'grid';
    document.getElementById('totalQuestions').textContent = summary.total || 0;
    document.getElementById('passCount').textContent = summary.correct || 0;
    document.getElementById('failCount').textContent = summary.incorrect || 0;
    document.getElementById('passRate').textContent = `${summary.pass_rate || 0}%`;
    document.getElementById('avgTime').textContent = `${summary.avg_response_time || 0}s`;

    // Show download section
    document.getElementById('downloadSection').style.display = 'block';

    // Level performance
    displayLevelPerformance(summary.level_stats || {});

    // Error distribution
    displayErrorDistribution(errorDist);

    // Results table
    displayResultsTable(currentResults);
}

function displayLevelPerformance(levelStats) {
    const container = document.getElementById('levelBars');
    container.innerHTML = '';

    const levels = [
        { key: 'Dễ', class: 'easy', label: '🟢 Dễ' },
        { key: 'Trung bình', class: 'medium', label: '🟡 Trung bình' },
        { key: 'Khó', class: 'hard', label: '🔴 Khó' },
    ];

    for (const level of levels) {
        const stats = levelStats[level.key];
        if (!stats) continue;

        const pct = stats.total > 0 ? Math.round(stats.correct / stats.total * 100) : 0;

        const item = document.createElement('div');
        item.className = 'level-bar-item';
        item.innerHTML = `
            <div class="level-bar-label">${level.label}</div>
            <div class="level-bar-track">
                <div class="level-bar-fill ${level.class}" style="width: ${pct}%">${pct}%</div>
            </div>
            <div class="level-bar-stats">${stats.correct}/${stats.total}</div>
        `;
        container.appendChild(item);
    }

    document.getElementById('levelPerformance').style.display = 'block';
}

function displayErrorDistribution(errorDist) {
    const container = document.getElementById('errorGrid');
    container.innerHTML = '';

    const groups = errorDist.by_group || {};
    const errorGroupNames = {
        'G1': 'Question Understanding',
        'G2': 'Business Rule Mapping',
        'G3': 'Schema Mapping',
        'G4': 'Calculation Logic',
    };

    let hasErrors = false;
    for (const [group, count] of Object.entries(groups)) {
        if (group === 'None' || count === 0) continue;
        hasErrors = true;

        const card = document.createElement('div');
        card.className = 'error-card';
        card.innerHTML = `
            <div class="error-card-title">${group}</div>
            <div class="error-card-count">${count}</div>
            <div class="error-card-label">${errorGroupNames[group] || group}</div>
        `;
        container.appendChild(card);
    }

    // Sub-labels
    const labels = errorDist.by_label || {};
    for (const [label, count] of Object.entries(labels)) {
        if (count === 0) continue;
        hasErrors = true;

        const card = document.createElement('div');
        card.className = 'error-card';
        card.style.borderLeftColor = 'var(--warning)';
        card.innerHTML = `
            <div class="error-card-title">${label}</div>
            <div class="error-card-count" style="color: var(--warning)">${count}</div>
            <div class="error-card-label">Sub-label</div>
        `;
        container.appendChild(card);
    }

    if (hasErrors) {
        document.getElementById('errorDistribution').style.display = 'block';
    }
}

function displayResultsTable(results) {
    const tbody = document.getElementById('resultsTableBody');
    tbody.innerHTML = '';

    results.forEach((r, idx) => {
        const tr = document.createElement('tr');
        tr.dataset.level = r.level || '';
        tr.dataset.result = r.is_correct === true ? 'pass' : r.is_correct === false ? 'fail' : 'unknown';

        const levelBadge = getLevelBadge(r.level);
        const resultBadge = getResultBadge(r.is_correct);
        const score = r.score || {};
        const ea = r.error_analysis || {};
        const errorGroup = ea.error_group && ea.error_group !== 'None' ? ea.error_group : '-';

        tr.innerHTML = `
            <td>${idx + 1}</td>
            <td class="question-cell" title="${escapeHtml(r.question)}">${escapeHtml(r.question)}</td>
            <td>${levelBadge}</td>
            <td>${resultBadge}</td>
            <td>${score.total_score || '-'}</td>
            <td>${errorGroup}</td>
            <td>${(r.elapsed_time || 0).toFixed(1)}s</td>
            <td><button class="btn btn-sm" onclick="showDetail(${idx})">View</button></td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById('resultsTableSection').style.display = 'block';
}

// ─── Filter Results ─────────────────────────────────────────

function filterResults() {
    const levelFilter = document.getElementById('filterLevel').value;
    const resultFilter = document.getElementById('filterResult').value;
    const rows = document.querySelectorAll('#resultsTableBody tr');

    rows.forEach(row => {
        const level = row.dataset.level;
        const result = row.dataset.result;

        let show = true;
        if (levelFilter !== 'all' && level !== levelFilter) show = false;
        if (resultFilter !== 'all' && result !== resultFilter) show = false;

        row.style.display = show ? '' : 'none';
    });
}

// ─── Detail Modal ───────────────────────────────────────────

function showDetail(idx) {
    const r = currentResults[idx];
    if (!r) return;

    const score = r.score || {};
    const ea = r.error_analysis || {};
    const patterns = score.patterns || {};

    const activePatterns = Object.entries(patterns)
        .filter(([k, v]) => v > 0)
        .map(([k, v]) => `${k} (${v})`)
        .join(', ') || 'None';

    const modal = document.getElementById('detailModal');
    const body = document.getElementById('modalBody');
    const title = document.getElementById('modalTitle');

    title.textContent = `Question ${idx + 1} Detail`;

    body.innerHTML = `
        <div class="modal-field">
            <div class="modal-field-label">Question</div>
            <div class="modal-field-value">${escapeHtml(r.question)}</div>
        </div>

        <div class="modal-field">
            <div class="modal-field-label">Level & Result</div>
            <div class="modal-field-value">
                ${getLevelBadge(r.level)} ${getResultBadge(r.is_correct)}
                &nbsp;&nbsp; Response time: ${(r.elapsed_time || 0).toFixed(2)}s
            </div>
        </div>

        <div class="modal-field">
            <div class="modal-field-label">Score Breakdown</div>
            <div class="modal-score-grid">
                <div class="modal-score-item">
                    <div class="modal-score-item-value">${score.d_score || 0}</div>
                    <div class="modal-score-item-label">D (Data Scope)</div>
                </div>
                <div class="modal-score-item">
                    <div class="modal-score-item-value">${score.b_score || 0}</div>
                    <div class="modal-score-item-label">B (Business)</div>
                </div>
                <div class="modal-score-item">
                    <div class="modal-score-item-value">${score.p_score || 0}</div>
                    <div class="modal-score-item-label">P (SQL Pattern)</div>
                </div>
                <div class="modal-score-item">
                    <div class="modal-score-item-value">${score.total_score || 0}</div>
                    <div class="modal-score-item-label">Total</div>
                </div>
            </div>
        </div>

        <div class="modal-field">
            <div class="modal-field-label">Calculated Level: ${score.level || '-'} ${score.override_rule && score.override_rule !== 'No' ? `(Override: ${score.override_rule})` : ''}</div>
            <div class="modal-field-value">SQL Patterns: ${activePatterns}</div>
        </div>

        ${ea.error_group && ea.error_group !== 'None' ? `
        <div class="modal-field">
            <div class="modal-field-label">Error Analysis</div>
            <div class="modal-field-value">
                <strong>Group:</strong> ${ea.error_group}<br>
                <strong>Labels:</strong> ${(ea.error_labels || []).join(', ')}<br>
                <strong>Severity:</strong> ${ea.severity || '-'}<br>
                <strong>Analysis:</strong> ${escapeHtml(ea.analysis || '')}
            </div>
        </div>
        ` : ''}

        <div class="modal-field">
            <div class="modal-field-label">Expected SQL</div>
            <div class="modal-sql">${escapeHtml(r.expected_sql || '(Not provided)')}</div>
        </div>

        <div class="modal-field">
            <div class="modal-field-label">Bot SQL</div>
            <div class="modal-sql">${escapeHtml(r.bot_sql || '(No SQL generated)')}</div>
        </div>

        ${r.error_message ? `
        <div class="modal-field">
            <div class="modal-field-label">Error Message</div>
            <div class="modal-field-value" style="color: var(--danger)">${escapeHtml(r.error_message)}</div>
        </div>
        ` : ''}

        ${r.bot_raw_response ? `
        <div class="modal-field">
            <div class="modal-field-label">Bot Raw Response</div>
            <div class="modal-sql" style="max-height: 200px; overflow-y: auto;">${escapeHtml(r.bot_raw_response)}</div>
        </div>
        ` : ''}
    `;

    modal.style.display = 'flex';
}

function closeModal(event) {
    if (event && event.target !== document.getElementById('detailModal')) return;
    document.getElementById('detailModal').style.display = 'none';
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.getElementById('detailModal').style.display = 'none';
    }
});

// ─── Single Question Evaluation ─────────────────────────────

async function evaluateSingle() {
    const question = document.getElementById('singleQuestion').value.trim();
    if (!question) {
        alert('Please enter a question');
        return;
    }

    const expectedSql = document.getElementById('singleExpectedSql').value.trim();
    const chatbotUrl = document.getElementById('chatbotUrl').value;

    document.getElementById('emptyState').style.display = 'none';
    const resultSection = document.getElementById('singleResult');
    const resultContent = document.getElementById('singleResultContent');
    resultSection.style.display = 'block';
    resultContent.innerHTML = '<p>⏳ Evaluating...</p>';

    try {
        const response = await fetch('/api/evaluate-single', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question,
                expected_sql: expectedSql,
                chatbot_api_url: chatbotUrl,
            }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Evaluation failed');
        }

        const data = await response.json();
        const score = data.score || {};
        const ea = data.error_analysis || {};

        resultContent.innerHTML = `
            <div class="modal-field">
                <div class="modal-field-label">Result</div>
                <div class="modal-field-value">
                    ${getResultBadge(data.is_correct)}
                    &nbsp; Response time: ${(data.elapsed_time || 0).toFixed(2)}s
                </div>
            </div>

            <div class="modal-field">
                <div class="modal-field-label">Score</div>
                <div class="modal-score-grid">
                    <div class="modal-score-item">
                        <div class="modal-score-item-value">${score.d_score || 0}</div>
                        <div class="modal-score-item-label">D Score</div>
                    </div>
                    <div class="modal-score-item">
                        <div class="modal-score-item-value">${score.b_score || 0}</div>
                        <div class="modal-score-item-label">B Score</div>
                    </div>
                    <div class="modal-score-item">
                        <div class="modal-score-item-value">${score.p_score || 0}</div>
                        <div class="modal-score-item-label">P Score</div>
                    </div>
                    <div class="modal-score-item">
                        <div class="modal-score-item-value">${score.total_score || 0}</div>
                        <div class="modal-score-item-label">Total</div>
                    </div>
                </div>
            </div>

            <div class="modal-field">
                <div class="modal-field-label">Level: ${score.level || '-'}</div>
            </div>

            ${ea.error_group && ea.error_group !== 'None' ? `
            <div class="modal-field">
                <div class="modal-field-label">Error Analysis</div>
                <div class="modal-field-value">
                    ${ea.error_group} - ${(ea.error_labels || []).join(', ')}<br>
                    ${escapeHtml(ea.analysis || '')}
                </div>
            </div>
            ` : ''}

            <div class="modal-field">
                <div class="modal-field-label">Bot SQL</div>
                <div class="modal-sql">${escapeHtml(data.bot_sql || '(No SQL)')}</div>
            </div>

            ${data.bot_raw_response ? `
            <div class="modal-field">
                <div class="modal-field-label">Bot Full Response</div>
                <div class="modal-sql" style="max-height: 200px; overflow-y: auto;">${escapeHtml(data.bot_raw_response)}</div>
            </div>
            ` : ''}

            ${data.error_message ? `
            <div class="modal-field">
                <div class="modal-field-label">Error</div>
                <div class="modal-field-value" style="color: var(--danger)">${escapeHtml(data.error_message)}</div>
            </div>
            ` : ''}
        `;

    } catch (err) {
        resultContent.innerHTML = `<p style="color: var(--danger)">❌ Error: ${escapeHtml(err.message)}</p>`;
    }
}

// ─── Download Reports ───────────────────────────────────────

function downloadReport(format) {
    if (!currentJobId) {
        alert('No evaluation results available');
        return;
    }
    window.open(`/api/job/${currentJobId}/report/${format}`, '_blank');
}

// ─── Helpers ────────────────────────────────────────────────

function getLevelBadge(level) {
    const classes = {
        'Dễ': 'badge-easy',
        'Trung bình': 'badge-medium',
        'Khó': 'badge-hard',
    };
    return `<span class="badge ${classes[level] || ''}">${level || '-'}</span>`;
}

function getResultBadge(isCorrect) {
    if (isCorrect === true) return '<span class="badge badge-pass">✅ PASS</span>';
    if (isCorrect === false) return '<span class="badge badge-fail">❌ FAIL</span>';
    return '<span class="badge badge-unknown">❓ UNKNOWN</span>';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function hideSections(ids) {
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
}
