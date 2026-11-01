/**
 * LinkScale Platform — High-Performance Dashboard Logic
 * Linear / Vercel Level Frontend Craftsmanship
 */

// Application State
const state = {
  token: localStorage.getItem('linkscale_token') || null,
  user: JSON.parse(localStorage.getItem('linkscale_user') || 'null'),
  urls: [],
  currentAnalyticsCode: null,
  currentTimeSeries: [],
};

// DOM Elements
const authBtn = document.getElementById('authBtn');
const authModal = document.getElementById('authModal');
const authForm = document.getElementById('authForm');
const authToggleLink = document.getElementById('authToggleLink');
const authSubmitBtn = document.getElementById('authSubmitBtn');
const authModalTitle = document.getElementById('authModalTitle');

const shortenForm = document.getElementById('shortenForm');
const shortenSubmitBtn = document.getElementById('shortenSubmitBtn');
const urlInput = document.getElementById('urlInput');
const pasteBtn = document.getElementById('pasteBtn');
const optionsToggle = document.getElementById('optionsToggle');
const optionsDrawer = document.getElementById('optionsDrawer');

const resultCard = document.getElementById('resultCard');
const shortUrlLink = document.getElementById('shortUrlLink');
const copyBtn = document.getElementById('copyBtn');
const openQrModalBtn = document.getElementById('openQrModalBtn');
const openResultLinkBtn = document.getElementById('openResultLinkBtn');

const qrModal = document.getElementById('qrModal');
const qrImg = document.getElementById('qrImg');
const qrDownloadBtn = document.getElementById('qrDownloadBtn');

const analyticsModal = document.getElementById('analyticsModal');
const analyticsModalTitle = document.getElementById('analyticsModalTitle');
const exportCsvBtn = document.getElementById('exportCsvBtn');

const urlsTableBody = document.getElementById('urlsTableBody');
const toastEl = document.getElementById('toast');
const systemStatusPill = document.getElementById('systemStatusPill');
const themeToggleBtn = document.getElementById('themeToggleBtn');

// UTM Builder Elements
const utmSourceInput = document.getElementById('utmSource');
const utmMediumInput = document.getElementById('utmMedium');
const utmCampaignInput = document.getElementById('utmCampaign');
const utmPreviewText = document.getElementById('utmPreviewText');
const clearUtmBtn = document.getElementById('clearUtmBtn');
const utmPresetPills = document.querySelectorAll('.utm-preset-pill[data-source]');

let isRegisterMode = false;

// -------------------------------------------------------------
// 1. Theme Management (Light / Dark with localStorage & media query)
// -------------------------------------------------------------
function initTheme() {
  const savedTheme = localStorage.getItem('linkscale_theme');
  if (savedTheme) {
    document.documentElement.setAttribute('data-theme', savedTheme);
  } else {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
}

if (themeToggleBtn) {
  themeToggleBtn.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', nextTheme);
    localStorage.setItem('linkscale_theme', nextTheme);
    showToast(`Switched to ${nextTheme} theme`);
    
    if (updateAmbientTheme) updateAmbientTheme();

    // Redraw chart if analytics modal is open
    if (state.currentAnalyticsCode && analyticsModal.classList.contains('active')) {
      drawClickTimelineChart(state.currentTimeSeries || []);
    }
  });
}

initTheme();

// -------------------------------------------------------------
// 2. Animated Ambient Aurora & Interactive Canvas Environment
// -------------------------------------------------------------
let updateAmbientTheme = null;

