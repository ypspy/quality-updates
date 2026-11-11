/**
 * Quality Updates - 사이트 전용 스크립트
 * 분기 규제 업데이트 페이지 스코프: docs/superpowers/specs/2026-06-26-quarterly-update-list-spacing-design.md
 */
(function () {
  'use strict';

  var QUARTERLY_PATH = /\/quality-updates\/\d{4}\//;

  function isQuarterlyUpdatePage() {
    return QUARTERLY_PATH.test(location.pathname);
  }

  function applyQuarterlyUpdateScope() {
    var article = document.querySelector('.md-content__inner');
    if (!article) {
      return;
    }
    if (isQuarterlyUpdatePage()) {
      article.classList.add('quarterly-update');
    } else {
      article.classList.remove('quarterly-update');
    }
  }

  function hasName(el, name) {
    return (el.getAttribute('data-names') || '').split('|').indexOf(name) !== -1;
  }

  function clearFssRails() {
    var firmRail = document.getElementById('fss-firm-rail');
    if (firmRail) firmRail.remove();
    var yearRail = document.getElementById('fss-year-rail');
    if (yearRail) yearRail.remove();
    var sectionRail = document.getElementById('fss-section-rail');
    if (sectionRail) sectionRail.remove();
    document.querySelectorAll('.md-sidebar--primary .md-nav--primary').forEach(function (nav) {
      if (nav.closest('header.md-header')) return;
      nav.hidden = false;
    });
    document.querySelectorAll('.fss-year-drawer-btn').forEach(function (btn) {
      btn.remove();
    });
    var yearBar = document.getElementById('fss-year-bar');
    if (yearBar) yearBar.remove();
    document.body.classList.remove('fss-year-open');
  }

  function initFssReview() {
    var root = document.getElementById('fss-review');
    // 이름 목록은 본문 script로 두지 않는다. instant navigation이 script의 id를 지운다.
    var indexNode = document.getElementById('fss-firm-index');
    if (!root || !root.classList.contains('fss-review') || !indexNode) {
      clearFssRails();
      return;
    }
    if (root.getAttribute('data-ready') === '1') {
      return;
    }
    root.setAttribute('data-ready', '1');
    var firms = JSON.parse(indexNode.textContent);
    var input = document.getElementById('fss-q');
    var list = document.getElementById('fss-list');
    var empty = document.getElementById('fss-empty');
    var clearBtn = document.getElementById('fss-clear');
    var active = -1;
    var matches = [];

    function showList(items) {
      matches = items;
      active = -1;
      list.innerHTML = items.map(function (name, i) {
        return '<button type="button" role="option" data-i="' + i + '">' + name + '</button>';
      }).join('');
      list.classList.toggle('open', items.length > 0);
      input.setAttribute('aria-expanded', items.length ? 'true' : 'false');
    }

    function mark() {
      Array.prototype.forEach.call(list.children, function (el, i) {
        el.setAttribute('aria-selected', i === active ? 'true' : 'false');
      });
    }

    var state = { name: null, kind: null, year: null };

    function groupPayload(group) {
      var bundle = group.closest('.fss-bundle');
      var kindNode = bundle ? bundle.querySelector('.fss-bundle-name') : null;
      var yearNode = group.closest('.fss-year');
      return {
        names: (group.getAttribute('data-names') || '').split('|'),
        kind: kindNode ? kindNode.textContent.trim() : '',
        year: yearNode ? (yearNode.getAttribute('data-year') || '') : ''
      };
    }

    function closeOriginals(group) {
      group.querySelectorAll('.fss-original').forEach(function (el) {
        el.hidden = true;
        el.classList.remove('fss-show');
      });
      group.querySelectorAll('.fss-badge').forEach(function (el) {
        el.classList.remove('on');
      });
    }

    function paint() {
      var filtering = Boolean(state.name || state.kind || state.year);
      document.querySelectorAll('.fss-years').forEach(function (el) {
        el.hidden = true;
      });
      root.querySelectorAll('.fss-show').forEach(function (el) {
        el.classList.remove('fss-show');
      });
      root.querySelectorAll('.fss-dim').forEach(function (el) {
        el.classList.remove('fss-dim');
      });
      root.querySelectorAll('.fss-year').forEach(function (panel) {
        var year = panel.getAttribute('data-year') || '';
        panel.hidden = Boolean(state.year) && state.year !== year;
        var label = panel.querySelector(':scope > p.fss-year-label');
        if (!label) {
          label = document.createElement('p');
          label.className = 'fss-year-label';
          panel.insertBefore(label, panel.firstChild);
        }
        label.textContent = window.FssFilter.yearLabel(year, false);
      });
      var visible = 0;
      root.querySelectorAll('.fss-group').forEach(function (group) {
        var vis = window.FssFilter.groupVisible(groupPayload(group), state);
        if (!vis.show) {
          group.classList.add('fss-dim');
          closeOriginals(group);
          return;
        }
        visible += 1;
        if (vis.open) {
          group.querySelectorAll('.fss-original').forEach(function (el) {
            var match = hasName(el, state.name);
            el.hidden = !match;
            if (match) el.classList.add('fss-show');
            else el.classList.remove('fss-show');
          });
          group.querySelectorAll('.fss-badge').forEach(function (el) {
            el.classList.toggle('on', hasName(el, state.name));
          });
        } else {
          closeOriginals(group);
        }
        if (!filtering) return;
        group.classList.add('fss-show');
        var badges = group.querySelector('.fss-badges');
        if (badges) badges.classList.add('fss-show');
        group.querySelectorAll('.fss-badge').forEach(function (el) {
          var match = !state.name || hasName(el, state.name);
          if (match) el.classList.add('fss-show');
          if (state.name && !match) el.classList.add('fss-dim');
        });
        var node = group.parentElement;
        while (node && node !== root) {
          node.classList.add('fss-show');
          node = node.parentElement;
        }
      });
      if (filtering) {
        ['.fss-year', '.fss-gun', '.fss-bundle', '.fss-jung', '.fss-dae'].forEach(function (sel) {
          root.querySelectorAll(sel).forEach(function (el) {
            if (!el.querySelector('.fss-group.fss-show')) {
              el.classList.add('fss-dim');
              el.classList.remove('fss-show');
            }
          });
        });
        root.querySelectorAll('.fss-dim').forEach(function (el) {
          el.classList.remove('fss-show');
        });
      }
      if (filtering && visible === 0) {
        empty.textContent = '이 조건에 해당하는 분류된 지적이 없습니다.';
        empty.hidden = false;
      } else {
        empty.hidden = true;
      }
      root.classList.toggle('is-filtering', filtering);
      document.querySelectorAll('#fss-firm-rail [data-firm]').forEach(function (btn) {
        btn.setAttribute('aria-pressed', btn.getAttribute('data-firm') === state.name ? 'true' : 'false');
      });
      document.querySelectorAll('#fss-firm-rail [data-kind]').forEach(function (btn) {
        btn.setAttribute('aria-pressed', btn.getAttribute('data-kind') === state.kind ? 'true' : 'false');
      });
      document.querySelectorAll('#fss-year-bar .fss-year-btn').forEach(function (btn) {
        var on = btn.getAttribute('data-year') === state.year;
        btn.classList.toggle('on', on);
        btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        btn.disabled = false;
      });
      document.querySelectorAll('#fss-section-rail a').forEach(function (link) {
        var id = (link.getAttribute('href') || '').replace(/^#/, '');
        var heading = id ? document.getElementById(id) : null;
        var section = heading ? heading.parentElement : null;
        link.hidden = Boolean(section && section.classList.contains('fss-dim'));
      });
      applyYearLabels();
      markFindingYears();
    }

    function markFindingYears() {
      var counts = window.FssFilter.findingYearCounts(
        Array.prototype.map.call(root.querySelectorAll('.fss-group'), groupPayload),
        state.name
      );
      document.querySelectorAll('#fss-year-bar .fss-year-btn').forEach(function (btn) {
        var year = btn.getAttribute('data-year') || '';
        var count = counts[year] || 0;
        var text = btn.querySelector('.fss-year-text');
        if (!text) {
          text = document.createElement('span');
          text.className = 'fss-year-text';
          text.textContent = btn.textContent;
          btn.textContent = '';
          btn.appendChild(text);
        }
        var mark = btn.querySelector('.fss-year-mark');
        if (!count) {
          if (mark) mark.remove();
          btn.classList.remove('has-finding');
          btn.removeAttribute('aria-label');
          return;
        }
        if (!mark) {
          mark = document.createElement('span');
          mark.className = 'fss-year-mark';
          btn.appendChild(mark);
        }
        mark.textContent = String(count);
        btn.classList.add('has-finding');
        btn.setAttribute('aria-label', window.FssFilter.yearLabel(year, false) + ', 지적 ' + count + '건');
      });
      alignWrappedYearButtons();
    }

    function clearFirm() {
      state = window.FssFilter.reduceFilter(state, { type: 'clearFirm' });
      if (input.value) input.value = '';
      showList([]);
      paint();
    }

    function chooseName(value) {
      state = window.FssFilter.reduceFilter(state, { type: 'name', value: value });
      input.value = state.name || '';
      showList([]);
      paint();
    }

    input.addEventListener('input', function () {
      var q = input.value.trim();
      if (!q) {
        clearFirm();
        return;
      }
      showList(firms.filter(function (name) { return name.indexOf(q) !== -1; }).slice(0, 8));
    });
    input.addEventListener('keydown', function (e) {
      if (!list.classList.contains('open')) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, matches.length - 1); mark(); }
      if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); mark(); }
      if (e.key === 'Enter' && active >= 0) { e.preventDefault(); chooseName(matches[active]); }
      if (e.key === 'Escape') showList([]);
    });
    list.addEventListener('click', function (e) {
      var btn = e.target.closest('button');
      if (!btn) return;
      chooseName(matches[Number(btn.getAttribute('data-i'))]);
    });
    clearBtn.addEventListener('click', function () {
      clearFirm();
      input.focus();
    });
    if (!document.getElementById('fss-firm-rail')) {
      var primaryInner = document.querySelector('.md-sidebar--primary .md-sidebar__inner');
      if (primaryInner) {
        var firmRail = document.createElement('div');
        firmRail.id = 'fss-firm-rail';
        window.FssFilter.REGISTERED.forEach(function (row) {
          var gun = document.createElement('p');
          gun.className = 'fss-rail-gun';
          gun.textContent = row.gun;
          firmRail.appendChild(gun);
          row.firms.forEach(function (name) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'fss-rail-firm';
            btn.setAttribute('data-firm', name);
            btn.textContent = name;
            firmRail.appendChild(btn);
          });
        });
        ['일반회계법인', '감사반'].forEach(function (kind) {
          var btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'fss-rail-kind';
          btn.setAttribute('data-kind', kind);
          btn.textContent = kind;
          firmRail.appendChild(btn);
        });
        primaryInner.insertBefore(firmRail, primaryInner.firstChild);
        document.querySelectorAll('.md-sidebar--primary .md-nav--primary').forEach(function (nav) {
          if (nav.closest('header.md-header')) return;
          nav.hidden = true;
        });
      }
    }
    if (!document.getElementById('fss-section-rail')) {
      var secondaryInner = document.querySelector('.md-sidebar--secondary .md-sidebar__inner');
      if (secondaryInner) {
        var sectionRail = document.createElement('nav');
        sectionRail.id = 'fss-section-rail';
        var outline = root.querySelectorAll('.fss-year > h2, .fss-dae > h2, .fss-jung > h3');
        Array.prototype.forEach.call(outline, function (heading, index) {
          if (!heading.id) heading.id = 'fss-h-' + index;
          var link = document.createElement('a');
          var isJung = heading.tagName.toUpperCase() === 'H3';
          link.className = isJung ? 'fss-jung-link' : 'fss-dae-link';
          link.href = '#' + heading.id;
          link.textContent = heading.textContent;
          sectionRail.appendChild(link);
        });
        secondaryInner.insertBefore(sectionRail, secondaryInner.firstChild);
      }
    }
    var seenYear = {};
    var years = [];
    root.querySelectorAll('.fss-year[data-year]').forEach(function (el) {
      var year = el.getAttribute('data-year') || '';
      if (!/^\d{4}$/.test(year) || seenYear[year]) return;
      seenYear[year] = true;
      years.push(year);
    });
    years.sort(function (a, b) { return Number(b) - Number(a); });
    if (!state.year && years.length) state.year = years[0];
    if (!document.getElementById('fss-year-bar')) {
      var yearBar = document.createElement('div');
      yearBar.id = 'fss-year-bar';
      yearBar.setAttribute('role', 'toolbar');
      yearBar.setAttribute('aria-label', '연도');
      years.forEach(function (year) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'fss-year-btn';
        btn.setAttribute('data-year', year);
        yearBar.appendChild(btn);
      });
      var article = document.querySelector('.md-content__inner');
      if (article) article.insertBefore(yearBar, article.firstChild);
      else root.insertBefore(yearBar, root.firstChild);
      yearBar.addEventListener('click', function (e) {
        var yearBtn = e.target.closest('.fss-year-btn');
        if (!yearBtn || !yearBar.contains(yearBtn)) return;
        state.year = yearBtn.getAttribute('data-year');
        paint();
      });
    }
    var firmRailEl = document.getElementById('fss-firm-rail');
    if (firmRailEl) {
      firmRailEl.addEventListener('click', function (e) {
        var firmBtn = e.target.closest('[data-firm]');
        if (firmBtn && firmRailEl.contains(firmBtn)) {
          state = window.FssFilter.reduceFilter(state, { type: 'name', value: firmBtn.getAttribute('data-firm') });
          input.value = state.name || '';
          showList([]);
          paint();
          return;
        }
        var kindBtn = e.target.closest('[data-kind]');
        if (!kindBtn || !firmRailEl.contains(kindBtn)) return;
        state = window.FssFilter.reduceFilter(state, { type: 'kind', value: kindBtn.getAttribute('data-kind') });
        input.value = '';
        showList([]);
        paint();
      });
    }
    root.addEventListener('click', function (e) {
      var badge = e.target.closest('.fss-badge');
      if (!badge || !root.contains(badge) || state.name) return;
      var group = badge.closest('.fss-group');
      var name = (badge.getAttribute('data-names') || '').split('|')[0];
      var opening = true;
      group.querySelectorAll('.fss-original').forEach(function (el) {
        if (hasName(el, name) && !el.hidden) opening = false;
        el.hidden = true;
      });
      group.querySelectorAll('.fss-badge').forEach(function (el) { el.classList.remove('on'); });
      if (opening) {
        group.querySelectorAll('.fss-original').forEach(function (el) {
          if (hasName(el, name)) el.hidden = false;
        });
        badge.classList.add('on');
      }
    });
    paint();
  }

  var yearQuery = window.matchMedia('(max-width: 40em)');

  function alignWrappedYearButtons() {
    var bar = document.getElementById('fss-year-bar');
    if (!bar) return;
    var buttons = Array.prototype.slice.call(bar.querySelectorAll('.fss-year-btn'));
    buttons.forEach(function (btn) {
      btn.style.marginLeft = '';
      btn.style.marginRight = '';
    });
    if (!buttons.length) return;
    var rows = [];
    buttons.forEach(function (btn) {
      var top = btn.offsetTop;
      var row = rows[rows.length - 1];
      if (!row || Math.abs(row.top - top) > 1) rows.push({ top: top, items: [btn] });
      else row.items.push(btn);
    });
    if (rows.length < 2) return;
    var anchor = rows[0].items[0].offsetLeft;
    rows.slice(1).forEach(function (row) {
      row.items[0].style.marginLeft = anchor + 'px';
      row.items[row.items.length - 1].style.marginRight = 'auto';
    });
  }

  function applyYearLabels() {
    var narrow = yearQuery.matches;
    document.querySelectorAll('.fss-year-btn').forEach(function (btn) {
      var year = btn.getAttribute('data-year') || '';
      if (!/^\d{4}$/.test(year)) return;
      var label = window.FssFilter.yearLabel(year, narrow);
      var text = btn.querySelector('.fss-year-text');
      if (text) text.textContent = label;
      else btn.textContent = label;
    });
    alignWrappedYearButtons();
  }

  var observedYearBar = null;
  var yearBarObserver = window.ResizeObserver ? new ResizeObserver(function () {
    alignWrappedYearButtons();
  }) : null;

  function watchYearBar() {
    if (!yearBarObserver) return;
    var bar = document.getElementById('fss-year-bar');
    if (bar === observedYearBar) return;
    if (observedYearBar) yearBarObserver.unobserve(observedYearBar);
    observedYearBar = bar;
    if (bar) yearBarObserver.observe(bar);
  }

  function init() {
    applyQuarterlyUpdateScope();
    initFssReview();
    applyYearLabels();
    watchYearBar();
  }

  if (yearQuery.addEventListener) {
    yearQuery.addEventListener('change', applyYearLabels);
  } else if (yearQuery.addListener) {
    yearQuery.addListener(applyYearLabels);
  }

  if (typeof document$ !== 'undefined') {
    document$.subscribe(init);
  } else if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
