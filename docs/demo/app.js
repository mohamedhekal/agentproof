"use strict";
/* AgentProof live demo. Runs the real package in the browser with Pyodide (Python compiled to WebAssembly).
   No server, no API keys, no tracking. A demo to explain the idea, not a benchmark. */

const PYODIDE_INDEX = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";

const I18N = {
  en: {
    liveDemo: "live demo", navRepo: "Repository", navWiki: "Wiki", navDeck: "Pitch deck (PDF)", synthetic: "All data is synthetic.",
    bannerTitle: "A demo to explain the idea.",
    bannerText: "Scripted reference agents on a simulated store, running entirely in your browser. It is not a benchmark of any AI model and it does not test your own agent. All data is synthetic.",
    heroTitle: "Break an agent's tools. Grade what really happened.",
    heroText: "Slide the chaos up and watch two agents handle the same 8 support scenarios under the same sabotaged tool calls. The grader reads the final state of the world (the ledger), not what the agent says.",
    labTitle: "1. Chaos lab", labIntro: "Same tasks, same fault schedule for every agent. Change the settings and run again.",
    chaosLabel: "Chaos level", runsLabel: "Runs per scenario", seedLabel: "Seed", agentsLabel: "Agents", runBtn: "Run",
    chaosHelp: "Chaos level = the chance that any single tool call is sabotaged: timeouts where the write DID happen, duplicate deliveries, lost acknowledgements, malformed replies.",
    loading: "Loading the Python runtime (about 10 MB, first visit only)...", loadingFiles: "Loading AgentProof...", ready: "Ready. Everything runs in your browser.",
    running: "Running...", failedBoot: "Could not load the runtime. Check your connection (it loads Pyodide from a CDN) and reload.",
    resolved: "tickets resolved", unsafe: "unsafe", handed: "handed to a human", reliability: "reliability (pass^k)", calls: "avg tool calls",
    scenario: "scenario", takeaway: (n, h, c) => `At chaos ${c}, the naive agent did something unsafe in ${n}% of runs; the hardened agent in ${h}%. Both resolved tickets, but only one was checked against the ledger.`,
    cellTitle: (p, r, u, s) => `${p} passed of ${r}; ${s} handed to a human; ${u} unsafe`,
    explTitle: "2. Failure explorer and replay",
    explIntro: "Pick a failing run. See every tool call and the fault injected on it, then replay it: no world, no randomness, no network.",
    filterAgent: "Agent", filterStatus: "Status", all: "all", noFailures: "No failing runs with these settings. Try more chaos.",
    pickRun: "Select a run on the left.", ticketLbl: "Ticket", whyLbl: "Why it failed", noReason: "(no reason recorded)",
    replaySame: "Replay with the same agent", replayOther: (o) => `Replay with ${o} on this exact recording`,
    identical: "IDENTICAL: the same agent makes the same calls in the same order. A failure becomes a deterministic test.",
    diverged: "DIVERGED: this agent behaves differently on the exact same recording (it would not have made these calls).",
    matched: (a, b) => `${a} of ${b} recorded calls matched`, step: "step", call: "call", outcome: "outcome", fault: "fault injected",
    claudeTitle: "3. A recorded Claude run, replayed offline",
    claudeIntro: "A real model was run once against these scenarios and every response was recorded. Replaying it here makes no API call and gives the same answer every time.",
    claudeBtn: "Replay the recorded run",
    claudeFacts: (m) => `${Math.round(m.pass_rate * m.total_runs)} of ${m.total_runs} runs resolved, ${Math.round(m.unsafe_rate * m.total_runs)} unsafe, ${m.avg_tool_calls} tool calls on average (${m.model_responses_replayed} recorded model responses, chaos 0.3).`,
    claudeCaveat: ["The prompt spells out every rule (refund limit, idempotency keys, untrusted notes), so this measures following rules under broken tools, not unprompted competence.",
      "40 runs is a small sample: zero failures supports a pass rate above roughly 92%.", "Live reruns can differ (sampling is not pinned). The recording is what makes it reproducible."],
    brainTitle: "4. Memory that survives corrections", brainIntro: "Bitemporal memory (when a fact was true vs when we learned it) versus plain retrieval, on invented messages. Mean of a few seeds.", brainBtn: "Run (3 seeds)",
    brainCols: ["phrasing the extractor has not seen", "system", "all questions", "tricky ones", "provenance"],
    brainNote: "The extractor is rule-based and tuned to the generator, so the top row is a ceiling, not a forecast. The second row shows what happens with unfamiliar phrasing.",
    autoTitle: "5. When should a human be pulled in?", autoIntro: "4,000 simulated actions; a fraud wave hits a previously safe class halfway. A static limit versus a router that learns from human verdicts.", autoBtn: "Run simulation",
    autoCols: ["policy", "human asked", "bad actions with no human", "asks over time"], autoNote: "A simulation with a modeled human, not a measurement of any real workflow.",
    limitsTitle: "What this demo does not show",
    limits: ["The agents are scripted policies, not LLMs, and 'naive' is a deliberate strawman.",
      "8 scenarios, one fault model, one simulated store: it shows the method and three classes of bug, not the safety of any product.",
      "The Claude result is 40 simulated runs with a rule-rich prompt, from one recorded session.",
      "The memory benchmark uses invented messages and rule-based extraction; the autonomy result is a simulation.",
      "The page runs the real Python package in your browser (Pyodide). Numbers change with the settings and the seed."],
    runIt: "Run it for real:",
  },
  ar: {
    liveDemo: "ديمو لايف", navRepo: "الريبو", navWiki: "الـ Wiki", navDeck: "الـ pitch deck (PDF)", synthetic: "كل الداتا synthetic.",
    bannerTitle: "ديمو لتوضيح الفكرة.",
    bannerText: "agents مكتوبة (scripted) على متجر محاكى، وكل حاجة بتشتغل في متصفحك. مش benchmark لأي موديل ومش بيختبر الـ agent بتاعك. كل الداتا synthetic.",
    heroTitle: "اكسّر الـ tools بتاعة الـ agent. وقيّم اللي حصل فعلاً.",
    heroText: "ارفع الـ chaos وشوف agentين بيتعاملوا مع نفس الـ 8 سيناريوهات تحت نفس الأعطال. الـ grader بيقرا الحالة النهائية للعالم (الـ ledger) مش كلام الـ agent.",
    labTitle: "1. معمل الـ chaos", labIntro: "نفس المهام ونفس جدول الأعطال لكل agent. غيّر الإعدادات وشغّل تاني.",
    chaosLabel: "مستوى الـ chaos", runsLabel: "تشغيلات لكل سيناريو", seedLabel: "الـ seed", agentsLabel: "الـ agents", runBtn: "شغّل",
    chaosHelp: "مستوى الـ chaos = احتمال إن أي استدعاء tool يتخرّب: timeout والكتابة اتنفّذت فعلاً، تسليم مكرر، رد ضايع، رد مشوّه.",
    loading: "بحمّل Python runtime (حوالي 10 ميجا، أول زيارة بس)...", loadingFiles: "بحمّل AgentProof...", ready: "جاهز. كل حاجة بتشتغل في متصفحك.",
    running: "بشغّل...", failedBoot: "ما قدرتش أحمّل الـ runtime. اتأكد من النت (بيحمّل Pyodide من CDN) وأعد التحميل.",
    resolved: "تيكت اتحل", unsafe: "غير آمن", handed: "اتحوّل لبني آدم", reliability: "الثبات (pass^k)", calls: "متوسط الاستدعاءات",
    scenario: "السيناريو", takeaway: (n, h, c) => `عند chaos ${c}، الـ naive عمل حاجة غير آمنة في ${n}% من التشغيلات، والـ hardened في ${h}%. الاتنين حلّوا تيكتات، بس واحد بس اتفحص على الـ ledger.`,
    cellTitle: (p, r, u, s) => `${p} نجح من ${r}؛ ${s} اتحوّل لبني آدم؛ ${u} غير آمن`,
    explTitle: "2. مستكشف الفشل والـ replay",
    explIntro: "اختار تشغيلة فاشلة. شوف كل استدعاء والعطل المحقون فيه، وبعدين أعدها: من غير عالم ولا عشوائية ولا شبكة.",
    filterAgent: "الـ agent", filterStatus: "الحالة", all: "الكل", noFailures: "مفيش تشغيلات فاشلة بالإعدادات دي. جرّب chaos أعلى.",
    pickRun: "اختار تشغيلة من الشمال.", ticketLbl: "التيكت", whyLbl: "ليه فشل", noReason: "(مفيش سبب مسجّل)",
    replaySame: "أعدها بنفس الـ agent", replayOther: (o) => `أعدها بـ ${o} على نفس التسجيل`,
    identical: "IDENTICAL: نفس الـ agent بيعمل نفس الاستدعاءات بنفس الترتيب. الفشل بقى اختبار حتمي.",
    diverged: "DIVERGED: الـ agent ده بيتصرف مختلف على نفس التسجيل بالظبط (ما كانش هيعمل الاستدعاءات دي).",
    matched: (a, b) => `${a} من ${b} استدعاء متطابق`, step: "الخطوة", call: "الاستدعاء", outcome: "النتيجة", fault: "العطل المحقون",
    claudeTitle: "3. تشغيلة Claude متسجّلة، بتتعاد offline",
    claudeIntro: "موديل حقيقي اتشغّل مرة واحدة على السيناريوهات دي وكل ردوده اتسجّلت. إعادتها هنا ما بتعملش أي API call وبتدّي نفس الإجابة كل مرة.",
    claudeBtn: "أعد التشغيلة المتسجّلة",
    claudeFacts: (m) => `${Math.round(m.pass_rate * m.total_runs)} من ${m.total_runs} تشغيلة اتحلّت، ${Math.round(m.unsafe_rate * m.total_runs)} غير آمنة، بمتوسط ${m.avg_tool_calls} استدعاء (${m.model_responses_replayed} رد موديل متسجّل، chaos 0.3).`,
    claudeCaveat: ["الـ prompt بيشرح كل القواعد (حد الاسترجاع، idempotency keys، الملاحظات المش موثوقة)، فده بيقيس اتّباع القواعد تحت tools متخرّبة، مش كفاءة من غير توجيه.",
      "40 تشغيلة عيّنة صغيرة: صفر فشل بيدعم نسبة نجاح فوق حوالي 92%.", "التشغيل الحي ممكن يختلف (الـ sampling مش مثبّت). التسجيل هو اللي بيخلّيه قابل للتكرار."],
    brainTitle: "4. ذاكرة بتتحمّل التصحيحات", brainIntro: "ذاكرة bitemporal (امتى الحقيقة كانت صح مقابل امتى عرفناها) مقابل retrieval عادي، على رسايل مخترعة. متوسط كام seed.", brainBtn: "شغّل (3 seeds)",
    brainCols: ["صياغة الـ extractor ما شافهاش", "النظام", "كل الأسئلة", "الأسئلة الصعبة", "provenance"],
    brainNote: "الـ extractor بقواعد ومظبوط على الـ generator، فالصف الأول سقف مش توقع. والصف التاني بيوري اللي بيحصل مع صياغة غريبة.",
    autoTitle: "5. امتى بني آدم يتدخل؟", autoIntro: "4000 فعل محاكى؛ موجة احتيال بتضرب فئة كانت آمنة في النص. حد ثابت مقابل راوتر بيتعلّم من أحكام البشر.", autoBtn: "شغّل المحاكاة",
    autoCols: ["السياسة", "اتسأل بني آدم", "أفعال غلط من غير بني آدم", "الأسئلة عبر الزمن"], autoNote: "محاكاة بحكم بشري مفترض، مش قياس لأي workflow حقيقي.",
    limitsTitle: "اللي الديمو ده ما بيوريهوش",
    limits: ["الـ agents سياسات مكتوبة مش LLMs، والـ naive strawman مقصود.",
      "8 سيناريوهات، نموذج أعطال واحد، متجر محاكى واحد: بيوري المنهج وتلات أنواع bugs، مش أمان أي منتج.",
      "نتيجة Claude هي 40 تشغيلة محاكاة بـ prompt غني بالقواعد، من جلسة واحدة متسجّلة.",
      "benchmark الذاكرة على رسايل مخترعة وextraction بقواعد؛ ونتيجة الـ autonomy محاكاة.",
      "الصفحة بتشغّل الـ package الحقيقي في متصفحك (Pyodide). الأرقام بتتغيّر مع الإعدادات والـ seed."],
    runIt: "شغّله بجد:",
  },
};

