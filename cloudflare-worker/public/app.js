const state = {
  logs: [],
  result: null,
  factors: [],
};

const $ = (id) => document.getElementById(id);
const now = () => new Date().toLocaleString("zh-CN", { hour12: false });

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
  if (level.includes("红色")) return ["启动应急复核", "跨部门联动", "最小必要告知"];
  if (level.includes("黄色")) return ["纳入重点关注", "制定干预计划", "按周复评"];
  if (level.includes("蓝色")) return ["常态跟踪", "补齐保护性资源"];
  return ["常态记录", "定期复评"];
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
  $("headerMeta").innerHTML = `版本：Cloudflare v1 · 案件：${ctx.case_id} · 角色：${ctx.role}`;
}

function factorRow(f, i) {
  return `
    <div class="factor-item">
      <input value="${f.label}" data-k="label" data-i="${i}" placeholder="因子名称" />
      <input value="${f.risk}" type="number" step="0.1" data-k="risk" data-i="${i}" />
      <input value="${f.neutral_raw}" type="number" step="0.1" data-k="neutral_raw" data-i="${i}" />
      <input value="${f.protection}" type="number" step="0.1" data-k="protection" data-i="${i}" />
      <input ${f.hard ? "checked" : ""} type="checkbox" data-k="hard" data-i="${i}" />
      <input value="${f.explain || ""}" data-k="explain" data-i="${i}" placeholder="说明" />
      <button class="danger" data-del="${i}">删除</button>
    </div>`;
}

function renderCollect() {
  const rows = state.factors.map(factorRow).join("");
  $("collect").innerHTML = `
    <div class="card">
      <h3>🧾 评估采集面板（完整录入）</h3>
      <p class="small">输入每个风险因子的风险/中性/保护值，支持硬触发标记，与你原系统规则引擎的汇总方向一致。</p>
      <div class="factor-list">${rows || "<p class='small'>暂无因子，请点击“新增因子”或“填充示例因子”。</p>"}</div>
      <div style="display:flex;gap:8px;margin-top:10px">
        <button id="addFactor">+ 新增因子</button>
        <button id="clearFactor">清空</button>
      </div>
    </div>`;

  $("collect").querySelectorAll("[data-k]").forEach((el) => {
    el.addEventListener("input", (e) => {
      const i = Number(e.target.dataset.i);
      const k = e.target.dataset.k;
      state.factors[i][k] = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    });
    el.addEventListener("change", (e) => {
      const i = Number(e.target.dataset.i);
      const k = e.target.dataset.k;
      state.factors[i][k] = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    });
  });

  $("collect").querySelectorAll("[data-del]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.factors.splice(Number(btn.dataset.del), 1);
      renderCollect();
    });
  });

  $("addFactor")?.addEventListener("click", () => {
    state.factors.push({ label: "新因子", risk: 0, neutral_raw: 0, protection: 0, hard: false, explain: "" });
    renderCollect();
  });
  $("clearFactor")?.addEventListener("click", () => {
    state.factors = [];
    renderCollect();
  });
}

function renderCockpit() {
  const r = state.result;
  if (!r) {
    $("cockpit").innerHTML = `<div class="card"><h3>⚖️ 司法合规驾驶舱</h3><p class="small">尚未生成研判结果，请先在左侧点击“生成合规研判”。</p></div>`;
    return;
  }
  const top = (r.contributions || []).slice(0, 8).map((x) => `<tr><td>${x.label}</td><td>${x.net?.toFixed?.(2) ?? x.net}</td><td>${x.explain || "-"}</td></tr>`).join("");
  $("cockpit").innerHTML = `
    <div class="grid4">
      <div class="kpi"><div class="small">规则净风险积分</div><div class="v">${Number(r.net_risk_score).toFixed(1)}</div></div>
      <div class="kpi"><div class="small">总风险分</div><div class="v">${Number(r.total_risk_score).toFixed(1)}</div></div>
      <div class="kpi"><div class="small">总保护分</div><div class="v">${Number(r.total_protection_score).toFixed(1)}</div></div>
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
      <table class="table"><thead><tr><th>因子</th><th>净贡献</th><th>说明</th></tr></thead><tbody>${top || "<tr><td colspan='3'>暂无</td></tr>"}</tbody></table>
    </div>`;
}

function renderRules() {
  const r = state.result;
  $("rules").innerHTML = `
    <div class="card">
      <h3>🔎 规则命中解释与可解释性</h3>
      <ul>
        <li>规则引擎：按因子汇总 risk / neutral / protection。</li>
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
  $("settings").innerHTML = `<div class="card"><h3>⚙️ 系统设置</h3><ul><li>当前部署：Cloudflare Workers + Static Assets</li><li>接口：POST /api/evaluate</li><li>建议：生产开启 Cloudflare Access 与速率限制。</li></ul></div>`;
}

async function evaluateNow() {
  const payload = {
    case_ctx: getCaseCtx(),
    contributions: state.factors.map((x, i) => ({
      key: `f_${i + 1}`,
      label: x.label || `因子${i + 1}`,
      risk: Number(x.risk) || 0,
      neutral_raw: Number(x.neutral_raw) || 0,
      protection: Number(x.protection) || 0,
      hard: Boolean(x.hard),
      explain: x.explain || "",
    })),
  };

  if (!payload.contributions.length) {
    alert("请先在采集面板添加至少一个因子");
    return;
  }

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
  state.factors = [
    { label: "A1 监护状况", risk: 4.4, neutral_raw: 1, protection: 0, hard: false, explain: "监护薄弱" },
    { label: "B1 攻击倾向", risk: 3, neutral_raw: 0, protection: 0, hard: true, explain: "频繁冲突" },
    { label: "E2 有害内容接触", risk: 4, neutral_raw: 0, protection: 0, hard: true, explain: "高频暴力内容" },
    { label: "F1 情感支持", risk: 0, neutral_raw: 0, protection: 2, hard: false, explain: "存在一定支持" },
  ];
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
  $("caseId").value = defaultCaseId();
  ["role", "caseId", "org", "evaluator", "studentType"].forEach((id) => $(id).addEventListener("input", renderHeader));
  $("btnGenerate").addEventListener("click", evaluateNow);
  $("btnSeed").addEventListener("click", seedFactors);
  initTabs();
  addLog("app_loaded", { version: "cloudflare-ui-v1" });
  renderAll();
}

init();
