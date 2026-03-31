export type Contribution = {
  key: string;
  label: string;
  risk: number;
  neutral_raw: number;
  protection: number;
  hard?: boolean;
  explain?: string;
};

export type EvalInput = {
  case_ctx?: Record<string, unknown>;
  contributions: Contribution[];
  app_version?: string;
};

const NEUTRAL_COEF = 0.3;
const GREEN_MAX = 0;
const BLUE_MAX = 9;
const YELLOW_MAX = 15;

const GREEN_ALERT = {
  level: "🟩 绿色预警 (低风险 / 常规关注)",
  core_measure: "以普适性预防为主。",
};

const BLUE_ALERT = {
  level: "🟦 蓝色提示 (轻度风险 / 学校社区协同关注)",
  core_measure: "以学校与社区为主的联合关注，无需立即启动司法干预。",
};

const YELLOW_ALERT = {
  level: "🟨 黄色预警 (中风险 / 重点关注)",
  core_measure: "启动早期、精准的社会干预。",
};

const RED_ALERT = {
  level: "🟥 红色预警 (高风险 / 危机干预)",
  core_measure: "启动多部门协同的危机干预。",
};

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

function hash16(raw: string): string {
  let h = 2166136261;
  for (let i = 0; i < raw.length; i++) {
    h ^= raw.charCodeAt(i);
    h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
  }
  return (h >>> 0).toString(16).padStart(8, "0");
}

export function evaluate(input: EvalInput) {
  if (!Array.isArray(input.contributions) || input.contributions.length === 0) {
    throw new Error("contributions 不能为空");
  }

  const normalized = input.contributions.map((c) => ({
    ...c,
    risk: Number(c.risk) || 0,
    neutral_raw: Number(c.neutral_raw) || 0,
    protection: Number(c.protection) || 0,
    hard: Boolean(c.hard),
    explain: c.explain ?? "",
  }));

  const total_risk_score = normalized.reduce((s, c) => s + c.risk, 0);
  const total_neutral_raw = normalized.reduce((s, c) => s + c.neutral_raw, 0);
  const total_protection_score = normalized.reduce((s, c) => s + c.protection, 0);

  const hard_flags = normalized.filter((c) => c.hard).map((c) => c.label);

  let eff_protection = total_protection_score;
  const eff_neutral = total_neutral_raw * NEUTRAL_COEF;

  const core_risk_val = total_risk_score;
  const prot_cap_factor = hard_flags.length > 0 ? 0.3 : core_risk_val >= 4 ? 0.5 : 0.8;
  if (total_risk_score > 0) {
    eff_protection = clamp(eff_protection, 0, total_risk_score * prot_cap_factor);
  }

  const net_risk_score = total_risk_score - eff_protection - eff_neutral;

  const alert =
    net_risk_score <= GREEN_MAX
      ? GREEN_ALERT
      : net_risk_score <= BLUE_MAX
        ? BLUE_ALERT
        : net_risk_score <= YELLOW_MAX
          ? YELLOW_ALERT
          : RED_ALERT;

  const df_contrib = normalized
    .map((c) => ({ ...c, neutral_eff: c.neutral_raw * NEUTRAL_COEF, net: c.risk - c.protection - c.neutral_raw * NEUTRAL_COEF }))
    .sort((a, b) => b.net - a.net);

  const ts = new Date().toISOString();
  const evalPayload = {
    case: input.case_ctx ?? {},
    net_risk_score: Number(net_risk_score.toFixed(3)),
    alert_level: alert.level,
    hard_flags,
    app_version: input.app_version ?? "cf-worker-0.1.0",
    ts,
  };
  const eval_id = `EV-${ts.slice(0, 10).replace(/-/g, "")}-${hash16(JSON.stringify(evalPayload))}`;

  return {
    eval_id,
    ts,
    alert,
    hard_flags,
    total_risk_score,
    total_neutral_raw,
    total_protection_score,
    eff_protection,
    eff_neutral,
    net_risk_score,
    contributions: df_contrib,
    eval_payload: { ...evalPayload, eval_id },
  };
}
