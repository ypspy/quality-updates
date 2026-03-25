/* Quality Updates Editor — main JS */
(function () {
  'use strict';

  let currentFile = null;
  let originalContent = null;
  // Each link:
  // - source: null | { type: 'pdf'|'web'|'clip', ref: string }
  // - pdf_path: kept for backward-compatible save payload (derived from source when type==='pdf')
  // sourcePanel: 'pdf'|'web' — editor-only; which SOURCE tab is shown (not sent to API).
  let linksData = [];   // [{date, title, url, state, source, pdf_path, sourcePanel, agency, line_index}]
  let pdfFiles = [];    // string[] (Option A)

  const RECENTS_KEY_PDF = 'quality-updates-editor:recentSources:pdf';
  const MAX_RECENTS = 10;
  const MAX_RESULTS_RENDERED = 12;

  // Dropdown state (single-open at a time)
  let openPicker = null; // { idx, rootEl, inputEl, listEl, activeIndex, items: [{path, kind:'recent'|'result'}] }

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

  function hasResolvedWebSource(entry) {
    const s = entry.source;
    return !!(s && s.type === 'web' && String(s.ref || '').trim());
  }

  /** needs_summary rows that still need a PDF path (PDF or null source only; WEB with URL is OK). */
  function isUnresolvedNeedsPdf(entry) {
    if (entry.state !== 'needs_summary') return false;
    if (hasResolvedWebSource(entry)) return false;
    return !entry.pdf_path;
  }

  async function onSave() {
    if (!currentFile) return alert('파일을 선택하세요.');
    const curation = linksData
      .filter(l => l.state !== 'done')
      .map(l => {
        const row = {
          title: l.title,
          line_index: l.line_index,
          state: l.state,
          pdf_path: getPdfPathForSave(l),
        };
        if (l.source) row.source = l.source;
        return row;
      });

    const unresolved = curation.filter(isUnresolvedNeedsPdf);
    if (unresolved.length > 0) {
      const ok = confirm(`${unresolved.length}개 항목이 "요약 필요"이지만 PDF가 선택되지 않았습니다.\n저장하면 미결정으로 처리됩니다. 계속할까요?`);
      if (!ok) return;
    }

    curation.forEach((c) => {
      if (isUnresolvedNeedsPdf(c)) c.state = 'undecided';
    });

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
    linksData = (data.links || []).map(normalizeLink);
    originalContent = data.content;
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
        td.textContent = link.agency || '기타';
        hdr.appendChild(td);
        tbody.appendChild(hdr);
      }

      const tr = document.createElement('tr');
      tr.dataset.idx = idx;
      tr.className = stateClass(link.state);

      tr.innerHTML = `
        <td>${escHtml(link.date)}</td>
        <td><span class="title-link" role="link" tabindex="0" data-url="${escHtml(link.url)}">${escHtml(link.title)}</span></td>
        <td>${escHtml(link.agency || '')}</td>
        <td>${stateBadge(link, idx)}</td>
        <td>${sourceCell(link, idx)}</td>
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
    tr.querySelector('td:nth-child(4)').innerHTML = stateBadge(link, idx);
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
    return { undecided: '', needs_summary: 'state-needs', skip: 'state-skip', done: 'state-done' }[state] || '';
  }

  function stateBadge(link, idx) {
    const labels = { undecided: '미결정', needs_summary: '요약 필요', skip: '스킵', done: '완료' };
    const cls = { undecided: 'badge-undecided', needs_summary: 'badge-needs', skip: 'badge-skip', done: 'badge-done' };
    return `<span class="state-badge ${cls[link.state]}" data-idx="${idx}" role="button" tabindex="0">${labels[link.state]}</span>`;
  }

  function sourceKind(link) {
    return link.sourcePanel === 'web' ? 'web' : 'pdf';
  }

  function sourceCell(link, idx) {
    if (link.state === 'done') return '';
    const kind = sourceKind(link);
    const webUrl = link.source && link.source.type === 'web' ? String(link.source.ref || '') : '';

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

    return `
      <div class="source-cell" data-idx="${idx}">
        <div class="source-kind-row" role="tablist" aria-label="출처 유형">
          <button type="button" class="source-tab${kind === 'pdf' ? ' is-active' : ''}" data-kind="pdf" role="tab" aria-selected="${kind === 'pdf' ? 'true' : 'false'}">PDF</button>
          <button type="button" class="source-tab${kind === 'web' ? ' is-active' : ''}" data-kind="web" role="tab" aria-selected="${kind === 'web' ? 'true' : 'false'}">WEB</button>
        </div>
        <div class="source-panel source-panel-pdf" data-panel="pdf" style="display:${kind === 'pdf' ? 'block' : 'none'}">${pdfBlock}</div>
        <div class="source-panel source-panel-web" data-panel="web" style="display:${kind === 'web' ? 'block' : 'none'}">
          <div class="web-source-row">
            <input class="web-url-input" type="url" inputmode="url" placeholder="https://…" value="${escHtml(webUrl)}" />
            <button class="source-btn web-btn-preview" type="button">미리보기/새로고침</button>
            <button class="source-btn web-btn-clear" type="button"${webUrl.trim() ? '' : ' disabled'}>비우기</button>
          </div>
        </div>
      </div>
    `;
  }

  // ── State cycling ────────────────────────────────────────────────────────────
  const STATE_CYCLE = ['undecided', 'needs_summary', 'skip'];

  function cycleState(idx) {
    const link = linksData[idx];
    const cur = STATE_CYCLE.indexOf(link.state);
    link.state = STATE_CYCLE[(cur + 1) % STATE_CYCLE.length];
    if (link.state !== 'needs_summary') {
      link.pdf_path = null;
      link.source = null;
      link.sourcePanel = 'pdf';
    }
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
  let previewSeq = 0;

  function openPreview(url) {
    previewSeq += 1;
    const seq = previewSeq;
    const iframe = document.getElementById('preview-iframe');
    const fallback = document.getElementById('iframe-fallback');
    const fallbackLink = document.getElementById('fallback-link');

    fallback.style.display = 'none';
    iframe.style.display = 'block';
    iframe.src = '/api/source/preview?url=' + encodeURIComponent(url);
    fallbackLink.href = isSafeHttpUrl(url) ? url : '#';

    iframe.onload = () => {
      if (seq !== previewSeq) return;
      try {
        const doc = iframe.contentDocument;
        if (doc && doc.body && doc.body.innerHTML === '') showFallback(url);
      } catch (e) {
        showFallback(url);
      }
    };
    iframe.onerror = () => {
      if (seq !== previewSeq) return;
      showFallback(url);
    };

    setTimeout(() => {
      if (seq !== previewSeq) return;
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

  // ── SOURCE cell (PDF | WEB) ─────────────────────────────────────────────────
  function wireSourceCell(tr, idx) {
    const cell = tr.querySelector('.source-cell');
    if (!cell) return;

    cell.querySelectorAll('.source-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        const kind = tab.getAttribute('data-kind');
        if (kind === 'pdf' || kind === 'web') setSourceKind(idx, kind);
      });
    });

    const webInput = cell.querySelector('.web-url-input');
    const webPreview = cell.querySelector('.web-btn-preview');
    const webClear = cell.querySelector('.web-btn-clear');
    if (webInput && webPreview && webClear) {
      webInput.addEventListener('input', () => {
        applyWebUrlFromInput(idx, webInput.value);
        webClear.disabled = !String(webInput.value || '').trim();
        const row = cell.closest('tr');
        if (row) reRenderRow(row, idx);
        updateCounter();
      });
      webPreview.addEventListener('click', () => {
        const u = String(webInput.value || '').trim();
        if (!u) return;
        openPreview(u);
      });
      webClear.addEventListener('click', () => {
        clearWebSource(idx);
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

    if (kind === 'pdf') {
      if (link.source && link.source.type === 'web') {
        link.source = null;
        link.pdf_path = null;
        link.state = 'undecided';
      }
    } else {
      if (link.source && link.source.type === 'pdf') {
        link.source = null;
        link.pdf_path = null;
        link.state = 'undecided';
      }
    }
    closeOpenPicker();
    updateCounter();
    renderTable();
  }

  function applyWebUrlFromInput(idx, raw) {
    const link = linksData[idx];
    link.sourcePanel = 'web';
    const u = String(raw || '').trim();
    if (u) {
      link.source = { type: 'web', ref: u };
      link.pdf_path = null;
      link.state = 'needs_summary';
    } else {
      link.source = null;
      link.pdf_path = null;
      link.state = 'undecided';
    }
  }

  function clearWebSource(idx) {
    const link = linksData[idx];
    link.sourcePanel = 'web';
    link.source = null;
    link.pdf_path = null;
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

    btnOpen.addEventListener('click', () => {
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
      openPdfPicker(idx, root, input, list);
    });

    input.addEventListener('focus', () => {
      // Don't auto-open on focus; ArrowDown / button opens (spec).
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown' && !isPickerOpenFor(idx)) {
        e.preventDefault();
        openPdfPicker(idx, root, input, list, { focusFirst: true });
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
    pushRecentPdfPath(fullPath);
    closeOpenPicker();
  }

  function clearPdfSource(idx) {
    const link = linksData[idx];
    link.sourcePanel = 'pdf';
    link.source = null;
    link.pdf_path = null;
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
    }
    if (!l.source) l.source = null;
    if (!l.pdf_path) l.pdf_path = null;

    l.sourcePanel = l.source && l.source.type === 'web' ? 'web' : 'pdf';

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
