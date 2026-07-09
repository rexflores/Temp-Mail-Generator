// Global State Management
const AppState = {
    accounts: JSON.parse(localStorage.getItem('tempMailAccounts') || '[]'),
    currentEmail: null,
    currentFolder: 'inbox',
    selectedEmails: new Set(),
    emails: [],
    isListening: false,
    currentEmailDetail: null,
    theme: localStorage.getItem('theme') || 'dark'
};

function saveAccounts() {
    localStorage.setItem('tempMailAccounts', JSON.stringify(AppState.accounts));
}

// Utility Functions
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Icon based on type
    let icon = 'info';
    if (type === 'success') icon = 'check-circle';
    if (type === 'error') icon = 'alert-circle';
    
    toast.innerHTML = `<i data-feather="${icon}"></i> <span>${message}</span>`;
    $('#toast-container').appendChild(toast);
    feather.replace();
    
    setTimeout(() => toast.classList.add('show'), 100);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (days === 1) {
        return 'Yesterday';
    } else if (days < 7) {
        return date.toLocaleDateString([], { weekday: 'short' });
    } else {
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
}

function sanitizeHtml(html) {
    return DOMPurify.sanitize(html, {
        ALLOWED_TAGS: ['p', 'br', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li', 'a', 'img', 'table', 'tr', 'td', 'th', 'tbody', 'thead'],
        ALLOWED_ATTR: ['href', 'src', 'alt', 'style', 'class', 'target', 'width', 'height', 'border', 'cellpadding', 'cellspacing']
    });
}

function showSkeletonLoader(container, count = 5) {
    const skeletons = Array(count).fill().map(() => `
        <div class="email-item">
            <div style="flex: 1;">
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-text"></div>
                <div class="skeleton skeleton-text" style="width: 70%;"></div>
            </div>
        </div>
    `).join('');
    container.innerHTML = skeletons;
}

// API Functions
async function apiCall(endpoint, options = {}) {
    try {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (AppState.currentEmail) {
            headers['X-Inbox-Id'] = AppState.currentEmail;
            const account = AppState.accounts.find(a => a.email === AppState.currentEmail);
            if (account && account.token) {
                headers['Authorization'] = `Bearer ${account.token}`;
            }
        }

        const response = await fetch(endpoint, {
            ...options,
            headers: headers
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

function renderActiveInboxes() {
    const container = $('#active-inboxes-container');
    const list = $('#inbox-list');
    
    if (AppState.accounts.length === 0) {
        if (container) container.classList.add('hidden');
        return;
    }
    
    if (container) container.classList.remove('hidden');
    if (list) {
        list.innerHTML = AppState.accounts.map(acc => `
            <div class="inbox-item ${acc.email === AppState.currentEmail ? 'active' : ''}" data-email="${acc.email}">
                <div style="overflow: hidden; text-overflow: ellipsis;" title="${acc.email}">${acc.email}</div>
                <i data-feather="chevron-right" style="width: 14px; height: 14px; opacity: 0.5;"></i>
            </div>
        `).join('');
        feather.replace();
        
        $$('.inbox-item').forEach(el => {
            el.addEventListener('click', () => switchAccount(el.dataset.email));
        });
    }
}

function switchAccount(email) {
    if (AppState.currentEmail === email) return;
    
    AppState.currentEmail = email;
    $('#current-email').textContent = email;
    $('#copy-email-btn').disabled = false;
    $('#start-listening-btn').disabled = false;
    $('#logout-btn')?.classList.remove('hidden');
    
    // Auto-close sidebar on mobile
    $('#sidebar')?.classList.remove('open');
    $('#sidebar-overlay')?.classList.remove('open');
    
    renderActiveInboxes();
    AppState.emails = [];
    renderEmailList([]);
    loadEmails(AppState.currentFolder);
}

async function registerEmail() {
    const emailPrefix = $('#email-prefix').value.trim();
    const domain = $('#domain-select').value;
    
    if (!emailPrefix) {
        showToast('Please enter an email prefix', 'error');
        return;
    }

    try {
        const currentEmailEl = $('#current-email');
        currentEmailEl.innerHTML = '<div class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></div> Registering...';
        
        const data = await apiCall('/register_email', {
            method: 'POST',
            body: JSON.stringify({ email_prefix: emailPrefix, domain: domain })
        });

        if (data.success) {
            if (!AppState.accounts.some(a => a.email === data.email)) {
                AppState.accounts.push({ email: data.email, password: data.password, token: data.token });
                saveAccounts();
            }
            
            AppState.currentEmail = data.email;
            currentEmailEl.textContent = data.email;
            $('#copy-email-btn').disabled = false;
            $('#start-listening-btn').disabled = false;
            $('#logout-btn')?.classList.remove('hidden');
            showToast(`Email registered: ${data.email}`, 'success');
            $('#email-prefix').value = '';
            
            renderActiveInboxes();
            startListening(); // automatically start listening
            
            // Clear current emails from UI
            AppState.emails = [];
            renderEmailList([]);
            updateFolderCounts();
        } else {
            showToast(data.error || 'Failed to register email', 'error');
            currentEmailEl.textContent = 'Registration failed';
        }
    } catch (error) {
        showToast('Failed to register email', 'error');
        $('#current-email').textContent = 'Registration failed';
    }
}

async function loginEmail(address, password) {
    try {
        const data = await apiCall('/login_email', {
            method: 'POST',
            body: JSON.stringify({ email: address, password: password })
        });
        if (data.success && data.token) {
            const acc = AppState.accounts.find(a => a.email === address);
            if (acc) {
                acc.token = data.token;
                saveAccounts();
            }
        }
        return data.success;
    } catch (error) {
        return false;
    }
}

function logoutEmail() {
    if (!AppState.currentEmail) return;
    
    // Remove from accounts
    AppState.accounts = AppState.accounts.filter(a => a.email !== AppState.currentEmail);
    saveAccounts();
    
    if (AppState.accounts.length > 0) {
        switchAccount(AppState.accounts[0].email);
        showToast('Inbox forgotten', 'success');
    } else {
        AppState.currentEmail = null;
        $('#current-email').textContent = 'No email registered yet';
        $('#copy-email-btn').disabled = true;
        $('#start-listening-btn').disabled = true;
        $('#logout-btn')?.classList.add('hidden');
        stopEmailPolling();
        AppState.emails = [];
        renderEmailList([]);
        updateFolderCounts();
        renderActiveInboxes();
        showToast('All inboxes forgotten', 'success');
    }
}

async function copyEmail() {
    if (!AppState.currentEmail) {
        showToast('No email to copy', 'error');
        return;
    }

    try {
        await navigator.clipboard.writeText(AppState.currentEmail);
        showToast('Email copied to clipboard!', 'success');
    } catch (error) {
        showToast('Failed to copy email', 'error');
    }
}

async function startListening() {
    if (!AppState.currentEmail) {
        showToast('Please register an email first', 'error');
        return;
    }

    AppState.isListening = true;
    $('#start-listening-btn').innerHTML = '<i data-feather="stop-circle"></i> Stop';
    $('#start-listening-btn').classList.remove('btn-primary');
    $('#start-listening-btn').classList.add('btn-secondary');
    feather.replace();
    
    showToast('Started listening for emails', 'success');
    
    // Render empty inbox if it's currently showing the initial empty state
    renderEmailList(AppState.emails);
    
    // Start polling for new emails (stateless to the backend)
    startEmailPolling();
}

let pollingInterval;
function startEmailPolling() {
    if(pollingInterval) stopEmailPolling();
    pollingInterval = setInterval(async () => {
        await loadEmails(AppState.currentFolder, false);
    }, 2000); // Poll every 2 seconds
}

function stopEmailPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

async function loadEmails(folder = 'inbox', showLoadingState = true) {
    try {
        const emailList = $('#email-list');
        
        if (showLoadingState && AppState.emails.length === 0) {
            showSkeletonLoader(emailList);
        }

        const data = await apiCall(`/api/emails?folder=${folder}`);
        
        if (data.success) {
            AppState.emails = data.emails;
            renderEmailList(data.emails);
            updateFolderCounts();
        } else {
            if(showLoadingState) {
                emailList.innerHTML = '<div class="loading">Failed to load emails</div>';
            }
        }
    } catch (error) {
        if(showLoadingState) {
            $('#email-list').innerHTML = '<div class="loading">Failed to load emails</div>';
        }
    }
}

function renderEmailList(emails) {
    const emailList = $('#email-list');
    
    if (emails.length === 0) {
        if(!AppState.isListening) {
            // Initial state
            emailList.innerHTML = `
                <div class="empty-state" id="initial-loading">
                    <div class="empty-state-icon">
                        <i data-feather="mail"></i>
                    </div>
                    <h3>Welcome to TempMail</h3>
                    <p>Register an email prefix to start receiving messages securely and privately.</p>
                </div>
            `;
        } else {
            emailList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon" style="background: transparent; color: var(--text-muted);">
                        <i data-feather="inbox"></i>
                    </div>
                    <h3>Empty ${AppState.currentFolder}</h3>
                    <p>No messages here yet.</p>
                </div>
            `;
        }
        feather.replace();
        return;
    }

    emailList.innerHTML = emails.map(email => `
        <div class="email-item ${email.is_read ? 'read' : ''}" data-email-id="${email.id}">
            <input type="checkbox" class="email-checkbox" data-email-id="${email.id}" ${AppState.selectedEmails.has(email.id) ? 'checked' : ''}>
            <i data-feather="star" class="email-star ${email.is_starred ? 'starred' : ''}" data-email-id="${email.id}"></i>
            <div class="email-from">${email.from_name || email.from}</div>
            <div class="email-content">
                <div class="email-subject">
                    ${email.subject}
                    ${email.content_type === 'html' ? '<span style="font-size: 10px; background: var(--primary-color); color: white; padding: 2px 6px; border-radius: 10px; margin-left: 8px;">HTML</span>' : ''}
                </div>
                <div class="email-preview">${email.preview_text}</div>
            </div>
            ${email.has_attachments ? '<i data-feather="paperclip" class="email-attachment-icon"></i>' : ''}
            <div class="email-date">${formatDate(email.date)}</div>
        </div>
    `).join('');

    feather.replace();
    attachEmailListeners();
}

function attachEmailListeners() {
    // Email item click
    $$('.email-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (e.target.type === 'checkbox' || e.target.matches('.email-star') || e.target.closest('.email-star')) return;
            
            const emailId = item.dataset.emailId;
            openEmailDetail(emailId);
        });
    });

    // Star toggle
    $$('.email-star').forEach(star => {
        star.addEventListener('click', (e) => {
            e.stopPropagation();
            const emailId = star.dataset.emailId;
            toggleEmailStar(emailId);
        });
    });

    // Checkbox selection
    $$('.email-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation();
            const emailId = checkbox.dataset.emailId;
            if (checkbox.checked) {
                AppState.selectedEmails.add(emailId);
            } else {
                AppState.selectedEmails.delete(emailId);
            }
            updateSelectionUI();
        });
    });
}

async function openEmailDetail(emailId) {
    try {
        $('#email-list-view').style.display = 'none';
        $('#email-detail').classList.add('active');
        
        $('#detail-content').innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                Loading message...
            </div>
        `;
        
        const data = await apiCall(`/api/emails/${emailId}`);
        
        if (data.success) {
            const email = data.email;
            AppState.currentEmailDetail = email;
            
            $('#detail-subject').textContent = email.subject;
            const fromName = email.from_name || email.from.split('@')[0];
            $('#detail-from').textContent = fromName;
            $('#detail-from-email').textContent = email.from;
            $('#detail-date').textContent = formatDate(email.date);
            
            // Set Avatar initial
            $('#sender-avatar').textContent = fromName.charAt(0).toUpperCase();
            
            // Render email content
            if (email.content_type === 'html' && email.html_content) {
                let html = email.html_content;
                // Replace inline cid: references with proxy URLs
                if (email.attachments) {
                    email.attachments.forEach(att => {
                        const cid = att.content_id || att.id;
                        if (cid) {
                            const account = AppState.accounts.find(a => a.email === AppState.currentEmail);
                            const token = account ? account.token : '';
                            const proxyUrl = `/api/emails/${emailId}/attachments/${att.id}?token=${encodeURIComponent(token)}`;
                            html = html.replace(new RegExp(`cid:${cid}`, 'gi'), proxyUrl);
                        }
                    });
                }
                $('#detail-content').innerHTML = sanitizeHtml(html);
                $('#detail-content').classList.add('html-mode');
            } else if (email.text_content) {
                if (email.text_content.includes('<a href') || email.text_content.includes('<br>')) {
                    $('#detail-content').innerHTML = email.text_content;
                } else {
                    $('#detail-content').innerHTML = `<pre style="white-space: pre-wrap; font-family: inherit; line-height: 1.6;">${email.text_content || 'No content'}</pre>`;
                }
                $('#detail-content').classList.remove('html-mode');
            } else {
                $('#detail-content').innerHTML = '<p style="color: var(--text-muted); font-style: italic;">No content available</p>';
                $('#detail-content').classList.remove('html-mode');
            }
            
            // Handle attachments
            if (email.attachments && email.attachments.length > 0) {
                renderAttachments(email.attachments);
                $('#detail-attachments').style.display = 'block';
            } else {
                $('#detail-attachments').style.display = 'none';
            }
            
            // Update email as read in the list
            const emailItem = $(`.email-item[data-email-id="${emailId}"]`);
            if (emailItem) {
                emailItem.classList.add('read');
            }
            
            // Update global state if needed
            const emailInList = AppState.emails.find(e => e.id === emailId);
            if(emailInList) emailInList.is_read = true;
            
        } else {
            showToast('Failed to load email details', 'error');
            $('#back-to-list').click();
        }
    } catch (error) {
        showToast('Failed to load email details', 'error');
        $('#back-to-list').click();
    }
}

function renderAttachments(attachments) {
    const attachmentsList = $('#attachments-list');
    attachmentsList.innerHTML = attachments.map(attachment => `
        <div class="attachment-item">
            <div class="attachment-icon">
                <i data-feather="file"></i>
            </div>
            <div class="attachment-info">
                <div class="attachment-name" title="${attachment.filename}">${attachment.filename}</div>
                <div class="attachment-meta">
                    ${formatFileSize(attachment.size)}
                </div>
            </div>
            <a href="/api/emails/${AppState.currentEmailDetail.id}/attachments/${attachment.id}?token=${encodeURIComponent(AppState.accounts.find(a => a.email === AppState.currentEmail)?.token || '')}" class="btn btn-ghost icon-only" title="Download" download>
                <i data-feather="download"></i>
            </a>
        </div>
    `).join('');
    feather.replace();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function toggleEmailStar(emailId) {
    try {
        const email = AppState.emails.find(e => e.id === emailId);
        const action = email.is_starred ? 'unstar' : 'star';
        
        const data = await apiCall(`/api/emails/${emailId}/action`, {
            method: 'POST',
            body: JSON.stringify({ action })
        });
        
        if (data.success) {
            email.is_starred = !email.is_starred;
            const star = $(`.email-star[data-email-id="${emailId}"]`);
            if(email.is_starred) {
                star.classList.add('starred');
            } else {
                star.classList.remove('starred');
            }
        }
    } catch (error) {
        showToast('Failed to update star', 'error');
    }
}

function updateFolderCounts() {
    const counts = AppState.emails.reduce((acc, email) => {
        acc[email.folder] = (acc[email.folder] || 0) + 1;
        return acc;
    }, {});
    
    // Reset all to 0 first
    ['inbox', 'sent', 'drafts', 'trash'].forEach(folder => {
        const countElement = $(`#${folder}-count`);
        if (countElement) {
            countElement.textContent = counts[folder] || 0;
        }
    });
}

function updateSelectionUI() {
    const selectedCount = AppState.selectedEmails.size;
    $('#select-all-btn').innerHTML = selectedCount > 0 
        ? `<i data-feather="square"></i> Deselect All`
        : `<i data-feather="check-square"></i> Select All`;
    feather.replace();
}

// Theme Management
function initTheme() {
    document.documentElement.setAttribute('data-theme', AppState.theme);
    updateThemeIcon();
}

function toggleTheme() {
    AppState.theme = AppState.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', AppState.theme);
    document.documentElement.setAttribute('data-theme', AppState.theme);
    updateThemeIcon();
}

function updateThemeIcon() {
    const themeIcon = $('#theme-toggle i');
    if(themeIcon) {
        themeIcon.setAttribute('data-feather', AppState.theme === 'light' ? 'moon' : 'sun');
        feather.replace();
    }
}

// Event Listeners Setup
function setupEventListeners() {
    $('#register-email-btn')?.addEventListener('click', registerEmail);
    $('#copy-email-btn')?.addEventListener('click', copyEmail);
    $('#start-listening-btn')?.addEventListener('click', startListening);
    $('#logout-btn')?.addEventListener('click', logoutEmail);
    $('#theme-toggle')?.addEventListener('click', toggleTheme);
    
    $('#menu-toggle')?.addEventListener('click', () => {
        $('#sidebar').classList.toggle('open');
        $('#sidebar-overlay')?.classList.toggle('open');
    });
    
    $('#sidebar-overlay')?.addEventListener('click', () => {
        $('#sidebar').classList.remove('open');
        $('#sidebar-overlay').classList.remove('open');
    });

    $('#refresh-btn')?.addEventListener('click', () => {
        loadEmails(AppState.currentFolder);
    });

    $('#back-to-list')?.addEventListener('click', () => {
        $('#email-detail').classList.remove('active');
        $('#email-list-view').style.display = 'flex';
        AppState.currentEmailDetail = null;
    });

    $('#delete-btn')?.addEventListener('click', async () => {
        if (!AppState.currentEmailDetail) return;
        
        if (!confirm('Are you sure you want to permanently delete this email? This cannot be undone.')) {
            return;
        }
        
        try {
            const emailId = AppState.currentEmailDetail.id;
            const data = await apiCall(`/api/emails/${emailId}/action`, {
                method: 'POST',
                body: JSON.stringify({ action: 'delete' })
            });
            
            if (data.success) {
                showToast('Email permanently deleted', 'success');
                // Remove from local state
                AppState.emails = AppState.emails.filter(e => e.id !== emailId);
                // Go back to list
                $('#back-to-list').click();
                // Re-render list
                renderEmailList(AppState.emails);
            } else {
                showToast(data.error || 'Failed to delete email', 'error');
            }
        } catch (error) {
            showToast('Failed to delete email', 'error');
        }
    });

    // Folder navigation
    $$('.folder-item').forEach(item => {
        item.addEventListener('click', () => {
            const folder = item.dataset.folder;
            
            // Update active folder
            $$('.folder-item').forEach(f => f.classList.remove('active'));
            item.classList.add('active');
            
            // Update state and load emails
            AppState.currentFolder = folder;
            $('#folder-title').textContent = item.querySelector('span').textContent;
            
            // Reset detail view if open
            $('#email-detail').classList.remove('active');
            $('#email-list-view').style.display = 'flex';
            
            // Auto-close sidebar on mobile
            $('#sidebar')?.classList.remove('open');
            $('#sidebar-overlay')?.classList.remove('open');
            
            loadEmails(folder);
        });
    });

    // Enter key for email registration
    $('#email-prefix')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            registerEmail();
        }
    });

    // Select All functionality
    $('#select-all-btn')?.addEventListener('click', () => {
        const checkboxes = $$('.email-checkbox');
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        
        checkboxes.forEach(cb => {
            cb.checked = !allChecked;
            const emailId = cb.dataset.emailId;
            if (!allChecked) {
                AppState.selectedEmails.add(emailId);
            } else {
                AppState.selectedEmails.delete(emailId);
            }
        });
        updateSelectionUI();
    });
}

async function fetchDomains() {
    try {
        const data = await apiCall('/get_domains');
        const select = $('#domain-select');
        if (data.success && data.domains.length > 0) {
            select.innerHTML = data.domains.map(d => `<option value="${d}">@${d}</option>`).join('');
        } else {
            select.innerHTML = '<option value="">No domains available</option>';
        }
    } catch (error) {
        $('#domain-select').innerHTML = '<option value="">Error loading domains</option>';
    }
}

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    feather.replace();
    setupEventListeners();
    fetchDomains();
    
    // Migrate old format if exists
    const savedAddress = localStorage.getItem('tempmail_address');
    const savedPassword = localStorage.getItem('tempmail_password');
    if (savedAddress && savedPassword) {
        if (!AppState.accounts.some(a => a.email === savedAddress)) {
            AppState.accounts.push({ email: savedAddress, password: savedPassword });
            saveAccounts();
        }
        localStorage.removeItem('tempmail_address');
        localStorage.removeItem('tempmail_password');
    }

    if (AppState.accounts.length > 0) {
        $('#current-email').innerHTML = '<div class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></div> Recovering...';
        
        const validAccounts = [];
        Promise.all(AppState.accounts.map(async (acc) => {
            const success = await loginEmail(acc.email, acc.password);
            if (success) {
                validAccounts.push(acc);
            }
        })).then(() => {
            AppState.accounts = validAccounts;
            saveAccounts();
            
            if (AppState.accounts.length > 0) {
                switchAccount(AppState.accounts[0].email);
                showToast(`Recovered ${AppState.accounts.length} inboxes`, 'success');
            } else {
                $('#current-email').textContent = 'No email registered yet';
                renderActiveInboxes();
                showToast('Previous inboxes expired. Please register a new one.', 'info');
            }
        });
    } else {
        renderActiveInboxes();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopEmailPolling();
});
