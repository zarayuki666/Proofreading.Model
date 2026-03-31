# 司法合规驾驶舱（未成年人风险研判）

这是一个基于 **Streamlit** 的风险研判与合规辅助系统，支持：

- 结构化采集（家庭、学校、同伴、网络、情绪、自我管理等）
- 规则引擎评分（风险 / 中性 / 保护）
- 可选 AI 模型融合评分（若 `ml_risk_model.pkl` 可加载）
- 分级预警与处置建议
- 审计留痕与 JSON/CSV 导出

> 说明：系统输出为“辅助研判结果”，不能替代专业判断与法定流程。

---

## 目录结构

```text
risk_dashboard_v4/
├── app.py                               # 主应用
├── requirements.txt                     # 依赖
├── ml_risk_model.pkl                    # 可选 AI 模型
├── adjustment.json                      # 校准映射配置
├── build_ml_model_v4.py                 # 模型训练脚本（离线）
├── build_adjustment_from_marked_table.py
├── build_adjustment_from_cases_multi.py
└── data/                                # 样本与中间数据
```

---

## 快速启动

### 1) 创建环境并安装依赖

```bash
cd risk_dashboard_v4
python -m venv .venv
source .venv/bin/activate  # Windows 用 .venv\\Scripts\\activate
pip install -U pip
pip install -r requirements.txt
```

### 2) 启动系统

```bash
streamlit run app.py
```

默认会在浏览器打开本地页面（通常为 `http://localhost:8501`）。

---

## 配置项

可通过环境变量控制：

- `APP_VERSION`：显示在界面右上角的版本号。
- `UI_BUILD`：界面构建标识。
- `ADJ_CFG`：校准配置文件路径（默认 `risk_dashboard_v4/adjustment.json`）。

示例：

```bash
APP_VERSION=0.4.0 UI_BUILD=prod streamlit run app.py
```

---

## Cloudflare Workers / Pages 部署（新增）

考虑到 Cloudflare Pages/Workers 以前端与边缘函数为主，**不能直接原样运行 Streamlit**，本仓库新增了一个边缘部署目录：

- `cloudflare-worker/`：Cloudflare Worker + 静态页面 Demo
- 提供 `POST /api/evaluate` 风险研判接口（规则引擎）
- 提供 `GET /health` 健康检查
- `public/index.html + app.js + style.css` 为完整驾驶舱前端（含侧栏、Tab、采集面板、规则解释、审计导出）

### 1) 本地调试 Worker

```bash
cd cloudflare-worker
npm install
npm run dev
```

### 2) 部署到 Cloudflare Workers

```bash
cd cloudflare-worker
npm install
npm run deploy
```

### 3) 结合 Cloudflare Pages

- 可将 `cloudflare-worker/public` 作为 Pages 静态站点目录；
- 同时部署 Worker，或在 Pages Functions 中复用同样逻辑；
- 页面端调用 `/api/evaluate` 获取研判结果。

> 说明：当前 Worker 版本聚焦“规则引擎 API 化”，AI 模型（`ml_risk_model.pkl`）仍建议保留在 Python 服务侧运行。

---

## 本次完善内容（针对“上传不完整”）

1. **补全项目说明文档**：提供完整启动、目录、配置说明。
2. **增强路径健壮性**：模型与校准文件使用 `app.py` 所在目录解析，避免从不同工作目录启动时报错。
3. **修复校准身份实时生效问题**：将身份角色读取改为运行时动态获取，切换“在校/辍学”后立即影响评分。
4. **提升结果可读性**：硬触发与贡献项优先展示题目标题，而非内部 key。
5. **清理依赖清单**：移除重复项并补充基础版本约束，降低安装歧义。
6. **新增 Cloudflare 部署版本**：补充 Worker 工程与静态页面 Demo，可直接部署到 Cloudflare Workers/Pages。

---

## 常见问题

### Q1：页面能打开，但 AI 分数显示为 “—”

说明 AI 模型未加载或推理失败。系统会自动退化为纯规则评估，不影响使用。

### Q2：想只用规则，不用 AI

删除或移走 `ml_risk_model.pkl` 即可。

### Q3：为什么切换学生类型后分值变化？

系统会根据 `adjustment.json` 中不同身份映射做校准；这属于设计行为。

---

## 合规声明

- 请遵循最小必要采集原则。
- 请避免导出包含直接身份识别信息的数据。
- 任何干预措施都应由具备资质的专业人员结合证据复核。