let lang = (navigator.language || "").startsWith("ar") ? "ar" : "en";
try { const saved = localStorage.getItem("ap-lang"); if (saved === "ar" || saved === "en") lang = saved; } catch (e) { /* storage may be blocked */ }
const t = (k, ...a) => { const v = (I18N[lang] || I18N.en)[k] ?? I18N.en[k] ?? k; return typeof v === "function" ? v(...a) : v; };
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
// Round half to even at one decimal, exactly like Python's formatting, so every number matches the CLI and the README.
const pct = (x) => {
  const n = x * 1000, f = Math.floor(n);
  const r = Math.abs(n - f - 0.5) < 1e-9 ? (f % 2 === 0 ? f : f + 1) : Math.round(n);
  return (r / 10).toFixed(1) + "%";
};
const pct0 = (x) => (x * 100).toFixed(0);

let pyodide = null, api = null, lastCompare = null, selected = null, booted = false;

function setStatus(text) { $("status").textContent = text; }
function applyLang() {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $("lang").textContent = lang === "ar" ? "English" : "العربية";
  $("limitsList").innerHTML = t("limits").map((x) => `<li>${esc(x)}</li>`).join("");
  if (lastCompare) { renderResults(lastCompare); fillExplorer(); renderTrace(); }
  setStatus(booted ? t("ready") : t("loading"));
}

