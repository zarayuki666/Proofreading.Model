import { evaluate, type EvalInput } from "./engine";

type Env = {
  ASSETS: Fetcher;
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
      return json({ ok: true }, 204);
    }

    if (pathname === "/health") {
      return json({ ok: true, service: "proofreading-risk-worker" });
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
