/**
 * Dashboard functionality
 */

// Protect this page
requireAuth();

// Display username
document.getElementById('username').textContent = getUsername();
const initials = getUsername().substring(0, 2).toUpperCase();
document.getElementById('userAvatar').textContent = initials;

// Tab switching
const tabs = document.querySelectorAll('.tab');
const tabContents = document.querySelectorAll('.tab-content');

tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        
        // Update active tab
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // Update active content
        tabContents.forEach(content => content.classList.remove('active'));
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        // Load data for specific tabs
        if (tabName === 'audits') {
            loadMyAudits();
        } else {
            // Stop polling when leaving My Audits tab
            stopAuditPolling();
        }
    });
});

// File upload zones
const artifactZone = document.getElementById('artifactZone');
const checklistZone = document.getElementById('checklistZone');
const artifactFile = document.getElementById('artifactFile');
const checklistFile = document.getElementById('checklistFile');

artifactZone.addEventListener('click', () => artifactFile.click());
checklistZone.addEventListener('click', () => checklistFile.click());

artifactFile.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        artifactZone.classList.add('has-file');
        artifactZone.querySelector('p').textContent = e.target.files[0].name;
    }
});

checklistFile.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        checklistZone.classList.add('has-file');
        checklistZone.querySelector('p').textContent = e.target.files[0].name;
    }
});

// Submit Audit Form
const auditForm = document.getElementById('auditForm');
auditForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const agentType = document.getElementById('agentType').value;
    const artifact = artifactFile.files[0];
    const checklist = checklistFile.files[0];
    
    if (!artifact || !checklist) {
        showToast('Please select both files', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('agent_type', agentType);
        formData.append('artifact_file', artifact);
        formData.append('checklist_file', checklist);
        
        // Submit audit
        const response = await authFetch('http://localhost:8000/api/audits/submit', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showToast(`Error: ${data.detail || 'Audit submission failed'}`, 'error');
            return;
        }
        
        // Reset form
        auditForm.reset();
        artifactZone.classList.remove('has-file');
        checklistZone.classList.remove('has-file');
        artifactZone.querySelector('p').textContent = 'Click to upload .txt or .docx';
        checklistZone.querySelector('p').textContent = 'Click to upload .txt or .docx';
        
        // Show success toast
        showToast('✅ Audit queued for processing! Check "My Audits" tab for status.', 'success');
        
        // Optionally switch to My Audits tab after a delay
        setTimeout(() => {
            document.querySelector('.tab[data-tab="audits"]').click();
        }, 2000);
        
    } catch (error) {
        console.error('Audit submission error:', error);
        showToast('Network error. Please ensure the server is running.', 'error');
    }
});

// Toast notification function
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    // Add to body
    document.body.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 100);
    
    // Remove after 5 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Load My Audits
async function loadMyAudits() {
    const auditsList = document.getElementById('auditsList');
    
    try {
        const response = await authFetch('http://localhost:8000/api/audits/my-audits');
        const data = await response.json();
        
        if (data.audits.length === 0) {
            auditsList.innerHTML = '<p class="text-muted">No audits found. Submit your first audit!</p>';
            stopAuditPolling();
            return;
        }
        
        // Check if table exists - if not, build it
        const existingTable = auditsList.querySelector('table');
        if (!existingTable) {
            buildAuditsTable(data.audits);
        } else {
            // Table exists - just update the cells
            updateAuditRows(data.audits);
        }
        
        // Check if any audits are still processing
        const hasActiveAudits = data.audits.some(a => 
            a.status === 'pending' || a.status === 'processing'
        );
        
        if (hasActiveAudits) {
            startAuditPolling();
        } else {
            stopAuditPolling();
        }
        
    } catch (error) {
        console.error('Error loading audits:', error);
        auditsList.innerHTML = '<p class="text-muted">Error loading audits. Please try again.</p>';
        stopAuditPolling();
    }
}

