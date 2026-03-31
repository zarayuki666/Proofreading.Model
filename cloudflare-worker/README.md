# Cloudflare Worker 部署说明

本目录提供项目的边缘部署版本：

- `src/index.ts`：HTTP 路由（`/health`、`/api/evaluate`）
- `src/engine.ts`：规则引擎核心计算
- `public/index.html`：静态测试页面

## 接口约定

### POST `/api/evaluate`

请求体示例：

```json
{
  "case_ctx": { "case_id": "CASE-001" },
  "contributions": [
    { "key": "a1", "label": "监护状况", "risk": 4.4, "neutral_raw": 1, "protection": 0, "hard": false }
  ]
}
```

返回：预警级别、净风险分、贡献排序、留痕编号等。

## 本地运行

```bash
npm install
npm run dev
```

## 部署

```bash
npm run deploy
```
