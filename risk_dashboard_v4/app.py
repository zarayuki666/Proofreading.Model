from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np  # 如果暂时没用到也无所谓
import pandas as pd
import plotly.express as px
import streamlit as st


def _audit(event: str, payload: Optional[Dict[str, Any]] = None) -> None:
    if "audit_log" not in st.session_state:
        st.session_state["audit_log"] = []
    st.session_state["audit_log"].append(
        {
            "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "event": event,
            "payload": payload or {},
        }
    )


def _audit_safe(event: str, payload: Optional[Dict[str, Any]] = None) -> None:
    try:
        _audit(event, payload)
    except Exception:
        return

# ---------------- 页面基础配置 ----------------
st.set_page_config(
    page_title="司法合规驾驶舱 · 未成年人风险研判",
    page_icon="⚖️",
    layout="wide",
)

APP_VERSION = os.getenv("APP_VERSION", "0.3.0")
UI_BUILD = os.getenv("UI_BUILD", "checkbox_grid_v5")

# ======== 加载 ML 模型（可选） ========
ML_BUNDLE = None
try:
    ML_BUNDLE = joblib.load("ml_risk_model.pkl")
except Exception:
    ML_BUNDLE = None

# ---------------- 预警文本常量（含蓝色提示） ----------------
GREEN_ALERT = {
    "level": "🟩 绿色预警 (低风险 / 常规关注)",
    "core_measure": "以普适性预防为主。",
    "actions": [
        "系统自动将法治教育、网络安全、家庭教育等相关资源推送至家长和学校。",
        "社区/学校开展常规法治与家庭教育指导。",
    ],
}

BLUE_ALERT = {
    "level": "🟦 蓝色提示 (轻度风险 / 学校社区协同关注)",
    "core_measure": "以学校与社区为主的联合关注，无需立即启动司法干预。",
    "actions": [
        "由班主任/心理老师将个案纳入学校重点关注或随访台账，定期沟通谈话。",
        "社区/村（居）委会与家长保持联络，必要时提供家庭教育和养育支持指导。",
        "关注同伴关系和网络行为，如出现明显恶化，再升级至黄色预警。",
    ],
}

YELLOW_ALERT = {
    "level": "🟨 黄色预警 (中风险 / 重点关注)",
    "core_measure": "启动早期、精准的社会干预。",
    "actions": [
        "信息通报与会商（学校/社区/民政/检察等）。",
        "司法社工介入并制定个性化帮扶计划。",
    ],
}

RED_ALERT = {
    "level": "🟥 红色预警 (高风险 / 危机干预)",
    "core_measure": "启动多部门协同的危机干预。",
    "actions": [
        "立即启动危机干预小组（检察/公安牵头）。",
        "评估是否启动司法程序或送入专门矫治教育机构。",
    ],
}

# ---------------- 基础参数 ----------------
RANGE_PER_ITEM = 5  # 量表范围 0–5
NEUTRAL_COEF = 0.3  # 中性项折扣系数

# ---------------- 权重配置（用于汇总） ----------------
MODULE_CONF = {
    "a1": {"label": "A1. 监护状况", "risk": 1.1, "neutral": 1.0, "protection": 1.0},
    "a2": {"label": "A2. 教养方式", "risk": 1.0, "neutral": 1.0, "protection": 1.0},
    "a3_1": {"label": "A3. 家庭沟通", "risk": 0.7, "neutral": 1.0, "protection": 1.0},
    "a3_2": {"label": "A3. 家庭冲突", "risk": 0.8, "neutral": 1.0, "protection": 1.0},
    "b1_1": {"label": "B1. 冲动", "risk": 1.0, "neutral": 1.0, "protection": 1.0},
    "b1_2": {"label": "B1. 攻击", "risk": 1.0, "neutral": 1.0, "protection": 1.0},
    "b2": {"label": "B2. 认知观念", "risk": 0.8, "neutral": 1.0, "protection": 1.0},
    "b3": {"label": "B3. 自我认同", "risk": 0.9, "neutral": 1.0, "protection": 1.0},
    "c1": {"label": "C1. 同伴关系", "risk": 1.0, "neutral": 1.0, "protection": 1.0},
    "c2": {"label": "C2. 社区环境", "risk": 0.8, "neutral": 1.0, "protection": 1.0},
    "d1": {"label": "D1. 在校表现", "risk": 1.0, "neutral": 1.0, "protection": 1.0},
    "d2": {"label": "D2. 法治教育", "risk": 0.9, "neutral": 1.0, "protection": 1.0},
    "e1a": {"label": "E1a. 上网时间", "risk": 0.8, "neutral": 1.0, "protection": 1.0},
    "e1b": {"label": "E1b. 深夜上网", "risk": 0.9, "neutral": 1.0, "protection": 1.0},
    "e2": {"label": "E2. 内容接触", "risk": 1.1, "neutral": 1.0, "protection": 1.0},
    "e3": {"label": "E3. 线上交往", "risk": 1.0, "neutral": 1.0, "protection": 1.0},
    "f1": {"label": "F1. 情感支持", "risk": 0.8, "neutral": 1.0, "protection": 1.0},
    "f2": {"label": "F2. 情感适应能力", "risk": 0.9, "neutral": 1.0, "protection": 1.0},
    "g1": {"label": "G1. 时间管理", "risk": 0.8, "neutral": 1.0, "protection": 1.0},
    "g2": {"label": "G2. 财务管理", "risk": 0.7, "neutral": 1.0, "protection": 1.0},
}

