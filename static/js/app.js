/**
 * YT Storm - Frontend Application
 */

// ─── State ────────────────────────────────────────────────────────────────────
let currentTab = 'single';
let selQuality = '720';
let jobs = {};
let pollTimer = null;
let currentPage = 'download';

// ─── Init ─────────────────────────────────────────────────────────────────────
window.onload = async () => {
  const res = await fetch('/default_dir');
  const d = await res.json();
  document.getElementById('out-dir').value = d.dir;
  document.getElementById('sb-dir').textContent = d.dir;
  startPolling();
  initDragDrop();
  initSubtitleToggle();
};

// ─── Navigation ───────────────────────────────────────────────────────────────
function navTo(page, el) {
  currentPage = page;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
}

// ─── Mode Tabs ────────────────────────────────────────────────────────────────
function switchTab(t, el) {
  currentTab = t;
  document.querySelectorAll('.mode-tab').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.dl-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + t).classList.add('active');
}

// ─── Quality ──────────────────────────────────────────────────────────────────
function selQ(el, quality) {
  document.querySelectorAll('.q-btn').forEach(p => p.classList.remove('sel'));
  el.classList.add('sel');
  selQuality = quality;
}

// ─── Start download ───────────────────────────────────────────────────────────
async function startDownload() {
  const btn = document.getElementById('dl-btn');
  const outDir = document.getElementById('out-dir').value.trim();
  let urls = [];

  if (currentTab === 'single') {
    const u = document.getElementById('single-url').value.trim();
    if (!u) return toast('URL boş olamaz!', 'err');
    urls = [u];
  } else if (currentTab === 'bulk') {
    const raw = document.getElementById('bulk-urls').value.trim();
    if (!raw) return toast('URL listesi boş!', 'err');
    urls = raw.split('\n').map(s => s.trim()).filter(Boolean);
    if (!urls.length) return toast('Geçerli URL bulunamadı.', 'err');
  } else {
    const u = document.getElementById('playlist-url').value.trim();
    if (!u) return toast('Playlist URL boş olamaz!', 'err');
    urls = [u];
  }

  const downloadSubs = document.getElementById('download-subs')?.checked || false;
  const subLang = document.getElementById('subtitle-lang')?.value?.trim() || 'tr,en';
  
  const payload = {
    urls,
    quality: selQuality,
    out_dir: outDir,
    is_playlist: currentTab === 'playlist',
    pl_start: document.getElementById('pl-start')?.value?.trim() || '',
    pl_end: document.getElementById('pl-end')?.value?.trim() || '',
    download_subtitles: downloadSubs,
    subtitle_lang: subLang,
  };

  btn.disabled = true;
  document.getElementById('dl-status').textContent = 'Kuyruğa ekleniyor…';

  try {
    const res = await fetch('/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const d = await res.json();
    if (d.ok) {
      toast(`${urls.length} indirme kuyruğa eklendi`, 'ok');
      document.getElementById('single-url').value = '';
      document.getElementById('bulk-urls').value = '';
      document.getElementById('playlist-url').value = '';
      // Auto-switch to queue page
      const queueNav = document.querySelectorAll('.nav-item')[1];
      navTo('queue', queueNav);
    } else {
      toast('Hata: ' + d.error, 'err');
    }
  } catch(e) { toast('Sunucuya bağlanılamadı.', 'err'); }

  btn.disabled = false;
  document.getElementById('dl-status').textContent = '';
}

// ─── Open folder ──────────────────────────────────────────────────────────────
async function openFolder() {
  const dir = document.getElementById('out-dir').value.trim();
  await fetch('/open_folder', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({dir}) });
}

// ─── Clear done ───────────────────────────────────────────────────────────────
async function clearDone() {
  await fetch('/clear_done', { method:'POST' });
}

// ─── Polling ──────────────────────────────────────────────────────────────────
function startPolling() {
  pollTimer = setInterval(fetchJobs, 1200);
  fetchJobs();
}

async function fetchJobs() {
  try {
    const res = await fetch('/jobs');
    const data = await res.json();
    jobs = data.jobs;
    renderJobs();
    updateStats();
  } catch(e) {}
}

