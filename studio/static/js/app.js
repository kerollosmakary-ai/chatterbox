'use strict';

// ── State ────────────────────────────────────────────────────────────────────
const state = {
  sources: [],
  sel: new Set(),           // selected source IDs
  activeTab: 'summary',
  docCache: {},             // tab -> markdown string
  podcast: null,
  pollTimer: null,
};

// ── API ──────────────────────────────────────────────────────────────────────
const api = {
  async req(method, path, body, isForm = false) {
    const opts = { method, headers: {} };
    if (body && !isForm) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    } else if (body) {
      opts.body = body;
    }
    const r = await fetch(`/api${path}`, opts);
    if (!r.ok) {
      const e = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(e.detail || 'Request failed');
    }
    return r.json();
  },
  sources:         ()       => api.req('GET',    '/sources'),
  deleteSource:    id       => api.req('DELETE', `/sources/${id}`),
  importUrl:       url      => api.req('POST',   '/sources/url',   { url }),
  uploadFile:      file     => { const f = new FormData(); f.append('file', file); return api.req('POST', '/sources/upload', f, true); },
  generateDoc:     (ids, t) => api.req('POST',   '/generate/document', { source_ids: ids, doc_type: t }),
  generatePodcast: (ids, t) => api.req('POST',   '/generate/podcast',  { source_ids: ids, title: t }),
  getPodcast:      id       => api.req('GET',    `/podcasts/${id}`),
  getSettings:     ()       => api.req('GET',    '/settings'),
  saveSettings:    data     => api.req('POST',   '/settings', data),
};

// ── Toasts ───────────────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  document.querySelectorAll('.toast').forEach(t => t.remove());
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => {
    el.classList.add('out');
    setTimeout(() => el.remove(), 300);
  }, 3400);
}

// ── Button helpers ───────────────────────────────────────────────────────────
function btnBusy(id, busy, label) {
  const b = document.getElementById(id);
  if (!b) return;
  if (busy) { b._saved = b.textContent; b.textContent = label || 'Loading…'; b.disabled = true; }
  else      { b.textContent = b._saved || label; b.disabled = false; }
}

// ── Sources ──────────────────────────────────────────────────────────────────
function renderSources() {
  const list = document.getElementById('sources-list');
  const ctr  = document.getElementById('source-counter');

  if (!state.sources.length) {
    list.innerHTML = `<div class="empty-state">
      <div class="empty-icon">📂</div><p>No sources yet</p>
      <p class="hint">Upload files or add a URL</p></div>`;
    ctr.textContent = '';
    return;
  }

  ctr.textContent = state.sources.length;

  list.innerHTML = state.sources.map(s => {
    const isSel = state.sel.has(s.id);
    const icon  = s.type === 'url' ? '🌐' : '📄';
    const meta  = s.char_count > 1000 ? `${(s.char_count/1000).toFixed(1)}k chars` : `${s.char_count} chars`;
    return `<div class="source-item${isSel ? ' sel' : ''}" onclick="toggleSrc('${s.id}')">
      <div class="src-check">${isSel ? '✓' : ''}</div>
      <div class="src-info">
        <span class="src-name">${icon} ${esc(s.name)}</span>
        <span class="src-meta">${meta}</span>
      </div>
      <button class="src-del" onclick="delSrc(event,'${s.id}')" title="Remove">×</button>
    </div>`;
  }).join('');
}

function toggleSrc(id) {
  state.sel.has(id) ? state.sel.delete(id) : state.sel.add(id);
  renderSources();
  syncBtns();
}

function syncBtns() {
  const has = state.sel.size > 0;
  document.getElementById('generate-doc-btn').disabled     = !has;
  document.getElementById('generate-podcast-btn').disabled = !has;
}

async function loadSources() {
  try {
    state.sources = await api.sources();
    renderSources();
    syncBtns();
  } catch (e) { toast('Could not load sources', 'error'); }
}

async function uploadFiles(files) {
  for (const f of files) {
    toast(`Uploading ${f.name}…`);
    try {
      const s = await api.uploadFile(f);
      state.sources.push(s);
      state.sel.add(s.id);
      renderSources(); syncBtns();
      toast(`✓ ${f.name} added`, 'success');
    } catch (e) { toast(`Upload failed: ${e.message}`, 'error'); }
  }
}

async function delSrc(ev, id) {
  ev.stopPropagation();
  try {
    await api.deleteSource(id);
    state.sources = state.sources.filter(s => s.id !== id);
    state.sel.delete(id);
    renderSources(); syncBtns();
  } catch (e) { toast(`Delete failed: ${e.message}`, 'error'); }
}

// ── URL dialog ───────────────────────────────────────────────────────────────
function openUrlDialog()  { modal('url-dialog', true);  $('url-input').focus(); }
function closeUrlDialog() { modal('url-dialog', false); $('url-input').value = ''; }