async function boot() {
  try {
    setStatus(t("loading"));
    pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX });
    setStatus(t("loadingFiles"));
    const bundle = await (await fetch("bundle.json")).json();
    for (const [path, text] of Object.entries(bundle.files)) {
      const full = "/home/pyodide/" + path;
      pyodide.FS.mkdirTree(full.slice(0, full.lastIndexOf("/")));
      pyodide.FS.writeFile(full, text);
    }
    pyodide.runPython("import sys; sys.path.insert(0, '/home/pyodide/py')");
    api = pyodide.pyimport("demo_api");
    booted = true;
    ["run", "claudeBtn", "brainBtn", "autoBtn"].forEach((id) => { $(id).disabled = false; });
    setStatus(t("ready"));
    await runCompare();
  } catch (e) {
    console.error(e);
    setStatus(t("failedBoot"));
  }
}

async function busy(btn, fn) {
  btn.disabled = true; setStatus(t("running"));
  await new Promise((r) => setTimeout(r, 30)); // let the browser paint before the blocking Python call
  try { await fn(); } finally { btn.disabled = false; setStatus(t("ready")); }
}
const call = (name, ...args) => JSON.parse(api[name](...args));

/* ---------- 1. chaos lab ---------- */
function selectedAgents() { return [...document.querySelectorAll("fieldset.agents input:checked")].map((i) => i.value); }
async function runCompare() {
  const labels = selectedAgents();
  if (!labels.length) return;
  await busy($("run"), async () => {
    lastCompare = call("run_compare", parseFloat($("chaos").value), parseInt($("runs").value, 10), parseInt($("seed").value || "0", 10), JSON.stringify(labels));
    selected = null;
    renderResults(lastCompare); fillExplorer(); renderTrace();
    $("explorer").hidden = false;
  });
}
function renderResults(d) {
  const labels = Object.keys(d.agents);
  const cards = labels.map((l) => {
    const m = d.agents[l];
    const cls = m.pass_rate >= 0.9 ? "good" : m.pass_rate >= 0.6 ? "warn" : "bad";
    return `<div class="agent"><h3>${esc(l)}</h3><div class="big ${cls}">${pct(m.pass_rate)}</div><div class="muted small">${esc(t("resolved"))}</div>
      <div class="bar"><i data-w="${pct0(m.pass_rate)}"></i></div>
      <div class="kv"><span>${esc(t("unsafe"))}</span><b class="${m.unsafe_rate > 0 ? "bad" : "good"}">${pct(m.unsafe_rate)}</b></div>
      <div class="kv"><span>${esc(t("handed"))}</span><b>${pct(m.safe_fail_rate)}</b></div>
      <div class="kv"><span>${esc(t("reliability"))}</span><b>${pct(m.reliability)}</b></div>
      <div class="kv"><span>${esc(t("calls"))}</span><b>${m.avg_tool_calls}</b></div></div>`;
  }).join("");
  const scen = Object.keys(d.agents[labels[0]].per_scenario);
  const head = `<tr><th>${esc(t("scenario"))}</th>${labels.map((l) => `<th>${esc(l)}</th>`).join("")}</tr>`;
  const rows = scen.map((s) => `<tr><td>${esc(s)}</td>${labels.map((l) => {
    const v = d.agents[l].per_scenario[s];
    const c = v.unsafe > 0 ? "un" : v.safe_fail > 0 ? "sf" : "ok";
    return `<td><span class="cell ${c}" title="${esc(t("cellTitle", v.pass, v.runs, v.unsafe, v.safe_fail))}">${v.pass}/${v.runs}${v.unsafe > 0 ? " ⚠" : ""}</span></td>`;
  }).join("")}</tr>`).join("");
  let take = "";
  if (d.agents.naive && d.agents.hardened) take = `<p class="note">${esc(t("takeaway", pct0(d.agents.naive.unsafe_rate), pct0(d.agents.hardened.unsafe_rate), d.chaos.toFixed(2)))}</p>`;
  $("results").innerHTML = `<div class="cards">${cards}</div>${take}<div class="scroll"><table>${head}${rows}</table></div>`;
  $("results").querySelectorAll("[data-w]").forEach((el) => { el.style.width = el.dataset.w + "%"; }); // CSSOM is allowed by the CSP; inline style attributes are not
}

