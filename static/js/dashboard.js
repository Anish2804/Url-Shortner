/**
 * LinkScale Platform - Modern Single-Page Dashboard Logic
 */

// Application State
const state = {
  token: localStorage.getItem('linkscale_token') || null,
  user: JSON.parse(localStorage.getItem('linkscale_user') || 'null'),
  urls: [],
  currentAnalyticsCode: null,
};

// DOM Elements
const authBtn = document.getElementById('authBtn');
const authModal = document.getElementById('authModal');
const authForm = document.getElementById('authForm');
const authToggleLink = document.getElementById('authToggleLink');
const authSubmitBtn = document.getElementById('authSubmitBtn');
const authModalTitle = document.getElementById('authModalTitle');

const shortenForm = document.getElementById('shortenForm');
const optionsToggle = document.getElementById('optionsToggle');
const optionsDrawer = document.getElementById('optionsDrawer');
const resultCard = document.getElementById('resultCard');
const shortUrlLink = document.getElementById('shortUrlLink');
const copyBtn = document.getElementById('copyBtn');
const openQrModalBtn = document.getElementById('openQrModalBtn');

const qrModal = document.getElementById('qrModal');
const qrImg = document.getElementById('qrImg');
const qrDownloadBtn = document.getElementById('qrDownloadBtn');

const analyticsModal = document.getElementById('analyticsModal');
const analyticsModalTitle = document.getElementById('analyticsModalTitle');
const exportCsvBtn = document.getElementById('exportCsvBtn');

const urlsTableBody = document.getElementById('urlsTableBody');
const toastEl = document.getElementById('toast');
const systemStatusPill = document.getElementById('systemStatusPill');

let isRegisterMode = false;

// -------------------------------------------------------------
// Toast Notification
// -------------------------------------------------------------
function showToast(message, duration = 3000) {
  toastEl.textContent = message;
  toastEl.classList.add('show');
  setTimeout(() => {
    toastEl.classList.remove('show');
  }, duration);
}

// -------------------------------------------------------------
// API Helper
// -------------------------------------------------------------
async function apiRequest(endpoint, method = 'GET', data = null, isBlob = false) {
  const headers = {};
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }
  if (data && !isBlob) {
    headers['Content-Type'] = 'application/json';
  }

  const options = {
    method,
    headers,
  };

  if (data) {
    options.body = JSON.stringify(data);
  }

  const response = await fetch(endpoint, options);

  if (isBlob) {
    if (!response.ok) {
      throw new Error(`Download failed with status ${response.status}`);
    }
    return await response.blob();
  }

  const json = await response.json();
  if (!response.ok || json.success === false) {
    const errorMsg = json.error ? json.error.message : 'API Request Failed';
    throw new Error(errorMsg);
  }
  return json.data;
}

// -------------------------------------------------------------
// System Health Telemetry Poll
// -------------------------------------------------------------
async function pollSystemHealth() {
  try {
    const res = await fetch('/health');
    const data = await res.json();
    if (data.status === 'healthy') {
      const dbLatency = data.dependencies?.database?.latency_ms || 1.2;
      systemStatusPill.innerHTML = `<span class="status-dot"></span> Online (${dbLatency}ms)`;
    } else {
      systemStatusPill.innerHTML = `<span class="status-dot" style="background:#f59e0b"></span> Degraded`;
    }
  } catch (err) {
    systemStatusPill.innerHTML = `<span class="status-dot" style="background:#ef4444"></span> Offline`;
  }
}

// -------------------------------------------------------------
// Authentication Workflow
// -------------------------------------------------------------
function updateAuthUI() {
  if (state.token && state.user) {
    authBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
        <circle cx="12" cy="7" r="4"></circle>
      </svg>
      ${state.user.username} (Logout)
    `;
    authBtn.classList.add('logged-in');
    loadUserUrls();
  } else {
    authBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
        <polyline points="10 17 15 12 10 7"></polyline>
        <line x1="15" y1="12" x2="3" y2="12"></line>
      </svg>
      Sign In
    `;
    authBtn.classList.remove('logged-in');
    renderUrlsTable([]);
  }
}

authBtn.addEventListener('click', () => {
  if (state.token) {
    // Logout
    localStorage.removeItem('linkscale_token');
    localStorage.removeItem('linkscale_user');
    state.token = null;
    state.user = null;
    updateAuthUI();
    showToast('Signed out successfully');
  } else {
    // Open Login Modal
    isRegisterMode = false;
    authModalTitle.textContent = 'Sign In to LinkScale';
    authSubmitBtn.textContent = 'Sign In';
    authToggleLink.textContent = "Don't have an account? Sign up";
    document.getElementById('emailGroup').style.display = 'none';
    authModal.classList.add('active');
  }
});