# ---------------- 题目配置（group 子题在父题中并排显示） ----------------
QUESTIONS_GROUPS = {
    "A. 家庭监护": {
        "a1": {
            "title": "监护状况",
            "type": "multi",
            "max_risk": 6,  # 新增：本题风险总分上限 6 分，防止叠加过猛
            "options": [
                {"label": "监护人积极参与（保护）", "r": 0, "n": 2, "p": 5},
                {"label": "单亲", "r": 2, "n": 3, "p": 0},
                {"label": "父母失业", "r": 2, "n": 2, "p": 0},
                {"label": "监护薄弱", "r": 2, "n": 1, "p": 0},
                {"label": "长期疾病", "r": 3, "n": 1, "p": 0},
                {"label": "流动", "r": 3, "n": 2, "p": 0},
                {"label": "留守", "r": 3, "n": 1, "p": 0},
                {"label": "父母常年不在", "r": 3, "n": 0, "p": 0},
                {"label": "父母失联", "r": 3, "n": 0, "p": 0},
                {"label": "事实无人抚养", "r": 5, "n": 0, "p": 0, "hard_trigger": True},
            ],
        },
        "a2": {
            "title": "教养方式",
            "type": "mcq",
            "options": [
                {"label": "权威型（合理）", "r": 0, "n": 3, "p": 4},
                {"label": "传统型（强调规则）", "r": 1, "n": 4, "p": 2},
                {"label": "溺爱型教养", "r": 3, "n": 1, "p": 0},
                {"label": "忽视型教养", "r": 3, "n": 0, "p": 0},
                {"label": "暴力型教养", "r": 5, "n": 0, "p": 0, "hard_trigger": True},
            ],
        },
        "a3": {
            "title": "家庭功能（沟通与冲突）",
            "type": "group",
            "subquestions": [
                {
                    "key": "a3_1",
                    "title": "家庭沟通情况",
                    "type": "scale",
                    "scale_label": "沟通不畅程度（0=顺畅,5=极差）",
                    "map_to": "risk",
                },
                {
                    "key": "a3_2",
                    "title": "家庭冲突情况",
                    "type": "scale",
                    "scale_label": "冲突激烈程度（0=和谐,5=暴力冲突）",
                    "map_to": "risk",
                },
            ],
        },
    },
    "B. 个体认知与心理": {
        "b1": {
            "title": "人格行为特征",
            "type": "group",
            "subquestions": [
                {
                    "key": "b1_1",
                    "title": "冲动控制",
                    "type": "scale",
                    "scale_label": "易冲动程度（0=沉稳,5=极易失控）",
                    "map_to": "risk",
                },
                {
                    "key": "b1_2",
                    "title": "暴力攻击倾向",
                    "type": "scale",
                    "scale_label": "攻击性行为频次（0=无,5=经常）",
                    "map_to": "risk",
                    "hard_threshold": 4,
                },
            ],
        },
        "b2": {
            "title": "认知观念（极端/消极）",
            "type": "hybrid",
            "mcq": [
                {"label": "价值观积极", "r": 0, "n": 0, "p": 5},
                {"label": "受同伴影响", "r": 1, "n": 3, "p": 1, "activates_scale": True},
                {"label": "价值观模糊", "r": 1, "n": 2, "p": 1, "activates_scale": True},
                {"label": "偶有极端倾向", "r": 3, "n": 1, "p": 0, "activates_scale": True},
                {"label": "极端激进", "r": 4, "n": 0, "p": 0, "activates_scale": True},
            ],
            "scale": {
                "scale_label": "极端程度（0=无,5=极强）",
                "map_to": "risk",
                "hard_threshold": 5,
            },
        },
        "b3": {
            "title": "自我认同",
            "type": "scale",
            "scale_label": "自我认同问题程度（0=自信,5=混乱/自卑）",
            "map_to": "risk",
        },
    },
    "C. 社会交往": {
        "c1": {
            "title": "同伴关系",
            "type": "hybrid",
            "mcq": [
                {"label": "无不良同伴", "r": 0, "n": 5, "p": 5},
                {"label": "偶有接触不良同伴", "r": 2, "n": 1, "p": 1, "activates_scale": True},
                {"label": "结交不良同伴", "r": 3, "n": 1, "p": 0, "activates_scale": True},
                {"label": "加入不良群体", "r": 4, "n": 0, "p": 0, "activates_scale": True},
            ],
            "scale": {
                "scale_label": "受不良同伴影响强度（0=无,5=极强）",
                "map_to": "risk",
                "hard_threshold": 4,
            },
        },
        "c2": {
            "title": "社区环境",
            "type": "hybrid",
            "mcq": [
                {"label": "社区资源丰富且治安好", "r": 0, "n": 3, "p": 4},
                {"label": "社区一般", "r": 1, "n": 2, "p": 2, "activates_scale": True},
                {"label": "社区资源贫乏", "r": 3, "n": 1, "p": 1, "activates_scale": True},
                {"label": "社区治安较差", "r": 4, "n": 1, "p": 0, "activates_scale": True},
                {"label": "社区犯罪频发", "r": 5, "n": 1, "p": 0, "hard_trigger": True, "activates_scale": True},
                {"label": "高风险社区", "r": 5, "n": 0, "p": 0, "hard_trigger": True, "activates_scale": True},
            ],
            "scale": {
                "scale_label": "受社区影响强度（0=无,5=极强）",
                "map_to": "risk",
                "hard_threshold": 4,
            },
        },
    },
    "D. 学校教育": {
        "d1": {
            "title": "在校表现",
            "type": "hybrid_multi",
            "mcq_multi": [
                {"label": "积极学习", "r": 0, "n": 4, "p": 4},
                {"label": "偶尔缺课", "r": 1, "n": 3, "p": 0},
                {"label": "偶尔逃课/逃学", "r": 2, "n": 2, "p": 0},
                {"label": "长期旷课", "r": 3, "n": 2, "p": 0, "activates_scale": True},
                {"label": "经常逃学", "r": 3, "n": 1, "p": 0, "activates_scale": True},
                {"label": "辍学", "r": 4, "n": 0, "p": 0, "activates_scale": True},
            ],
            "scale": {
                "scale_label": "逃学/旷课频次与持续性（0=无,5=非常频繁/持续）",
                "map_to": "risk",
                "hard_threshold": 4,
            },
        },
        "d2": {
            "title": "法治教育覆盖",
            "type": "hybrid",
            "mcq": [
                {"label": "深度参与/法治活动活跃", "r": 0, "n": 3, "p": 5, "activates_scale": True},
                {"label": "按课表开展", "r": 1, "n": 2, "p": 2, "activates_scale": True},
                {"label": "偶尔宣传", "r": 2, "n": 1, "p": 1, "activates_scale": True},
                {"label": "无法治教育", "r": 3, "n": 1, "p": 0},
            ],
            "scale": {
                "scale_label": "法治教育学习效果（0=无效果,5=效果良好）",
                "map_to": "protection",
            },
        },
    },
    "E. 网络行为": {
        "e1a": {
            "title": "上网时长/影响生活",
            "type": "scale",
            "scale_label": "对日常生活干扰程度（0=无,5=严重颠倒）",
            "map_to": "risk",
        },
        "e1b": {
            "title": "深夜违规上网",
            "type": "scale",
            "scale_label": "深夜上网频次（0=无,5=通宵）",
            "map_to": "risk",
        },
        "e2": {
            "title": "内容接触（是否接触有害内容）",
            "type": "hybrid_multi",
            "mcq_multi": [
                {"label": "主要接触正面/学习资源", "r": 0, "n": 3, "p": 5},
                {"label": "接触游戏内容", "r": 1, "n": 1, "p": 0, "activates_scale": True},
                {"label": "接触色情内容", "r": 2, "n": 1, "p": 0, "activates_scale": True},
                {"label": "接触诈骗信息", "r": 3, "n": 0, "p": 0, "hard_trigger": True, "activates_scale": True},
                {"label": "接触暴力/血腥内容", "r": 4, "n": 0, "p": 0, "hard_trigger": True, "activates_scale": True},
                {"label": "接触黑灰产信息", "r": 5, "n": 0, "p": 0, "hard_trigger": True, "activates_scale": True},
            ],
            "scale": {
                "scale_label": "接触频次/沉浸程度（0=无,5=频繁）",
                "map_to": "risk",
                "hard_threshold": 5,
            },
        },
        "e3": {
            "title": "线上交往行为",
            "type": "multi",
            "options": [
                {"label": "线上交往健康", "r": 0, "n": 3, "p": 5},
                {"label": "被网络欺凌/受害", "r": 2, "n": 2, "p": 0, "activates_scale": True},
                {"label": "接触不良社交圈", "r": 3, "n": 1, "p": 0, "activates_scale": True},
                {"label": "参与/发起网络欺凌", "r": 5, "n": 0, "p": 0, "hard_trigger": True},
            ],
            "scale": {
                "scale_label": "受影响程度（0=无,5=极强）",
                "map_to": "risk",
                "hard_threshold": 4,
            },
        },
    },
    "F. 情感发展": {
        "f1": {
            "title": "情感支持",
            "type": "scale",
            "scale_label": "获得家庭/社交关爱与支持（0=差,5=强）",
            "map_to": "protection",
        },
        "f2": {
            "title": "情感情绪调节能力",
            "type": "scale",
            "scale_label": "情绪调节困难程度（0=良好,5=困难）",
            "map_to": "risk",
        },
    },
    "G. 自我管理": {
        "g1": {
            "title": "时间管理/自律",
            "type": "scale",
            "scale_label": "时间管理问题程度（0=自律,5=完全无序）",
            "map_to": "risk",
        },
        "g2": {
            "title": "财务管理",
            "type": "hybrid",
            "mcq": [
                {"label": "理财能力良好", "r": 0, "n": 3, "p": 5},
                {"label": "无欠债", "r": 0, "n": 4, "p": 2},
                {"label": "偶尔冲动消费", "r": 1, "n": 2, "p": 1, "activates_scale": True},
                {"label": "被诈骗", "r": 3, "n": 1, "p": 0, "activates_scale": True},
                {"label": "存在欠债", "r": 3, "n": 2, "p": 0, "activates_scale": True},
                {"label": "严重财务问题/贷款", "r": 4, "n": 0, "p": 0, "activates_scale": True},
            ],
            "scale": {
                "scale_label": "理财观念/行为问题程度（0=良好,5=严重）",
                "map_to": "risk",
                "hard_threshold": 4,
            },
        },
    },
}