// Build initial audits table
function buildAuditsTable(audits) {
    const auditsList = document.getElementById('auditsList');
    
    const table = `
        <table class="results-table">
            <thead>
                <tr>
                    <th>Audit #</th>
                    <th>Agent Type</th>
                    <th>Status</th>
                    <th>Progress</th>
                    <th>Created (IST)</th>
                    <th>Completed (IST)</th>
                    <th>Duration</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody id="auditsTableBody">
                ${audits.map((audit, index) => `
                    <tr data-session-id="${audit.session_id}">
                        <td><strong>#${audits.length - index}</strong></td>
                        <td>${formatAgentType(audit.agent_type)}</td>
                        <td class="status-cell">
                            ${getStatusBadge(audit.status)}
                            ${audit.status === 'failed' && audit.error_message ? 
                                `<br><small style="color: var(--error); font-size: 0.75rem;" title="${audit.error_message}">⚠️ ${audit.error_message.substring(0, 50)}...</small>` : 
                                ''
                            }
                        </td>
                        <td class="progress-cell">${Math.round(audit.progress_percentage || 0)}%</td>
                        <td>${formatISTDateTime(audit.created_at)}</td>
                        <td class="completed-cell">${audit.completed_at ? formatISTDateTime(audit.completed_at) : '-'}</td>
                        <td class="duration-cell">${audit.duration_seconds ? formatDuration(audit.duration_seconds) : '-'}</td>
                        <td class="action-cell">
                            ${audit.status === 'completed' ? 
                                `<button class="btn btn-secondary" onclick="loadResults('${audit.session_id}')">View Results</button>` :
                                `<span class="text-muted">Pending</span>`
                            }
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    auditsList.innerHTML = table;
}

// Update existing rows without rebuilding table (smooth updates)
function updateAuditRows(audits) {
    audits.forEach(audit => {
        const row = document.querySelector(`tr[data-session-id="${audit.session_id}"]`);
        if (!row) {
            // New audit added - rebuild table
            buildAuditsTable(audits);
            return;
        }
        
        // Update status cell
        const statusCell = row.querySelector('.status-cell');
        const newStatusBadge = getStatusBadge(audit.status);
        if (statusCell && statusCell.innerHTML !== newStatusBadge) {
            statusCell.innerHTML = newStatusBadge;
        }
        
        // Update progress cell
        const progressCell = row.querySelector('.progress-cell');
        const newProgress = `${Math.round(audit.progress_percentage || 0)}%`;
        if (progressCell && progressCell.textContent !== newProgress) {
            progressCell.textContent = newProgress;
        }
        
        // Update completed cell
        const completedCell = row.querySelector('.completed-cell');
        const newCompleted = audit.completed_at ? formatISTDateTime(audit.completed_at) : '-';
        if (completedCell && completedCell.textContent !== newCompleted) {
            completedCell.textContent = newCompleted;
        }
        
        // Update duration cell
        const durationCell = row.querySelector('.duration-cell');
        const newDuration = audit.duration_seconds ? formatDuration(audit.duration_seconds) : '-';
        if (durationCell && durationCell.textContent !== newDuration) {
            durationCell.textContent = newDuration;
        }
        
        // Update action cell
        const actionCell = row.querySelector('.action-cell');
        const newAction = audit.status === 'completed' ? 
            `<button class="btn btn-secondary" onclick="loadResults('${audit.session_id}')">View Results</button>` :
            `<span class="text-muted">Pending</span>`;
        if (actionCell && actionCell.innerHTML !== newAction) {
            actionCell.innerHTML = newAction;
        }
    });
}

// Auto-polling for audit updates
let auditPollingInterval = null;

function startAuditPolling() {
    // Don't start multiple intervals
    if (auditPollingInterval) {
        return;
    }
    
    console.log('🔄 Started auto-polling for audit updates');
    auditPollingInterval = setInterval(() => {
        loadMyAudits();
    }, 2000); // Poll every 2 seconds
}

function stopAuditPolling() {
    if (auditPollingInterval) {
        clearInterval(auditPollingInterval);
        auditPollingInterval = null;
        console.log('⏸️ Stopped auto-polling');
    }
}

