# Cloudflare Worker 部署说明（完整版，对齐 risk_dashboard_v4）

本目录已对标 `risk_dashboard_v4/` 源码的核心问卷与规则流程：

- 问卷结构来源：`risk_dashboard_v4/app.py` 中 `QUESTIONS_GROUPS`
- 评估输出结构：`eval_id / alert / hard_flags / contributions / net_risk_score`
- 前端流程：采集录入 → 驾驶舱 → 规则解释 → 审计导出

## 同步机制（关键）

为避免“Cloudflare 版与 app.py 漂移”，新增了 schema 抽取脚本：

```bash
python cloudflare-worker/scripts/extract_schema.py
```

会把 `risk_dashboard_v4/app.py` 中的 `QUESTIONS_GROUPS` 与 `MODULE_CONF` 抽取到：

- `cloudflare-worker/public/questionnaire.schema.json`

前端 `public/app.js` 运行时读取该 schema 并动态渲染题目（支持 `scale/mcq/multi/group/hybrid/hybrid_multi`）。

## 接口

- `GET /health`
- `GET /api/schema`
- `POST /api/evaluate`

### 请求体（前端默认）

```json
{
  "case_ctx": {
    "case_id": "CASE-001",
    "role": "专业人员",
    "student_type": "在校"
  },
  "contributions": [
    {
      "key": "a3_1",
      "label": "家庭沟通情况",
      "risk": 3,
      "neutral_raw": 0,
      "protection": 0,
      "hard": false,
      "explain": "scale=3"
    }
  ]
}
```

## 本地运行

```bash
npm install
npm run check
npm run dev
```

## 部署

```bash
npm run deploy
```
