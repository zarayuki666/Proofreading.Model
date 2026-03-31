# Cloudflare Worker 部署说明（对齐 risk_dashboard_v4）

本目录是基于 `risk_dashboard_v4/app.py` 规则口径抽离出的 Cloudflare 版本，目标是：

- 前端交互流程与原项目一致（采集 → 生成研判 → 规则解释 → 审计导出）
- 后端规则输出结构一致（净风险、预警级别、硬触发、贡献项、eval_id）
- 输入支持 `raw_scores`（0~5）并按同源 `adjustment` 映射为风险值

## 接口

- `GET /health`
- `GET /api/schema`
- `POST /api/evaluate`

### 请求体（推荐 raw_scores）

```json
{
  "case_ctx": {
    "case_id": "CASE-001",
    "role": "专业人员",
    "student_type": "在校"
  },
  "raw_scores": [
    { "key": "a3_1", "label": "A3 家庭沟通", "score": 4 },
    { "key": "b1_2", "label": "B1 暴力攻击倾向", "score": 4, "hard": true }
  ]
}
```

> 兼容模式：仍支持 `contributions` 直接输入。

## 前端页面

`public/index.html` + `public/app.js` + `public/style.css` 提供完整驾驶舱页面：

- 左侧基础信息
- 采集录入（16 个同源因子）
- 驾驶舱 KPI 与处置建议
- 规则解释
- 审计留痕与导出

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
