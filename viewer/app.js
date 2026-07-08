// 리뷰 뷰어 (프레임워크 無). 구조: 책 > 교지(런) > 스테이지.
// 첫 화면=장 목록(교정 현황) → 클릭 시 편집 화면(좌우 대비).
// 상단 #book=책, #run=편집 교지, #left-src=원문 또는 임의 교지. 대비=좌 vs 우.
let currentCid = null, activeRun = null, activeBook = null, runVersions = [], enText = "";
const $ = (id) => document.getElementById(id);

// 공통 쿼리스트링: 지정한 파라미터 + 항상 book. run 은 명시할 때만.
function qy(params) {
  const p = { book: activeBook, ...params };
  const s = Object.entries(p).filter(([, v]) => v != null && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
  return s ? "?" + s : "";
}

function esc(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
function inline(s) { return esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\[([^\]]+)\]\([^)]+\)/g, "$1"); }
function renderMd(md, cid) {
  const lines = (md || "").replace(/\r\n/g, "\n").split("\n");
  let html = "", inList = false, para = [];
  const flushPara = () => { if (para.length) { const t = para.join(" ").trim(); if (t) html += `<p>${inline(t)}</p>`; para = []; } };
  const closeList = () => { if (inList) { html += "</ul>"; inList = false; } };
  for (let raw of lines) {
    const line = raw.replace(/\s+$/, "");
    const img = line.match(/^\s*!\[(.*?)\]\(([^)]+)\)\s*$/);
    if (img) { flushPara(); closeList(); const file = img[2].split("/").pop();
      html += `<figure><img src="/figures/${cid}/${file}${qy({})}" alt="${esc(img[1])}">`;
      if (img[1]) html += `<figcaption style="text-align:center;color:#566;font-size:13px">${esc(img[1])}</figcaption>`;
      html += `</figure>`; continue; }
    if (!line.trim()) { flushPara(); closeList(); continue; }
    let m;
    if ((m = line.match(/^(#{1,6})\s+(.*)$/))) { flushPara(); closeList(); const lvl = m[1].length; html += `<h${lvl}>${inline(m[2])}</h${lvl}>`; continue; }
    if ((m = line.match(/^\s*[-*+]\s+(.*)$/))) { flushPara(); if (!inList) { html += "<ul>"; inList = true; } html += `<li>${inline(m[1])}</li>`; continue; }
    if ((m = line.match(/^>\s?(.*)$/))) { flushPara(); closeList(); html += `<blockquote>${inline(m[1])}</blockquote>`; continue; }
    para.push(line);
  }
  flushPara(); closeList(); return html;
}
function lineDiff(a, b) {
  const A = a.split("\n"), B = b.split("\n"), n = A.length, m = B.length;
  const dp = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--)
    dp[i][j] = A[i] === B[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  let i = 0, j = 0, out = "";
  const L = (cls, t) => t.trim() ? `<div class="dl ${cls}">${esc(t)}</div>` : (cls === "same" ? "" : `<div class="dl ${cls}">&nbsp;</div>`);
  while (i < n && j < m) {
    if (A[i] === B[j]) { out += L("same", A[i]); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { out += L("del", A[i]); i++; }
    else { out += L("add", B[j]); j++; }
  }
  while (i < n) out += L("del", A[i++]);
  while (j < m) out += L("add", B[j++]);
  return out;
}

async function loadBooks() {
  const d = await (await fetch("/api/books")).json();
  activeBook = d.active;
  const bs = $("book"); bs.innerHTML = "";
  (d.books || []).forEach((b) => { const o = document.createElement("option"); o.value = b; o.textContent = b; bs.appendChild(o); });
  bs.value = activeBook;
}
async function loadRuns() {
  const d = await (await fetch("/api/runs" + qy({}))).json();
  runVersions = d.versions || []; activeRun = d.active; activeBook = d.book || activeBook;
  const rs = $("run"); rs.innerHTML = "";
  runVersions.forEach((v) => { const o = document.createElement("option"); o.value = v.run; o.textContent = `${v.label} · ${v.run}`; rs.appendChild(o); });
  rs.value = activeRun;
  const ls = $("left-src"); ls.innerHTML = "";
  const oen = document.createElement("option"); oen.value = "en"; oen.textContent = "영문 원문"; ls.appendChild(oen);
  runVersions.forEach((v) => { const o = document.createElement("option"); o.value = "v:" + v.run; o.textContent = `${v.label} · ${v.run}`; ls.appendChild(o); });
  ls.value = "en";
}

// ---- 첫 화면: 목록 ----
async function renderIndex() {
  const rows = await (await fetch("/api/index" + qy({ run: activeRun }))).json();
  const tb = $("idx-body"); tb.innerHTML = "";
  rows.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td class="mono">${esc(r.id)}</td><td>${esc(r.title)}</td><td>${esc(r.author)}</td>`
      + `<td><span class="tag">${esc(r.src)}</span></td><td>${r.proofs.map((p) => `<span class="tag proof">${esc(p)}</span>`).join(" ")}</td>`;
    tr.addEventListener("click", () => openEditor(r.id));
    tb.appendChild(tr);
  });
  $("list-book").textContent = activeBook || "";
  setStatus(`교정 현황 · ${activeBook} · ${activeRun} · ${rows.length}개 장`);
}
function showList() {
  $("view-list").classList.remove("hidden"); $("view-editor").classList.add("hidden");
  $("nav-list").classList.add("hidden"); $("editor-tools").classList.add("hidden");
  $("pdf-attach").classList.remove("hidden");   // PDF 첨부는 목록에서만
  renderIndex();
}

// ---- 편집 화면 ----
async function openEditor(cid) {
  $("view-list").classList.add("hidden"); $("view-editor").classList.remove("hidden");
  $("nav-list").classList.remove("hidden"); $("editor-tools").classList.remove("hidden");
  $("pdf-attach").classList.add("hidden");
  await loadChapter(cid);
}
async function loadChapter(cid) {
  currentCid = cid;
  const d = await (await fetch("/api/chapter/" + encodeURIComponent(cid) + qy({ run: activeRun }))).json();
  enText = d.en || ""; $("ko").value = d.latest || ""; $("ko-mode").textContent = d.src;
  $("ed-cid").textContent = cid;
  $("pdf-build").classList.add("hidden");   // 새 장 = hwpx 빌드 전이므로 PDF 버튼 숨김
  await loadLeft(); showEdit(); renderKoPreview();
  setStatus(`${cid} · 편집=${activeRun}(${d.src})`);
}
async function leftText() {
  const v = $("left-src").value;
  if (v === "en") return null;
  const d = await (await fetch(`/api/runtext/${encodeURIComponent(currentCid)}` + qy({ v: v.slice(2) }))).json();
  return d.text || "";
}
async function loadLeft() {
  if ($("left-src").value === "en") { $("en").innerHTML = renderMd(enText, currentCid); }
  else { $("en").innerHTML = renderMd(await leftText(), currentCid); }
}
function renderKoPreview() { $("ko-preview").innerHTML = renderMd($("ko").value, currentCid); }
async function renderDiff() {
  const base = await leftText();
  if (base === null) { $("ko-diff").innerHTML = "<p style='color:#900'>좌측을 ‘교지’로 선택하면 대비가 표시됩니다(영문은 대비 불가).</p>"; return; }
  $("ko-diff").innerHTML = lineDiff(base, $("ko").value);
}
function setStatus(t) { $("status").textContent = t; }
function showEdit() { $("ko").classList.remove("hidden"); $("ko-preview").classList.add("hidden"); $("ko-diff").classList.add("hidden"); $("preview-toggle").textContent = "프리뷰"; $("diff-toggle").classList.remove("on"); }
function togglePreview() {
  const pv = $("ko-preview");
  if (pv.classList.contains("hidden")) { renderKoPreview(); pv.classList.remove("hidden"); $("ko").classList.add("hidden"); $("ko-diff").classList.add("hidden"); $("preview-toggle").textContent = "편집"; $("diff-toggle").classList.remove("on"); }
  else showEdit();
}
async function toggleDiff() {
  const df = $("ko-diff");
  if (df.classList.contains("hidden")) { await renderDiff(); df.classList.remove("hidden"); $("ko").classList.add("hidden"); $("ko-preview").classList.add("hidden"); $("diff-toggle").classList.add("on"); }
  else showEdit();
}
async function save() {
  const r = await fetch("/api/save/" + encodeURIComponent(currentCid) + qy({ run: activeRun }), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ko: $("ko").value }) });
  const j = await r.json(); setStatus(j.ok ? `저장됨 → ${activeRun}/04-review` : "저장 실패"); $("ko-mode").textContent = "04-review";
}
async function build() {
  setStatus("hwpx 빌드 중…");
  const r = await fetch("/api/build/" + encodeURIComponent(currentCid) + qy({ run: activeRun }), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ko: $("ko").value }) });
  const j = await r.json();
  if (!j.ok) { setStatus("빌드 실패: " + j.error); return; }
  setStatus("hwpx 빌드 완료 → " + j.hwpx + "  (한글에서 확인 후 [PDF 빌드])");
  $("pdf-build").classList.remove("hidden");   // hwpx 생기면 PDF 빌드 버튼 노출
}
async function pdfBuild() {
  if (!currentCid) return;
  const b = $("pdf-build"); b.disabled = true;
  setStatus("PDF 변환 중… (한컴)");
  try {
    const r = await fetch("/api/pdf/" + encodeURIComponent(currentCid) + qy({ run: activeRun }),
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    const j = await r.json();
    setStatus(j.ok ? ("PDF 생성됨" + (j.cover_removed ? "(표지 제외)" : "") + " → " + j.pdf + "  (폴더 열림)") : ("PDF 실패: " + j.error));
  } catch (e) { setStatus("PDF 실패: " + e); }
  finally { b.disabled = false; }
}

// ---- 새 원고(PDF) → 워크스페이스 생성 (＋PDF 첨부 모달) ----
function openWs() { $("ws-msg").textContent = ""; $("ws-overlay").classList.remove("hidden"); $("ws-title").focus(); }
function closeWs() { $("ws-overlay").classList.add("hidden"); }
async function createWorkspace(file) {
  const title = ($("ws-title").value || "").trim();
  if (!title) { $("ws-msg").textContent = "책 제목을 먼저 입력하세요."; return; }
  if (!file) { $("ws-msg").textContent = "PDF 파일을 선택/드롭하세요."; return; }
  $("ws-msg").textContent = `업로드·추출 중… (${file.name})`;
  try {
    const buf = await file.arrayBuffer();
    const r = await fetch("/api/workspace?title=" + encodeURIComponent(title),
      { method: "POST", headers: { "Content-Type": "application/pdf" }, body: buf });
    const j = await r.json();
    if (!j.ok) { $("ws-msg").textContent = "실패: " + (j.error || ""); return; }
    $("ws-msg").textContent = `생성됨: ${j.book}`;
    await loadBooks();
    activeBook = j.book;
    const bs = $("book");
    if ([...bs.options].some((o) => o.value === j.book)) bs.value = j.book;
    await loadRuns(); showList();
    closeWs();
  } catch (e) { $("ws-msg").textContent = "실패: " + e; }
}

// ---- LLM(codex) 연결 상태 + GPT 번역/윤문 ----
async function refreshLlmChip() {
  const chip = $("llm-chip");
  try {
    const s = await (await fetch("/api/llm/status")).json();
    if (s.installed && s.authenticated) {
      chip.textContent = `● ${s.label} · ${s.selected_model || "codex 자동"}`;
      chip.className = "chip ok"; chip.title = `연결됨 — 계정: ${s.email || "?"}`;
    } else if (!s.installed) {
      chip.textContent = "● codex 미설치"; chip.className = "chip bad"; chip.title = "codex CLI 설치 필요";
    } else {
      chip.textContent = "● 미로그인"; chip.className = "chip bad"; chip.title = "codex login 필요";
    }
    return s;
  } catch { chip.textContent = "● 상태 불명"; chip.className = "chip bad"; return null; }
}
async function openLlm() {
  $("llm-overlay").classList.remove("hidden");
  const s = await refreshLlmChip();
  const conn = $("llm-conn");
  if (s && s.installed && s.authenticated) {
    conn.innerHTML = `✓ 연결됨 (${esc(s.label)}) — 계정: <b>${esc(s.email || "?")}</b>`; conn.className = "conn ok";
  } else if (s && !s.installed) {
    conn.innerHTML = "codex CLI가 설치되어 있지 않습니다. Node.js 설치 후 <code>npm i -g @openai/codex</code>."; conn.className = "conn bad";
  } else {
    conn.innerHTML = "로그인이 필요합니다. 아래 <b>로그인 관리</b>를 눌러 <code>codex login</code>을 실행하세요."; conn.className = "conn bad";
  }
  await loadModels(false);
}
function closeLlm() { $("llm-overlay").classList.add("hidden"); }
async function loadModels(force) {
  const d = await (await fetch("/api/llm/models" + (force ? "?force=1" : ""))).json();
  const sel = $("llm-model"); sel.innerHTML = "";
  const def = document.createElement("option"); def.value = ""; def.textContent = "기본값 (codex 자동 선택)"; sel.appendChild(def);
  (d.models || []).forEach((m) => { const o = document.createElement("option"); o.value = m; o.textContent = m; sel.appendChild(o); });
  sel.value = d.selected || "";
  $("llm-cur-model").textContent = d.selected || "기본값(codex 자동)";
}
async function applyModel() {
  const m = $("llm-model").value;
  const d = await (await fetch("/api/llm/model", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model: m }) })).json();
  $("llm-model-msg").textContent = d.ok ? "적용되었습니다." : "적용 실패";
  $("llm-cur-model").textContent = d.selected || "기본값(codex 자동)";
  refreshLlmChip();
}
async function llmLogin() {
  const d = await (await fetch("/api/llm/login", { method: "POST" })).json();
  $("llm-model-msg").textContent = d.hint || "";
}
async function llmLogout() { await fetch("/api/llm/logout", { method: "POST" }); await openLlm(); }

function handleLlmError(j, label) {
  setStatus(`GPT ${label} 실패: ${j.error || j.kind || ""}`);
  if (j.kind === "not_installed" || j.kind === "not_authenticated") openLlm();
  else alert(`GPT ${label} 실패:\n${j.error || j.kind}`);
}
async function runLlm(kind) {
  if (!currentCid) return;
  const label = kind === "refine" ? "윤문(03)" : "번역(02)";
  const bt = $("gpt-translate"), br = $("gpt-refine");
  bt.disabled = br.disabled = true;
  setStatus(`GPT ${label} 중… (장 하나에 수 분 걸릴 수 있습니다)`);
  try {
    const ep = kind === "refine" ? "refine" : "translate";
    const r = await fetch(`/api/${ep}/` + encodeURIComponent(currentCid) + qy({ run: activeRun }),
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    const j = await r.json();
    if (j.ok) {
      $("ko").value = j.ko; $("ko-mode").textContent = j.stage; showEdit(); renderKoPreview();
      setStatus(`GPT ${label} 완료 → 검토 후 [교지 저장]/[hwpx 빌드]`);
    } else handleLlmError(j, label);
  } catch (e) { setStatus(`GPT ${label} 실패: ${e}`); }
  finally { bt.disabled = br.disabled = false; }
}

$("ws-drop").addEventListener("click", () => $("ws-file").click());
$("ws-file").addEventListener("change", (e) => { if (e.target.files[0]) createWorkspace(e.target.files[0]); });
$("ws-drop").addEventListener("dragover", (e) => { e.preventDefault(); $("ws-drop").classList.add("over"); });
$("ws-drop").addEventListener("dragleave", () => $("ws-drop").classList.remove("over"));
$("ws-drop").addEventListener("drop", (e) => {
  e.preventDefault(); $("ws-drop").classList.remove("over");
  const f = e.dataTransfer.files[0]; if (f) createWorkspace(f);
});
$("pdf-attach").addEventListener("click", openWs);
$("ws-close").addEventListener("click", closeWs);
$("ws-overlay").addEventListener("click", (e) => { if (e.target === $("ws-overlay")) closeWs(); });

$("llm-settings").addEventListener("click", openLlm);
$("llm-close").addEventListener("click", closeLlm);
$("llm-refresh").addEventListener("click", () => loadModels(true).then(refreshLlmChip));
$("llm-apply").addEventListener("click", applyModel);
$("llm-login").addEventListener("click", llmLogin);
$("llm-logout").addEventListener("click", llmLogout);
$("llm-overlay").addEventListener("click", (e) => { if (e.target === $("llm-overlay")) closeLlm(); });
$("gpt-translate").addEventListener("click", () => runLlm("translate"));
$("gpt-refine").addEventListener("click", () => runLlm("refine"));

$("book").addEventListener("change", async (e) => { activeBook = e.target.value; await loadRuns(); showList(); });
$("nav-list").addEventListener("click", showList);
$("run").addEventListener("change", async (e) => { activeRun = e.target.value; if ($("view-editor").classList.contains("hidden")) renderIndex(); else loadChapter(currentCid); });
$("left-src").addEventListener("change", async () => { await loadLeft(); if (!$("ko-diff").classList.contains("hidden")) renderDiff(); });
$("save").addEventListener("click", save);
$("build").addEventListener("click", build);
$("pdf-build").addEventListener("click", pdfBuild);
$("preview-toggle").addEventListener("click", togglePreview);
$("diff-toggle").addEventListener("click", toggleDiff);
$("ko").addEventListener("input", () => setStatus("편집 중…"));

(async () => { await loadBooks(); await loadRuns(); showList(); refreshLlmChip(); })();
