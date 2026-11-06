# -*- coding: utf-8 -*-
"""plan-iterate normalize_review 字段漂移兜底测试。

直接调用 plugins/rulertu-flow/skills/plan-iterate/scripts/normalize.py 的
normalize_review，覆盖真实故障形态（2026-11-06 peirasim 五轮评审的模型输出
priority/problem/location/impact/recommendation 五段式，severity 缺失触发
"invalid issue severity"、脚本以退出码 4 终止）与必须仍然拒绝的协议违规形态。
"""
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
NORMALIZE = REPO_ROOT / "plugins" / "rulertu-flow" / "skills" / "plan-iterate" / "scripts" / "normalize.py"
_spec = importlib.util.spec_from_file_location("plan_iterate_normalize", NORMALIZE)
assert _spec is not None and _spec.loader is not None  # 脚本随仓库分发，缺失即仓库损坏
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
normalize_review = _module.normalize_review
ReviewError = _module.ReviewError


def drift_review() -> dict:
    """真实故障形态：与 peirasim 五轮评审 JSON 同构的最小样例。"""
    return {
        "overall_quality": "不通过。",
        "score": 6.0,
        "issues": [{
            "priority": "P1",
            "location": "方案第 56-57 行；src/api.py:101",
            "problem": "多次运行、显式种子和研究计划没有打通请求入口。",
            "impact": "API 下单链路无法成立。",
            "recommendation": "明确请求字段并逐层传递。",
        }],
        "suggestions": ["补充字段流转表。"],
    }


def test_drift_fields_are_mapped_to_protocol() -> None:
    """priority/problem/recommendation 映射回协议字段，detail 回退 impact，location 剥除。"""
    normalized = normalize_review(drift_review())
    issue = normalized["issues"][0]
    assert issue["severity"] == "P1"
    assert issue["title"] == "多次运行、显式种子和研究计划没有打通请求入口。"
    assert issue["detail"] == "API 下单链路无法成立。"
    assert issue["suggestion"] == "明确请求字段并逐层传递。"
    assert set(issue) == {"severity", "title", "detail", "suggestion"}


def test_protocol_conformant_issue_passes_through() -> None:
    """协议字段齐备的输入不受兜底影响。"""
    review = {
        "overall_quality": "通过。",
        "score": 8.6,
        "issues": [{"severity": "P2", "title": "标题", "detail": "细节", "suggestion": "建议"}],
        "suggestions": [],
    }
    normalized = normalize_review(review)
    assert normalized["issues"][0] == {"severity": "P2", "title": "标题", "detail": "细节", "suggestion": "建议"}


def test_fix_beats_recommendation_when_both_present() -> None:
    """fix 与 recommendation 同时在场时既有 fix 映射不让位，recommendation 作多余字段剥除。"""
    review = {
        "overall_quality": "通过。",
        "score": 7.0,
        "issues": [{"severity": "P2", "title": "标题", "detail": "细节", "fix": "fix 优先", "recommendation": "让位"}],
        "suggestions": [],
    }
    normalized = normalize_review(review)
    issue = normalized["issues"][0]
    assert issue["suggestion"] == "fix 优先"
    assert set(issue) == {"severity", "title", "detail", "suggestion"}


def test_missing_severity_and_priority_still_rejected() -> None:
    """severity 与 priority 双缺仍是协议违规，兜底不得掩盖。"""
    review = drift_review()
    for key in ("priority", "severity"):
        review["issues"][0].pop(key, None)
    with pytest.raises(ReviewError):
        normalize_review(review)


def test_non_p_severity_still_rejected() -> None:
    """severity 在场但取值非法（如「高」）仍拒绝，priority 不顶替已存在的 severity。"""
    review = drift_review()
    review["issues"][0]["severity"] = "高"
    with pytest.raises(ReviewError):
        normalize_review(review)


def test_boolean_score_still_rejected() -> None:
    """布尔型分数仍拒绝。"""
    review = drift_review()
    review["score"] = True
    with pytest.raises(ReviewError):
        normalize_review(review)