// Load Results
async function loadResults(sessionId) {
    const resultsContent = document.getElementById('resultsContent');
    resultsContent.innerHTML = '<p class="text-muted">Loading results...</p>';
    
    try {
        const response = await authFetch(`http://localhost:8000/api/audits/results/${sessionId}`);
        const data = await response.json();
        
        if (!response.ok) {
            resultsContent.innerHTML = `<p class="text-muted">Error: ${data.detail || 'Failed to load results'}</p>`;
            return;
        }
        
        // Calculate stats from findings
        const total = data.findings.length;
        const compliant = data.findings.filter(f => f.finding_type === 'compliant').length;
        const nonCompliant = data.findings.filter(f => f.finding_type === 'non_compliant').length;
        const missing = data.findings.filter(f => f.finding_type === 'missing').length;
        const complianceRate = total > 0 ? Math.round((compliant / total) * 100) : 0;
        
        const resultsHTML = `
            <div class="mb-lg">
                <h3>Audit Summary</h3>
                <p class="text-muted mb-md">Session: <code>${sessionId}</code></p>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--space-md);">
                    <div class="stats-card">
                        <div class="stat-label">Compliance Rate</div>
                        <div class="stat-value" style="color: ${complianceRate >= 80 ? 'var(--success)' : complianceRate >= 60 ? 'var(--warning)' : 'var(--error)'};">
                            ${complianceRate}%
                        </div>
                    </div>
                    <div class="stats-card">
                        <div class="stat-label">Total Items</div>
                        <div class="stat-value">${total}</div>
                    </div>
                    <div class="stats-card">
                        <div class="stat-label">Compliant</div>
                        <div class="stat-value" style="color: var(--success);">${compliant}</div>
                    </div>
                    <div class="stats-card">
                        <div class="stat-label">Non-Compliant</div>
                        <div class="stat-value" style="color: var(--error);">${nonCompliant}</div>
                    </div>
                    <div class="stats-card">
                        <div class="stat-label">Missing</div>
                        <div class="stat-value" style="color: var(--warning);">${missing}</div>
                    </div>
                </div>
            </div>
            
            <div>
                <h3>Findings</h3>
                <div style="display: flex; flex-direction: column; gap: var(--space-sm);">
                    ${data.findings.map((finding, index) => `
                        <details class="card" style="cursor: pointer;">
                            <summary style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong>#${index + 1}</strong>: ${finding.checklist_item.substring(0, 100)}...
                                </div>
                                ${getFindingBadge(finding.finding_type)}
                            </summary>
                            <div class="mt-md">
                                <p><strong>Description:</strong></p>
                                <p>${finding.description}</p>
                                ${finding.severity ? `<p class="mt-sm"><strong>Severity:</strong> ${getSeverityBadge(finding.severity)}</p>` : ''}
                                ${finding.location_in_document ? `<p class="mt-sm"><strong>Location:</strong> ${finding.location_in_document}</p>` : ''}
                                ${finding.recommendation ? `<p class="mt-sm"><strong>Recommendation:</strong> ${finding.recommendation}</p>` : ''}
                            </div>
                        </details>
                    `).join('')}
                </div>
            </div>
        `;
        
        resultsContent.innerHTML = resultsHTML;
        
        // Switch to results tab
        document.querySelector('.tab[data-tab="results"]').click();
    } catch (error) {
        console.error('Error loading results:', error);
        resultsContent.innerHTML = '<p class="text-muted">Network error loading results.</p>';
    }
}

// Helper Functions
function formatISTDateTime(utcDateString) {
    const date = new Date(utcDateString);
    
    // Convert to IST (UTC + 5:30)
    const istDate = new Date(date.getTime() + (5.5 * 60 * 60 * 1000));
    
    // Format: "9 Feb 2026, 10:45 AM"
    const options = {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    };
    
    return istDate.toLocaleString('en-IN', options);
}

function formatDuration(seconds) {
    if (!seconds) return '-';
    
    const sec = Math.round(seconds);
    
    if (sec < 60) {
        return `${sec}s`;
    } else if (sec < 3600) {
        const mins = Math.floor(sec / 60);
        const secs = sec % 60;
        return `${mins}m ${secs}s`;
    } else {
        const hours = Math.floor(sec / 3600);
        const mins = Math.floor((sec % 3600) / 60);
        return `${hours}h ${mins}m`;
    }
}

function formatAgentType(type) {
    const map = {
        'sow_reviewer': 'SoW Reviewer',
        'project_plan_reviewer': 'Project Plan',
        'architecture_compliance': 'Architecture'
    };
    return map[type] || type;
}

function getStatusBadge(status) {
    const badges = {
        'completed': '<span class="badge badge-success">Completed</span>',
        'processing': '<span class="badge badge-info">Processing</span>',
        'failed': '<span class="badge badge-error">Failed</span>',
        'pending': '<span class="badge badge-warning">Pending</span>'
    };
    return badges[status] || status;
}

function getFindingBadge(type) {
    const badges = {
        'compliant': '<span class="badge badge-success">✅ Compliant</span>',
        'non_compliant': '<span class="badge badge-error">❌ Non-Compliant</span>',
        'missing': '<span class="badge badge-warning">⚠️ Missing</span>',
        'advisory': '<span class="badge badge-info">💡 Advisory</span>'
    };
    return badges[type] || type;
}

function getSeverityBadge(severity) {
    const badges = {
        'critical': '<span class="badge badge-error">🔴 Critical</span>',
        'high': '<span class="badge badge-error">High</span>',
        'medium': '<span class="badge badge-warning">Medium</span>',
        'low': '<span class="badge badge-info">Low</span>'
    };
    return badges[severity] || severity;
}

function showLoading(message) {
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="spinner"></div>
        <div class="loading-text">${message}</div>
    `;
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.remove();
    }
}
