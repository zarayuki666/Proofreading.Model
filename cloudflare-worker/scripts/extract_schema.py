from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "risk_dashboard_v4" / "app.py"
OUT = ROOT / "cloudflare-worker" / "public" / "questionnaire.schema.json"


def main() -> None:
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    payload = {}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in {"QUESTIONS_GROUPS", "MODULE_CONF"}:
                    payload[t.id] = ast.literal_eval(node.value)

    if "QUESTIONS_GROUPS" not in payload:
        raise RuntimeError("QUESTIONS_GROUPS not found in app.py")

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated: {OUT}")


if __name__ == "__main__":
    main()