# ---------- 将所有题目 key 摊平，便于显示与统计 ----------
KEY_TO_QCONF: Dict[str, Dict[str, Any]] = {}
SUBKEY_TO_PARENT: Dict[str, str] = {}

for parent_label, group in QUESTIONS_GROUPS.items():
    for k, qc in group.items():
        q_type = qc.get("type")
        if q_type == "group":
            for sub in qc.get("subquestions", []):
                sub_key = sub["key"]
                KEY_TO_QCONF[sub_key] = sub
                SUBKEY_TO_PARENT[sub_key] = parent_label
        else:
            KEY_TO_QCONF[k] = qc
            SUBKEY_TO_PARENT[k] = parent_label

# ---------- 量表原始得分收集（供 ML 模型使用） ----------
RAW_SCALE_VALUES: Dict[str, float] = {}

# ---------- 读取校准配置 & 身份选择 ----------
ADJ_CFG = os.getenv("ADJ_CFG", "adjustment.json")

try:
    with open(ADJ_CFG, "r", encoding="utf-8") as f:
        ADJ = json.load(f)
except Exception:
    ADJ = {}

student_type = st.session_state.get("student_type", "在校学生")

ROLE_MAP = {
    "在校学生": "student",
    "辍学/已离校青少年": "dropout",
}
CURRENT_ROLE = ROLE_MAP.get(student_type, "ALL")

# 这类题目在生成 adjustment.json 时就已经做过 1-risk 的处理
JSON_PROTECTIVE_KEYS = {"f1"}  # 情感支持


def _hash_payload(obj: Dict[str, Any]) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _alert_badge(level: str) -> str:
    # level text like "🟢 绿色（常态）" etc
    if "绿色" in level:
        cls = "badge badge-green"
    elif "蓝色" in level:
        cls = "badge badge-blue"
    elif "黄色" in level:
        cls = "badge badge-yellow"
    else:
        cls = "badge badge-red"
    return f'<span class="{cls}"><span class="badge-dot"></span>{level}</span>'


# ---------- 0-5 量表 → 按身份校准分数 ----------
def adjust_score(q_key: str, raw_v: int, map_to: str = "risk") -> float:
    """
    根据 adjustment.json + 当前身份，把 0-5 原始分校正到 0-5 区间。
    - map_to == "risk"      → 按风险强度使用
    - map_to == "protection"→ 一般做 1 - 风险，表示保护强度
    """
    q_cfg = ADJ.get(q_key, {})
    role_cfg = q_cfg.get(CURRENT_ROLE) or q_cfg.get("ALL") or {}
    mp = role_cfg.get("map", {})

    val01 = mp.get(str(int(raw_v)))
    if val01 is None:
        # 如果没配映射，就按线性 0~1 处理
        val01 = raw_v / 5.0

    try:
        val01 = float(val01)
    except Exception:
        val01 = raw_v / 5.0

    # 为防止 JSON 中配置越界，这里统一夹紧到 [0, 1]
    val01 = max(0.0, min(1.0, val01))

    # 对“保护项”做一次 1 - p 翻转，前提是 JSON 里存的是风险概率
    if map_to == "protection" and q_key not in JSON_PROTECTIVE_KEYS:
        val01 = 1.0 - val01

    return round(val01 * 5.0, 2)


