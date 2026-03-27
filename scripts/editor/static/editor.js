/* Quality Updates Editor — main JS */
(function () {
  'use strict';

  let currentFile = null;
  let originalContent = null;
  let isSaving = false;
  let lastSavedDigest = '';
  let autoSaveTimer = null;
  const AUTO_SAVE_INTERVAL_MS = 60 * 1000;
  // Each link:
  // - source: null | { type: 'pdf'|'web'|'clip', ref: string }
  // - pdf_path: kept for backward-compatible save payload (derived from source when type==='pdf')
  // sourcePanel: 'pdf'|'web'|'clip' — editor-only; which SOURCE tab is shown (not sent to API).
  // clipDraft: optional string — unsaved CLIP textarea (not sent to API).
  let linksData = [];   // [{date, title, url, state, source, pdf_path, sourcePanel, clipDraft?, agency, line_index}]
  let pdfFiles = [];    // string[] (Option A)
  let lastPdfFilesLoadedAt = 0;
  let pdfFilesInputDebounceTimer = null;
  let pdfFilesInputDebounceSeq = 0;

  const RECENTS_KEY_PDF = 'quality-updates-editor:recentSources:pdf';
  const MAX_RECENTS = 10;
  const MAX_RESULTS_RENDERED = 12;

  // Dropdown state (single-open at a time)
  let openPicker = null; // { idx, rootEl, inputEl, listEl, activeIndex, items: [{path, kind:'recent'|'result'}] }

  // ── Toast (download saved 등) ──────────────────────────────────────────────
  let toastHideTimer = null;

  function ensureToastEl() {
    let el = document.getElementById('editor-toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'editor-toast';
      el.setAttribute('role', 'status');
      el.setAttribute('aria-live', 'polite');
      document.body.appendChild(el);
    }
    return el;
  }

  function showToast(text) {
    const el = ensureToastEl();
    el.textContent = text;
    el.classList.add('is-visible');
    if (toastHideTimer) clearTimeout(toastHideTimer);
    toastHideTimer = setTimeout(() => {
      el.classList.remove('is-visible');
      toastHideTimer = null;
    }, 1000);
  }

  /** save_fetched(구 save_pdf) / kasb_file — JSON만 사용 (한글 메시지 UTF-8). */
  async function runSaveByPath(path, opts) {
    const clearIframeOnSuccess = opts && opts.clearIframeOnSuccess;
    try {
      const r = await fetch(path, {
        headers: { Accept: 'application/json' },
        credentials: 'same-origin',
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok || data.ok === false) {
        showToast(data.message || ('오류 (' + r.status + ')'));
        return;
      }
      showToast(data.message || '저장됨');
      if (clearIframeOnSuccess) {
        const iframe = document.getElementById('preview-iframe');
        iframe.src = 'about:blank';
      }
      await loadPdfFiles();
      renderTable();
    } catch (_) {
      showToast('저장 요청 실패');
    }
  }

  function setupParentSaveMessageListener() {
    window.addEventListener('message', (e) => {
      if (e.origin !== window.location.origin) return;
      const d = e.data;
      if (!d || d.type !== 'quality-updates-fetch-save' || !d.path) return;
      runSaveByPath(String(d.path), { clearIframeOnSuccess: true });
    });
  }

  function wireIframeDelegatedSaveClicks(iframe) {
    try {
      const doc = iframe.contentDocument;
      if (!doc || !doc.documentElement) return;
      if (doc.documentElement.dataset.editorSaveDelegate === '1') return;
      doc.documentElement.dataset.editorSaveDelegate = '1';
      doc.addEventListener('click', onIframeSaveLinkClick, true);
    } catch (_) { /* cross-origin */ }
  }

  function onIframeSaveLinkClick(ev) {
    const a = ev.target.closest('a');
    if (!a || !a.href) return;
    let u;
    try {
      u = new URL(a.href, window.location.origin);
    } catch (_) {
      return;
    }
    if (u.origin !== window.location.origin) return;
    const p = u.pathname || '';
    if (p !== '/api/source/kasb_file' && p !== '/api/source/save_pdf' && p !== '/api/source/save_fetched') return;
    ev.preventDefault();
    ev.stopPropagation();
    runSaveByPath(u.pathname + u.search, { clearIframeOnSuccess: false });
  }

  // ── Bootstrap ──────────────────────────────────────────────────────────────
  async function init() {
    setupParentSaveMessageListener();
    await loadConfig();
    await populateFileSelect();
    await loadPdfFiles();
    document.getElementById('file-select').addEventListener('change', onFileChange);
    document.getElementById('btn-save').addEventListener('click', onSave);
    document.getElementById('btn-export-md').addEventListener('click', onExportToMd);
    document.getElementById('btn-import-md').addEventListener('click', onImportFromMd);
    document.getElementById('btn-change-folder').addEventListener('click', onChangeFolder);
    document.getElementById('btn-clear-downloads').addEventListener('click', onClearDownloads);
    setupDivider();
    startAutoSave();
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
    if (currentFile && files.includes(currentFile)) {
      sel.value = currentFile;
      await loadLinks(currentFile);
      return;
    }
    // Stale config (deleted/moved file or test fixture path): keep UI usable.
    if (currentFile && !files.includes(currentFile)) {
      currentFile = null;
      try {
        await fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ last_file: '' }),
        });
      } catch (_) {
        // Non-fatal; selection remains available.
      }
    }
  }

  async function loadPdfFiles() {
    pdfFiles = await fetchJSON('/api/downloads');
    lastPdfFilesLoadedAt = Date.now();
  }

  async function ensureFreshPdfFiles(force) {
    const shouldRefresh = !!force || (Date.now() - lastPdfFilesLoadedAt > 15000);
    if (!shouldRefresh) return;
    try {
      await loadPdfFiles();
    } catch (_) {
      // Keep existing list on transient failures.
    }
  }

  // ── Events ──────────────────────────────────────────────────────────────────
  async function onFileChange(e) {
    currentFile = e.target.value;
    if (currentFile) await loadLinks(currentFile);
  }

  function hasResolvedWebSource(entry) {
    const s = entry.source;
    return !!(s && s.type === 'web' && String(s.ref || '').trim());
  }

  function hasResolvedShotSource(entry) {
    const s = entry.source;
    return !!(s && s.type === 'shot' && String(s.ref || '').trim());
  }

  function hasResolvedClipSource(entry) {
    const s = entry.source;
    return !!(s && s.type === 'clip' && String(s.ref || '').trim());
  }

  /** needs_summary rows that still need a PDF path (WEB/CLIP with ref counts as resolved). */
  function isUnresolvedNeedsPdf(entry) {
    if (entry.state !== 'needs_summary') return false;
    if (hasResolvedWebSource(entry)) return false;
    if (hasResolvedShotSource(entry)) return false;
    if (hasResolvedClipSource(entry)) return false;
    const pdfRef =
      entry.pdf_path ||
      (entry.source && entry.source.type === 'pdf' ? entry.source.ref : null);
    return !pdfRef;
  }

  async function onSave() {
    const result = await saveCurrentFile({ isAuto: false });
    if (!result.ok) return;
    // Disk content changed; refresh line_index before alerting success.
    try {
      await loadLinks(currentFile);
    } catch (e) {
      alert(
        '파일은 저장되었지만 목록을 다시 불러오지 못했습니다. 페이지를 새로고침(F5)하세요.\n' +
          (e && e.message ? e.message : String(e))
      );
      return;
    }
    alert('저장 완료');
  }

  function startAutoSave() {
    if (autoSaveTimer) clearInterval(autoSaveTimer);
    autoSaveTimer = setInterval(() => {
      void onAutoSaveTick();
    }, AUTO_SAVE_INTERVAL_MS);
  }

  async function onAutoSaveTick() {
    if (!currentFile || isSaving) return;
    const digest = buildCurationDigest();
    if (!digest || digest === lastSavedDigest) return;
    const result = await saveCurrentFile({ isAuto: true });
    if (!result.ok) return;
    try {
      await loadLinks(currentFile);
    } catch (_) {
      // If refresh fails, keep local state; next save can retry.
    }
    showToast('자동 저장됨');
  }

  function buildCuration() {
    return linksData
      .filter(l => l.state !== 'done')
      .map(l => {
        const row = {
          title: l.title,
          line_index: Number(l.line_index),
          state: l.state,
          pdf_path: getPdfPathForSave(l),
        };
        if (l.source) row.source = l.source;
        return row;
      });
  }

  function buildCurationDigest() {
    try {
      return JSON.stringify(buildCuration());
    } catch (_) {
      return '';
    }
  }

  async function saveCurrentFile(opts) {
    const isAuto = !!(opts && opts.isAuto);
    if (!currentFile) {
      if (!isAuto) alert('파일을 선택하세요.');
      return { ok: false };
    }
    if (isSaving) return { ok: false };
    isSaving = true;

    const curation = buildCuration();
    const unresolved = curation.filter(isUnresolvedNeedsPdf);
    if (!isAuto && unresolved.length > 0) {
      const ok = confirm(`${unresolved.length}개 항목이 "요약 필요"이지만 PDF가 선택되지 않았습니다.\n저장하면 미결정으로 처리됩니다. 계속할까요?`);
      if (!ok) {
        isSaving = false;
        return { ok: false };
      }
    }
    curation.forEach((c) => {
      if (isUnresolvedNeedsPdf(c)) c.state = 'undecided';
    });

    let res;
    try {
      res = await fetch('/api/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file: currentFile, curation }),
      });
    } catch (e) {
      isSaving = false;
      const msg = '저장 요청 실패(네트워크): ' + (e && e.message ? e.message : String(e));
      if (isAuto) showToast('자동 저장 실패');
      else alert(msg);
      return { ok: false };
    }
    if (!res.ok) {
      isSaving = false;
      let detail = '';
      try {
        const err = await res.json();
        if (err && err.error) detail = String(err.error);
      } catch (_) { /* non-JSON body */ }
      if (isAuto) showToast('자동 저장 실패');
      else alert('저장 실패 (' + res.status + ')' + (detail ? '\n' + detail : ''));
      return { ok: false };
    }

    lastSavedDigest = JSON.stringify(curation);
    isSaving = false;
    return { ok: true };
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

  async function onExportToMd() {
    if (!currentFile) {
      alert('파일을 선택하세요.');
      return;
    }
    // Export uses sidecar as source of truth; persist in-memory edits first.
    const saveResult = await saveCurrentFile({ isAuto: true });
    if (!saveResult.ok) {
      alert('현재 상태를 저장하지 못해 본문 반영을 중단했습니다.');
      return;
    }
    const ok = confirm('현재 에디터 상태를 .md 본문 주석으로 반영합니다. 계속할까요?');
    if (!ok) return;
    const res = await fetch('/api/sync/export_to_md', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file: currentFile }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      alert((data && data.error) ? data.error : '본문 반영 실패');
      return;
    }
    await loadLinks(currentFile);
    alert(`본문 반영 완료 (${Number(data.written || 0)}개 상태)`);
  }

  async function onImportFromMd() {
    if (!currentFile) {
      alert('파일을 선택하세요.');
      return;
    }
    const ok = confirm('.md 본문의 주석 상태를 sidecar로 가져옵니다. 계속할까요?');
    if (!ok) return;
    const res = await fetch('/api/sync/import_from_md', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file: currentFile }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      alert((data && data.error) ? data.error : '본문 가져오기 실패');
      return;
    }
    await loadLinks(currentFile);
    alert(`본문에서 가져오기 완료 (${Number(data.imported || 0)}개 상태)`);
  }

  async function onClearDownloads() {
    const ok1 = confirm('현재 설정된 다운로드 폴더의 모든 파일을 삭제합니다.\n계속할까요?');
    if (!ok1) return;
    const token = prompt('정말 삭제하려면 DELETE 를 입력하세요.');
    if (token !== 'DELETE') {
      showToast('취소됨');
      return;
    }
    try {
      const res = await fetch('/api/downloads/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: 'DELETE' }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.ok === false) {
        showToast(data.error || ('오류 (' + res.status + ')'));
        return;
      }
      showToast(`삭제됨: ${Number(data.deleted || 0)}개`);
      await loadPdfFiles();
      renderTable();
    } catch (_) {
      showToast('삭제 요청 실패');
    }
  }

  // ── Data loading ────────────────────────────────────────────────────────────
  async function loadLinks(file) {
    const data = await fetchJSON(`/api/links?file=${encodeURIComponent(file)}`);
    linksData = (data.links || []).map(normalizeLink);
    originalContent = data.content;
    lastSavedDigest = buildCurationDigest();
    renderTable();
    updateCounter();
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  function renderTable() {
    const tbody = document.getElementById('link-tbody');
    tbody.innerHTML = '';
    let lastAgency = null;

    closeOpenPicker();

    linksData.forEach((link, idx) => {
      // Section header row
      if (link.agency !== lastAgency) {
        lastAgency = link.agency;
        const hdr = document.createElement('tr');
        hdr.className = 'section-header';
        const td = document.createElement('td');
        td.colSpan = 5;
        td.className = 'section-header-cell';
        td.textContent = link.agency || '기타';
        hdr.appendChild(td);
        tbody.appendChild(hdr);
      }

      const tr = document.createElement('tr');
      tr.dataset.idx = idx;
      tr.className = stateClass(link.state);

      tr.innerHTML = `
        <td colspan="5" class="link-row-td">
          <div class="link-row-stack">
            <div class="link-row-line1">
              <div class="cell-date">${escHtml(link.date)}</div>
              <div class="cell-title"><span class="title-link" role="link" tabindex="0" data-url="${escHtml(link.url)}">${escHtml(link.title)}</span></div>
              <div class="cell-agency">${escHtml(link.agency || '')}</div>
              <div class="cell-state">${stateBadge(link, idx)}</div>
            </div>
            <div class="link-row-line2">${sourceCell(link, idx)}</div>
          </div>
        </td>
      `;

      // Title click → preview
      const titleEl = tr.querySelector('.title-link');
      titleEl.addEventListener('click', () => openPreview(link.url));
      titleEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          openPreview(link.url);
        }
      });

      // State badge click (not done)
      if (link.state !== 'done') {
        const badge = tr.querySelector('.state-badge');
        badge.addEventListener('click', () => cycleState(idx));
        badge.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            cycleState(idx);
          }
        });
      }

      wireSourceCell(tr, idx);

      tbody.appendChild(tr);
    });
  }

  function reRenderRow(tr, idx) {
    const link = linksData[idx];
    tr.className = stateClass(link.state);
    const stateEl = tr.querySelector('.cell-state');
    if (stateEl) stateEl.innerHTML = stateBadge(link, idx);
    if (link.state !== 'done') {
      const badge = tr.querySelector('.state-badge');
      badge.addEventListener('click', () => cycleState(idx));
      badge.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          cycleState(idx);
        }
      });
    }
  }

  function stateClass(state) {
    return { undecided: '', needs_summary: 'state-needs', skip: 'state-skip', no_summary: 'state-nosummary', done: 'state-done' }[state] || '';
  }

  function stateBadge(link, idx) {
    const labels = { undecided: '미결정', needs_summary: '요약 필요', skip: '스킵', no_summary: '요약 없음', done: '완료' };
    const cls = { undecided: 'badge-undecided', needs_summary: 'badge-needs', skip: 'badge-skip', no_summary: 'badge-nosummary', done: 'badge-done' };
    return `<span class="state-badge ${cls[link.state]}" data-idx="${idx}" role="button" tabindex="0">${labels[link.state]}</span>`;
  }

  function sourceKind(link) {
    if (link.source && link.source.type === 'web') return 'web';
    if (link.source && link.source.type === 'clip') return 'clip';
    if (link.source && link.source.type === 'shot') return 'web';
    if (link.sourcePanel === 'web') return 'web';
    if (link.sourcePanel === 'clip') return 'clip';
    return 'pdf';
  }

  function sourceCell(link, idx) {
    if (link.state === 'done') return '';
    const kind = sourceKind(link);
    const shotPath = link.source && link.source.type === 'shot' ? String(link.source.ref || '').trim() : '';
    const webLinked = hasResolvedWebSource(link) || !!shotPath;
    const clipId = link.source && link.source.type === 'clip' ? String(link.source.ref || '') : '';
    const clipDraft = link.clipDraft != null ? String(link.clipDraft) : '';

    const selectedPath = link.source && link.source.type === 'pdf' ? link.source.ref : (link.pdf_path || '');
    const fileName = selectedPath ? basename(selectedPath) : '';
    const inputValue = selectedPath ? fileName : '';

    const listId = `source-list-${idx}`;
    const pdfBlock = pdfFiles.length === 0
      ? '<span class="source-no-pdf">폴더 없음</span>'
      : `
      <div class="source-picker" data-idx="${idx}">
        <div class="source-picker-top">
          <input
            class="source-input"
            type="text"
            value="${escHtml(inputValue)}"
            placeholder="PDF 검색…"
            autocomplete="off"
            role="combobox"
            aria-autocomplete="list"
            aria-expanded="false"
            aria-controls="${listId}"
          />
          <button class="source-btn source-btn-open" type="button" title="열기">▼</button>
          <button class="source-btn source-btn-clear" type="button" title="비우기"${selectedPath ? '' : ' disabled'}>×</button>
        </div>
        <div class="source-dropdown" id="${listId}" role="listbox" style="display:none"></div>
      </div>
    `;

    const clipLinked = clipId
      ? `<div class="clip-linked">연결됨: <code>${escHtml(clipId)}</code></div>`
      : '';

    const shotLinked = shotPath
      ? `<div class="shot-linked">캡쳐됨: <code>${escHtml(shotPath)}</code></div>`
      : '';

    const webSaveDisabled = !link.url;
    return `
      <div class="source-cell" data-idx="${idx}">
        <div class="source-kind-row" role="tablist" aria-label="출처 유형">
          <button type="button" class="source-tab${kind === 'pdf' ? ' is-active' : ''}" data-kind="pdf" role="tab" aria-selected="${kind === 'pdf' ? 'true' : 'false'}">PDF</button>
          <button type="button" class="source-tab${kind === 'web' ? ' is-active' : ''}" data-kind="web" role="tab" aria-selected="${kind === 'web' ? 'true' : 'false'}">WEB</button>
          <button type="button" class="source-tab${kind === 'clip' ? ' is-active' : ''}" data-kind="clip" role="tab" aria-selected="${kind === 'clip' ? 'true' : 'false'}">CLIP</button>
        </div>
        <div class="source-panel source-panel-pdf" data-panel="pdf" style="display:${kind === 'pdf' ? 'block' : 'none'}">${pdfBlock}</div>
        <div class="source-panel source-panel-web" data-panel="web" style="display:${kind === 'web' ? 'block' : 'none'}">
          <p class="web-source-hint">WEB은 표의 <strong>원문 링크</strong> 본문만 서버에서 가져와 미리보기합니다. URL을 따로 넣지 않습니다.</p>
          <div class="web-url-readonly" title="${escHtml(link.url)}">${escHtml(link.url)}</div>
          ${shotLinked}
          <div class="web-source-row">
            <button class="source-btn web-btn-preview" type="button"${link.url ? '' : ' disabled'}>미리보기/새로고침</button>
            <button class="source-btn web-btn-save-clip" type="button"${webSaveDisabled ? ' disabled' : ''}>캡쳐+OCR 저장 및 연결</button>
            <button class="source-btn web-btn-clear" type="button"${webLinked ? '' : ' disabled'}>연결 해제</button>
          </div>
        </div>
        <div class="source-panel source-panel-clip" data-panel="clip" style="display:${kind === 'clip' ? 'block' : 'none'}">
          ${clipLinked}
          <textarea class="clip-draft" placeholder="붙여넣은 텍스트…" rows="4">${escHtml(clipDraft)}</textarea>
          <div class="clip-toolbar">
            <button class="source-btn clip-btn-save" type="button"${clipDraft.trim() ? '' : ' disabled'}>저장 및 연결</button>
            <button class="source-btn clip-btn-preview" type="button"${clipId ? '' : ' disabled'}>미리보기</button>
            <button class="source-btn clip-btn-clear" type="button"${clipId ? '' : ' disabled'}>연결 해제</button>
          </div>
        </div>
      </div>
    `;
  }

  // ── State cycling ────────────────────────────────────────────────────────────
  // Toggle order preference:
  // undecided -> skip -> no_summary -> needs_summary
  const STATE_CYCLE = ['undecided', 'skip', 'no_summary', 'needs_summary'];

  function cycleState(idx) {
    const link = linksData[idx];
    const cur = STATE_CYCLE.indexOf(link.state);
    link.state = STATE_CYCLE[(cur + 1) % STATE_CYCLE.length];
    if (link.state !== 'needs_summary') {
      link.pdf_path = null;
      link.source = null;
      link.sourcePanel = 'pdf';
      link.clipDraft = null;
    }
    updateCounter();
    renderTable(); // simple full re-render
  }

  // ── Counter ──────────────────────────────────────────────────────────────────
  function updateCounter() {
    const counts = { total: linksData.length, needs_summary: 0, skip: 0, no_summary: 0, undecided: 0, done: 0 };
    linksData.forEach(l => { counts[l.state] = (counts[l.state] || 0) + 1; });
    document.getElementById('cnt-total').textContent = counts.total;
    document.getElementById('cnt-needs').textContent = counts.needs_summary;
    document.getElementById('cnt-skip').textContent = counts.skip;
    document.getElementById('cnt-no-summary').textContent = counts.no_summary;
    document.getElementById('cnt-undecided').textContent = counts.undecided;
    document.getElementById('cnt-done').textContent = counts.done;
  }

  // ── Preview (iframe + fallback) ──────────────────────────────────────────────
  let previewSeq = 0;

  function showPreviewIframe(srcUrl, onBeforeSrc) {
    previewSeq += 1;
    const seq = previewSeq;
    const iframe = document.getElementById('preview-iframe');
    const fallback = document.getElementById('iframe-fallback');

    fallback.style.display = 'none';
    iframe.style.display = 'block';
    if (typeof onBeforeSrc === 'function') {
      onBeforeSrc(iframe, seq);
    }
    iframe.src = srcUrl;
    return seq;
  }

  function openClipPreview(clipId) {
    const id = String(clipId || '').trim();
    if (!id) return;
    showPreviewIframe('/api/clips/' + encodeURIComponent(id), (iframe, s) => {
      iframe.onload = () => {
        if (s !== previewSeq) return;
        try {
          wireIframeDelegatedSaveClicks(iframe);
        } catch (_) { /* ignore */ }
      };
      iframe.onerror = null;
    });
  }

  function openPreview(url) {
    const fallbackLink = document.getElementById('fallback-link');
    fallbackLink.href = isSafeHttpUrl(url) ? url : '#';

    const seq = showPreviewIframe('/api/source/preview_fast?url=' + encodeURIComponent(url), (iframe, s) => {
      iframe.onload = () => {
        if (s !== previewSeq) return;
        try {
          wireIframeDelegatedSaveClicks(iframe);
          const doc = iframe.contentDocument;
          if (doc && doc.body && doc.body.innerHTML === '') showFallback(url);
        } catch (e) {
          showFallback(url);
        }
      };
      iframe.onerror = () => {
        if (s !== previewSeq) return;
        showFallback(url);
      };
    });

    setTimeout(() => {
      if (seq !== previewSeq) return;
      try {
        const iframe = document.getElementById('preview-iframe');
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
    document.getElementById('fallback-link').href = isSafeHttpUrl(url) ? url : '#';
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

  // ── SOURCE cell (PDF | WEB | CLIP) ───────────────────────────────────────────
  function wireSourceCell(tr, idx) {
    const cell = tr.querySelector('.source-cell');
    if (!cell) return;

    cell.querySelectorAll('.source-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        const kind = tab.getAttribute('data-kind');
        if (kind === 'pdf' || kind === 'web' || kind === 'clip') setSourceKind(idx, kind);
      });
    });

    const webPreview = cell.querySelector('.web-btn-preview');
    const webSaveClip = cell.querySelector('.web-btn-save-clip');
    const webClear = cell.querySelector('.web-btn-clear');
    if (webPreview && webSaveClip && webClear) {
      webPreview.addEventListener('click', () => {
        const u = String(linksData[idx].url || '').trim();
        if (!u) return;
        openPreview(u);
      });
      webSaveClip.addEventListener('click', async () => {
        const u = String(linksData[idx].url || '').trim();
        if (!u) return;
        webSaveClip.disabled = true;
        try {
          const res = await fetch('/api/source/web_capture_to_clip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: u }),
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok || !data || !data.id) {
            const extra = data && data.path ? `\n(스크린샷 저장: ${data.path})` : '';
            alert(((data && data.error) ? data.error : '미리보기 저장 실패') + extra);
            return;
          }
          if (data && data.path) {
            showToast(`스크린샷 저장: ${data.path}`);
          }
          const link = linksData[idx];
          // Source of record: screenshot path (stable evidence for tables).
          link.sourcePanel = 'web';
          link.source = { type: 'shot', ref: data.path };
          link.pdf_path = null;
          link.state = 'needs_summary';
          link.clipDraft = null;
          updateCounter();
          renderTable();
          // OCR 결과는 clip으로 저장되지만, source는 screenshot으로 둔다.
          // 필요 시 CLIP preview는 응답 id로 직접 열 수 있다.
          openClipPreview(data.id);
        } finally {
          // Button recreated on render; best-effort re-enable for no-render paths.
          try { webSaveClip.disabled = false; } catch (_) {}
        }
      });
      webClear.addEventListener('click', () => {
        clearWebSource(idx);
        updateCounter();
        renderTable();
      });
    }

    const clipTa = cell.querySelector('.clip-draft');
    const clipSave = cell.querySelector('.clip-btn-save');
    const clipPrev = cell.querySelector('.clip-btn-preview');
    const clipClr = cell.querySelector('.clip-btn-clear');
    if (clipTa && clipSave && clipPrev && clipClr) {
      clipTa.addEventListener('input', () => {
        linksData[idx].clipDraft = clipTa.value;
        clipSave.disabled = !String(clipTa.value || '').trim();
      });
      clipSave.addEventListener('click', async () => {
        const raw = String(clipTa.value || '').trim();
        if (!raw) return;
        const res = await fetch('/api/clips', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ raw }),
        });
        let data = null;
        try {
          data = await res.json();
        } catch (e) {
          data = null;
        }
        if (!res.ok) {
          alert((data && data.error) ? data.error : '클립 저장 실패');
          return;
        }
        const link = linksData[idx];
        link.sourcePanel = 'clip';
        link.source = { type: 'clip', ref: data.id };
        link.pdf_path = null;
        link.state = 'needs_summary';
        link.clipDraft = null;
        updateCounter();
        renderTable();
      });
      clipPrev.addEventListener('click', () => {
        const link = linksData[idx];
        const id = link.source && link.source.type === 'clip' ? String(link.source.ref || '').trim() : '';
        if (!id) return;
        openClipPreview(id);
      });
      clipClr.addEventListener('click', () => {
        clearClipSource(idx);
        updateCounter();
        renderTable();
      });
    }

    wireSourcePicker(tr, idx);
  }

  function setSourceKind(idx, kind) {
    const link = linksData[idx];
    const cur = sourceKind(link);
    if (cur === kind) return;

    link.sourcePanel = kind;

    if (kind !== 'pdf' && link.source && link.source.type === 'pdf') {
      link.source = null;
      link.pdf_path = null;
      link.state = 'undecided';
    }
    if (kind !== 'web' && link.source && link.source.type === 'web') {
      link.source = null;
      link.pdf_path = null;
      link.state = 'undecided';
    }
    if (kind !== 'clip' && link.source && link.source.type === 'clip') {
      link.source = null;
      link.pdf_path = null;
      link.state = 'undecided';
    }
    if (kind !== 'clip') {
      link.clipDraft = null;
    }
    if (kind === 'web') {
      link.sourcePanel = 'web';
      link.source = { type: 'web', ref: link.url };
      link.pdf_path = null;
      link.state = 'needs_summary';
    }
    closeOpenPicker();
    updateCounter();
    renderTable();
  }

  function clearWebSource(idx) {
    const link = linksData[idx];
    link.sourcePanel = 'web';
    link.source = null;
    link.pdf_path = null;
    link.clipDraft = null;
    link.state = 'undecided';
    closeOpenPicker();
  }

  function clearClipSource(idx) {
    const link = linksData[idx];
    link.sourcePanel = 'clip';
    link.source = null;
    link.pdf_path = null;
    link.clipDraft = null;
    link.state = 'undecided';
    closeOpenPicker();
  }

  // ── SOURCE (PDF) picker ──────────────────────────────────────────────────────
  function wireSourcePicker(tr, idx) {
    const root = tr.querySelector('.source-panel-pdf .source-picker');
    if (!root) return;

    const input = root.querySelector('.source-input');
    const btnOpen = root.querySelector('.source-btn-open');
    const btnClear = root.querySelector('.source-btn-clear');
    const list = root.querySelector('.source-dropdown');

    const link = linksData[idx];
    const selectedPath = link.source && link.source.type === 'pdf' ? link.source.ref : (link.pdf_path || '');
    input.dataset.fullPath = selectedPath || '';

    btnOpen.addEventListener('click', async () => {
      await ensureFreshPdfFiles(true);
      input.focus();
      openPdfPicker(idx, root, input, list);
    });

    btnClear.addEventListener('click', () => {
      clearPdfSource(idx);
      updateCounter();
      renderTable();
    });

    input.addEventListener('input', () => {
      // If user edits input manually, treat it as search (not a value).
      // Keep the selected full path in data-full-path until selection/clear.
      // Debounce + force refresh: new files may have been added to downloads_folder externally.
      pdfFilesInputDebounceSeq += 1;
      const seq = pdfFilesInputDebounceSeq;
      if (pdfFilesInputDebounceTimer) clearTimeout(pdfFilesInputDebounceTimer);
      pdfFilesInputDebounceTimer = setTimeout(() => {
        if (seq !== pdfFilesInputDebounceSeq) return;
        void ensureFreshPdfFiles(true).then(() => {
          // Re-open with latest pdfFiles after refresh.
          openPdfPicker(idx, root, input, list);
        });
      }, 250);
    });

    input.addEventListener('focus', () => {
      // Don't auto-open on focus; ArrowDown / button opens (spec).
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown' && !isPickerOpenFor(idx)) {
        e.preventDefault();
        void ensureFreshPdfFiles(true).then(() => {
          openPdfPicker(idx, root, input, list, { focusFirst: true });
        });
        return;
      }

      if (!isPickerOpenFor(idx)) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        closeOpenPicker();
        return;
      }

      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        moveActiveIndex(e.key === 'ArrowDown' ? 1 : -1);
        return;
      }

      if (e.key === 'Enter') {
        e.preventDefault();
        if (!openPicker || openPicker.items.length === 0) return;
        const item = openPicker.items[openPicker.activeIndex] || openPicker.items[0];
        if (item) selectPdfSource(idx, item.path);
        updateCounter();
        renderTable();
        return;
      }
    });
  }

  function openPdfPicker(idx, rootEl, inputEl, listEl, opts) {
    opts = opts || {};

    if (!openPicker || openPicker.idx !== idx) {
      closeOpenPicker();
      openPicker = {
        idx,
        rootEl,
        inputEl,
        listEl,
        activeIndex: 0,
        items: [],
      };
      document.addEventListener('mousedown', onDocMouseDown, true);
      document.addEventListener('keydown', onDocKeyDown, true);
    } else {
      openPicker.rootEl = rootEl;
      openPicker.inputEl = inputEl;
      openPicker.listEl = listEl;
    }

    const query = inputEl.value || '';
    const { sections, flatItems } = buildPdfSections(query);
    openPicker.items = flatItems;
    openPicker.activeIndex = Math.min(openPicker.activeIndex, Math.max(0, flatItems.length - 1));
    if (opts.focusFirst) openPicker.activeIndex = 0;

    renderPdfDropdown(sections);
    setComboboxExpanded(true);
    listEl.style.display = 'block';
  }

  function closeOpenPicker() {
    if (!openPicker) return;
    setComboboxExpanded(false);
    if (openPicker.listEl) openPicker.listEl.style.display = 'none';
    if (openPicker.listEl) openPicker.listEl.innerHTML = '';
    document.removeEventListener('mousedown', onDocMouseDown, true);
    document.removeEventListener('keydown', onDocKeyDown, true);
    openPicker = null;
  }

  function isPickerOpenFor(idx) {
    return !!openPicker && openPicker.idx === idx && openPicker.listEl && openPicker.listEl.style.display !== 'none';
  }

  function onDocMouseDown(e) {
    if (!openPicker) return;
    if (openPicker.rootEl && openPicker.rootEl.contains(e.target)) return;
    closeOpenPicker();
  }

  function onDocKeyDown(e) {
    // Global ESC close even if focus moved elsewhere (spec includes Esc closes)
    if (e.key === 'Escape' && openPicker) {
      closeOpenPicker();
    }
  }

  function moveActiveIndex(delta) {
    if (!openPicker) return;
    const n = openPicker.items.length;
    if (n === 0) return;
    openPicker.activeIndex = (openPicker.activeIndex + delta + n) % n;
    refreshActiveOption();
  }

  function setComboboxExpanded(expanded) {
    if (!openPicker || !openPicker.inputEl) return;
    openPicker.inputEl.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  }

  function buildPdfSections(rawQuery) {
    const query = String(rawQuery || '');
    const qNorm = normalizeForMatch(query);

    const recent = qNorm ? [] : getRecentPdfPaths();
    const results = filterAndSortPdfPaths(pdfFiles, query);

    // Avoid dupes between recent and results
    const recentSet = new Set(recent);
    const filteredResults = results.filter(p => !recentSet.has(p));

    const sections = [];
    const flatItems = [];

    const pushItems = (paths, kind) => {
      paths.forEach((p) => {
        flatItems.push({ path: p, kind });
      });
    };

    // Limit rendered options total to MAX_RESULTS_RENDERED
    let remaining = MAX_RESULTS_RENDERED;

    if (recent.length > 0) {
      const take = recent.slice(0, remaining);
      remaining -= take.length;
      sections.push({ title: '최근', kind: 'recent', items: take });
      pushItems(take, 'recent');
    }

    if (remaining > 0) {
      const take = filteredResults.slice(0, remaining);
      sections.push({ title: qNorm ? '검색 결과' : '전체', kind: 'result', items: take });
      pushItems(take, 'result');
    } else if (sections.length === 0) {
      sections.push({ title: '검색 결과', kind: 'result', items: [] });
    }

    return { sections, flatItems };
  }

  function renderPdfDropdown(sections) {
    if (!openPicker) return;
    const list = openPicker.listEl;
    if (!list) return;
    list.innerHTML = '';

    let optionIndex = 0; // index into openPicker.items

    sections.forEach((sec) => {
      const hdr = document.createElement('div');
      hdr.className = 'source-section-title';
      hdr.textContent = sec.title;
      list.appendChild(hdr);

      if (!sec.items || sec.items.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'source-empty';
        empty.textContent = '결과 없음';
        list.appendChild(empty);
        return;
      }

      sec.items.forEach((path) => {
        const myIndex = optionIndex;
        const opt = document.createElement('div');
        opt.className = 'source-option';
        opt.setAttribute('role', 'option');
        opt.dataset.optionIndex = String(myIndex);
        opt.dataset.fullPath = path;
        opt.id = `source-opt-${openPicker.idx}-${myIndex}`;

        const name = basename(path);
        opt.innerHTML = `
          <div class="source-option-main">${escHtml(name)}</div>
          <div class="source-option-sub">${escHtml(path)}</div>
        `;

        opt.addEventListener('mouseenter', () => {
          if (!openPicker) return;
          openPicker.activeIndex = myIndex;
          refreshActiveOption();
        });

        opt.addEventListener('mousedown', (e) => {
          // prevent input blur before click handler completes
          e.preventDefault();
        });

        opt.addEventListener('click', () => {
          selectPdfSource(openPicker.idx, path);
          updateCounter();
          renderTable();
        });

        list.appendChild(opt);
        optionIndex += 1;
      });
    });

    refreshActiveOption();
  }

  function refreshActiveOption() {
    if (!openPicker) return;
    const list = openPicker.listEl;
    if (!list) return;
    const opts = list.querySelectorAll('.source-option');
    opts.forEach((el) => {
      const i = Number(el.dataset.optionIndex || '0');
      const active = i === openPicker.activeIndex;
      el.classList.toggle('is-active', active);
      el.setAttribute('aria-selected', active ? 'true' : 'false');
      if (active) {
        if (openPicker && openPicker.inputEl && el.id) {
          openPicker.inputEl.setAttribute('aria-activedescendant', el.id);
        }
        // Keep active option visible
        el.scrollIntoView({ block: 'nearest' });
      }
    });
  }

  function selectPdfSource(idx, fullPath) {
    const link = linksData[idx];
    link.sourcePanel = 'pdf';
    link.source = { type: 'pdf', ref: fullPath };
    link.state = 'needs_summary';
    link.pdf_path = fullPath; // keep legacy payload behavior
    link.clipDraft = null;
    pushRecentPdfPath(fullPath);
    closeOpenPicker();
  }

  function clearPdfSource(idx) {
    const link = linksData[idx];
    link.sourcePanel = 'pdf';
    link.source = null;
    link.pdf_path = null;
    link.clipDraft = null;
    link.state = 'undecided';
    closeOpenPicker();
  }

  function getRecentPdfPaths() {
    try {
      const raw = localStorage.getItem(RECENTS_KEY_PDF);
      const arr = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(arr)) return [];
      return arr.filter((x) => typeof x === 'string' && x.trim().length > 0).slice(0, MAX_RECENTS);
    } catch (e) {
      return [];
    }
  }

  function pushRecentPdfPath(path) {
    const p = String(path || '').trim();
    if (!p) return;
    const cur = getRecentPdfPaths();
    const next = [p, ...cur.filter((x) => x !== p)].slice(0, MAX_RECENTS);
    try {
      localStorage.setItem(RECENTS_KEY_PDF, JSON.stringify(next));
    } catch (e) {
      // ignore (private mode/quota)
    }
  }

  function filterAndSortPdfPaths(paths, rawQuery) {
    const query = String(rawQuery || '');
    const qNorm = normalizeForMatch(query);
    const all = Array.isArray(paths) ? paths : [];
    if (!qNorm) return all.slice();

    const scored = [];
    for (const p of all) {
      const cand = String(p || '');
      const candNorm = normalizeForMatch(cand);
      const idx = candNorm.indexOf(qNorm);
      if (idx === -1) continue;
      const isExact = candNorm === qNorm;
      const isPrefix = idx === 0;
      scored.push({ path: cand, idx, isExact, isPrefix });
    }

    scored.sort((a, b) => {
      // exact > prefix > earlier match index > lex
      if (a.isExact !== b.isExact) return a.isExact ? -1 : 1;
      if (a.isPrefix !== b.isPrefix) return a.isPrefix ? -1 : 1;
      if (a.idx !== b.idx) return a.idx - b.idx;
      return a.path.localeCompare(b.path);
    });

    return scored.map((x) => x.path);
  }

  function normalizeForMatch(s) {
    return String(s || '')
      .toLowerCase()
      .replace(/[\s\-_]+/g, '');
  }

  function basename(p) {
    return String(p || '').split(/[\\/]/).pop() || '';
  }

  function normalizeLink(link) {
    const l = Object.assign({}, link);

    // Back-compat: if backend provides `source`, use it.
    // If not, but legacy `pdf_path` exists, treat it as PDF source.
    if (!l.source && l.pdf_path) {
      l.source = { type: 'pdf', ref: l.pdf_path };
    }
    if (l.source && l.source.type === 'pdf' && !l.pdf_path) {
      l.pdf_path = l.source.ref;
    }
    if (l.source && l.source.type === 'web') {
      l.pdf_path = null;
      l.source = { type: 'web', ref: l.url };
    }
    if (l.source && l.source.type === 'shot') {
      l.pdf_path = null;
    }
    if (l.source && l.source.type === 'clip') {
      l.pdf_path = null;
    }
    if (!l.source) l.source = null;
    if (!l.pdf_path) l.pdf_path = null;

    l.sourcePanel =
      l.source && l.source.type === 'web' ? 'web'
        : l.source && l.source.type === 'clip' ? 'clip'
          : 'pdf';

    return l;
  }

  function getPdfPathForSave(link) {
    if (!link) return null;
    if (link.source && link.source.type === 'pdf' && link.source.ref) return link.source.ref;
    return link.pdf_path || null;
  }

  // ── Utils ────────────────────────────────────────────────────────────────────
  async function fetchJSON(url) {
    const res = await fetch(url);
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`Request failed (${res.status}): ${text || url}`);
    }
    return res.json();
  }

  function escHtml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function isSafeHttpUrl(u) {
    try {
      const url = new URL(String(u || ''), window.location.origin);
      return url.protocol === 'http:' || url.protocol === 'https:';
    } catch (e) {
      return false;
    }
  }

  // ── Start ────────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);
})();
