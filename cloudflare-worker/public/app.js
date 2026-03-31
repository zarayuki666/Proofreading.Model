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
  schema: null,
  responses: {},
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
  if (level.includes("红色")) return ["立即启动危机干预小组", "跨部门联动处置", "按日复评与留痕"];
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
  $("headerMeta").innerHTML = `版本：Cloudflare v3 · 案件：${ctx.case_id} · 角色：${ctx.role}`;
  $("headerMeta").innerHTML = `版本：Cloudflare v2 · 案件：${ctx.case_id} · 角色：${ctx.role}`;
}

function ensureResponseForQuestion(qKey, qCfg) {
  if (state.responses[qKey]) return;
  if (qCfg.type === "scale") state.responses[qKey] = { score: 0 };
  if (qCfg.type === "group") state.responses[qKey] = { subs: Object.fromEntries(qCfg.subquestions.map((s) => [s.key, 0])) };
  if (qCfg.type === "mcq") state.responses[qKey] = { selected: 0 };
  if (qCfg.type === "multi") state.responses[qKey] = { selected: [] };
  if (qCfg.type === "hybrid") state.responses[qKey] = { selected: 0, scale: 0 };
  if (qCfg.type === "hybrid_multi") state.responses[qKey] = { selected: [], scale: 0 };
}

function renderScaleInput(name, value, min = 0, max = 5) {
  return `
    <div class="scale-row">
      <input type="range" min="${min}" max="${max}" step="1" value="${value}" data-name="${name}" data-kind="range" />
      <input type="number" min="${min}" max="${max}" step="1" value="${value}" data-name="${name}" data-kind="number" />
    <div class="factor-item">
      <div><b>${f.key}</b></div>
      <div>${f.label}</div>
      <input type="range" min="0" max="5" step="1" value="${f.score}" data-k="score" data-i="${i}" />
      <input value="${f.score}" type="number" min="0" max="5" step="1" data-k="score_num" data-i="${i}" />
      <input ${f.hard ? "checked" : ""} type="checkbox" data-k="hard" data-i="${i}" />
      <input value="${f.explain || ""}" data-k="explain" data-i="${i}" placeholder="备注" />
    </div>`;
}

function renderQuestion(qKey, qCfg) {
  ensureResponseForQuestion(qKey, qCfg);
  const r = state.responses[qKey];
  if (qCfg.type === "scale") {
    return `<div class="q-card"><h4>${qCfg.title}</h4><p class="small">${qCfg.scale_label || "量表评分"}</p>${renderScaleInput(`${qKey}.score`, r.score)}</div>`;
  }

  if (qCfg.type === "group") {
    const subs = qCfg.subquestions
      .map((s) => `<div class="sub-q"><label>${s.title}</label><p class="small">${s.scale_label || "量表评分"}</p>${renderScaleInput(`${qKey}.subs.${s.key}`, r.subs[s.key] ?? 0)}</div>`)
      .join("");
    return `<div class="q-card"><h4>${qCfg.title}</h4>${subs}</div>`;
  }

  if (qCfg.type === "mcq") {
    const ops = qCfg.options
      .map((op, i) => `<label class="op"><input type="radio" name="${qKey}.selected" value="${i}" ${Number(r.selected) === i ? "checked" : ""} /> ${op.label}</label>`)
      .join("");
    return `<div class="q-card"><h4>${qCfg.title}</h4>${ops}</div>`;
  }

  if (qCfg.type === "multi") {
    const ops = qCfg.options
      .map((op, i) => `<label class="op"><input type="checkbox" data-name="${qKey}.selected" value="${i}" ${(r.selected || []).includes(i) ? "checked" : ""} /> ${op.label}</label>`)
      .join("");
    return `<div class="q-card"><h4>${qCfg.title}</h4>${ops}</div>`;
  }

  if (qCfg.type === "hybrid") {
    const ops = qCfg.mcq
      .map((op, i) => `<label class="op"><input type="radio" name="${qKey}.selected" value="${i}" ${Number(r.selected) === i ? "checked" : ""} /> ${op.label}</label>`)
      .join("");
    const selected = qCfg.mcq[Number(r.selected)] || {};
    const scale = selected.activates_scale ? `<div class="sub-q"><p class="small">${qCfg.scale?.scale_label || "补充量表"}</p>${renderScaleInput(`${qKey}.scale`, r.scale ?? 0)}</div>` : "";
    return `<div class="q-card"><h4>${qCfg.title}</h4>${ops}${scale}</div>`;
  }

  if (qCfg.type === "hybrid_multi") {
    const ops = qCfg.mcq_multi
      .map((op, i) => `<label class="op"><input type="checkbox" data-name="${qKey}.selected" value="${i}" ${(r.selected || []).includes(i) ? "checked" : ""} /> ${op.label}</label>`)
      .join("");
    const activated = (r.selected || []).some((i) => qCfg.mcq_multi[i]?.activates_scale);
    const scale = activated ? `<div class="sub-q"><p class="small">${qCfg.scale?.scale_label || "补充量表"}</p>${renderScaleInput(`${qKey}.scale`, r.scale ?? 0)}</div>` : "";
    return `<div class="q-card"><h4>${qCfg.title}</h4>${ops}${scale}</div>`;
  }

  return `<div class="q-card"><h4>${qCfg.title || qKey}</h4><p class="small">暂未支持题型：${qCfg.type}</p></div>`;
}

