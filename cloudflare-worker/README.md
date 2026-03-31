# Cloudflare Worker 部署说明

本目录是基于 `risk_dashboard_v4` 规则引擎抽离出的 Cloudflare 部署版本，支持：

- `GET /health`：健康检查
- `GET /api/schema`：接口结构与示例
- `POST /api/evaluate`：风险研判计算
  - 支持 `contributions`（与你当前 Streamlit 汇总口径一致）
  - 也支持 `raw_scores`（0~5 原始分），会按 `adjustment.json` 同源映射进行风险值换算

## 目录

- `src/index.ts`：路由与 API 出口
- `src/engine.ts`：规则计算与 raw_scores 映射
- `public/`：静态演示页面

## 请求示例

### 1) contributions 模式

```json
{
  "case_ctx": { "case_id": "CASE-001" },
  "contributions": [
    { "key": "a1", "label": "监护状况", "risk": 4.4, "neutral_raw": 1, "protection": 0, "hard": false }
  ]
}
```

### 2) raw_scores 模式

```json
{
  "case_ctx": { "case_id": "CASE-002" },
  "raw_scores": [
    { "key": "b1_2", "label": "暴力攻击倾向", "score": 4, "hard": true },
    { "key": "e2", "label": "有害内容接触", "score": 5 }
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

> 生产建议：在 Cloudflare 控制台为 Worker 绑定 Access 策略、WAF 与 Rate Limiting。
