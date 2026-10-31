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

    function restore() {
      root.classList.remove('is-filtering');
      empty.hidden = true;
      root.querySelectorAll('.fss-show').forEach(function (el) {
        el.classList.remove('fss-show');
      });
      root.querySelectorAll('.fss-original').forEach(function (el) { el.hidden = true; });
      root.querySelectorAll('.fss-badge.on, .fss-group.hit').forEach(function (el) {
        el.classList.remove('on', 'hit');
      });
      root.querySelectorAll('.fss-jung').forEach(function (jung) {
        jung.querySelectorAll('.fss-year').forEach(function (panel, i) {
          panel.hidden = i !== 0;
        });
        jung.querySelectorAll('.fss-year-btn').forEach(function (btn, i) {
          btn.classList.toggle('on', i === 0);
          btn.hidden = false;
        });
      });
    }

    function apply(name) {
      input.value = name;
      showList([]);
      restore();
      root.classList.add('is-filtering');
      var hits = 0;
      root.querySelectorAll('.fss-group').forEach(function (group) {
        if (!hasName(group, name)) return;
        hits += 1;
        group.classList.add('fss-show', 'hit');
        group.querySelectorAll('.fss-badge, .fss-original, .fss-badges').forEach(function (el) {
          if (hasName(el, name) || el.classList.contains('fss-badges')) {
            el.classList.add('fss-show');
            if (el.classList.contains('fss-original')) el.hidden = false;
            if (el.classList.contains('fss-badge')) el.classList.add('on');
          }
        });
        var node = group.parentElement;
        while (node && node !== root) {
          node.classList.add('fss-show');
          if (node.classList.contains('fss-year')) node.hidden = false;
          node = node.parentElement;
        }
      });
      root.querySelectorAll('.fss-jung').forEach(function (jung) {
        jung.querySelectorAll('.fss-year-btn').forEach(function (btn) {
          var panel = jung.querySelector('.fss-year[data-year="' + btn.getAttribute('data-year') + '"]');
          var visible = panel && panel.classList.contains('fss-show');
          btn.hidden = !visible;
          btn.classList.toggle('on', visible);
        });
      });
      empty.hidden = hits > 0;
    }

    input.addEventListener('input', function () {
      var q = input.value.trim();
      if (!q) {
        showList([]);
        restore();
        return;
      }
      showList(firms.filter(function (name) { return name.indexOf(q) !== -1; }).slice(0, 8));
    });
    input.addEventListener('keydown', function (e) {
      if (!list.classList.contains('open')) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, matches.length - 1); mark(); }
      if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); mark(); }
      if (e.key === 'Enter' && active >= 0) { e.preventDefault(); apply(matches[active]); }
      if (e.key === 'Escape') showList([]);
    });
    list.addEventListener('click', function (e) {
      var btn = e.target.closest('button');
      if (!btn) return;
      apply(matches[Number(btn.getAttribute('data-i'))]);
    });
    clearBtn.addEventListener('click', function () {
      input.value = '';
      showList([]);
      restore();
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
      if (!badge || !root.contains(badge) || root.classList.contains('is-filtering')) return;
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
  }

  function init() {
    applyQuarterlyUpdateScope();
    initFssReview();
  }

  if (typeof document$ !== 'undefined') {
    document$.subscribe(init);
  } else if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
