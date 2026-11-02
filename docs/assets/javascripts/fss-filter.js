var REGISTERED = [
  { gun: "가군", firms: ["삼일회계법인", "삼정회계법인", "안진회계법인", "한영회계법인"] },
  { gun: "나군", firms: ["대주회계법인", "삼덕회계법인", "서현회계법인", "성현회계법인", "신한회계법인", "우리회계법인", "이촌회계법인", "한울회계법인"] },
  { gun: "다군", firms: ["다산회계법인", "대성삼경회계법인", "대현회계법인", "도원회계법인", "동현회계법인", "삼도회계법인", "삼화회계법인", "서우회계법인", "신우회계법인", "안경회계법인", "예교지성회계법인", "이정회계법인", "인덕회계법인", "정진세림회계법인", "진일회계법인", "태성회계법인", "한미회계법인", "현대회계법인"] },
  { gun: "라군", firms: ["광교회계법인", "동아송강회계법인", "회계법인리안", "선일회계법인", "선진회계법인", "회계법인세일원", "예일회계법인", "정동회계법인", "정인회계법인", "한길회계법인"] }
];

function yearLabel(year, narrow) {
  if (narrow) return "'" + year.slice(-2) + "년";
  return year + "년";
}

function reduceFilter(state, action) {
  var next = { name: state.name, kind: state.kind, year: state.year };
  if (action.type === "name") {
    if (state.name === action.value) {
      next.name = null;
    } else {
      next.name = action.value;
      next.kind = null;
    }
    return next;
  }
  if (action.type === "kind") {
    if (state.kind === action.value) {
      next.kind = null;
    } else {
      next.kind = action.value;
      next.name = null;
    }
    return next;
  }
  if (action.type === "year") {
    next.year = state.year === action.value ? null : action.value;
    return next;
  }
  if (action.type === "clearFirm") {
    next.name = null;
    next.kind = null;
    return next;
  }
  return next;
}

function groupVisible(group, state) {
  if (state.year && state.year !== group.year) {
    return { show: false, open: false };
  }
  if (state.name) {
    if (group.names.indexOf(state.name) !== -1) {
      return { show: true, open: true };
    }
    return { show: false, open: false };
  }
  if (state.kind) {
    if (group.kind === state.kind) {
      return { show: true, open: false };
    }
    return { show: false, open: false };
  }
  return { show: true, open: false };
}

var api = { REGISTERED: REGISTERED, yearLabel: yearLabel, reduceFilter: reduceFilter, groupVisible: groupVisible };
if (typeof module !== "undefined" && module.exports) module.exports = api;
if (typeof window !== "undefined") window.FssFilter = api;
