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
