"""Normalize and strictly validate a plan review document."""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from typing import Any

class ReviewError(ValueError):
    """The reviewer output does not satisfy the shared protocol."""

def normalize_review(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReviewError("review must be an object")
    review = dict(value)
    if "overall_quality" not in review and "review" in review:
        review["overall_quality"] = review.pop("review")
    review.setdefault("suggestions", [])
    issues = review.get("issues")
    if not isinstance(review.get("overall_quality"), str) or not review["overall_quality"].strip():
        raise ReviewError("overall_quality must be a non-empty string")
    score = review.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 10:
        raise ReviewError("score must be a number from 0 to 10")
    if not isinstance(issues, list) or not isinstance(review["suggestions"], list):
        raise ReviewError("issues and suggestions must be arrays")
    normalized_issues = []
    for issue in issues:
        if not isinstance(issue, dict):
            raise ReviewError("each issue must be an object")
        item = dict(issue)
        if "suggestion" not in item and "fix" in item:
            item["suggestion"] = item.pop("fix")
        # 兜底（异构后端字段漂移，如 GLM 输出 evidence/impact/fix 三段式而留空 detail）：
        # detail 缺失或空白时依次回退 impact/evidence/title；随后剥除协议外字段。
        if not isinstance(item.get("detail"), str) or not item["detail"].strip():
            for alt in ("impact", "evidence", "title"):
                candidate = item.get(alt)
                if isinstance(candidate, str) and candidate.strip():
                    item["detail"] = candidate
                    break
        item = {k: item[k] for k in ("severity", "title", "detail", "suggestion") if k in item}
        if item.get("severity") not in {"P0", "P1", "P2"}:
            raise ReviewError("invalid issue severity")
        for field in ("title", "detail", "suggestion"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ReviewError(f"issue.{field} must be a non-empty string")
        if set(item) != {"severity", "title", "detail", "suggestion"}:
            raise ReviewError("issue contains unknown fields")
        normalized_issues.append(item)
    if any(not isinstance(item, str) for item in review["suggestions"]):
        raise ReviewError("suggestions must contain strings")
    review["issues"] = normalized_issues
    # 兜底（异构后端顶层字段漂移，如 GLM 附带 passed 布尔）：剥除协议外字段；
    # 必需四字段缺失仍拒绝（真不完整 ≠ 字段多余）。
    missing = {"overall_quality", "score", "issues", "suggestions"} - set(review)
    if missing:
        raise ReviewError(f"review missing required fields: {sorted(missing)}")
    review = {k: review[k] for k in ("overall_quality", "score", "issues", "suggestions")}
    return review

def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise

def normalize_file(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewError(str(exc)) from exc
    review = normalize_review(raw)
    atomic_write_json(path, review)
    return review