/* ---------- 2. failure explorer ---------- */
function fillExplorer() {
  if (!lastCompare) return;
  const sel = $("fAgent"), cur = sel.value;
  sel.innerHTML = `<option value="all">${esc(t("all"))}</option>` + Object.keys(lastCompare.agents).map((l) => `<option value="${esc(l)}">${esc(l)}</option>`).join("");
  sel.value = [...sel.options].some((o) => o.value === cur) ? cur : "all";
  renderList();
}
function renderList() {
  if (!lastCompare) return;
  const a = $("fAgent").value, s = $("fStatus").value;
  const items = lastCompare.failures.filter((f) => (a === "all" || f.agent === a) && (s === "all" || f.status === s)).slice(0, 80);
  $("failList").innerHTML = items.length ? items.map((f, i) => `<li role="option" tabindex="0" data-i="${i}" aria-selected="${!!(selected && selected.agent === f.agent && selected.scenario === f.scenario && selected.seed === f.seed)}">
      <span><span class="chip ${f.status}">${f.status}</span> ${esc(f.agent)}</span><small>${esc(f.scenario)} · seed ${f.seed}</small></li>`).join("")
    : `<li>${esc(t("noFailures"))}</li>`;
  $("failList").querySelectorAll("li[data-i]").forEach((li) => {
    const pick = () => { selected = items[+li.dataset.i]; renderList(); renderTrace(); };
    li.addEventListener("click", pick);
    li.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
  });
}
function fmtArgs(args) {
  const parts = Object.entries(args).filter(([, v]) => v !== null).map(([k, v]) => `${k}=${JSON.stringify(v)}`);
  const s = parts.join(", "); return s.length > 70 ? s.slice(0, 67) + "..." : s;
}
function renderTrace(replayHtml) {
  const box = $("traceView");
  if (!selected || !api) { box.innerHTML = `<span class="muted">${esc(t("pickRun"))}</span>`; return; }
  const tr = call("get_trace", selected.agent, selected.scenario, selected.seed);
  const other = tr.agent === "naive" ? "hardened" : "naive";
  const why = (tr.unsafe.length ? tr.unsafe : tr.unmet);
  const rows = tr.events.map((e) => {
    const out = e.error ? `<span class="err">ERROR ${esc(e.error.type)}: ${esc(e.error.message)}</span>` : esc(JSON.stringify(e.result)).slice(0, 90);
    return `<tr class="ev"><td>${e.i}</td><td>${esc(e.tool)}(${esc(fmtArgs(e.args))})</td><td>${out}</td><td>${e.fault ? `<span class="fault">${esc(e.fault)}</span>` : ""}</td></tr>`;
  }).join("");
  box.innerHTML = `<div><span class="chip ${tr.status}">${tr.status}</span> <b>${esc(tr.agent)}</b> · ${esc(tr.scenario)} · seed ${tr.seed}</div>
    <p><b>${esc(t("ticketLbl"))}:</b> ${esc(tr.ticket)}</p>
    <p><b>${esc(t("whyLbl"))}:</b> ${esc(why.length ? why.join("; ") : t("noReason"))}${tr.error ? " · " + esc(tr.error) : ""}</p>
    <div class="scroll"><table><tr><th>${esc(t("step"))}</th><th>${esc(t("call"))}</th><th>${esc(t("outcome"))}</th><th>${esc(t("fault"))}</th></tr>${rows}</table></div>
    <p><button id="rpSame" type="button">${esc(t("replaySame"))}</button> <button id="rpOther" type="button">${esc(t("replayOther", other))}</button></p>
    <div id="rpOut">${replayHtml || ""}</div>`;
  const doReplay = (as) => async () => {
    const r = call("replay_trace", tr.agent, tr.scenario, tr.seed, as);
    const text = r.outcome === "identical" ? t("identical") : t("diverged");
    renderTrace(`<div class="note"><b>${esc(as)}</b>: ${esc(text)}<br><span class="muted small">${esc(t("matched", r.calls_matched, r.calls_recorded))}${r.detail ? " · " + esc(r.detail) : ""}</span></div>`);
  };
  $("rpSame").addEventListener("click", doReplay(tr.agent));
  $("rpOther").addEventListener("click", doReplay(other));
}