async function importUrl() {
  const url = $('url-input').value.trim();
  if (!url) return;
  btnBusy('url-import-btn', true, 'Fetching…');
  try {
    const s = await api.importUrl(url);
    state.sources.push(s);
    state.sel.add(s.id);
    renderSources(); syncBtns();
    closeUrlDialog();
    toast(`✓ "${s.name}" added`, 'success');
  } catch (e) { toast(`Import failed: ${e.message}`, 'error'); }
  finally     { btnBusy('url-import-btn', false, 'Import'); }
}

// ── Document generation ──────────────────────────────────────────────────────
function switchTab(type) {
  state.activeTab = type;
  document.querySelectorAll('.doc-tab').forEach(t =>
    t.classList.toggle('active', t.dataset.type === type));

  if (state.docCache[type]) {
    showDoc(state.docCache[type]);
  } else {
    $('document-content').innerHTML = `<div class="empty-state">
      <div class="empty-icon">✨</div>
      <p>Click <strong>Generate</strong> to create a ${tabLabel(type)}</p></div>`;
    $('copy-btn').style.display = 'none';
  }
}

async function generateDocument() {
  const ids = [...state.sel];
  if (!ids.length) { toast('Select at least one source', 'error'); return; }

  btnBusy('generate-doc-btn', true, '✨ Generating…');
  $('copy-btn').style.display = 'none';
  $('document-content').innerHTML =
    '<div class="loading-box"><div class="spinner"></div><p>Generating with AI…</p></div>';

  try {
    const doc = await api.generateDoc(ids, state.activeTab);
    state.docCache[state.activeTab] = doc.content;
    showDoc(doc.content);
    toast(`✓ ${tabLabel(state.activeTab)} ready`, 'success');
  } catch (e) {
    $('document-content').innerHTML = `<div class="error-box">${esc(e.message)}</div>`;
    toast(e.message, 'error');
  } finally {
    btnBusy('generate-doc-btn', false, '✨ Generate');
  }
}

function showDoc(md) {
  $('document-content').innerHTML = `<div class="md">${marked.parse(md)}</div>`;
  $('copy-btn').style.display = '';
}

function copyContent() {
  const md = state.docCache[state.activeTab];
  if (!md) return;
  navigator.clipboard.writeText(md).then(() => toast('✓ Copied to clipboard', 'success'));
}

// ── Podcast generation ───────────────────────────────────────────────────────
async function generatePodcast() {
  const ids = [...state.sel];
  if (!ids.length) { toast('Select at least one source', 'error'); return; }

  btnBusy('generate-podcast-btn', true, '🎙️ Generating…');
  $('podcast-area').innerHTML =
    '<div class="loading-box" style="padding:20px"><div class="spinner sm"></div><p>Writing script &amp; rendering audio…</p></div>';

  try {
    const srcName = state.sources.find(s => ids.includes(s.id))?.name || 'AI Overview';
    const p = await api.generatePodcast(ids, srcName);
    state.podcast = p;
    renderPodcast(p);
    if (!p.audio_ready) startPoll(p.id);
  } catch (e) {
    $('podcast-area').innerHTML = `<div class="error-box">${esc(e.message)}</div>`;
    toast(e.message, 'error');
  } finally {
    btnBusy('generate-podcast-btn', false, 'Generate Podcast');
  }
}

function renderPodcast(p) {
  const audioHtml = p.audio_ready
    ? `<audio class="audio-player" controls>
         <source src="${p.audio_path}" type="audio/mpeg">
       </audio>`
    : p.error
      ? `<div class="error-box" style="margin-bottom:10px">Audio error: ${esc(p.error)}</div>`
      : `<div class="audio-pending"><div class="spinner sm"></div> Rendering audio… (may take a minute)</div>`;

  $('podcast-area').innerHTML = `
    <div class="podcast-card">
      <div class="podcast-meta-row">
        <span class="podcast-emoji">🎙️</span>
        <div>
          <div class="podcast-title">${esc(p.title)}</div>
          <div class="podcast-sub">${p.source_ids.length} source${p.source_ids.length > 1 ? 's' : ''}</div>
        </div>
      </div>
      ${audioHtml}
      <details class="script-toggle">
        <summary>View script</summary>
        <div class="script-body">${fmtScript(p.script)}</div>
      </details>
    </div>`;
}

function fmtScript(script) {
  if (!script) return '';
  return script.trim().split('\n').map(line => {
    if (/^HOST1:/i.test(line)) {
      return `<div class="script-line"><span class="host-badge h1">Alex</span>${esc(line.slice(6).trim())}</div>`;
    }
    if (/^HOST2:/i.test(line)) {
      return `<div class="script-line"><span class="host-badge h2">Sam</span>${esc(line.slice(6).trim())}</div>`;
    }
    return '';
  }).join('');
}

