const FACTOR_CATALOG = [
  { key: "a3_1", label: "A3 家庭沟通" },
  { key: "a3_2", label: "A3 家庭冲突" },
  { key: "b1_1", label: "B1 冲动控制" },
  { key: "b1_2", label: "B1 暴力攻击倾向" },
  { key: "b3", label: "B3 自我认同" },
  { key: "c1", label: "C1 同伴关系" },
  { key: "c2", label: "C2 社区环境" },
  { key: "d1", label: "D1 在校表现" },
  { key: "d2", label: "D2 法治教育" },
  { key: "e1a", label: "E1a 上网时间" },
  { key: "e1b", label: "E1b 深夜上网" },
  { key: "e2", label: "E2 内容接触" },
  { key: "f1", label: "F1 情感支持" },
  { key: "f2", label: "F2 情感适应能力" },
  { key: "g1", label: "G1 时间管理" },
  { key: "g2", label: "G2 财务管理" },
];

const state = {
  logs: [],
  result: null,
  factors: [],
};

const $ = (id) => document.getElementById(id);
const now = () => new Date().toLocaleString("zh-CN", { hour12: false });

function buildDefaultFactors() {
  return FACTOR_CATALOG.map((x) => ({
    key: x.key,
    label: x.label,
    score: 0,
    hard: false,
    explain: "",
  }));
}

function addLog(event, payload = {}) {
  state.logs.push({ ts: now(), event, payload });
  renderAudit();
}

function defaultCaseId() {
  const d = new Date();
  return `CASE-${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}-${crypto.randomUUID().slice(0, 8)}`;
}

function alertClass(level = "") {
  if (level.includes("绿色")) return "green";
  if (level.includes("蓝色")) return "blue";
  if (level.includes("黄色")) return "yellow";
  return "red";
}

function sop(level = "") {
  if (level.includes("红色")) return ["立即启动危机干预", "多部门会商处置", "按日复评与留痕"];
  if (level.includes("黄色")) return ["纳入重点关注", "制定个性化帮扶计划", "按周复评"];
  if (level.includes("蓝色")) return ["学校社区协同关注", "补齐保护性资源", "常态跟踪"];
  return ["常态记录", "普适性预防", "定期复评"];
}

function getCaseCtx() {
  return {
    case_id: $("caseId").value,
    role: $("role").value,
    org: $("org").value,
    evaluator: $("evaluator").value,
    student_type: $("studentType").value,
  };
}

function renderHeader() {
  const ctx = getCaseCtx();
  $("headerMeta").innerHTML = `版本：Cloudflare v2 · 案件：${ctx.case_id} · 角色：${ctx.role}`;
}

function factorRow(f, i) {
  return `
    <div class="factor-item">
      <div><b>${f.key}</b></div>
      <div>${f.label}</div>
      <input type="range" min="0" max="5" step="1" value="${f.score}" data-k="score" data-i="${i}" />
      <input value="${f.score}" type="number" min="0" max="5" step="1" data-k="score_num" data-i="${i}" />
      <input ${f.hard ? "checked" : ""} type="checkbox" data-k="hard" data-i="${i}" />
      <input value="${f.explain || ""}" data-k="explain" data-i="${i}" placeholder="备注" />
    </div>`;
}

function renderCollect() {
  const rows = state.factors.map(factorRow).join("");
  $("collect").innerHTML = `
    <div class="card">
      <h3>🧾 评估采集面板（与 app.py 因子口径一致）</h3>
      <p class="small">录入 0~5 原始量表分值，后端会按 adjustment 映射计算风险值。硬触发可手动标记。</p>
      <div class="small" style="display:grid;grid-template-columns:.6fr 1.2fr .8fr .5fr .4fr 1fr;gap:6px;margin:8px 0"><b>键</b><b>因子</b><b>滑杆</b><b>分值</b><b>硬触发</b><b>备注</b></div>
      <div class="factor-list">${rows}</div>
      <div style="display:flex;gap:8px;margin-top:10px">
        <button id="resetFactor">恢复默认因子</button>
      </div>
    </div>`;

  $("collect").querySelectorAll("[data-k]").forEach((el) => {
    const syncScore = (i, val) => {
      const safe = Math.max(0, Math.min(5, Number(val) || 0));
      state.factors[i].score = safe;
      renderCollect();
    };

    el.addEventListener("input", (e) => {
      const i = Number(e.target.dataset.i);
      const k = e.target.dataset.k;
      if (k === "score" || k === "score_num") {
        syncScore(i, e.target.value);
        return;
      }
      state.factors[i][k] = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    });

    el.addEventListener("change", (e) => {
      const i = Number(e.target.dataset.i);
      const k = e.target.dataset.k;
      if (k === "score" || k === "score_num") {
        syncScore(i, e.target.value);
        return;
      }
      state.factors[i][k] = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    });
  });

  $("resetFactor")?.addEventListener("click", () => {
    state.factors = buildDefaultFactors();
    addLog("factor_reset", { n: state.factors.length });
    renderCollect();
  });
}