# ---------- 渲染函数（返回 r,n,p,is_hard） ----------
def render_question(qkey, qconf, ident="ALL"):
    """渲染题目控件（UI）。计分统一在 _score_question_from_state() 从 st.session_state 读取。"""
    t = qconf.get("type")
    title = qconf.get("title", qkey)

    def _with_unknown(opts):
        # 单选题/混合题在最前面加一个“未评估/未知”，避免默认值造成置信度虚高
        unknown = {"label": "未评估/未知", "_unknown": True, "r": 0, "n": 0, "p": 0}
        return [unknown] + list(opts or [])

    def _title(text_: str):
        st.markdown(f'<div class="qtitle">{text_}</div>', unsafe_allow_html=True)

    def _hint(text_: str):
        if text_:
            st.markdown(f'<div class="qsub">{text_}</div>', unsafe_allow_html=True)

    def _select_0_5(label: str, key: str):
        """统一 0-5 量表展示：标题 + 灰色说明 + slider（隐藏原生 label，避免标题不一致）。"""
        if label:
            st.caption(label)
        try:
            st.select_slider(
                "量表",
                options=["未评估", 0, 1, 2, 3, 4, 5],
                value="未评估",
                key=key,
                label_visibility="collapsed",
            )
        except TypeError:
            # 兼容旧版本 Streamlit（没有 label_visibility）
            st.select_slider(
                label or "量表（0-5）",
                options=["未评估", 0, 1, 2, 3, 4, 5],
                value="未评估",
                key=key,
            )

    def _render_checkbox_grid(labels: List[str], key_prefix: str, n_cols: int = 2, on_change=None):
        cols = st.columns(max(1, n_cols), gap="small")
        for i, lab in enumerate(labels):
            with cols[i % max(1, n_cols)]:
                if on_change is None:
                    st.checkbox(lab, key=f"{key_prefix}_{i}")
                else:
                    st.checkbox(lab, key=f"{key_prefix}_{i}", on_change=on_change, args=(i,))

    def _render_single_choice_boxes(qkey_: str, options: List[Dict[str, Any]], n_cols: int = 2):
        """把单选题做成“互斥的 checkbox 小框”。选择结果写回 st.session_state[f'mcq_{qkey_}']。"""
        labels = [o.get("label", "") for o in options]
        labels = [x for x in labels if x]  # 防御
        if not labels:
            return "未评估/未知"

        state_key = f"mcq_{qkey_}"
        box_prefix = f"mcqbox_{qkey_}"

        # 兼容：如果之前用 st.radio 存过 mcq_{qkey_}，则优先复用它
        sel = st.session_state.get(state_key)
        if sel not in labels:
            sel = labels[0]
            st.session_state[state_key] = sel

        # 每次渲染都把 box 状态同步到当前 sel，保证互斥
        for i, lab in enumerate(labels):
            st.session_state[f"{box_prefix}_{i}"] = lab == sel

        def _on_change(changed_idx: int):
            ck = f"{box_prefix}_{changed_idx}"
            if st.session_state.get(ck, False):
                # 选中某项：取消其他项
                st.session_state[state_key] = labels[changed_idx]
                for j in range(len(labels)):
                    if j != changed_idx:
                        st.session_state[f"{box_prefix}_{j}"] = False
            else:
                # 如果用户把当前项也取消，且没有任何项被选中 → 回到“未评估/未知”
                if not any(st.session_state.get(f"{box_prefix}_{j}", False) for j in range(len(labels))):
                    st.session_state[f"{box_prefix}_0"] = True
                    st.session_state[state_key] = labels[0]

        _render_checkbox_grid(labels, box_prefix, n_cols=n_cols, on_change=_on_change)
        return st.session_state.get(state_key, labels[0])

    # ======== 各题型渲染：统一成“第一张图”样式（小方框 + 两列 + 标题一致） ========
    if t == "mcq":
        _title(title)
        options = _with_unknown(qconf.get("options", []))
        _render_single_choice_boxes(qkey, options, n_cols=2)

    elif t == "multi":
        _title(title)
        opts = qconf.get("options", [])
        labels = [o.get("label", "") for o in opts]
        _render_checkbox_grid(labels, key_prefix=f"multi_{qkey}", n_cols=2)

        # multi 可选展开 scale（如 e3）
        if qconf.get("scale"):
            if any(
                st.session_state.get(f"multi_{qkey}_{i}", False) and (opts[i].get("activates_scale") is True)
                for i in range(len(opts))
            ):
                scale = qconf.get("scale", {})
                _select_0_5(scale.get("scale_label", "量表（0-5）"), key=f"scale_{qkey}")

    elif t == "scale":
        _title(title)
        _select_0_5(qconf.get("scale_label", "量表（0-5）"), key=f"scale_{qkey}")

    elif t == "group":
        _title(title)
        subs = qconf.get("subquestions", []) or []
        if len(subs) <= 1:
            for sub in subs:
                render_question(sub["key"], sub, ident)
        else:
            cols = st.columns(2, gap="large")
            for i, sub in enumerate(subs):
                with cols[i % 2]:
                    render_question(sub["key"], sub, ident)

    elif t == "hybrid":
        _title(title)
        options = _with_unknown(qconf.get("mcq", []))
        chosen_label = _render_single_choice_boxes(qkey, options, n_cols=2)
        chosen_opt = next((o for o in options if o.get("label") == chosen_label), options[0])
        if chosen_opt.get("activates_scale"):
            scale = qconf.get("scale", {})
            _select_0_5(scale.get("scale_label", "量表（0-5）"), key=f"scale_{qkey}")

    elif t == "hybrid_multi":
        _title(title)
        opts = qconf.get("mcq_multi", []) or []
        labels = [o.get("label", "") for o in opts]
        _render_checkbox_grid(labels, key_prefix=f"multi_{qkey}", n_cols=2)

        if qconf.get("scale"):
            if any(
                st.session_state.get(f"multi_{qkey}_{i}", False) and (opts[i].get("activates_scale") is True)
                for i in range(len(opts))
            ):
                scale = qconf.get("scale", {})
                _select_0_5(scale.get("scale_label", "量表（0-5）"), key=f"scale_{qkey}")


