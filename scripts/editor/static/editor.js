/* Quality Updates Editor — main JS */
(function () {
  'use strict';

  let currentFile = null;
  let originalContent = null;
  let linksData = [];   // [{date, title, url, state, pdf_path, agency, line_index}]
  let pdfFiles = [];

  // ── Bootstrap ──────────────────────────────────────────────────────────────
  async function init() {
    await loadConfig();
    await populateFileSelect();
    await loadPdfFiles();
    document.getElementById('file-select').addEventListener('change', onFileChange);
    document.getElementById('btn-save').addEventListener('click', onSave);
    document.getElementById('btn-change-folder').addEventListener('click', onChangeFolder);
    setupDivider();
  }

  async function loadConfig() {
    const cfg = await fetchJSON('/api/config');
    document.getElementById('dl-folder-display').textContent = '다운로드 폴더: ' + cfg.downloads_folder;
    if (cfg.last_file) {
      currentFile = cfg.last_file;
    }
  }

  async function populateFileSelect() {
    const files = await fetchJSON('/api/files');
    const sel = document.getElementById('file-select');
    files.forEach(f => {
      const opt = document.createElement('option');
      opt.value = f;
      opt.textContent = f.split('/').slice(-1)[0];
      sel.appendChild(opt);
    });
    if (currentFile) {
      sel.value = currentFile;
      await loadLinks(currentFile);
    }
  }

  async function loadPdfFiles() {
    pdfFiles = await fetchJSON('/api/downloads');
  }

  // ── Events ──────────────────────────────────────────────────────────────────
  async function onFileChange(e) {
    currentFile = e.target.value;
    if (currentFile) await loadLinks(currentFile);
  }

  async function onSave() {
    if (!currentFile) return alert('파일을 선택하세요.');
    const curation = linksData
      .filter(l => l.state !== 'done')
      .map(l => ({
        title: l.title,
        line_index: l.line_index,
        state: l.state,
        pdf_path: l.pdf_path || null,
      }));
    const res = await fetch('/api/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file: currentFile, curation }),
    });
    if (res.ok) alert('저장 완료');
    else alert('저장 실패');
  }

  async function onChangeFolder() {
    const folder = prompt('다운로드 폴더 경로 (예: downloads/ 또는 C:/Users/me/Downloads)');
    if (!folder) return;
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ downloads_folder: folder }),
    });
    document.getElementById('dl-folder-display').textContent = '다운로드 폴더: ' + folder;
    await loadPdfFiles();
    renderTable();
  }

  // ── Data loading ────────────────────────────────────────────────────────────
  async function loadLinks(file) {
    const data = await fetchJSON(`/api/links?file=${encodeURIComponent(file)}`);
    linksData = data.links;
    originalContent = data.content;
    renderTable();
    updateCounter();
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  function renderTable() {
    const tbody = document.getElementById('link-tbody');
    tbody.innerHTML = '';
    let lastAgency = null;

    linksData.forEach((link, idx) => {
      // Section header row
      if (link.agency !== lastAgency) {
        lastAgency = link.agency;
        const hdr = document.createElement('tr');
        hdr.className = 'section-header';
        const td = document.createElement('td');
        td.colSpan = 5;
        td.textContent = link.agency || '기타';
        hdr.appendChild(td);
        tbody.appendChild(hdr);
      }

      const tr = document.createElement('tr');
      tr.dataset.idx = idx;
      tr.className = stateClass(link.state);

      tr.innerHTML = `
        <td>${link.date}</td>
        <td><span class="title-link" data-url="${escHtml(link.url)}">${escHtml(link.title)}</span></td>
        <td>${link.agency || ''}</td>
        <td>${stateBadge(link, idx)}</td>
        <td>${pdfDropdown(link, idx)}</td>
      `;

      // Title click → preview
      tr.querySelector('.title-link').addEventListener('click', () => openPreview(link.url));

      // State badge click (not done)
      if (link.state !== 'done') {
        tr.querySelector('.state-badge').addEventListener('click', () => cycleState(idx));
      }

      // PDF dropdown change
      const sel = tr.querySelector('.pdf-select');
      if (sel) {
        sel.addEventListener('change', e => {
          linksData[idx].pdf_path = e.target.value || null;
          if (e.target.value) linksData[idx].state = 'needs_summary';
          updateCounter();
          reRenderRow(tr, idx);
        });
      }

      tbody.appendChild(tr);
    });
  }

  function reRenderRow(tr, idx) {
    const link = linksData[idx];
    tr.className = stateClass(link.state);
    tr.querySelector('td:nth-child(4)').innerHTML = stateBadge(link, idx);
    if (link.state !== 'done') {
      tr.querySelector('.state-badge').addEventListener('click', () => cycleState(idx));
    }
  }

  function stateClass(state) {
    return { undecided: '', needs_summary: 'state-needs', skip: 'state-skip', done: 'state-done' }[state] || '';
  }

  function stateBadge(link, idx) {
    const labels = { undecided: '미결정', needs_summary: '요약 필요', skip: '스킵', done: '완료' };
    const cls = { undecided: 'badge-undecided', needs_summary: 'badge-needs', skip: 'badge-skip', done: 'badge-done' };
    return `<span class="state-badge ${cls[link.state]}" data-idx="${idx}">${labels[link.state]}</span>`;
  }

  function pdfDropdown(link, idx) {
    if (link.state === 'done') return '';
    if (pdfFiles.length === 0) return '<span style="color:#aaa">폴더 없음</span>';
    const selected = link.pdf_path || '';
    const options = ['<option value="">선택 안 함</option>',
      ...pdfFiles.map(f => `<option value="${escHtml(f)}"${f === selected ? ' selected' : ''}>${f.split(/[\\/]/).pop()}</option>`)
    ].join('');
    return `<select class="pdf-select" data-idx="${idx}">${options}</select>`;
  }

  // ── State cycling ────────────────────────────────────────────────────────────
  const STATE_CYCLE = ['undecided', 'needs_summary', 'skip'];

  function cycleState(idx) {
    const link = linksData[idx];
    const cur = STATE_CYCLE.indexOf(link.state);
    link.state = STATE_CYCLE[(cur + 1) % STATE_CYCLE.length];
    if (link.state !== 'needs_summary') link.pdf_path = null;
    updateCounter();
    renderTable(); // simple full re-render
  }

  // ── Counter ──────────────────────────────────────────────────────────────────
  function updateCounter() {
    const counts = { total: linksData.length, needs_summary: 0, skip: 0, undecided: 0, done: 0 };
    linksData.forEach(l => { counts[l.state] = (counts[l.state] || 0) + 1; });
    document.getElementById('cnt-total').textContent = counts.total;
    document.getElementById('cnt-needs').textContent = counts.needs_summary;
    document.getElementById('cnt-skip').textContent = counts.skip;
    document.getElementById('cnt-undecided').textContent = counts.undecided;
    document.getElementById('cnt-done').textContent = counts.done;
  }

  // ── Preview (iframe + fallback) ──────────────────────────────────────────────
  function openPreview(url) {
    const iframe = document.getElementById('preview-iframe');
    const fallback = document.getElementById('iframe-fallback');
    const fallbackLink = document.getElementById('fallback-link');

    fallback.style.display = 'none';
    iframe.style.display = 'block';
    iframe.src = url;
    fallbackLink.href = url;

    iframe.onload = () => {
      try {
        const doc = iframe.contentDocument;
        if (doc && doc.body && doc.body.innerHTML === '') showFallback(url);
      } catch (e) {
        showFallback(url);
      }
    };
    iframe.onerror = () => showFallback(url);

    setTimeout(() => {
      try {
        const doc = iframe.contentDocument;
        if (doc && doc.body && doc.body.innerHTML === '') showFallback(url);
      } catch (e) {
        showFallback(url);
      }
    }, 3000);
  }

  function showFallback(url) {
    document.getElementById('preview-iframe').style.display = 'none';
    const fallback = document.getElementById('iframe-fallback');
    fallback.style.display = 'block';
    document.getElementById('fallback-link').href = url;
  }

  // ── Divider drag ─────────────────────────────────────────────────────────────
  function setupDivider() {
    const divider = document.getElementById('divider');
    const left = document.getElementById('left-panel');
    let dragging = false;

    divider.addEventListener('mousedown', () => { dragging = true; });
    document.addEventListener('mousemove', e => {
      if (!dragging) return;
      const main = document.getElementById('main');
      const rect = main.getBoundingClientRect();
      const pct = Math.min(80, Math.max(20, ((e.clientX - rect.left) / rect.width) * 100));
      left.style.width = pct + '%';
    });
    document.addEventListener('mouseup', () => { dragging = false; });
  }

  // ── Utils ────────────────────────────────────────────────────────────────────
  async function fetchJSON(url) {
    const res = await fetch(url);
    return res.json();
  }

  function escHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Start ────────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);
})();