function startPoll(pid) {
  if (state.pollTimer) clearInterval(state.pollTimer);
  let ticks = 0;
  state.pollTimer = setInterval(async () => {
    ticks++;
    if (ticks > 80) { clearInterval(state.pollTimer); return; }  // 4 min timeout
    try {
      const p = await api.getPodcast(pid);
      if (p.audio_ready || p.error) {
        clearInterval(state.pollTimer);
        state.podcast = p;
        renderPodcast(p);
        if (p.audio_ready) toast('🎙️ Podcast audio ready!', 'success');
        else               toast(`Audio error: ${p.error}`, 'error');
      }
    } catch (_) {}
  }, 3000);
}

// ── Settings ─────────────────────────────────────────────────────────────────
const MODEL_MAP = {
  anthropic:  ['claude-opus-4-8', 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001'],
  openai:     ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  groq:       ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768'],
  openrouter: ['anthropic/claude-opus-4-8', 'openai/gpt-4o', 'meta-llama/llama-3.3-70b-instruct'],
};

function populateModels(provider, current) {
  const sel = $('settings-model');
  sel.innerHTML = (MODEL_MAP[provider] || []).map(m =>
    `<option value="${m}"${m === current ? ' selected' : ''}>${m}</option>`).join('');
}

async function openSettings() {
  try {
    const s = await api.getSettings();
    $('settings-provider').value = s.provider;
    $('settings-api-key').placeholder = s.api_key ? '(key set — paste to replace)' : 'Paste your API key…';
    populateModels(s.provider, s.model);
    $('settings-voice-h1').value = s.tts_voice_host1 || 'en-US-GuyNeural';
    $('settings-voice-h2').value = s.tts_voice_host2 || 'en-US-JennyNeural';
  } catch (e) { toast('Could not load settings', 'error'); }
  modal('settings-modal', true);
}

function closeSettings() { modal('settings-modal', false); }

async function saveSettings() {
  const provider = $('settings-provider').value;
  const apiKey   = $('settings-api-key').value.trim();
  const model    = $('settings-model').value;
  const h1       = $('settings-voice-h1').value;
  const h2       = $('settings-voice-h2').value;

  const data = { provider, model, tts_voice_host1: h1, tts_voice_host2: h2 };
  if (apiKey) data.api_key = apiKey;

  btnBusy('save-settings-btn', true, 'Saving…');
  try {
    await api.saveSettings(data);
    closeSettings();
    toast('✓ Settings saved', 'success');
  } catch (e) { toast(`Save failed: ${e.message}`, 'error'); }
  finally     { btnBusy('save-settings-btn', false, 'Save'); }
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function $(id)      { return document.getElementById(id); }
function modal(id, show) { $(id).classList.toggle('hidden', !show); }

function tabLabel(t) {
  return { summary:'Summary', keypoints:'Key Points', studyguide:'Study Guide', faq:'FAQ' }[t] || t;
}

// ── Drag & drop ───────────────────────────────────────────────────────────────
function setupDnD() {
  const sb = $('sidebar');
  sb.addEventListener('dragover',  e => { e.preventDefault(); sb.classList.add('drag-over'); });
  sb.addEventListener('dragleave', e => { if (!sb.contains(e.relatedTarget)) sb.classList.remove('drag-over'); });
  sb.addEventListener('drop', e => {
    e.preventDefault(); sb.classList.remove('drag-over');
    const files = [...e.dataTransfer.files];
    if (files.length) uploadFiles(files);
  });
}

// ── Init ──────────────────────────────────────────────────────────────────────
function init() {
  // File input
  $('file-input').addEventListener('change', e => {
    uploadFiles([...e.target.files]);
    e.target.value = '';
  });

  // Tab buttons
  document.querySelectorAll('.doc-tab').forEach(btn =>
    btn.addEventListener('click', () => switchTab(btn.dataset.type)));

  // Provider → model list
  $('settings-provider').addEventListener('change', e =>
    populateModels(e.target.value, ''));

  // URL dialog keyboard shortcuts
  $('url-input').addEventListener('keydown', e => {
    if (e.key === 'Enter')  importUrl();
    if (e.key === 'Escape') closeUrlDialog();
  });

  // Close modals on backdrop click
  document.querySelectorAll('.modal').forEach(m =>
    m.addEventListener('click', e => { if (e.target === m) m.classList.add('hidden'); }));

  setupDnD();
  loadSources();
  syncBtns();

  // Configure marked
  marked.setOptions({ breaks: true, gfm: true });
}

document.addEventListener('DOMContentLoaded', init);