authToggleLink.addEventListener('click', (e) => {
  e.preventDefault();
  isRegisterMode = !isRegisterMode;
  if (isRegisterMode) {
    authModalTitle.textContent = 'Create LinkScale Account';
    authSubmitBtn.textContent = 'Register';
    authToggleLink.textContent = 'Already have an account? Sign in';
    document.getElementById('emailGroup').style.display = 'block';
  } else {
    authModalTitle.textContent = 'Sign In to LinkScale';
    authSubmitBtn.textContent = 'Sign In';
    authToggleLink.textContent = "Don't have an account? Sign up";
    document.getElementById('emailGroup').style.display = 'none';
  }
});

authForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('authUsername').value.trim();
  const password = document.getElementById('authPassword').value;
  const email = document.getElementById('authEmail').value.trim();

  try {
    authSubmitBtn.disabled = true;
    authSubmitBtn.textContent = 'Processing...';

    if (isRegisterMode) {
      await apiRequest('/api/v1/auth/register', 'POST', { username, email, password });
      showToast('Account registered! Signing in...');
    }

    const loginData = await apiRequest('/api/v1/auth/login', 'POST', {
      username_or_email: username,
      password: password,
    });

    state.token = loginData.access_token;
    state.user = { username: username };
    localStorage.setItem('linkscale_token', state.token);
    localStorage.setItem('linkscale_user', JSON.stringify(state.user));

    authModal.classList.remove('active');
    updateAuthUI();
    showToast(`Welcome back, ${username}!`);
  } catch (err) {
    showToast(`Error: ${err.message}`);
  } finally {
    authSubmitBtn.disabled = false;
    authSubmitBtn.textContent = isRegisterMode ? 'Register' : 'Sign In';
  }
});

// -------------------------------------------------------------
// Options Drawer Toggle
// -------------------------------------------------------------
optionsToggle.addEventListener('click', () => {
  const isOpen = optionsDrawer.classList.toggle('open');
  optionsToggle.querySelector('span').textContent = isOpen ? 'Hide Advanced Options ▲' : 'Advanced Options (Alias, Password, Burner, UTM) ▼';
});

// -------------------------------------------------------------
// UTM Campaign Builder Helpers
// -------------------------------------------------------------
const utmSourceInput = document.getElementById('utmSource');
const utmMediumInput = document.getElementById('utmMedium');
const utmCampaignInput = document.getElementById('utmCampaign');
const utmPreviewText = document.getElementById('utmPreviewText');
const clearUtmBtn = document.getElementById('clearUtmBtn');
const utmPresetPills = document.querySelectorAll('.utm-preset-pill[data-source]');

function buildUrlWithUtm(baseStr) {
  if (!baseStr) return '';
  try {
    let urlObj;
    if (!baseStr.startsWith('http://') && !baseStr.startsWith('https://')) {
      urlObj = new URL(`https://${baseStr}`);
    } else {
      urlObj = new URL(baseStr);
    }
    const src = utmSourceInput ? utmSourceInput.value.trim() : '';
    const med = utmMediumInput ? utmMediumInput.value.trim() : '';
    const camp = utmCampaignInput ? utmCampaignInput.value.trim() : '';

    if (src) urlObj.searchParams.set('utm_source', src);
    if (med) urlObj.searchParams.set('utm_medium', med);
    if (camp) urlObj.searchParams.set('utm_campaign', camp);

    return urlObj.toString();
  } catch (err) {
    return baseStr;
  }
}

function updateUtmPreview() {
  if (!utmPreviewText) return;
  const base = document.getElementById('urlInput').value.trim();
  const src = utmSourceInput ? utmSourceInput.value.trim() : '';
  const med = utmMediumInput ? utmMediumInput.value.trim() : '';
  const camp = utmCampaignInput ? utmCampaignInput.value.trim() : '';

  if (!base) {
    if (src || med || camp) {
      const dummy = new URL('https://example.com');
      if (src) dummy.searchParams.set('utm_source', src);
      if (med) dummy.searchParams.set('utm_medium', med);
      if (camp) dummy.searchParams.set('utm_campaign', camp);
      utmPreviewText.textContent = `...${dummy.search}`;
    } else {
      utmPreviewText.textContent = '(Paste destination URL above to preview)';
    }
    return;
  }

  const finalUrl = buildUrlWithUtm(base);
  utmPreviewText.textContent = finalUrl;
}