function renderCockpit() {
  const r = state.result;
  if (!r) {
    $("cockpit").innerHTML = `<div class="card"><h3>⚖️ 司法合规驾驶舱</h3><p class="small">尚未生成研判结果，请先点击“生成合规研判”。</p></div>`;
    return;
  }
  const top = (r.contributions || []).slice(0, 10).map((x) => `<tr><td>${x.key}</td><td>${x.label}</td><td>${x.net?.toFixed?.(2) ?? x.net}</td><td>${x.explain || "-"}</td></tr>`).join("");
  $("cockpit").innerHTML = `
    <div class="grid4">
      <div class="kpi"><div class="small">规则净风险积分</div><div class="v">${Number(r.net_risk_score).toFixed(2)}</div></div>
      <div class="kpi"><div class="small">总风险分</div><div class="v">${Number(r.total_risk_score).toFixed(2)}</div></div>
      <div class="kpi"><div class="small">总保护分</div><div class="v">${Number(r.total_protection_score).toFixed(2)}</div></div>
      <div class="kpi"><div class="small">预警等级</div><div class="badge ${alertClass(r.alert?.level)}">${r.alert?.level || "-"}</div></div>
    </div>
    <div class="card" style="margin-top:12px">
      <h3>🧷 合规处置建议</h3>
      <p>${r.alert?.core_measure || ""}</p>
      <ul>${sop(r.alert?.level).map((s) => `<li>${s}</li>`).join("")}</ul>
      ${r.hard_flags?.length ? `<p class='small'>硬触发项：${r.hard_flags.join("；")}</p>` : ""}
    </div>
    <div class="card" style="margin-top:12px">
      <h3>🧠 TOP 风险因子</h3>
      <table class="table"><thead><tr><th>Key</th><th>因子</th><th>净贡献</th><th>说明</th></tr></thead><tbody>${top || "<tr><td colspan='4'>暂无</td></tr>"}</tbody></table>
    </div>`;
}

function renderRules() {
  const r = state.result;
  $("rules").innerHTML = `
    <div class="card">
      <h3>🔎 规则命中解释与可解释性</h3>
      <ul>
        <li>输入模式：raw_scores（0~5）→ adjustment 映射成 risk。</li>
        <li>中性折扣：neutral_eff = neutral_raw × 0.30。</li>
        <li>保护限幅：按硬触发和核心风险动态限制抵消比例。</li>
      </ul>
      ${r ? `<p>净风险：<b>${Number(r.net_risk_score).toFixed(2)}</b>；预警：<b>${r.alert.level}</b>；研判编号：<code>${r.eval_id}</code></p>` : "<p class='small'>未生成研判结果，暂无法展示命中细节。</p>"}
    </div>`;
}

function renderAudit() {
  const r = state.result;
  const rows = state.logs.slice(-30).reverse().map((x) => `<tr><td>${x.ts}</td><td>${x.event}</td><td>${JSON.stringify(x.payload)}</td></tr>`).join("");
  $("audit").innerHTML = `
    <div class="card">
      <h3>🗂️ 审计留痕与导出</h3>
      <p class="small">可下载当前研判 JSON（脱敏由你在提交前自行处理）。</p>
      <button id="downloadJson" ${r ? "" : "disabled"}>⬇️ 下载研判 JSON</button>
      <table class="table" style="margin-top:10px"><thead><tr><th>时间</th><th>事件</th><th>载荷</th></tr></thead><tbody>${rows || "<tr><td colspan='3'>暂无日志</td></tr>"}</tbody></table>
    </div>`;
  $("downloadJson")?.addEventListener("click", () => {
    if (!state.result) return;
    const blob = new Blob([JSON.stringify(state.result, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${state.result.eval_id}.json`;
    a.click();
  });
}

function renderSettings() {
  $("settings").innerHTML = `<div class="card"><h3>⚙️ 系统设置</h3><ul><li>当前部署：Cloudflare Workers + Static Assets</li><li>接口：POST /api/evaluate（raw_scores）</li><li>建议：生产开启 Cloudflare Access、WAF 与速率限制。</li></ul></div>`;
}

async function evaluateNow() {
  const payload = {
    case_ctx: getCaseCtx(),
    raw_scores: state.factors.map((x) => ({
      key: x.key,
      label: x.label,
      score: Number(x.score) || 0,
      hard: Boolean(x.hard),
      explain: x.explain || "",
    })),
  };

  const res = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    addLog("evaluation_failed", data);
    alert(data.error || "生成失败");
    return;
  }

  state.result = data;
  addLog("evaluation_created", { eval_id: data.eval_id, alert: data.alert?.level });
  renderAll();
}

function seedFactors() {
  state.factors = buildDefaultFactors();
  const boost = {
    a3_1: 4,
    b1_2: 4,
    e2: 5,
    c1: 4,
  };
  state.factors = state.factors.map((x) => ({
    ...x,
    score: boost[x.key] ?? 1,
    hard: x.key === "b1_2" || x.key === "e2",
    explain: boost[x.key] ? "示例高风险" : "示例低风险",
  }));
  addLog("seed_loaded", { n: state.factors.length });
  renderCollect();
}

function initTabs() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");
      $(btn.dataset.tab).classList.add("active");
    });
  });
}

function renderAll() {
  renderHeader();
  renderCollect();
  renderCockpit();
  renderRules();
  renderAudit();
  renderSettings();
}

function init() {
  state.factors = buildDefaultFactors();
  $("caseId").value = defaultCaseId();
  ["role", "caseId", "org", "evaluator", "studentType"].forEach((id) => $(id).addEventListener("input", renderHeader));
  $("btnGenerate").addEventListener("click", evaluateNow);
  $("btnSeed").addEventListener("click", seedFactors);
  initTabs();
  addLog("app_loaded", { version: "cloudflare-ui-v2" });
  renderAll();
}

init();