function initAmbientBackground() {
  const canvas = document.getElementById('ambientCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let width = 0;
  let height = 0;
  let dpr = 1;

  // Mouse Parallax & Reactive Spring
  const mouse = { x: -1000, y: -1000, targetX: 0, targetY: 0, currentX: 0, currentY: 0 };

  window.addEventListener('mousemove', (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
    // Normalize coordinates for subtle organic parallax
    mouse.targetX = (e.clientX / (width || 1) - 0.5) * 50;
    mouse.targetY = (e.clientY / (height || 1) - 0.5) * 35;
  }, { passive: true });

  window.addEventListener('mouseleave', () => {
    mouse.x = -1000;
    mouse.y = -1000;
    mouse.targetX = 0;
    mouse.targetY = 0;
  });

  // Aurora Nebula Orbs Configuration
  const orbs = [
    { baseX: 0.22, baseY: 0.16, rMin: 340, rMax: 500, speedX: 0.00045, speedY: 0.00035, phaseX: 0, phaseY: 1.2, parallax: 0.8, colorDark: [16, 185, 129, 0.16], colorLight: [16, 185, 129, 0.07] },
    { baseX: 0.74, baseY: 0.20, rMin: 360, rMax: 540, speedX: 0.00038, speedY: 0.00042, phaseX: 2.1, phaseY: 0.5, parallax: 1.1, colorDark: [110, 231, 183, 0.13], colorLight: [110, 231, 183, 0.06] },
    { baseX: 0.48, baseY: 0.38, rMin: 290, rMax: 440, speedX: 0.00052, speedY: 0.00048, phaseX: 4.2, phaseY: 3.1, parallax: 0.6, colorDark: [45, 212, 191, 0.12], colorLight: [45, 212, 191, 0.05] },
    { baseX: 0.82, baseY: 0.62, rMin: 310, rMax: 480, speedX: 0.00032, speedY: 0.00030, phaseX: 1.5, phaseY: 4.5, parallax: 0.4, colorDark: [5, 150, 105, 0.11], colorLight: [5, 150, 105, 0.05] }
  ];

  // Ambient Floating Stardust Particles
  const PARTICLE_COUNT = 34;
  const particles = [];

  function initParticles() {
    particles.length = 0;
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push({
        x: Math.random() * (width || window.innerWidth),
        y: Math.random() * (height || window.innerHeight),
        vx: (Math.random() - 0.5) * 0.22,
        vy: -0.12 - Math.random() * 0.32,
        baseRadius: 1 + Math.random() * 1.4,
        alpha: 0.2 + Math.random() * 0.45,
        phase: Math.random() * Math.PI * 2,
        speed: 0.008 + Math.random() * 0.012
      });
    }
  }

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);
    if (particles.length === 0) {
      initParticles();
    }
  }

  resize();
  window.addEventListener('resize', resize, { passive: true });

  let animFrameId = null;
  let isRunning = true;

  function render(time) {
    if (!isRunning) return;

    // Smooth mouse parallax damping
    mouse.currentX += (mouse.targetX - mouse.currentX) * 0.05;
    mouse.currentY += (mouse.targetY - mouse.currentY) * 0.05;

    const isLight = document.documentElement.getAttribute('data-theme') === 'light';

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Ethereal blending: screen in dark mode for soft glowing nebula layers
    ctx.globalCompositeOperation = isLight ? 'source-over' : 'screen';

    // 1. Draw Aurora Orbs
    for (let i = 0; i < orbs.length; i++) {
      const orb = orbs[i];
      const ox = width * orb.baseX + Math.sin(time * orb.speedX + orb.phaseX) * (width * 0.07) + mouse.currentX * orb.parallax;
      const oy = height * orb.baseY + Math.cos(time * orb.speedY + orb.phaseY) * (height * 0.07) + mouse.currentY * orb.parallax;
      const r = orb.rMin + (Math.sin(time * 0.0006 + orb.phaseX) * 0.5 + 0.5) * (orb.rMax - orb.rMin);

      const color = isLight ? orb.colorLight : orb.colorDark;
      const grad = ctx.createRadialGradient(ox, oy, 0, ox, oy, Math.max(r, 10));
      grad.addColorStop(0, `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${color[3]})`);
      grad.addColorStop(0.55, `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${color[3] * 0.4})`);
      grad.addColorStop(1, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0)`);

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(ox, oy, r, 0, Math.PI * 2);
      ctx.fill();
    }

    // 2. Draw Dust Particles & Proximity Connections
    ctx.globalCompositeOperation = 'source-over';
    const pColor = isLight ? '5, 150, 105' : '110, 231, 183';
    const maxConnDist = 95;

    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];

      // Drift & shimmer
      p.x += p.vx;
      p.y += p.vy;
      p.phase += p.speed;

      // Mouse repulsion aura
      if (mouse.x > 0 && mouse.y > 0) {
        const dx = p.x - mouse.x;
        const dy = p.y - mouse.y;
        const dist = Math.hypot(dx, dy);
        if (dist < 110 && dist > 1) {
          const force = ((110 - dist) / 110) * 1.1;
          p.x += (dx / dist) * force;
          p.y += (dy / dist) * force;
        }
      }

      // Edge wrap
      if (p.x < -10) p.x = width + 10;
      if (p.x > width + 10) p.x = -10;
      if (p.y < -10) p.y = height + 10;
      if (p.y > height + 10) p.y = -10;

      // Pulse alpha
      const currentAlpha = Math.max(0.08, p.alpha * (0.7 + 0.3 * Math.sin(p.phase)));

      // Draw particle
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.baseRadius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${pColor}, ${currentAlpha})`;
      ctx.fill();

      // Proximity network connections
      for (let j = i + 1; j < particles.length; j++) {
        const p2 = particles[j];
        const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
        if (dist < maxConnDist) {
          const lineAlpha = (1 - dist / maxConnDist) * 0.12 * (isLight ? 0.6 : 1);
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = `rgba(${pColor}, ${lineAlpha})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }
    }

    if (!prefersReduced) {
      animFrameId = requestAnimationFrame(render);
    }
  }

  // Handle visibility change (pause when tab hidden to preserve GPU/battery)
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      isRunning = false;
      if (animFrameId) cancelAnimationFrame(animFrameId);
    } else {
      if (!isRunning && !prefersReduced) {
        isRunning = true;
        animFrameId = requestAnimationFrame(render);
      }
    }
  });

  updateAmbientTheme = () => {
    if (prefersReduced) {
      render(1000);
    }
  };

  animFrameId = requestAnimationFrame(render);
}

initAmbientBackground();

// -------------------------------------------------------------
// 3. Spotlight Cursor Follower
// -------------------------------------------------------------
document.querySelectorAll('.spotlight-card').forEach(card => {
  card.addEventListener('mousemove', (e) => {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    card.style.setProperty('--mouse-x', `${x}px`);
    card.style.setProperty('--mouse-y', `${y}px`);
  });
});

// -------------------------------------------------------------
// 4. Toast Notifications
// -------------------------------------------------------------
let toastTimer = null;
function showToast(message, duration = 3000) {
  if (!toastEl) return;
  toastEl.textContent = message;
  toastEl.classList.add('show');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toastEl.classList.remove('show');
  }, duration);
}

// -------------------------------------------------------------
// 4. API Request Helper
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
// 5. System Health Telemetry Poll
// -------------------------------------------------------------
async function pollSystemHealth() {
  if (!systemStatusPill) return;
  try {
    const res = await fetch('/health');
    const data = await res.json();
    if (data.status === 'healthy') {
      const dbLatency = data.dependencies?.database?.latency_ms || 1.2;
      systemStatusPill.innerHTML = `<span class="status-dot"></span> Online (${dbLatency}ms)`;
    } else {
      systemStatusPill.innerHTML = `<span class="status-dot" style="background:var(--warning)"></span> Degraded`;
    }
  } catch (err) {
    systemStatusPill.innerHTML = `<span class="status-dot" style="background:var(--danger)"></span> Offline`;
  }
}

// -------------------------------------------------------------
// 6. Keyboard Shortcut (Cmd+K / Ctrl+K) & Paste Helper
// -------------------------------------------------------------
window.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    if (urlInput) {
      urlInput.focus();
      urlInput.select();
      showToast('Focus: Paste destination link');
    }
  }
});

if (pasteBtn && urlInput) {
  pasteBtn.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        urlInput.value = text.trim();
        updateUtmPreview();
        showToast('Pasted from clipboard! 📋');
        urlInput.focus();
      }
    } catch (err) {
      urlInput.focus();
      showToast('Paste link manually or grant clipboard permission');
    }
  });
}

// -------------------------------------------------------------
// 7. UTM Campaign Builder
// -------------------------------------------------------------
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
  const base = urlInput ? urlInput.value.trim() : '';
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
if (urlInput) urlInput.addEventListener('input', updateUtmPreview);

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
// 8. Advanced Options Accordion
// -------------------------------------------------------------
if (optionsToggle && optionsDrawer) {
  optionsToggle.addEventListener('click', () => {
    const isOpen = optionsDrawer.classList.toggle('open');
    optionsToggle.classList.toggle('open', isOpen);
    optionsToggle.setAttribute('aria-expanded', isOpen);
  });
}

// -------------------------------------------------------------
// 9. Shorten URL Submission Workflow
// -------------------------------------------------------------
shortenForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  let originalUrl = urlInput.value.trim();
  if (!originalUrl) return;

  if (!state.token) {
    showToast('Please sign in or create an account to shorten links 🔒');
    if (authModal) authModal.classList.add('active');
    return;
  }

  // Auto-prepend https:// if protocol is omitted
  if (!originalUrl.startsWith('http://') && !originalUrl.startsWith('https://')) {
    originalUrl = `https://${originalUrl}`;
    urlInput.value = originalUrl;
  }

  // Merge UTM tags if provided
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

  const submitBtn = shortenSubmitBtn || shortenForm.querySelector('button[type="submit"]');

  try {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `
      <div class="spinner" style="width: 18px; height: 18px; border-width: 2px;"></div>
      <span>Shortening...</span>
    `;

    const data = await apiRequest('/api/v1/urls/', 'POST', payload);

    // Display Result Card
    shortUrlLink.href = data.short_url;
    shortUrlLink.textContent = data.short_url;
    if (openResultLinkBtn) openResultLinkBtn.href = data.short_url;
    resultCard.classList.add('active');

    // Update Result Badges
    const badgesContainer = document.getElementById('resultBadges');
    badgesContainer.innerHTML = '';
    if (data.is_one_time) {
      badgesContainer.innerHTML += `<span class="badge badge-burner">🔥 One-Time Burner</span>`;
    }
    if (data.is_password_protected) {
      badgesContainer.innerHTML += `<span class="badge badge-secure">🔒 Locked</span>`;
    }
    badgesContainer.innerHTML += `<span class="badge badge-info">${data.redirect_http_code} Redirect</span>`;

    // Store code for QR button
    resultCard.dataset.code = data.custom_alias || data.short_code;

    showToast('Short URL generated! ⚡');
    if (state.token) {
      loadUserUrls();
    }
  } catch (err) {
    showToast(`Failed: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
      <span class="btn-text">Shorten URL</span>
      <svg class="btn-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="5" y1="12" x2="19" y2="12"></line>
        <polyline points="12 5 19 12 12 19"></polyline>
      </svg>
    `;
  }
});

// -------------------------------------------------------------
// 10. Copy Button Morphing Micro-Interaction
// -------------------------------------------------------------
copyBtn.addEventListener('click', () => {
  const url = shortUrlLink.textContent;
  if (!url) return;
  navigator.clipboard.writeText(url).then(() => {
    copyBtn.innerHTML = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
      <span>Copied!</span>
    `;
    copyBtn.classList.add('btn-copied');
    showToast('Link copied to clipboard! 📋');

    setTimeout(() => {
      copyBtn.innerHTML = `
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        <span>Copy</span>
      `;
      copyBtn.classList.remove('btn-copied');
    }, 2000);
  });
});

// QR Code Preview from Result Card
openQrModalBtn.addEventListener('click', () => {
  const code = resultCard.dataset.code;
  if (code) openQrModal(code);
});

// -------------------------------------------------------------
// 11. QR Code Modal
// -------------------------------------------------------------
function openQrModal(code) {
  qrImg.src = `/api/v1/urls/${encodeURIComponent(code)}/qr`;
  qrDownloadBtn.onclick = () => {
    const a = document.createElement('a');
    a.href = qrImg.src;
    a.download = `qr_${code}.png`;
    a.click();
    showToast('QR Code downloaded! 📱');
  };
  qrModal.classList.add('active');
}

// -------------------------------------------------------------
// 12. Load & Render User URLs Table with Rich Empty State
// -------------------------------------------------------------
async function loadUserUrls() {
  if (!state.token) {
    renderUrlsTable([]);
    return;
  }
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
        <td colspan="4">
          <div class="empty-state-box">
            <div class="empty-icon-wrap">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
              </svg>
            </div>
            <h3>${state.token ? 'No Shortened Links Yet' : 'Sign in to Manage & Track Your Links'}</h3>
            <p>${state.token ? 'Shorten your first destination URL above to start logging visitor analytics.' : 'Create a free account to view your click logs, geographic breakdown, and export CSV spreadsheets.'}</p>
            ${!state.token ? `<button class="btn-primary" onclick="authBtn.click()">Sign In / Register</button>` : ''}
          </div>
        </td>
      </tr>
    `;
    return;
  }

  urlsTableBody.innerHTML = urls.map(u => {
    const code = u.custom_alias || u.short_code;
    const dest = u.original_url;
    const clicks = u.click_count || 0;
    const isBurner = u.is_one_time ? '<span class="badge badge-burner" style="margin-left:0.35rem">Burner</span>' : '';
    const isPwd = u.is_password_protected ? '<span class="badge badge-secure" style="margin-left:0.35rem">Locked</span>' : '';

    return `
      <tr>
        <td>
          <div style="display:flex; align-items:center;">
            <a href="/${code}" target="_blank" class="table-code-link">/${code}</a>
            ${isBurner}
            ${isPwd}
          </div>
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
// 13. Delete Short Link
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
// 14. Analytics Modal & Emerald Canvas Chart
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
  if (countriesListEl) countriesListEl.innerHTML = '<span style="color:var(--text-dim)">Loading...</span>';
  devicesListEl.innerHTML = '<span style="color:var(--text-dim)">Loading...</span>';
  browsersListEl.innerHTML = '<span style="color:var(--text-dim)">Loading...</span>';

  try {
    const data = await apiRequest(`/api/v1/analytics/urls/${encodeURIComponent(code)}`);

    totalClicksEl.textContent = data.total_clicks || 0;
    uniqueVisitorsEl.textContent = data.unique_visitors || 0;
    botClicksEl.textContent = data.bot_clicks || 0;
    state.currentTimeSeries = data.time_series || [];

    // Draw Emerald Line Chart on Canvas
    drawClickTimelineChart(state.currentTimeSeries);

    // Render Countries Breakdown
    if (countriesListEl) {
      if (data.countries && data.countries.length > 0) {
        countriesListEl.innerHTML = data.countries.map(c => `
          <div>
            <div class="breakdown-row">
              <span>${c.category}</span>
              <span style="font-weight:600; font-family:var(--font-mono)">${c.count} (${c.percentage}%)</span>
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
            <span style="font-weight:600; font-family:var(--font-mono)">${d.count} (${d.percentage}%)</span>
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
            <span style="font-weight:600; font-family:var(--font-mono)">${b.count} (${b.percentage}%)</span>
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

// High-Performance Emerald HTML5 Canvas Chart Renderer
function drawClickTimelineChart(timeSeries) {
  const canvas = document.getElementById('clicksChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const width = (canvas.width = canvas.parentElement.clientWidth);
  const height = (canvas.height = 180);

  ctx.clearRect(0, 0, width, height);

  const isLight = document.documentElement.getAttribute('data-theme') === 'light';

  if (!timeSeries || timeSeries.length === 0) {
    ctx.fillStyle = isLight ? '#525C55' : '#8A918D';
    ctx.font = '13px Inter, sans-serif';
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
  ctx.strokeStyle = isLight ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.05)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i <= 3; i++) {
    const y = padding + (chartHeight / 3) * i;
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
  }
  ctx.stroke();

  // Emerald Area Gradient Fill
  const gradient = ctx.createLinearGradient(0, padding, 0, height - padding);
  gradient.addColorStop(0, 'rgba(34, 197, 94, 0.35)');
  gradient.addColorStop(1, 'rgba(34, 197, 94, 0.0)');

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

  // Draw Emerald Line
  ctx.strokeStyle = '#22C55E';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  timeSeries.forEach((pt, idx) => {
    const x = padding + (timeSeries.length === 1 ? chartWidth / 2 : idx * stepX);
    const y = height - padding - (pt.clicks / maxClicks) * chartHeight;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Draw Glowing Data Points
  timeSeries.forEach((pt, idx) => {
    const x = padding + (timeSeries.length === 1 ? chartWidth / 2 : idx * stepX);
    const y = height - padding - (pt.clicks / maxClicks) * chartHeight;
    ctx.fillStyle = '#4ADE80';
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = isLight ? '#ffffff' : '#050706';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Date/Hour label
    ctx.fillStyle = isLight ? '#525C55' : '#8A918D';
    ctx.font = '10px JetBrains Mono, monospace';
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
    exportCsvBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
      </svg>
      Export CSV Spreadsheet
    `;
  }
});

// -------------------------------------------------------------
// 15. Authentication Workflow
// -------------------------------------------------------------
function updateAuthUI() {
  if (state.token && state.user) {
    authBtn.innerHTML = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
        <circle cx="12" cy="7" r="4"></circle>
      </svg>
      <span>${state.user.username} (Logout)</span>
    `;
    authBtn.classList.add('logged-in');
    loadUserUrls();
  } else {
    authBtn.innerHTML = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
        <polyline points="10 17 15 12 10 7"></polyline>
        <line x1="15" y1="12" x2="3" y2="12"></line>
      </svg>
      <span>Sign In</span>
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
    authModalTitle.textContent = 'Create an Account';
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
    authSubmitBtn.textContent = 'Authenticating...';

    if (isRegisterMode) {
      await apiRequest('/api/v1/auth/register', 'POST', {
        username,
        password,
        email: email || `${username}@example.com`,
      });
      showToast('Registration successful! Signing you in...');
    }

    const loginRes = await apiRequest('/api/v1/auth/login', 'POST', { username, password });
    state.token = loginRes.access_token;

    const meRes = await apiRequest('/api/v1/auth/me');
    state.user = meRes;

    localStorage.setItem('linkscale_token', state.token);
    localStorage.setItem('linkscale_user', JSON.stringify(state.user));

    authModal.classList.remove('active');
    updateAuthUI();
    showToast(`Welcome back, ${username}! 👋`);
    if (urlInput && urlInput.value.trim()) {
      shortenForm.requestSubmit();
    }
  } catch (err) {
    showToast(`Error: ${err.message}`);
  } finally {
    authSubmitBtn.disabled = false;
    authSubmitBtn.textContent = isRegisterMode ? 'Register' : 'Sign In';
  }
});

// -------------------------------------------------------------
// 16. Modal Dismissal
// -------------------------------------------------------------
document.querySelectorAll('.modal-close, .modal-overlay').forEach(el => {
  el.addEventListener('click', (e) => {
    if (e.target === el) {
      document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
    }
  });
});

// -------------------------------------------------------------
// 17. Initialization
// -------------------------------------------------------------
window.addEventListener('DOMContentLoaded', () => {
  updateAuthUI();
  pollSystemHealth();
  setInterval(pollSystemHealth, 20000);
});