if (utmSourceInput) utmSourceInput.addEventListener('input', updateUtmPreview);
if (utmMediumInput) utmMediumInput.addEventListener('input', updateUtmPreview);
if (utmCampaignInput) utmCampaignInput.addEventListener('input', updateUtmPreview);
document.getElementById('urlInput').addEventListener('input', updateUtmPreview);

utmPresetPills.forEach(pill => {
  pill.addEventListener('click', () => {
    utmPresetPills.forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    if (utmSourceInput) utmSourceInput.value = pill.dataset.source || '';
    if (utmMediumInput) utmMediumInput.value = pill.dataset.medium || '';
    if (utmCampaignInput) utmCampaignInput.value = pill.dataset.campaign || '';
    updateUtmPreview();
    showToast(`Applied ${pill.textContent} preset 🎯`);
  });
});

if (clearUtmBtn) {
  clearUtmBtn.addEventListener('click', () => {
    utmPresetPills.forEach(p => p.classList.remove('active'));
    if (utmSourceInput) utmSourceInput.value = '';
    if (utmMediumInput) utmMediumInput.value = '';
    if (utmCampaignInput) utmCampaignInput.value = '';
    updateUtmPreview();
  });
}

// -------------------------------------------------------------
// Shorten URL Workflow
// -------------------------------------------------------------
shortenForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  let originalUrl = document.getElementById('urlInput').value.trim();
  const src = utmSourceInput ? utmSourceInput.value.trim() : '';
  const med = utmMediumInput ? utmMediumInput.value.trim() : '';
  const camp = utmCampaignInput ? utmCampaignInput.value.trim() : '';

  if (src || med || camp) {
    originalUrl = buildUrlWithUtm(originalUrl);
  }

  const customAlias = document.getElementById('aliasInput').value.trim() || null;
  const password = document.getElementById('passwordInput').value || null;
  const isOneTime = document.getElementById('oneTimeToggle').checked;
  const redirectHttpCode = parseInt(document.getElementById('httpCodeSelect').value, 10);

  const payload = {
    original_url: originalUrl,
    custom_alias: customAlias,
    password: password,
    is_one_time: isOneTime,
    redirect_http_code: redirectHttpCode,
  };

  const submitBtn = shortenForm.querySelector('button[type="submit"]');

  try {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `Shortening...`;

    const data = await apiRequest('/api/v1/urls/', 'POST', payload);

    // Display Result Card
    shortUrlLink.href = data.short_url;
    shortUrlLink.textContent = data.short_url;
    resultCard.classList.add('active');

    // Update Result Badges
    const badgesContainer = document.getElementById('resultBadges');
    badgesContainer.innerHTML = '';
    if (data.is_one_time) {
      badgesContainer.innerHTML += `<span class="badge badge-burner">🔥 One-Time Burner</span>`;
    }
    if (data.is_password_protected) {
      badgesContainer.innerHTML += `<span class="badge badge-secure">🔒 Password Protected</span>`;
    }
    badgesContainer.innerHTML += `<span class="badge badge-info">${data.redirect_http_code} Redirect</span>`;

    // Store current code for QR button
    resultCard.dataset.code = data.custom_alias || data.short_code;

    showToast('Short URL generated successfully! ⚡');
    if (state.token) {
      loadUserUrls();
    }
  } catch (err) {
    showToast(`Failed: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
      Shorten URL
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="5" y1="12" x2="19" y2="12"></line>
        <polyline points="12 5 19 12 12 19"></polyline>
      </svg>
    `;
  }
});

// Copy to Clipboard
copyBtn.addEventListener('click', () => {
  const url = shortUrlLink.textContent;
  navigator.clipboard.writeText(url).then(() => {
    showToast('Link copied to clipboard! 📋');
  });
});

// QR Code Preview from Result Card
openQrModalBtn.addEventListener('click', () => {
  const code = resultCard.dataset.code;
  openQrModal(code);
});

// -------------------------------------------------------------
// QR Code Modal
// -------------------------------------------------------------
function openQrModal(code) {
  qrImg.src = `/api/v1/urls/${encodeURIComponent(code)}/qr`;
  qrDownloadBtn.onclick = () => {
    const a = document.createElement('a');
    a.href = qrImg.src;
    a.download = `qr_${code}.png`;
    a.click();
  };
  qrModal.classList.add('active');
}

// -------------------------------------------------------------
// Load & Render User URLs Table
// -------------------------------------------------------------
async function loadUserUrls() {
  if (!state.token) return;
  try {
    const data = await apiRequest('/api/v1/urls/?limit=20');
    state.urls = data.items || [];
    renderUrlsTable(state.urls);
  } catch (err) {
    console.error('Failed to load links:', err);
  }
}

