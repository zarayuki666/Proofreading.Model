export type Contribution = {
  key: string;
  label: string;
  risk: number;
  neutral_raw: number;
  protection: number;
  hard?: boolean;
  explain?: string;
};

export type RawScoreInput = {
  key: string;
  label?: string;
  score: number; // 0-5
  hard?: boolean;
  explain?: string;
};

export type EvalInput = {
  case_ctx?: Record<string, unknown>;
  contributions?: Contribution[];
  raw_scores?: RawScoreInput[];
  app_version?: string;
};

const NEUTRAL_COEF = 0.3;
const GREEN_MAX = 0;
const BLUE_MAX = 9;
const YELLOW_MAX = 15;

const ADJUSTMENT_MAP: Record<string, Record<string, number>> = {
  a3_1: { "0": 0.1806, "1": 0.2025, "2": 0.3471, "3": 0.5044, "4": 0.6389, "5": 0.6755 },
  a3_2: { "0": 0.1957, "1": 0.2213, "2": 0.2834, "3": 0.5925, "4": 0.5925, "5": 0.5925 },
  b1_1: { "0": 0.2149, "1": 0.235, "2": 0.2988, "3": 0.4947, "4": 0.5916, "5": 0.6637 },
  b1_2: { "0": 0.2289, "1": 0.2361, "2": 0.3032, "3": 0.4972, "4": 0.5929, "5": 0.6703 },
  b3: { "0": 0.1959, "1": 0.2189, "2": 0.2909, "3": 0.4803, "4": 0.5224, "5": 0.5224 },
  c1: { "0": 0.2186, "1": 0.2359, "2": 0.2962, "3": 0.4949, "4": 0.6395, "5": 0.6395 },
  c2: { "0": 0.2401, "1": 0.2401, "2": 0.2976, "3": 0.4879, "4": 0.5939, "5": 0.5939 },
  d1: { "0": 0.2265, "1": 0.2371, "2": 0.3035, "3": 0.4971, "4": 0.6445, "5": 0.6445 },
  d2: { "0": 0.4098, "1": 0.4098, "2": 0.4098, "3": 0.4098, "4": 0.4098, "5": 0.4098 },
  e1a: { "0": 0.1911, "1": 0.2843, "2": 0.3045, "3": 0.5358, "4": 0.5724, "5": 0.6201 },
  e1b: { "0": 0.2309, "1": 0.2722, "2": 0.4501, "3": 0.5966, "4": 0.6255, "5": 0.6255 },
  e2: { "0": 0.1989, "1": 0.2703, "2": 0.3693, "3": 0.4891, "4": 0.5601, "5": 0.5601 },
  f1: { "0": 0.7532, "1": 0.7532, "2": 0.7532, "3": 0.7532, "4": 0.7532, "5": 0.7532 },
  f2: { "0": 0.2149, "1": 0.2354, "2": 0.297, "3": 0.4945, "4": 0.5265, "5": 0.7382 },
  g1: { "0": 0.1913, "1": 0.2968, "2": 0.2968, "3": 0.536, "4": 0.5753, "5": 0.6182 },
  g2: { "0": 0.2264, "1": 0.2344, "2": 0.3026, "3": 0.4945, "4": 0.5275, "5": 0.743 },
};

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

function normalizeByRawScores(rawScores: RawScoreInput[]): Contribution[] {
  return rawScores.map((item) => {
    const safeScore = clamp(Math.round(Number(item.score) || 0), 0, 5);
    const mapped = ADJUSTMENT_MAP[item.key]?.[String(safeScore)] ?? safeScore;
    return {
      key: item.key,
      label: item.label ?? item.key,
      risk: Number(mapped),
      neutral_raw: 0,
      protection: 0,
      hard: Boolean(item.hard),
      explain: item.explain ?? `raw_score=${safeScore}`,
    };
  });
}

function normalizeContributions(input: EvalInput): Contribution[] {
  if (Array.isArray(input.contributions) && input.contributions.length > 0) {
    return input.contributions.map((c) => ({
      ...c,
      risk: Number(c.risk) || 0,
      neutral_raw: Number(c.neutral_raw) || 0,
      protection: Number(c.protection) || 0,
      hard: Boolean(c.hard),
      explain: c.explain ?? "",
    }));
  }

  if (Array.isArray(input.raw_scores) && input.raw_scores.length > 0) {
    return normalizeByRawScores(input.raw_scores);
  }

  throw new Error("contributions/raw_scores 至少提供一项");
}

export function evaluate(input: EvalInput) {
  const normalized = normalizeContributions(input);

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
    app_version: input.app_version ?? "cf-worker-0.2.0",
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