/* ---------- 3-5. claude / brain / autonomy ---------- */
async function runClaude() {
  await busy($("claudeBtn"), async () => {
    const m = call("claude_replay");
    $("claudeOut").innerHTML = `<p class="lead ${m.unsafe_rate === 0 ? "good" : "bad"}">${esc(t("claudeFacts", m))}</p><ul class="muted">${t("claudeCaveat").map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`;
  });
}
async function runBrain() {
  await busy($("brainBtn"), async () => {
    const d = call("run_brain", 3), c = t("brainCols");
    $("brainOut").innerHTML = `<div class="scroll"><table><tr>${c.map((x) => `<th>${esc(x)}</th>`).join("")}</tr>${d.rows.map((r) =>
      `<tr><td>${pct0(r.unseen)}%</td><td>${esc(r.system)}</td><td>${pct(r.all)}</td><td>${pct(r.tricky)}</td><td>${pct(r.provenance)}</td></tr>`).join("")}</table></div><p class="note small">${esc(t("brainNote"))}</p>`;
  });
}
const SPARK = "▁▂▃▄▅▆▇█";
const spark = (v) => v.map((x) => SPARK[Math.min(7, Math.floor(x * 7.999))]).join("");
async function runAuto() {
  await busy($("autoBtn"), async () => {
    const d = call("run_autonomy"), c = t("autoCols");
    $("autoOut").innerHTML = `<div class="scroll"><table><tr>${c.map((x) => `<th>${esc(x)}</th>`).join("")}</tr>${Object.entries(d.policies).map(([k, v]) =>
      `<tr><td>${esc(k)}</td><td>${pct(v.ask_rate)}</td><td class="${v.bad_auto_rate > 0.05 ? "bad" : v.bad_auto_rate > 0 ? "warn" : "good"}">${pct(v.bad_auto_rate)}</td><td>${spark(v.ask_by_window)}</td></tr>`).join("")}</table></div><p class="note small">${esc(t("autoNote"))}</p>`;
  });
}

/* ---------- wiring ---------- */
document.addEventListener("DOMContentLoaded", () => {
  applyLang();
  $("lang").addEventListener("click", () => { lang = lang === "ar" ? "en" : "ar"; try { localStorage.setItem("ap-lang", lang); } catch (e) { /* ignore */ } applyLang(); });
  $("chaos").addEventListener("input", () => { $("chaosOut").textContent = parseFloat($("chaos").value).toFixed(2); });
  $("run").addEventListener("click", runCompare);
  $("fAgent").addEventListener("change", renderList);
  $("fStatus").addEventListener("change", renderList);
  $("claudeBtn").addEventListener("click", runClaude);
  $("brainBtn").addEventListener("click", runBrain);
  $("autoBtn").addEventListener("click", runAuto);
  window.addEventListener("load", boot);
});