function renderUrlsTable(urls) {
  if (!urls || urls.length === 0) {
    urlsTableBody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; color: var(--text-dim); padding: 2rem;">
          ${state.token ? 'No links created yet. Paste a URL above to shorten your first link!' : 'Sign in to view your shortened links and detailed analytics.'}
        </td>
      </tr>
    `;
    return;
  }

  urlsTableBody.innerHTML = urls.map(u => {
    const code = u.custom_alias || u.short_code;
    const dest = u.original_url;
    const clicks = u.click_count || 0;
    const isBurner = u.is_one_time ? '🔥 Burner' : '';
    const isPwd = u.is_password_protected ? '🔒 Locked' : '';

    return `
      <tr>
        <td>
          <a href="/${code}" target="_blank" class="table-code-link">/${code}</a>
          <span style="font-size:0.75rem; color:var(--text-dim); margin-left:0.3rem;">${isBurner} ${isPwd}</span>
        </td>
        <td>
          <div class="table-dest" title="${dest}">${dest}</div>
        </td>
        <td>
          <span class="clicks-pill">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
            ${clicks}
          </span>
        </td>
        <td>
          <div class="table-action-btns">
            <button class="icon-btn" title="View Deep Analytics" onclick="openAnalyticsModal('${code}')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="20" x2="18" y2="10"></line>
                <line x1="12" y1="20" x2="12" y2="4"></line>
                <line x1="6" y1="20" x2="6" y2="14"></line>
              </svg>
            </button>
            <button class="icon-btn" title="View QR Code" onclick="openQrModal('${code}')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>
            </button>
            <button class="icon-btn" title="Copy Short Link" onclick="navigator.clipboard.writeText('${window.location.origin}/${code}'); showToast('Copied link! 📋')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
            </button>
            <button class="icon-btn danger" title="Delete Link" onclick="deleteUrl('${code}')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// -------------------------------------------------------------
// Delete Link
// -------------------------------------------------------------
async function deleteUrl(code) {
  if (!confirm(`Are you sure you want to delete /${code}?`)) return;
  try {
    await apiRequest(`/api/v1/urls/${encodeURIComponent(code)}`, 'DELETE');
    showToast(`Deleted /${code}`);
    loadUserUrls();
  } catch (err) {
    showToast(`Delete failed: ${err.message}`);
  }
}

// -------------------------------------------------------------
// Analytics Modal & Canvas Chart
// -------------------------------------------------------------
async function openAnalyticsModal(code) {
  state.currentAnalyticsCode = code;
  analyticsModalTitle.textContent = `Analytics for /${code}`;
  analyticsModal.classList.add('active');

  const totalClicksEl = document.getElementById('metricTotalClicks');
  const uniqueVisitorsEl = document.getElementById('metricUniqueVisitors');
  const botClicksEl = document.getElementById('metricBotClicks');
  const countriesListEl = document.getElementById('countriesBreakdownList');
  const devicesListEl = document.getElementById('devicesBreakdownList');
  const browsersListEl = document.getElementById('browsersBreakdownList');

  totalClicksEl.textContent = '...';
  uniqueVisitorsEl.textContent = '...';
  botClicksEl.textContent = '...';
  if (countriesListEl) countriesListEl.innerHTML = 'Loading...';
  devicesListEl.innerHTML = 'Loading...';
  browsersListEl.innerHTML = 'Loading...';

  try {
    const data = await apiRequest(`/api/v1/analytics/urls/${encodeURIComponent(code)}`);

    totalClicksEl.textContent = data.total_clicks || 0;
    uniqueVisitorsEl.textContent = data.unique_visitors || 0;
    botClicksEl.textContent = data.bot_clicks || 0;

    // Draw Timeline Chart on Canvas
    drawClickTimelineChart(data.time_series || []);

    // Render Countries Breakdown
    if (countriesListEl) {
      if (data.countries && data.countries.length > 0) {
        countriesListEl.innerHTML = data.countries.map(c => `
          <div>
            <div class="breakdown-row">
              <span>${c.category}</span>
              <span style="font-weight:600">${c.count} (${c.percentage}%)</span>
            </div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill" style="width: ${c.percentage}%"></div>
            </div>
          </div>
        `).join('');
      } else {
        countriesListEl.innerHTML = '<span style="color:var(--text-dim)">No location data yet</span>';
      }
    }

    // Render Devices Breakdown
    if (data.devices && data.devices.length > 0) {
      devicesListEl.innerHTML = data.devices.map(d => `
        <div>
          <div class="breakdown-row">
            <span>${d.category}</span>
            <span style="font-weight:600">${d.count} (${d.percentage}%)</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${d.percentage}%"></div>
          </div>
        </div>
      `).join('');
    } else {
      devicesListEl.innerHTML = '<span style="color:var(--text-dim)">No device clicks yet</span>';
    }

    // Render Browsers Breakdown
    if (data.browsers && data.browsers.length > 0) {
      browsersListEl.innerHTML = data.browsers.map(b => `
        <div>
          <div class="breakdown-row">
            <span>${b.category}</span>
            <span style="font-weight:600">${b.count} (${b.percentage}%)</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${b.percentage}%"></div>
          </div>
        </div>
      `).join('');
    } else {
      browsersListEl.innerHTML = '<span style="color:var(--text-dim)">No browser data yet</span>';
    }

  } catch (err) {
    showToast(`Failed to load analytics: ${err.message}`);
  }
}

// Lightweight HTML5 Canvas Chart Renderer
function drawClickTimelineChart(timeSeries) {
  const canvas = document.getElementById('clicksChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const width = (canvas.width = canvas.parentElement.clientWidth);
  const height = (canvas.height = 180);

  ctx.clearRect(0, 0, width, height);

  if (!timeSeries || timeSeries.length === 0) {
    ctx.fillStyle = '#64748b';
    ctx.font = '14px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('No click history yet for this timeframe', width / 2, height / 2);
    return;
  }

  const padding = 35;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const maxClicks = Math.max(...timeSeries.map(p => p.clicks), 5);
  const stepX = chartWidth / Math.max(timeSeries.length - 1, 1);

  // Draw Grid lines
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i <= 3; i++) {
    const y = padding + (chartHeight / 3) * i;
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
  }
  ctx.stroke();

  // Draw Area Gradient Fill
  const gradient = ctx.createLinearGradient(0, padding, 0, height - padding);
  gradient.addColorStop(0, 'rgba(99, 102, 241, 0.45)');
  gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');

  ctx.beginPath();
  timeSeries.forEach((pt, idx) => {
    const x = padding + (timeSeries.length === 1 ? chartWidth / 2 : idx * stepX);
    const y = height - padding - (pt.clicks / maxClicks) * chartHeight;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.lineTo(timeSeries.length === 1 ? padding + chartWidth / 2 : padding + chartWidth, height - padding);
  ctx.lineTo(timeSeries.length === 1 ? padding + chartWidth / 2 : padding, height - padding);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // Draw Line
  ctx.strokeStyle = '#818cf8';
  ctx.lineWidth = 3;
  ctx.beginPath();
  timeSeries.forEach((pt, idx) => {
    const x = padding + (timeSeries.length === 1 ? chartWidth / 2 : idx * stepX);
    const y = height - padding - (pt.clicks / maxClicks) * chartHeight;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Draw Data Points
  timeSeries.forEach((pt, idx) => {
    const x = padding + (timeSeries.length === 1 ? chartWidth / 2 : idx * stepX);
    const y = height - padding - (pt.clicks / maxClicks) * chartHeight;
    ctx.fillStyle = '#6366f1';
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Date label
    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(pt.date_or_hour.slice(-5), x, height - 10);
  });
}

// Export CSV Trigger
exportCsvBtn.addEventListener('click', async () => {
  if (!state.currentAnalyticsCode) return;
  try {
    exportCsvBtn.disabled = true;
    exportCsvBtn.textContent = 'Generating CSV...';
    const blob = await apiRequest(`/api/v1/analytics/urls/${encodeURIComponent(state.currentAnalyticsCode)}/export`, 'GET', null, true);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analytics_${state.currentAnalyticsCode}_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    showToast('CSV export downloaded! 📊');
  } catch (err) {
    showToast(`Export failed: ${err.message}`);
  } finally {
    exportCsvBtn.disabled = false;
    exportCsvBtn.textContent = 'Export CSV Spreadsheet';
  }
});

// -------------------------------------------------------------
// Close Modals
// -------------------------------------------------------------
document.querySelectorAll('.modal-close, .modal-overlay').forEach(el => {
  el.addEventListener('click', (e) => {
    if (e.target === el) {
      document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
    }
  });
});

// -------------------------------------------------------------
// Initialization
// -------------------------------------------------------------
window.addEventListener('DOMContentLoaded', () => {
  updateAuthUI();
  pollSystemHealth();
  setInterval(pollSystemHealth, 20000);
});
