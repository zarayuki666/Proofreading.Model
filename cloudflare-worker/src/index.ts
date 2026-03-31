import { evaluate, type EvalInput } from "./engine";

type Env = {
  ASSETS: Fetcher;
};

const apiSchema = {
  service: "proofreading-risk-worker",
  version: "0.2.0",
  endpoints: {
    health: "GET /health",
    evaluate: "POST /api/evaluate",
  },
  evaluate_payload: {
    case_ctx: { case_id: "CASE-001" },
    contributions: [
      { key: "a1", label: "监护状况", risk: 4.4, neutral_raw: 1, protection: 0, hard: false },
    ],
    raw_scores: [{ key: "b1_2", label: "暴力攻击倾向", score: 4, hard: true }],
  },
  note: "contributions 与 raw_scores 二选一；若都提供，优先 contributions",
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "GET,POST,OPTIONS",
      "access-control-allow-headers": "content-type",
    },
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const { pathname } = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "access-control-allow-origin": "*",
          "access-control-allow-methods": "GET,POST,OPTIONS",
          "access-control-allow-headers": "content-type",
        },
      });
    }

    if (pathname === "/health") {
      return json({ ok: true, service: "proofreading-risk-worker", version: "0.2.0" });
    }

    if (pathname === "/api/schema" && request.method === "GET") {
      return json(apiSchema);
    }

    if (pathname === "/api/evaluate" && request.method === "POST") {
      try {
        const payload = (await request.json()) as EvalInput;
        const result = evaluate(payload);
        return json(result);
      } catch (error) {
        return json({ ok: false, error: (error as Error).message }, 400);
      }
    }

    if (pathname.startsWith("/api/")) {
      return json({ ok: false, error: "Not Found" }, 404);
    }

    return env.ASSETS.fetch(request);
  },
};
