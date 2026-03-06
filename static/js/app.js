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

  const payload = {
    urls,
    quality: selQuality,
    out_dir: outDir,
    is_playlist: currentTab === 'playlist',
    pl_start: document.getElementById('pl-start')?.value?.trim() || '',
    pl_end: document.getElementById('pl-end')?.value?.trim() || '',
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