// ─── Render jobs ──────────────────────────────────────────────────────────────
function renderJobs() {
  const container = document.getElementById('jobs-container');
  const ids = Object.keys(jobs);

  if (!ids.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⬇</div>
        <div class="empty-title">Kuyruk boş</div>
        <div class="empty-sub">İndirme eklemek için sol menüden başlayın</div>
      </div>`;
    return;
  }

  ids.sort((a,b) => {
    const order = {running:0, queued:1, done:2, error:3};
    return (order[jobs[a].status]||9) - (order[jobs[b].status]||9);
  });

  container.innerHTML = ids.map(id => {
    const j = jobs[id];
    const pct = j.progress || 0;
    const logHtml = (j.logs || []).slice(-12).map(l => {
      let cls = '';
      if (l.includes('ERROR') || l.includes('Hata')) cls = 'log-err';
      else if (l.includes('✅') || l.includes('Tamamlandı')) cls = 'log-ok';
      else if (l.includes('[download]') || l.includes('[info]')) cls = 'log-info';
      return `<span class="${cls}">${escHtml(l)}</span>`;
    }).join('\n');

    return `
    <div class="job-item ${j.status}">
      <div class="job-top">
        <div class="job-indicator ${j.status}"></div>
        <div class="job-name">${escHtml(j.title || id)}</div>
        <span class="job-chip chip-${j.status}">${labelOf(j.status)}</span>
      </div>
      ${j.status === 'running' || pct > 0 ? `
        <div class="job-progress">
          <div class="prog-track"><div class="prog-fill" style="width:${pct}%"></div></div>
          <span class="prog-pct">${pct}%</span>
        </div>` : ''}
      ${logHtml ? `<div class="job-log">${logHtml}</div>` : ''}
    </div>`;
  }).join('');

  document.querySelectorAll('.job-log').forEach(b => { b.scrollTop = b.scrollHeight; });
}

function labelOf(s) {
  return {running:'İNDİRİLİYOR', done:'TAMAM', error:'HATA', queued:'BEKLIYOR'}[s] || s;
}
function escHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// ─── Stats ────────────────────────────────────────────────────────────────────
function updateStats() {
  const vals = Object.values(jobs);
  document.getElementById('s-total').textContent   = vals.length;
  document.getElementById('s-running').textContent = vals.filter(j=>j.status==='running').length;
  document.getElementById('s-done').textContent    = vals.filter(j=>j.status==='done').length;
  document.getElementById('s-err').textContent     = vals.filter(j=>j.status==='error').length;
}

// ─── Toast ────────────────────────────────────────────────────────────────────
let toastTimer;
function toast(msg, type='ok') {
  const el = document.getElementById('toast');
  document.getElementById('toast-icon').textContent = type === 'ok' ? '✓' : '✕';
  document.getElementById('toast-msg').textContent = msg;
  el.className = 'show ' + type;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.className = '', 3200);
}

// ─── Drag & Drop ──────────────────────────────────────────────────────────────
function initDragDrop() {
  const dropZone = document.getElementById('drop-zone');
  if (!dropZone) return;
  
  // Prevent default drag behaviors
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
  });
  
  // Highlight drop zone
  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.add('drag-over'), false);
  });
  
  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.remove('drag-over'), false);
  });
  
  // Handle drop
  dropZone.addEventListener('drop', handleDrop, false);
  
  // Click to paste from clipboard
  dropZone.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && isValidUrl(text)) {
        document.getElementById('single-url').value = text.trim();
        toast('URL yapıştırıldı!', 'ok');
        previewVideo();
      }
    } catch(e) {
      // Clipboard access denied
    }
  });
}

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

function handleDrop(e) {
  const dt = e.dataTransfer;
  const text = dt.getData('text/plain') || dt.getData('text/uri-list');
  
  if (text && isValidUrl(text)) {
    document.getElementById('single-url').value = text.trim();
    toast('URL eklendi!', 'ok');
    previewVideo();
  } else {
    toast('Geçerli bir URL değil', 'err');
  }
}

function isValidUrl(string) {
  try {
    const url = new URL(string);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch (_) {
    return false;
  }
}

// ─── Video Preview ────────────────────────────────────────────────────────────
let previewTimeout;

function onUrlChange(value) {
  clearTimeout(previewTimeout);
  if (value && isValidUrl(value)) {
    previewTimeout = setTimeout(() => previewVideo(), 500);
  }
}

async function previewVideo() {
  const url = document.getElementById('single-url').value.trim();
  if (!url || !isValidUrl(url)) return;
  
  const container = document.getElementById('video-preview');
  const loading = container.querySelector('.preview-loading');
  const content = container.querySelector('.preview-content');
  
  container.classList.remove('hidden');
  loading.classList.remove('hidden');
  content.classList.add('hidden');
  
  try {
    const res = await fetch('/preview', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url})
    });
    const data = await res.json();
    
    if (data.ok && data.preview) {
      const p = data.preview;
      
      document.getElementById('preview-thumb').src = p.thumbnail || '';
      document.getElementById('preview-title').textContent = p.title;
      document.getElementById('preview-channel').textContent = p.channel;
      document.getElementById('preview-duration').textContent = p.duration_string || formatDuration(p.duration);
      document.getElementById('preview-views').textContent = formatViews(p.view_count);
      
      // Subtitles info
      const subsEl = document.getElementById('preview-subs');
      const subsTextEl = document.getElementById('preview-subs-text');
      if (p.subtitles && p.subtitles.length > 0) {
        subsEl.classList.remove('hidden');
        subsTextEl.textContent = `Altyazı: ${p.subtitles.slice(0, 5).join(', ')}${p.subtitles.length > 5 ? '...' : ''}`;
      } else {
        subsEl.classList.add('hidden');
      }
      
      loading.classList.add('hidden');
      content.classList.remove('hidden');
    } else {
      closePreview();
      toast(data.error || 'Önizleme yüklenemedi', 'err');
    }
  } catch(e) {
    closePreview();
    toast('Önizleme hatası', 'err');
  }
}

function closePreview() {
  document.getElementById('video-preview').classList.add('hidden');
}

function formatDuration(seconds) {
  if (!seconds) return '';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
  return `${m}:${s.toString().padStart(2,'0')}`;
}

function formatViews(count) {
  if (!count) return '';
  if (count >= 1000000) return (count / 1000000).toFixed(1) + 'M görüntüleme';
  if (count >= 1000) return (count / 1000).toFixed(1) + 'K görüntüleme';
  return count + ' görüntüleme';
}

// ─── Subtitle Toggle ──────────────────────────────────────────────────────────
function initSubtitleToggle() {
  const checkbox = document.getElementById('download-subs');
  const langWrapper = document.getElementById('subtitle-lang-wrapper');
  
  if (checkbox && langWrapper) {
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) {
        langWrapper.classList.remove('hidden');
      } else {
        langWrapper.classList.add('hidden');
      }
    });
  }
}

// ─── History ──────────────────────────────────────────────────────────────────
let historyLimit = 20;
let currentHistoryOffset = 0;
let totalHistoryCount = 0;
let historySearchTimeout;

async function loadHistory(offset = 0) {
  const search = document.getElementById('history-search')?.value || '';
  currentHistoryOffset = Math.max(0, offset);
  
  try {
    const params = new URLSearchParams({
      limit: historyLimit,
      offset: currentHistoryOffset,
      search: search
    });
    
    const res = await fetch(`/history?${params}`);
    const data = await res.json();
    
    if (data.ok) {
      totalHistoryCount = data.total;
      renderHistory(data.downloads);
      updatePagination();
    }
  } catch(e) {
    console.error('History load error:', e);
  }
}

function renderHistory(downloads) {
  const container = document.getElementById('history-container');
  
  if (!downloads || downloads.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📚</div>
        <div class="empty-title">Henüz indirme yok</div>
        <div class="empty-sub">İndirmeleriniz burada görünecek</div>
      </div>`;
    return;
  }
  
  container.innerHTML = downloads.map(d => `
    <div class="history-item" data-id="${d.id}">
      <img class="history-thumb" src="${d.thumbnail || ''}" alt="" onerror="this.style.display='none'" />
      <div class="history-info">
        <div class="history-title">${escHtml(d.title || d.url)}</div>
        <div class="history-meta">
          <span>${d.channel || ''}</span>
          <span>${d.quality || ''}</span>
          <span class="history-status ${d.status}">${d.status === 'completed' ? '✓ Başarılı' : '✗ Başarısız'}</span>
          <span>${formatDate(d.downloaded_at)}</span>
        </div>
      </div>
      <div class="history-actions-item">
        <button class="history-btn" onclick="redownload('${escHtml(d.url)}')" title="Tekrar İndir">🔄</button>
        <button class="history-btn delete" onclick="deleteHistoryItem(${d.id})" title="Sil">🗑</button>
      </div>
    </div>
  `).join('');
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('tr-TR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function updatePagination() {
  const pagination = document.getElementById('history-pagination');
  const pageInfo = document.getElementById('history-page-info');
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  
  const totalPages = Math.ceil(totalHistoryCount / historyLimit);
  const currentPage = Math.floor(currentHistoryOffset / historyLimit) + 1;
  
  if (totalPages <= 1) {
    pagination.classList.add('hidden');
    return;
  }
  
  pagination.classList.remove('hidden');
  pageInfo.textContent = `${currentPage} / ${totalPages}`;
  prevBtn.disabled = currentHistoryOffset === 0;
  nextBtn.disabled = currentHistoryOffset + historyLimit >= totalHistoryCount;
}

function searchHistory() {
  clearTimeout(historySearchTimeout);
  historySearchTimeout = setTimeout(() => {
    loadHistory(0);
  }, 300);
}

async function deleteHistoryItem(id) {
  try {
    const res = await fetch(`/history/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.ok) {
      toast('Kayıt silindi', 'ok');
      loadHistory(currentHistoryOffset);
      loadHistoryStats();
    }
  } catch(e) {
    toast('Silme hatası', 'err');
  }
}

async function clearAllHistory() {
  if (!confirm('Tüm indirme geçmişi silinecek. Emin misiniz?')) return;
  
  try {
    const res = await fetch('/history/clear', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      toast(`${data.cleared} kayıt silindi`, 'ok');
      loadHistory(0);
      loadHistoryStats();
    }
  } catch(e) {
    toast('Temizleme hatası', 'err');
  }
}

async function loadHistoryStats() {
  try {
    const res = await fetch('/history/stats');
    const data = await res.json();
    if (data.ok && data.stats) {
      document.getElementById('stat-total').textContent = data.stats.total;
      document.getElementById('stat-completed').textContent = data.stats.completed;
      document.getElementById('stat-failed').textContent = data.stats.failed;
      document.getElementById('stat-size').textContent = data.stats.total_size_formatted;
    }
  } catch(e) {}
}

function redownload(url) {
  document.getElementById('single-url').value = url;
  navTo('download', document.querySelector('.nav-item'));
  toast('URL eklendi, indirmeyi başlatabilirsiniz', 'ok');
}

// ─── Settings ─────────────────────────────────────────────────────────────────
let settingsLoaded = false;

async function loadSettings() {
  if (settingsLoaded) return;
  
  try {
    const res = await fetch('/settings');
    const data = await res.json();
    
    if (data.ok && data.settings) {
      const s = data.settings;
      
      // Apply settings to form elements
      setSelectValue('setting-theme', s.theme);
      setSelectValue('setting-default_quality', s.default_quality);
      setSelectValue('setting-concurrent_downloads', s.concurrent_downloads);
      setCheckbox('setting-download_subtitles', s.download_subtitles);
      setInputValue('setting-subtitle_lang', s.subtitle_lang);
      setInputValue('setting-proxy', s.proxy);
      setCheckbox('setting-auto_preview', s.auto_preview);
      setCheckbox('setting-notifications', s.notifications);
      
      // Apply default quality to download page
      if (s.default_quality) {
        selQuality = s.default_quality;
      }
      
      settingsLoaded = true;
    }
  } catch(e) {
    console.error('Settings load error:', e);
  }
}

function setSelectValue(id, value) {
  const el = document.getElementById(id);
  if (el && value !== undefined) el.value = value;
}

function setCheckbox(id, checked) {
  const el = document.getElementById(id);
  if (el) el.checked = !!checked;
}

function setInputValue(id, value) {
  const el = document.getElementById(id);
  if (el) el.value = value || '';
}

async function saveSetting(key, value) {
  try {
    await fetch(`/settings/${key}`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ value })
    });
    toast('Ayar kaydedildi', 'ok');
  } catch(e) {
    toast('Kaydetme hatası', 'err');
  }
}

// ─── Navigation Enhancement ───────────────────────────────────────────────────
const originalNavTo = navTo;
navTo = function(page, el) {
  originalNavTo(page, el);
  
  // Load page-specific data
  if (page === 'history') {
    loadHistory(0);
    loadHistoryStats();
  } else if (page === 'settings') {
    loadSettings();
  }
}
