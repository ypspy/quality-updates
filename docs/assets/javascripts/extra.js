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

  function initFssReview() {
    var root = document.getElementById('fss-review');
    var indexNode = document.getElementById('fss-firm-index');
    if (!root || !indexNode || root.getAttribute('data-ready') === '1') {
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
          el.classList.add('fss-show');
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
    root.addEventListener('click', function (e) {
      var yearBtn = e.target.closest('.fss-year-btn');
      if (yearBtn && root.contains(yearBtn)) {
        var jung = yearBtn.closest('.fss-jung');
        var year = yearBtn.getAttribute('data-year');
        jung.querySelectorAll('.fss-year-btn').forEach(function (btn) {
          btn.classList.toggle('on', btn === yearBtn);
        });
        jung.querySelectorAll('.fss-year').forEach(function (panel) {
          var match = panel.getAttribute('data-year') === year;
          panel.hidden = !match;
          if (root.classList.contains('is-filtering')) {
            panel.classList.toggle('fss-show', match && panel.querySelector('.fss-group.hit'));
          }
        });
        return;
      }
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

  function applyYearLabels() {
    var narrow = yearQuery.matches;
    document.querySelectorAll('.fss-year-btn').forEach(function (btn) {
      var year = btn.getAttribute('data-year') || '';
      if (!/^\d{4}$/.test(year)) return;
      btn.textContent = window.FssFilter.yearLabel(year, narrow);
    });
  }

  function init() {
    applyQuarterlyUpdateScope();
    initFssReview();
    applyYearLabels();
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
