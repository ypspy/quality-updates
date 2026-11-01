const test = require("node:test");
const assert = require("node:assert/strict");
const { REGISTERED, yearLabel, reduceFilter, groupVisible } = require("./fss-filter.js");

const empty = { name: null, kind: null, year: null };

test("registered order follows 참고2", function () {
  assert.deepEqual(REGISTERED.map(function (row) { return row.gun; }), ["가군", "나군", "다군", "라군"]);
  assert.deepEqual(REGISTERED[0].firms, ["삼일회계법인", "삼정회계법인", "안진회계법인", "한영회계법인"]);
  assert.equal(REGISTERED[3].firms[REGISTERED[3].firms.length - 1], "한길회계법인");
  assert.equal(REGISTERED.reduce(function (n, row) { return n + row.firms.length; }, 0), 40);
});

test("yearLabel", function () {
  assert.equal(yearLabel("2024", false), "2024년");
  assert.equal(yearLabel("2023", true), "'23년");
});

test("name and kind are one firm-side filter", function () {
  var named = reduceFilter(empty, { type: "name", value: "삼정회계법인" });
  assert.deepEqual(named, { name: "삼정회계법인", kind: null, year: null });
  var kind = reduceFilter(named, { type: "kind", value: "일반회계법인" });
  assert.deepEqual(kind, { name: null, kind: "일반회계법인", year: null });
  assert.deepEqual(reduceFilter(kind, { type: "kind", value: "일반회계법인" }), empty);
});

test("year survives clearFirm", function () {
  var both = reduceFilter(
    reduceFilter(empty, { type: "name", value: "대주회계법인" }),
    { type: "year", value: "2020" }
  );
  assert.deepEqual(reduceFilter(both, { type: "clearFirm" }), { name: null, kind: null, year: "2020" });
  assert.deepEqual(reduceFilter(both, { type: "year", value: "2020" }), { name: "대주회계법인", kind: null, year: null });
});

test("groupVisible", function () {
  var firm = { names: ["삼정회계법인", "안진회계법인"], kind: "등록", year: "2020" };
  var named = { name: "삼정회계법인", kind: null, year: "2020" };
  assert.deepEqual(groupVisible(firm, named), { show: true, open: true });
  assert.deepEqual(groupVisible(firm, { name: "삼정회계법인", kind: null, year: "2019" }), { show: false, open: false });
  assert.deepEqual(groupVisible(
    { names: ["가립회계법인"], kind: "일반회계법인", year: "2022" },
    { name: null, kind: "일반회계법인", year: null }
  ), { show: true, open: false });
  assert.deepEqual(groupVisible(firm, empty), { show: true, open: false });
});