# ---------- 视觉注入 ----------
def _inject_cockpit_css() -> None:
    st.markdown(
        r"""
<style>
/* --- Global / background --- */
.stApp {
  background:
    radial-gradient(1200px 600px at 10% 0%, rgba(56,189,248,.22), transparent 55%),
    radial-gradient(900px 500px at 85% 15%, rgba(34,197,94,.14), transparent 55%),
    radial-gradient(900px 700px at 70% 95%, rgba(168,85,247,.18), transparent 55%),
    linear-gradient(180deg, #0a1222 0%, #0b1426 55%, #0b1428 100%);
  color: #E9EEF7;
}
[data-testid="stAppViewContainer"]::before{
  content:"";
  position:fixed;
  inset:0;
  pointer-events:none;
  background-image:
    linear-gradient(rgba(148,163,184,.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148,163,184,.06) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(circle at 30% 20%, rgba(0,0,0,1) 20%, rgba(0,0,0,.35) 55%, rgba(0,0,0,0) 80%);
  opacity:.55;
}
/* Hide Streamlit header */
header[data-testid="stHeader"] { visibility: hidden; height: 0; }
div[data-testid="stToolbar"] { visibility: hidden; height: 0; }

h1,h2,h3 { letter-spacing: .2px; }
.qtitle{ font-size: 1.05rem; font-weight: 800; margin: .25rem 0 .35rem 0; }
.qsub{ color: rgba(232,238,247,.78); font-size: .88rem; margin: 0 0 .25rem 0; }
.small-muted { color: rgba(232,238,247,.78); font-size: 0.88rem; }
.kpi { padding: 14px 14px; border-radius: 16px; background: rgba(20,32,56,.72); border: 1px solid rgba(148,163,184,.24); box-shadow: 0 14px 35px rgba(0,0,0,.28); backdrop-filter: blur(10px); }
.card { padding: 16px 16px; border-radius: 18px; background: rgba(10,18,36,.68); border: 1px solid rgba(148,163,184,.22); box-shadow: 0 18px 45px rgba(0,0,0,.32); backdrop-filter: blur(12px); }
.badge {
  display:inline-flex; align-items:center; gap:8px;
  padding: 6px 10px; border-radius: 999px;
  border: 1px solid rgba(148,163,184,.25);
  background: rgba(20,32,56,.72);
  font-size: .9rem;
}
.badge-dot{ width:10px; height:10px; border-radius:99px; display:inline-block; box-shadow: 0 0 18px rgba(56,189,248,.35); }
.badge-green .badge-dot{ background:#22c55e; box-shadow:0 0 18px rgba(34,197,94,.35); }
.badge-blue  .badge-dot{ background:#38bdf8; box-shadow:0 0 18px rgba(56,189,248,.35); }
.badge-yellow .badge-dot{ background:#fbbf24; box-shadow:0 0 18px rgba(251,191,36,.35); }
.badge-red   .badge-dot{ background:#fb7185; box-shadow:0 0 18px rgba(251,113,133,.35); }

hr { border-color: rgba(148,163,184,.18); }

/* Buttons */
.stButton > button {
  border-radius: 14px;
  border: 1px solid rgba(94,234,212,.45);
  background: linear-gradient(90deg, rgba(56,189,248,.26), rgba(94,234,212,.20));
  color: #E9EEF7;
  box-shadow: 0 12px 28px rgba(0,0,0,.25);
}
.stButton > button:hover {
  border: 1px solid rgba(94,234,212,.65);
  transform: translateY(-1px);
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(8,14,28,.92), rgba(8,14,28,.85));
  border-right: 1px solid rgba(148,163,184,.12);
}
/* ====== Option boxes (checkbox-like) tighter layout ====== */
div[data-testid="stCheckbox"] { margin-bottom: 0.25rem; }
div[data-testid="stCheckbox"] label { gap: 0.45rem; }
div[data-testid="stCheckbox"] p { margin: 0; font-size: 0.98rem; }
div[data-testid="stCheckbox"] input[type="checkbox"] {
  width: 16px; height: 16px;
  border-radius: 4px;
}
/* Inputs / selects / text areas */
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
  background: rgba(10,18,36,.88) !important;
  color: #E9EEF7 !important;
  border: 1px solid rgba(148,163,184,.28) !important;
  box-shadow: none !important;
}
div[data-baseweb="select"] > div {
  background: rgba(10,18,36,.88) !important;
  color: #E9EEF7 !important;
  border: 1px solid rgba(148,163,184,.28) !important;
}
div[data-baseweb="select"] span {
  color: #E9EEF7 !important;
}
/* Tabs */
div[data-baseweb="tab-list"] {
  background: rgba(10,18,36,.4);
  border-radius: 999px;
  padding: 4px;
}
button[data-baseweb="tab"] {
  color: rgba(232,238,247,.75) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: #E9EEF7 !important;
  background: rgba(94,234,212,.15) !important;
  border-radius: 999px;
}
/* Expanders */
details[data-testid="stExpander"] {
  background: rgba(10,18,36,.58);
  border-radius: 14px;
  border: 1px solid rgba(148,163,184,.22);
  padding: 4px 8px;
}
details[data-testid="stExpander"] summary {
  background: rgba(16,27,48,.75);
  border-radius: 12px;
  color: #E9EEF7;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def _get_raw_scale_value(k: str) -> float:
    """用于 AI 特征：取 0-5 原始量表分；未评估/未激活视为 0。"""
    qconf = KEY_TO_QCONF.get(k, {})
    t = qconf.get("type")

    def _to_float(v) -> float:
        try:
            if isinstance(v, (int, float)):
                return float(v)
        except Exception:
            pass
        return 0.0

    try:
        if t == "scale":
            return _to_float(st.session_state.get(f"scale_{k}", 0.0))

        if t == "hybrid":
            sel = st.session_state.get(f"mcq_{k}", "未评估/未知")
            chosen = next((o for o in qconf.get("mcq", []) if o.get("label") == sel), None)
            if chosen and chosen.get("activates_scale"):
                return _to_float(st.session_state.get(f"scale_{k}", 0.0))
            return 0.0

        if t == "hybrid_multi":
            opts = qconf.get("mcq_multi", [])
            activated = any(
                st.session_state.get(f"multi_{k}_{idx}", False) and opts[idx].get("activates_scale")
                for idx in range(len(opts))
            )
            if activated:
                return _to_float(st.session_state.get(f"scale_{k}", 0.0))
            return 0.0
    except Exception:
        return 0.0

    return 0.0


def _score_question_from_state(k: str, qconf: Dict[str, Any]) -> Tuple[float, float, float, bool, str]:
    """返回 (risk, neutral, protection, hard, explain)"""
    t = qconf.get("type")
    explain = ""
    is_hard = False
    r = n = p = 0.0

    def _read_scale_value(scale_key: str) -> int:
        v = st.session_state.get(scale_key, "未评估")
        try:
            if isinstance(v, (int, float)):
                return int(v)
        except Exception:
            pass
        return 0

    if t == "mcq":
        sel = st.session_state.get(f"mcq_{k}", "未评估/未知")
        chosen = next((o for o in qconf.get("options", []) if o.get("label") == sel), None)
        if chosen:
            r, n, p = float(chosen.get("r", 0)), float(chosen.get("n", 0)), float(chosen.get("p", 0))
            is_hard = bool(chosen.get("hard_trigger", False))
            explain = sel if sel != "未评估/未知" else ""

    elif t == "multi":
        chosen_labels: List[str] = []
        for idx, opt in enumerate(qconf.get("options", [])):
            if st.session_state.get(f"multi_{k}_{idx}", False):
                chosen_labels.append(opt.get("label", ""))
                r += float(opt.get("r", 0))
                n += float(opt.get("n", 0))
                p += float(opt.get("p", 0))
                if opt.get("hard_trigger", False):
                    is_hard = True
        explain = "；".join([x for x in chosen_labels if x])

        # multi 可选 scale
        if qconf.get("scale"):
            opts = qconf.get("options", [])
            activated = any(
                st.session_state.get(f"multi_{k}_{i}", False) and opts[i].get("activates_scale")
                for i in range(len(opts))
            )
            if activated:
                raw_v = _read_scale_value(f"scale_{k}")
                explain += ("" if not explain else " + ") + f"量表={raw_v}/5"
                hard_thresh = float(qconf.get("scale", {}).get("hard_threshold", 99))
                if raw_v >= hard_thresh:
                    is_hard = True
                map_to = qconf.get("scale", {}).get("map_to", "risk")
                adj_v = float(adjust_score(k, raw_v, map_to))
                explain += f" → {adj_v:g}"
                if map_to == "risk":
                    r += adj_v
                elif map_to == "neutral":
                    n += adj_v
                else:
                    p += adj_v

        cap = qconf.get("max_risk")
        if cap is not None:
            r = min(r, float(cap))

    elif t == "scale":
        raw_v = _read_scale_value(f"scale_{k}")
        hard_thresh = float(qconf.get("hard_threshold", 99))
        if raw_v >= hard_thresh:
            is_hard = True
        map_to = qconf.get("map_to", "risk")
        adj_v = float(adjust_score(k, raw_v, map_to))
        explain = f"量表={raw_v}/5 → {adj_v:g}"
        if map_to == "risk":
            r += adj_v
        elif map_to == "neutral":
            n += adj_v
        else:
            p += adj_v

    elif t == "hybrid":
        sel = st.session_state.get(f"mcq_{k}", "未评估/未知")
        chosen = next((o for o in qconf.get("mcq", []) if o.get("label") == sel), None)
        if chosen:
            r, n, p = float(chosen.get("r", 0)), float(chosen.get("n", 0)), float(chosen.get("p", 0))
            is_hard = bool(chosen.get("hard_trigger", False))
            explain = sel
            if chosen.get("activates_scale"):
                raw_v = _read_scale_value(f"scale_{k}")
                explain += f" + 量表={raw_v}/5"
                hard_thresh = float(qconf.get("scale", {}).get("hard_threshold", 99))
                if raw_v >= hard_thresh:
                    is_hard = True
                map_to = qconf.get("scale", {}).get("map_to", "risk")
                adj_v = float(adjust_score(k, raw_v, map_to))
                explain += f" → {adj_v:g}"
                if map_to == "risk":
                    r += adj_v
                elif map_to == "neutral":
                    n += adj_v
                else:
                    p += adj_v

        # 未评估/未知：保持 0 分，不写 explain
        if sel == "未评估/未知":
            explain = ""

    elif t == "hybrid_multi":
        chosen_labels = []
        opts = qconf.get("mcq_multi", [])
        for idx, opt in enumerate(opts):
            if st.session_state.get(f"multi_{k}_{idx}", False):
                chosen_labels.append(opt.get("label", ""))
                r += float(opt.get("r", 0))
                n += float(opt.get("n", 0))
                p += float(opt.get("p", 0))
                if opt.get("hard_trigger", False):
                    is_hard = True
        explain = "；".join([x for x in chosen_labels if x])

        activated = any(
            st.session_state.get(f"multi_{k}_{idx}", False) and opts[idx].get("activates_scale")
            for idx in range(len(opts))
        )
        if activated:
            raw_v = _read_scale_value(f"scale_{k}")
            explain += ("" if not explain else " + ") + f"量表={raw_v}/5"
            hard_thresh = float(qconf.get("scale", {}).get("hard_threshold", 99))
            if raw_v >= hard_thresh:
                is_hard = True
            map_to = qconf.get("scale", {}).get("map_to", "risk")
            adj_v = float(adjust_score(k, raw_v, map_to))
            explain += f" → {adj_v:g}"
            if map_to == "risk":
                r += adj_v
            elif map_to == "neutral":
                n += adj_v
            else:
                p += adj_v

        cap = qconf.get("max_risk")
        if cap is not None:
            r = min(r, float(cap))

    return r, n, p, is_hard, explain


def _compute_evaluation(case_ctx: Dict[str, Any]) -> Dict[str, Any]:
    """核心研判：规则 +（可选）AI。"""
    hard_flags: List[str] = []
    contributions: List[Dict[str, Any]] = []

    # 模块汇总
    module_acc: Dict[str, Dict[str, float]] = {}
    for mk in MODULE_CONF.keys():
        module_acc[mk] = {"risk": 0.0, "neutral_raw": 0.0, "protection": 0.0}

    # 逐题聚合
    for k, qconf in KEY_TO_QCONF.items():
        r, n, p, is_hard, explain = _score_question_from_state(k, qconf)

        # 模块权重（按 key 前缀匹配 MODULE_CONF）
        module_key = k
        # 有些键是 a3_1 等，直接在 MODULE_CONF 里；否则退化为前两段
        if module_key not in MODULE_CONF:
            # 例如 e1a, e1b 等：尽量匹配前两位/前三位
            candidates = [module_key, module_key.split("_")[0], "_".join(module_key.split("_")[:2])]
            module_key = next((c for c in candidates if c in MODULE_CONF), module_key.split("_")[0])

        mconf = MODULE_CONF.get(module_key, {"label": module_key, "risk": 1.0, "neutral": 1.0, "protection": 1.0})
        wr, wn, wp = float(mconf.get("risk", 1.0)), float(mconf.get("neutral", 1.0)), float(mconf.get("protection", 1.0))

        risk_w = r * wr
        neutral_w = n * wn
        prot_w = p * wp

        module_acc.setdefault(module_key, {"risk": 0.0, "neutral_raw": 0.0, "protection": 0.0})
        module_acc[module_key]["risk"] += risk_w
        module_acc[module_key]["neutral_raw"] += neutral_w
        module_acc[module_key]["protection"] += prot_w

        if is_hard and (r > 0 or n > 0 or p > 0):
            # 题目 label 取：子题显示“父题 - 子题”
            parent = SUBKEY_TO_PARENT.get(k)
            label = f"{parent} · {qconf.get('label', k)}" if parent else qconf.get("label", k)
            hard_flags.append(label)

        # 记录贡献（用于 TOP 因子 / 专业研判）
        parent = SUBKEY_TO_PARENT.get(k)
        qlabel = qconf.get("label", k)
        if parent:
            qlabel = f"{parent} · {qlabel}"
        contributions.append(
            {
                "key": k,
                "label": qlabel,
                "risk": risk_w,
                "neutral_raw": neutral_w,
                "neutral_eff": neutral_w * float(NEUTRAL_COEF),
                "protection": prot_w,
                "explain": explain,
            }
        )

    # 汇总分数
    total_risk_score = sum(v["risk"] for v in module_acc.values())
    total_neutral_raw = sum(v["neutral_raw"] for v in module_acc.values())
    total_protection_score = sum(v["protection"] for v in module_acc.values())

    # —— 保护分抵消上限（与原逻辑保持一致）——
    core_risk_val = 0.0
    # 用“核心风险域”粗略代表：选取 A/B/C/D/E 中风险合计
    for mk in ["a1", "a2", "a3_1", "a3_2", "b1_1", "b1_2", "c1", "c2", "d1", "d2", "e1a", "e1b", "e2"]:
        if mk in module_acc:
            core_risk_val += module_acc[mk]["risk"]

    eff_protection = total_protection_score
    eff_neutral = total_neutral_raw * float(NEUTRAL_COEF)

    if len(hard_flags) > 0:
        prot_cap_factor = 0.3
    elif core_risk_val >= 4.0:
        prot_cap_factor = 0.5
    else:
        prot_cap_factor = 0.8

    if total_risk_score > 0:
        max_prot_offset = total_risk_score * prot_cap_factor
        if eff_protection > max_prot_offset:
            eff_protection = max_prot_offset

    net_risk_score = total_risk_score - eff_protection - eff_neutral

    # 四级经验阈值（与原保持一致）
    GREEN_MAX = 0.0
    BLUE_MAX = 9.0
    YELLOW_MAX = 15.0

    if net_risk_score <= GREEN_MAX:
        alert = GREEN_ALERT
    elif net_risk_score <= BLUE_MAX:
        alert = BLUE_ALERT
    elif net_risk_score <= YELLOW_MAX:
        alert = YELLOW_ALERT
    else:
        alert = RED_ALERT

    # AI 分数（可选）
    ml_risk_score = None
    if ML_BUNDLE is not None:
        try:
            model = ML_BUNDLE["model"]
            base_keys = ML_BUNDLE.get("base_keys", [])
            # extra_features 目前在训练脚本里只是占位；保留兼容
            x_vec = [float(_get_raw_scale_value(k)) for k in base_keys]

            # 与训练脚本一致的交互项（保持原 app 的三个交互）
            def _v(k: str) -> float:
                return float(_get_raw_scale_value(k))

            inter_fam_emo = _v("a3_2") * _v("f2")
            inter_vio_peer = _v("b1_2") * _v("c1")
            inter_net_drop = _v("e1a") * _v("d1")
            x_vec.extend([inter_fam_emo, inter_vio_peer, inter_net_drop])

            pred = model.predict([x_vec])[0]
            ml_risk_score = max(0.0, min(100.0, float(pred) * 100.0))
        except Exception as e:
            _audit_safe("ml_infer_failed", {"error": str(e)})

    df_contrib = pd.DataFrame(contributions)
    df_contrib["net"] = df_contrib["risk"] - df_contrib["protection"] - df_contrib["neutral_eff"]
    df_contrib = df_contrib.sort_values("net", ascending=False)

    df_module = pd.DataFrame(
        [
            {
                "模块": MODULE_CONF.get(k, {}).get("label", k),
                "risk": v["risk"],
                "protection": v["protection"],
                "neutral_eff": v["neutral_raw"] * float(NEUTRAL_COEF),
                "net": v["risk"] - v["protection"] - v["neutral_raw"] * float(NEUTRAL_COEF),
            }
            for k, v in module_acc.items()
            if (v["risk"] != 0 or v["protection"] != 0 or v["neutral_raw"] != 0)
        ]
    ).sort_values("net", ascending=False)

    # 生成研判编号（用于留痕）
    eval_payload = {
        "case": case_ctx,
        "net_risk_score": round(float(net_risk_score), 3),
        "ml_risk_score": None if ml_risk_score is None else round(float(ml_risk_score), 3),
        "alert_level": alert.get("level"),
        "hard_flags": hard_flags,
        "app_version": APP_VERSION,
    }
    eval_id = f"EV-{datetime.utcnow().strftime('%Y%m%d')}-{_hash_payload(eval_payload)}"
    eval_payload["eval_id"] = eval_id
    eval_payload["ts"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    result = {
        "eval_id": eval_id,
        "ts": eval_payload["ts"],
        "case_ctx": case_ctx,
        "app_version": APP_VERSION,
        "total_risk_score": float(total_risk_score),
        "total_protection_score": float(total_protection_score),
        "total_neutral_raw": float(total_neutral_raw),
        "eff_protection": float(eff_protection),
        "eff_neutral": float(eff_neutral),
        "net_risk_score": float(net_risk_score),
        "alert": alert,
        "hard_flags": hard_flags,
        "ml_risk_score": ml_risk_score,
        "df_contrib": df_contrib,
        "df_module": df_module,
        "eval_payload": eval_payload,
    }
    return result


def _render_header(case_ctx: Dict[str, Any]) -> None:
    title = "⚖️ 司法合规驾驶舱"
    subtitle = "未成年人风险动态评估 · 分级干预 · 合规留痕"
    right = f"版本：{APP_VERSION} · 环境：{'规则+AI' if ML_BUNDLE is not None else '规则'}"
    st.markdown(
        f"""
<div class="card" style="padding:18px 18px 14px 18px;">
  <div style="display:flex; align-items:flex-end; justify-content:space-between; gap:16px;">
    <div>
      <div style="font-size:1.55rem; font-weight:800;">{title}</div>
      <div class="small-muted" style="margin-top:6px;">{subtitle}</div>
    </div>
    <div class="small-muted" style="text-align:right; line-height:1.35;">
      <div>{right}</div>
      <div>案件：{case_ctx.get('case_id','—')} · 角色：{case_ctx.get('role','—')}</div>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _sop_checklist(alert_level: str) -> List[Dict[str, str]]:
    """以“合规流程”语言输出，避免过度指令化。"""
    if "红色" in alert_level:
        return [
            {"step": "启动应急合规复核", "why": "存在高风险或硬触发项，需优先人工研判"},
            {"step": "核验信息源与证据链", "why": "确保事实基础、记录完整、可追溯"},
            {"step": "跨部门联动预案", "why": "按机构制度启动联动（学校/社工/司法协同）"},
            {"step": "最小必要告知与记录", "why": "符合个人信息保护与未成年人保护要求"},
        ]
    if "黄色" in alert_level:
        return [
            {"step": "纳入重点关注台账", "why": "中高风险：需要持续观察与阶段复评"},
            {"step": "制定阶段性干预计划", "why": "以风险-保护因子为导向配置资源"},
            {"step": "定期复评与留痕", "why": "形成闭环：评估→干预→复评→调整"},
        ]
    if "蓝色" in alert_level:
        return [
            {"step": "建立常态跟踪", "why": "轻度风险：建议跟进、观察变化"},
            {"step": "补齐保护性资源", "why": "通过家庭/学校支持降低风险"},
        ]
    return [
        {"step": "常态记录", "why": "当前未见显著风险：保持基础记录与必要复评"},
    ]


def _render_cockpit(result: Optional[Dict[str, Any]], case_ctx: Dict[str, Any], show_internal: bool) -> None:
    if not result:
        st.info("尚未生成研判结果。请在「评估采集面板」补充信息后，点击「生成合规研判」。")
        return

    alert = result["alert"]
    net = float(result["net_risk_score"])
    ml = result.get("ml_risk_score")

    # KPIs
    c1, c2, c3, c4 = st.columns([1.15, 1.15, 1.15, 1.55], gap="large")
    with c1:
        st.markdown('<div class="kpi">', unsafe_allow_html=True)
        st.metric("规则净风险积分", f"{net:+.1f}")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="kpi">', unsafe_allow_html=True)
        if ml is None:
            st.metric("AI 风险评分", "—")
            st.caption("AI 模型未加载或推理失败")
        else:
            st.metric("AI 风险评分", f"{ml:.1f} / 100")
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="kpi">', unsafe_allow_html=True)
        st.markdown(_alert_badge(alert["level"]), unsafe_allow_html=True)
        st.caption("预警等级（经验阈值）")
        st.markdown("</div>", unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="kpi">', unsafe_allow_html=True)
        st.caption("合规研判编号（留痕）")
        st.code(result["eval_id"])
        st.caption(f"生成时间：{result['ts']}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # 左：画像 / 右：合规处置
    left, right = st.columns([1.3, 1.0], gap="large")
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📌 风险域画像（模块净贡献）")
        dfm = result["df_module"].copy()
        if not dfm.empty:
            fig = px.bar(dfm.head(10), x="net", y="模块", orientation="h")
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=35, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("当前暂无可展示的模块贡献。")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card" style="margin-top:14px;">', unsafe_allow_html=True)
        st.subheader("🧠 TOP 风险因子（净贡献）")
        dfc = result["df_contrib"].copy()
        if not dfc.empty:
            show_cols = ["label", "net", "risk", "protection", "neutral_eff", "explain"]
            st.dataframe(dfc[show_cols].head(8), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🧾 合规处置建议（需专业复核）")
        st.write(alert.get("core_measure", ""))
        for step in _sop_checklist(alert["level"]):
            st.markdown(
                f"- **{step['step']}**  ·  <span class='small-muted'>{step['why']}</span>",
                unsafe_allow_html=True,
            )
        if result["hard_flags"]:
            st.error("检测到硬触发项（建议优先人工复核）：")
            for hf in result["hard_flags"][:8]:
                st.write(f"- {hf}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card" style="margin-top:14px;">', unsafe_allow_html=True)
        st.subheader("🧷 合规依据提示（概览）")
        st.caption("提示：以下仅为通用合规框架提示，不构成法律意见。")
        st.markdown(
            """
- 未成年人保护（家庭、学校、社会、司法保护）相关规范与工作机制
- 预防未成年人不良行为/违法犯罪的分级干预与矫治理念
- 家庭教育与监护责任的支持与督促机制
- 个人信息保护与未成年人信息处理的最小必要、目的限定、留痕审计原则
            """
        )
        st.markdown("</div>", unsafe_allow_html=True)

    if show_internal:
        st.markdown("---")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🔬 计算过程（内部可见）")
        st.markdown(
            f"""
- 总风险分 = **{result['total_risk_score']:.1f}**
- 总保护分 = **{result['total_protection_score']:.1f}**
- 总中性原始分 = **{result['total_neutral_raw']:.1f}**
- 中性折扣 = {result['total_neutral_raw']:.1f} × {NEUTRAL_COEF:.2f} = **{result['eff_neutral']:.1f}**
- 保护抵消上限系数 = **{result['eff_protection']/result['total_protection_score']:.2f}**（已自动限幅）
- 净风险积分 = {result['total_risk_score']:.1f} − {result['eff_protection']:.1f} − {result['eff_neutral']:.1f} = **{result['net_risk_score']:.1f}**
            """
        )
        st.markdown("</div>", unsafe_allow_html=True)


def _render_collection_panel() -> None:
    st.caption("说明：采集面板用于结构化录入。驾驶舱会以“画像 + 合规处置”呈现结果。")

    for group_title, group in QUESTIONS_GROUPS.items():
        # 本组题目数：按“顶层题目”计数（与截图一致；group 子题不另算）
        q_count = len(group)

        with st.expander(f"🧩 {group_title}", expanded=False):
            st.caption(f"本组题目数：{q_count}")

            left, right = st.columns(2, gap="large")

            # 与截图一致：按题目顺序交替放左右栏（a1 左、a2 右、a3 左…）
            for idx, (q_key, q_conf) in enumerate(group.items()):
                target = left if idx % 2 == 0 else right
                with target:
                    render_question(q_key, q_conf)


def _render_rules_explain(result: Optional[Dict[str, Any]]) -> None:
    st.subheader("🔎 规则命中解释与可解释性")
    st.markdown(
        f"""
本系统采用“规则引擎 +（可选）AI 模型”的双引擎结构：

- **规则引擎**：对每个风险/中性/保护因子赋分，并按模块权重汇总；
- **中性因子折扣**：neutral_eff = neutral_raw × {NEUTRAL_COEF:.2f}；
- **保护因子限幅**：当存在硬触发或核心风险较高时，保护分抵消比例会被限制，以避免“保护项掩盖高风险”。

> 注意：阈值、权重与映射属于“研判辅助参数”，建议依据本地制度、样本验证、专家共识持续校准。
        """
    )
    if not result:
        st.info("未生成研判结果，暂无法展示规则命中细节。")
        return
    st.markdown("#### 命中摘要")
    st.write(f"- 预警等级：{result['alert']['level']}")
    st.write(f"- 硬触发项数量：{len(result['hard_flags'])}")
    st.write(f"- 净风险积分：{result['net_risk_score']:+.1f}")
    st.markdown("#### 模块与题目贡献")
    st.dataframe(result["df_module"].head(12), use_container_width=True, hide_index=True)
    st.dataframe(result["df_contrib"].head(20), use_container_width=True, hide_index=True)


def _render_audit_and_export(result: Optional[Dict[str, Any]], show_internal: bool) -> None:
    st.subheader("🗂️ 审计留痕与导出")
    st.caption("建议：在机构内部制度下使用。导出前可选择脱敏。")

    redact = st.checkbox("导出脱敏版本（隐藏机构/人员识别信息）", value=True)

    if not result:
        st.info("尚未生成研判结果。")
        return

    payload = dict(result["eval_payload"])
    if redact:
        payload = dict(payload)
        case = dict(payload.get("case", {}))
        for k in ["org", "evaluator", "subject_name", "id_number", "phone"]:
            if k in case:
                case[k] = "***"
        payload["case"] = case

    st.markdown("#### 导出")
    st.download_button(
        "⬇️ 下载研判 JSON（留痕/归档）",
        data=json.dumps(payload, ensure_ascii=False, indent=2),
        file_name=f"{result['eval_id']}.json",
        mime="application/json",
        use_container_width=True,
    )

    if show_internal:
        # 专业人员可导出贡献明细
        csv = result["df_contrib"].to_csv(index=False)
        st.download_button(
            "⬇️ 下载贡献明细 CSV（内部研判）",
            data=csv,
            file_name=f"{result['eval_id']}_contrib.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("#### 审计日志（运行时）")
    logs = st.session_state.get("audit_log", [])
    if logs:
        st.dataframe(pd.DataFrame(logs).tail(50), use_container_width=True, hide_index=True)
    else:
        st.caption("暂无日志。")


# --- App start ---
_inject_cockpit_css()

# Sidebar: case context + permission
with st.sidebar:
    st.markdown("### ⚙️ 案件上下文")
    st.caption(f"UI Build: {UI_BUILD} · App: {APP_VERSION}")
    role = st.selectbox("使用角色", ["专业人员", "管理员", "观察者"], index=0)
    show_internal = st.toggle("显示内部研判细节", value=(role in ["专业人员", "管理员"]))
    case_id = st.text_input(
        "案件编号（内部）",
        value=st.session_state.get("case_id", f"CASE-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"),
    )
    st.session_state["case_id"] = case_id

    org = st.text_input("机构/单位（可选）", value=st.session_state.get("org", ""))
    evaluator = st.text_input("评估人员（可选）", value=st.session_state.get("evaluator", ""))
    st.session_state["org"] = org
    st.session_state["evaluator"] = evaluator

    st.markdown("---")
    st.markdown("### 🧑‍⚖️ 基本信息（用于校准）")
    student_type = st.selectbox(
        "学生类型（在校 / 辍学）",
        ["在校学生", "辍学/已离校青少年"],
        index=0 if st.session_state.get("student_type", "在校学生") == "在校学生" else 1,
    )
    st.session_state["student_type"] = student_type
    st.caption("说明：仅用于校准参数，不用于身份识别。")

    st.markdown("---")
    st.markdown("### 🔐 合规提示")
    st.caption("• 最小必要采集 • 目的限定 • 可追溯留痕 • 权限分级访问")

case_ctx = {
    "case_id": st.session_state.get("case_id", ""),
    "org": st.session_state.get("org", ""),
    "evaluator": st.session_state.get("evaluator", ""),
    "role": role,
    "student_type": st.session_state.get("student_type", "在校学生"),
}

_render_header(case_ctx)

tabs = st.tabs(["⚖️ 司法合规驾驶舱", "🧾 评估采集面板", "🔎 规则命中解释", "🗂️ 审计留痕与导出", "⚙️ 系统设置"])

with tabs[0]:
    st.markdown(" ")
    colA, colB = st.columns([1.0, 1.0], gap="large")
    with colA:
        st.caption("生成研判：将当前采集信息固化为一次“可追溯”的评估快照。")
    with colB:
        if st.button("🚦 生成合规研判", use_container_width=True):
            try:
                result = _compute_evaluation(case_ctx)
                st.session_state["last_result"] = result
                _audit_safe("evaluation_created", {"eval_id": result["eval_id"], "alert": result["alert"]["level"]})
                st.toast(f"已生成研判：{result['eval_id']}", icon="✅")
            except Exception as e:
                _audit_safe("evaluation_failed", {"error": str(e)})
                st.error(f"生成失败：{e}")

    _render_cockpit(st.session_state.get("last_result"), case_ctx, show_internal)

with tabs[1]:
    _render_collection_panel()

with tabs[2]:
    _render_rules_explain(st.session_state.get("last_result"))

with tabs[3]:
    _render_audit_and_export(st.session_state.get("last_result"), show_internal)

with tabs[4]:
    st.subheader("⚙️ 系统设置 / 校准提示")
    st.caption("这些参数通常由机构管理员/研究团队维护。")
    st.markdown("#### 当前校准与模型")
    st.write(f"- 学生类型：{case_ctx['student_type']}")
    st.write(f"- AI 模型：{'已加载' if ML_BUNDLE is not None else '未加载'}")
    st.write("- 调整参数文件：adjustment.json（如启用）")
    st.markdown("#### 建议（面向维护者）")
    st.markdown(
        """
- 若仅做规则研判，可在 requirements 中移除 **pgmpy**（会拉取 torch 与大量依赖），显著减少镜像/安装体积。
- 将 theme 配置放进容器的 `/root/.streamlit/config.toml`，或把 `.streamlit` 目录复制到镜像中，避免“宿主机改了容器不生效”。
- 生产部署建议固定依赖版本（requirements pin），并做最小化镜像（多阶段构建）。
        """
    )

# Footer
st.markdown(
    "<div class='small-muted' style='margin-top:18px;'>"
    "免责声明：本系统为研判辅助工具，输出需由具备资质的专业人员结合事实、证据与本地制度复核后使用。"
    "</div>",
    unsafe_allow_html=True,
)