function renderCollect() {
  if (!state.schema) {
    $("collect").innerHTML = `<div class="card"><p>问卷配置加载中...</p></div>`;
    return;
  }

  const sections = Object.entries(state.schema.QUESTIONS_GROUPS)
    .map(([sName, sec]) => {
      const qs = Object.entries(sec)
        .map(([qKey, qCfg]) => renderQuestion(qKey, qCfg))
        .join("");
      return `<div class="card" style="margin-bottom:10px"><h3>${sName}</h3>${qs}</div>`;
    })
    .join("");

  $("collect").innerHTML = `${sections}<div class="card"><button id="resetQuestionnaire">重置整套问卷</button></div>`;

  $("collect").querySelectorAll('input[type="range"], input[type="number"]').forEach((el) => {
    const apply = (raw) => {
      const v = Math.max(0, Math.min(5, Number(raw) || 0));
      const name = el.dataset.name;
      const path = name.split(".");
      if (path.length === 2) state.responses[path[0]][path[1]] = v;
      if (path.length === 3) state.responses[path[0]][path[1]][path[2]] = v;
      renderCollect();
    };
    el.addEventListener("input", (e) => apply(e.target.value));
    el.addEventListener("change", (e) => apply(e.target.value));
  });

  $("collect").querySelectorAll('input[type="radio"]').forEach((el) => {
    el.addEventListener("change", (e) => {
      const [qKey, field] = e.target.name.split(".");
      state.responses[qKey][field] = Number(e.target.value);
      renderCollect();
    });
  });

  $("collect").querySelectorAll('input[type="checkbox"][data-name]').forEach((el) => {
    el.addEventListener("change", (e) => {
      const [qKey, field] = e.target.dataset.name.split(".");
      const idx = Number(e.target.value);
      const arr = new Set(state.responses[qKey][field] || []);
      if (e.target.checked) arr.add(idx);
      else arr.delete(idx);
      state.responses[qKey][field] = [...arr].sort((a, b) => a - b);
      renderCollect();
    });
  });

  $("resetQuestionnaire")?.addEventListener("click", () => {
    state.responses = {};
    renderCollect();
  });
}

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function buildContributions() {
  const out = [];
  const groups = state.schema.QUESTIONS_GROUPS;

  Object.values(groups).forEach((sec) => {
    Object.entries(sec).forEach(([qKey, qCfg]) => {
      const r = state.responses[qKey] || {};

      if (qCfg.type === "scale") {
        const score = Number(r.score) || 0;
        out.push({ key: qKey, label: qCfg.title, risk: score, neutral_raw: 0, protection: 0, hard: qCfg.hard_threshold ? score >= qCfg.hard_threshold : false, explain: `scale=${score}` });
        return;
      }

      if (qCfg.type === "group") {
        (qCfg.subquestions || []).forEach((s) => {
          const score = Number(r.subs?.[s.key]) || 0;
          out.push({ key: s.key, label: s.title, risk: score, neutral_raw: 0, protection: 0, hard: s.hard_threshold ? score >= s.hard_threshold : false, explain: `scale=${score}` });
        });
        return;
      }

      if (qCfg.type === "mcq") {
        const op = qCfg.options?.[Number(r.selected) || 0] || { r: 0, n: 0, p: 0 };
        out.push({ key: qKey, label: qCfg.title, risk: Number(op.r) || 0, neutral_raw: Number(op.n) || 0, protection: Number(op.p) || 0, hard: Boolean(op.hard_trigger), explain: op.label || "" });
        return;
      }

      if (qCfg.type === "multi") {
        const selected = (r.selected || []).map((i) => qCfg.options[i]).filter(Boolean);
        let risk = selected.reduce((s, op) => s + (Number(op.r) || 0), 0);
        const neutral = selected.reduce((s, op) => s + (Number(op.n) || 0), 0);
        const protection = selected.reduce((s, op) => s + (Number(op.p) || 0), 0);
        if (typeof qCfg.max_risk === "number") risk = clamp(risk, 0, qCfg.max_risk);
        out.push({ key: qKey, label: qCfg.title, risk, neutral_raw: neutral, protection, hard: selected.some((op) => op.hard_trigger), explain: selected.map((op) => op.label).join("；") || "未选择" });
        return;
      }

      if (qCfg.type === "hybrid") {
        const op = qCfg.mcq?.[Number(r.selected) || 0] || { r: 0, n: 0, p: 0 };
        const scaleActivated = Boolean(op.activates_scale);
        const scaleVal = scaleActivated ? Number(r.scale) || 0 : 0;
        const scaleHard = qCfg.scale?.hard_threshold ? scaleVal >= qCfg.scale.hard_threshold : false;
        out.push({ key: qKey, label: qCfg.title, risk: (Number(op.r) || 0) + scaleVal, neutral_raw: Number(op.n) || 0, protection: Number(op.p) || 0, hard: Boolean(op.hard_trigger) || scaleHard, explain: `${op.label || ""}${scaleActivated ? ` + scale=${scaleVal}` : ""}` });
        return;
      }

      if (qCfg.type === "hybrid_multi") {
        const selectedOps = (r.selected || []).map((i) => qCfg.mcq_multi[i]).filter(Boolean);
        const scaleActivated = selectedOps.some((op) => op.activates_scale);
        const scaleVal = scaleActivated ? Number(r.scale) || 0 : 0;
        const scaleHard = qCfg.scale?.hard_threshold ? scaleVal >= qCfg.scale.hard_threshold : false;
        out.push({
          key: qKey,
          label: qCfg.title,
          risk: selectedOps.reduce((s, op) => s + (Number(op.r) || 0), 0) + scaleVal,
          neutral_raw: selectedOps.reduce((s, op) => s + (Number(op.n) || 0), 0),
          protection: selectedOps.reduce((s, op) => s + (Number(op.p) || 0), 0),
          hard: selectedOps.some((op) => op.hard_trigger) || scaleHard,
          explain: `${selectedOps.map((op) => op.label).join("；") || "未选择"}${scaleActivated ? ` + scale=${scaleVal}` : ""}`,
        });
      }
    });
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

  return out;
}

function renderCockpit() {
  const r = state.result;
  if (!r) {
    $("cockpit").innerHTML = `<div class="card"><h3>⚖️ 司法合规驾驶舱</h3><p class="small">尚未生成研判结果，请先点击“生成合规研判”。</p></div>`;
    return;
  }
  const top = (r.contributions || []).slice(0, 12).map((x) => `<tr><td>${x.key}</td><td>${x.label}</td><td>${x.net?.toFixed?.(2) ?? x.net}</td><td>${x.explain || "-"}</td></tr>`).join("");
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
        <li>问卷题型：scale / mcq / multi / group / hybrid / hybrid_multi（来源于 app.py）。</li>
        <li>输入模式：raw_scores（0~5）→ adjustment 映射成 risk。</li>
        <li>中性折扣：neutral_eff = neutral_raw × 0.30。</li>
        <li>保护限幅：按硬触发与核心风险动态限幅。</li>
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
  $("settings").innerHTML = `<div class="card"><h3>⚙️ 系统设置</h3><ul><li>当前部署：Cloudflare Workers + Static Assets</li><li>问卷配置：public/questionnaire.schema.json（由 app.py 生成）</li><li>建议：生产开启 Cloudflare Access、WAF 与速率限制。</li></ul></div>`;
  $("settings").innerHTML = `<div class="card"><h3>⚙️ 系统设置</h3><ul><li>当前部署：Cloudflare Workers + Static Assets</li><li>接口：POST /api/evaluate（raw_scores）</li><li>建议：生产开启 Cloudflare Access、WAF 与速率限制。</li></ul></div>`;
}

async function evaluateNow() {
  if (!state.schema) {
    alert("问卷配置未加载完成");
    return;
  }
  const payload = {
    case_ctx: getCaseCtx(),
    contributions: buildContributions(),
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

function seedQuestionnaire() {
  if (!state.schema) return;
  state.responses = {};
  Object.values(state.schema.QUESTIONS_GROUPS).forEach((sec) => {
    Object.entries(sec).forEach(([qKey, qCfg]) => {
      ensureResponseForQuestion(qKey, qCfg);
      if (qCfg.type === "scale") state.responses[qKey].score = 3;
      if (qCfg.type === "group") Object.keys(state.responses[qKey].subs).forEach((k) => (state.responses[qKey].subs[k] = 3));
      if (qCfg.type === "mcq") state.responses[qKey].selected = Math.min(1, (qCfg.options || []).length - 1);
      if (qCfg.type === "multi") state.responses[qKey].selected = [0];
      if (qCfg.type === "hybrid") {
        state.responses[qKey].selected = Math.min(1, (qCfg.mcq || []).length - 1);
        state.responses[qKey].scale = 3;
      }
      if (qCfg.type === "hybrid_multi") {
        state.responses[qKey].selected = [0];
        state.responses[qKey].scale = 3;
      }
    });
  });
  addLog("seed_loaded", { questions: Object.keys(state.responses).length });
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

async function loadSchema() {
  const res = await fetch("/questionnaire.schema.json", { cache: "no-store" });
  if (!res.ok) throw new Error("加载问卷配置失败");
  state.schema = await res.json();
}

async function init() {
function init() {
  state.factors = buildDefaultFactors();
  $("caseId").value = defaultCaseId();
  ["role", "caseId", "org", "evaluator", "studentType"].forEach((id) => $(id).addEventListener("input", renderHeader));
  $("btnGenerate").addEventListener("click", evaluateNow);
  $("btnSeed").addEventListener("click", seedQuestionnaire);
  initTabs();

  try {
    await loadSchema();
    addLog("schema_loaded", { sections: Object.keys(state.schema.QUESTIONS_GROUPS || {}).length });
  } catch (e) {
    addLog("schema_failed", { error: e.message });
    alert(`问卷配置加载失败: ${e.message}`);
  }

  addLog("app_loaded", { version: "cloudflare-ui-v3" });
  addLog("app_loaded", { version: "cloudflare-ui-v2" });
  renderAll();
}

init();
