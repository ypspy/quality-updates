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

  function init() {
    applyQuarterlyUpdateScope();
  }

  if (typeof document$ !== 'undefined') {
    document$.subscribe(init);
  } else if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
