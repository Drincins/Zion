# bot/report_data.py
import datetime as dt
import json
import logging
import os
import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, List, Any, Dict

from sqlalchemy import and_, func

from backend.bd.database import SessionLocal
from backend.bd.models import (
    Checklist,
    ChecklistAnswer,
    ChecklistQuestion,
    ChecklistQuestionAnswer,
    ChecklistSection,
    Company,
    User,
)

from .checklists_timezone import to_moscow

logger = logging.getLogger(__name__)


@dataclass
class AnswerRow:
    number: int
    question: str
    qtype: str
    answer: str
    comment: Optional[str] = None
    score: Optional[float] = None    # набранный балл
    weight: Optional[float] = None   # максимальный вес вопроса
    photo_path: Optional[str] = None
    photo_label: Optional[str] = None
    section_id: Optional[int] = None
    section_title: Optional[str] = None


@dataclass
class SectionResult:
    title: str
    answers: List[AnswerRow]
    total_score: Optional[float] = None
    total_max: Optional[float] = None
    percent: Optional[float] = None


@dataclass
class AttemptData:
    attempt_id: int
    checklist_name: str
    user_name: str
    company_name: Optional[str]
    department: Optional[str]
    submitted_at: dt.datetime
    answers: List[AnswerRow]
    total_score: Optional[float] = None
    total_max: Optional[float] = None
    percent: Optional[float] = None
    is_scored: bool = False
    sections: Optional[List[SectionResult]] = None


@dataclass
class AttemptScoreSummary:
    attempt_id: int
    is_scored: bool
    total_score: Optional[float] = None
    total_max: Optional[float] = None
    percent: Optional[float] = None


# ---------------- formatting helpers ----------------

def _fmt_number(value: Optional[float]) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return ("{:.2f}".format(float(value))).rstrip("0").rstrip(".")
    return str(value)


def format_attempt_result(data: AttemptData, include_unscored: bool = False) -> Optional[str]:
    if data.is_scored and data.total_score is not None and data.total_max is not None:
        percent_text = f" ({_fmt_number(data.percent)}%)" if data.percent is not None else ""
        return (
            f"Набрано {_fmt_number(data.total_score)} из "
            f"{_fmt_number(data.total_max)} баллов{percent_text}"
        )

    if include_unscored:
        scored_rows = [r.score for r in data.answers if isinstance(r.score, (int, float))]
        if scored_rows:
            total_score = sum(float(s) for s in scored_rows)
            return f"Набранные баллы: {_fmt_number(total_score)}"

    return None


# ---------------- helpers ----------------

def _dbg_enabled() -> bool:
    return os.getenv("DEBUG_SCORES", "").strip().lower() in {"1", "true", "yes", "on"}


def _log(msg: str):
    if _dbg_enabled():
        logger.debug(msg)


def _as_dict(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


def _first_present(d: dict, keys: List[str]):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _to_float(v) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _merge_meta(*parts: dict) -> dict:
    merged: Dict[str, Any] = {}
    for p in parts:
        if isinstance(p, dict):
            merged.update(p)
    return merged


def _extract_weight(meta: dict) -> Optional[float]:
    candidate = _first_present(meta, [
        # англ варианты
        "weight", "score_weight", "points", "max_points", "max_score", "score", "weight_value",
        # русские
        "вес", "балл", "баллы",
    ])
    return _to_float(candidate)


def _extract_scale_max(meta: dict) -> Optional[float]:
    # прямые ключи
    direct = _first_present(meta, ["max", "scale_max", "max_value", "upper", "upper_bound"])
    mx = _to_float(direct)
    if mx:
        return mx

    # options: len / max(value)
    opts = meta.get("options")
    if isinstance(opts, (list, tuple)) and len(opts) > 0:
        if not isinstance(opts[0], dict):
            return _to_float(len(opts)) or None
        vals = []
        for it in opts:
            if isinstance(it, dict):
                cand = _first_present(it, ["value", "val", "score", "points"])
                f = _to_float(cand)
                if f is not None:
                    vals.append(f)
        if vals:
            return max(vals)
        return _to_float(len(opts)) or None

    # values / choices
    for key in ["values", "choices"]:
        seq = meta.get(key)
        if isinstance(seq, (list, tuple)) and len(seq) > 0:
            return _to_float(len(seq)) or None

    # range "1-5"
    rng = meta.get("range")
    if isinstance(rng, str):
        m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*$", rng)
        if m:
            return _to_float(m.group(2))

    return None


# ---------------- main ----------------

def get_attempt_data(attempt_id: int) -> AttemptData:
    """
    Считает score/weight так:
      - yes/no:   Да → score=weight, иначе 0
      - scale:    score = weight * (value / scale_max), scale_max берём из meta/столбцов; дефолт 10
      - прочие:   score=None
    Источники данных для weight/scale_max (по убыв. приоритета):
      1) ChecklistQuestion.meta
      2) Отдельные числовые поля у ChecklistQuestion (если есть): weight/score_weight/max/scale_max/max_value
    """
    with SessionLocal() as db:
        attempt: ChecklistAnswer = (
            db.query(ChecklistAnswer)
            .filter(ChecklistAnswer.id == attempt_id)
            .one()
        )

        checklist_obj = db.get(Checklist, attempt.checklist_id)
        checklist_name = checklist_obj.name if checklist_obj else f"Checklist #{attempt.checklist_id}"
        is_scored = bool(getattr(checklist_obj, "is_scored", False))

        user_row = db.get(User, attempt.user_id)
        if user_row:
            parts = [user_row.last_name, user_row.first_name, user_row.middle_name]
            cleaned = [p.strip() for p in parts if p and p.strip()]
            user_name = " ".join(cleaned) if cleaned else (user_row.username or "Неизвестный сотрудник")
        else:
            user_name = "Неизвестный сотрудник"

        company_name = None
        department_name = getattr(attempt, "department", None)
        if user_row:
            if user_row.company_id:
                company_name = (
                    db.query(Company.name)
                    .filter(Company.id == user_row.company_id)
                    .scalar()
                )
            if not department_name:
                departments: list[str] = []
                if getattr(user_row, "workplace_restaurant", None):
                    departments.append(user_row.workplace_restaurant.name)
                for rest in (user_row.restaurants or []):
                    if rest and rest.name:
                        departments.append(rest.name)
                seen: set[str] = set()
                unique = [name for name in departments if not (name in seen or seen.add(name))]
                if unique:
                    department_name = ", ".join(unique)

        submitted_at = attempt.submitted_at or dt.datetime.utcnow()
        submitted_at = to_moscow(submitted_at) or submitted_at

        # вопросы (meta берём сразу), чтобы сохранить порядок
        q_sub = (
            db.query(
                ChecklistQuestion.id,
                ChecklistQuestion.text,
                ChecklistQuestion.type,
                ChecklistQuestion.order,
                ChecklistQuestion.meta,
                ChecklistQuestion.weight.label("qweight"),
                ChecklistQuestion.section_id,
                ChecklistSection.name.label("section_title"),
                ChecklistSection.order.label("section_order"),
            )
            .outerjoin(ChecklistSection, ChecklistSection.id == ChecklistQuestion.section_id)
            .filter(ChecklistQuestion.checklist_id == attempt.checklist_id)
            .subquery()
        )

        # ответы этой попытки (без meta у ответа)
        q_and_a = (
            db.query(
                q_sub.c.id.label("qid"),
                q_sub.c.text.label("qtext"),
                q_sub.c.type.label("qtype"),
                q_sub.c.order.label("qorder"),
                q_sub.c.meta.label("qmeta"),
                q_sub.c.qweight.label("qweight"),
                q_sub.c.section_id.label("section_id"),
                q_sub.c.section_title.label("section_title"),
                q_sub.c.section_order.label("section_order"),
                ChecklistQuestionAnswer.response_value,
                ChecklistQuestionAnswer.comment,
                ChecklistQuestionAnswer.photo_path,
            )
            .outerjoin(
                ChecklistQuestionAnswer,
                (ChecklistQuestionAnswer.question_id == q_sub.c.id)
                & (ChecklistQuestionAnswer.answer_id == attempt_id)
            )
            .order_by(
                func.coalesce(q_sub.c.section_order, 10 ** 6).asc(),
                q_sub.c.order.asc(),
                q_sub.c.id.asc(),
            )
            .all()
        )

        rows: List[AnswerRow] = []
        total_score_acc = 0.0
        total_max_acc = 0.0
        has_scored_questions = False
        sections_map: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        for idx, row in enumerate(q_and_a, start=1):
            answer_raw = row.response_value
            answer_str = "" if answer_raw is None else str(answer_raw)

            # meta из вопроса
            m_q = _as_dict(row.qmeta)

            m_cols: Dict[str, Any] = {}
            if row.qweight is not None:
                m_cols["weight"] = row.qweight

            meta_all = _merge_meta(m_q, m_cols)

            weight    = _extract_weight(meta_all)
            scale_max = _extract_scale_max(meta_all) or 5.0

            qtype = (row.qtype or "").lower().strip()
            score: Optional[float] = None

            if weight is not None:
                has_scored_questions = True
                if qtype in {"yesno", "boolean", "bool", "yn"}:
                    s = answer_str.strip().lower()
                    score = weight if s in {"yes", "да", "true", "1"} else 0.0
                elif qtype in {"scale", "rating"}:
                    try:
                        val = float(answer_str) if answer_str.strip() != "" else 0.0
                    except Exception:
                        val = 0.0
                    mx = scale_max if (scale_max and scale_max > 0) else 5.0
                    ratio = val / mx if mx else 0.0
                    ratio = max(0.0, min(1.0, ratio))
                    score = weight * ratio
                else:
                    score = None

            if weight is None:
                _log(f"[SCORE] No weight for Q{idx} (id={row.qid}): '{row.qtext[:50]}', meta_all={meta_all}")
            else:
                _log(f"[SCORE] Q{idx} (id={row.qid}): weight={weight}, type={qtype}, ans='{answer_str}', scale_max={scale_max} -> score={score}")
                total_max_acc += weight
                if score is not None:
                    total_score_acc += max(0.0, score)
                else:
                    # вопрос с весом, но без подсчитанного балла — считаем 0
                    total_score_acc += 0.0

            section_title = (row.section_title or "Без раздела").strip() or "Без раздела"
            section_id = row.section_id
            section_key = section_id if section_id is not None else f"__none__:{section_title}"

            if section_key not in sections_map:
                sections_map[section_key] = {
                    "result": SectionResult(title=section_title, answers=[]),
                    "score_acc": 0.0,
                    "max_acc": 0.0,
                }

            answer_row = AnswerRow(
                number=idx,
                question=row.qtext,
                qtype=row.qtype,
                answer=answer_str,
                comment=row.comment,
                score=score,
                weight=weight,
                photo_path=row.photo_path,
                photo_label=f"Вопрос №{idx}",
                section_id=section_id,
                section_title=section_title,
            )
            rows.append(answer_row)

            section_entry = sections_map[section_key]
            section_entry["result"].answers.append(answer_row)
            if weight is not None:
                section_entry["max_acc"] += weight
                if score is not None:
                    section_entry["score_acc"] += max(0.0, score)
                else:
                    section_entry["score_acc"] += 0.0

        section_results: List[SectionResult] = []
        for entry in sections_map.values():
            result = entry["result"]
            max_acc = entry["max_acc"]
            score_acc = entry["score_acc"]
            if is_scored and max_acc > 0:
                result.total_max = round(max_acc, 2)
                result.total_score = round(score_acc, 2)
                result.percent = round((score_acc / max_acc) * 100, 2) if max_acc else None
            section_results.append(result)

        total_score = None
        total_max = None
        percent = None
        if is_scored and has_scored_questions and total_max_acc > 0:
            total_score = round(total_score_acc, 2)
            total_max = round(total_max_acc, 2)
            percent = round((total_score_acc / total_max_acc) * 100, 2)

        return AttemptData(
            attempt_id=attempt_id,
            checklist_name=checklist_name,
            user_name=user_name,
            company_name=company_name,
            department=department_name,
            submitted_at=submitted_at,
            answers=rows,
            total_score=total_score,
            total_max=total_max,
            percent=percent,
            is_scored=is_scored,
            sections=section_results or None,
        )


def get_attempt_scores_map(attempt_ids: List[int]) -> Dict[int, AttemptScoreSummary]:
    """
    Batch score calculation for report lists.
    Mirrors scoring logic from get_attempt_data but avoids per-attempt N+1 calls.
    """
    normalized_ids: list[int] = []
    seen_ids: set[int] = set()
    for raw_id in attempt_ids or []:
        try:
            attempt_id = int(raw_id)
        except Exception:
            continue
        if attempt_id <= 0 or attempt_id in seen_ids:
            continue
        seen_ids.add(attempt_id)
        normalized_ids.append(attempt_id)

    if not normalized_ids:
        return {}

    with SessionLocal() as db:
        attempts_info = (
            db.query(
                ChecklistAnswer.id.label("attempt_id"),
                Checklist.is_scored.label("is_scored"),
            )
            .join(Checklist, Checklist.id == ChecklistAnswer.checklist_id)
            .filter(ChecklistAnswer.id.in_(normalized_ids))
            .all()
        )
        if not attempts_info:
            return {}

        score_state: Dict[int, Dict[str, Any]] = {}
        for row in attempts_info:
            aid = int(row.attempt_id)
            score_state[aid] = {
                "is_scored": bool(row.is_scored),
                "total_score_acc": 0.0,
                "total_max_acc": 0.0,
                "has_scored_questions": False,
            }

        rows = (
            db.query(
                ChecklistAnswer.id.label("attempt_id"),
                ChecklistQuestion.type.label("qtype"),
                ChecklistQuestion.meta.label("qmeta"),
                ChecklistQuestion.weight.label("qweight"),
                ChecklistQuestionAnswer.response_value.label("response_value"),
            )
            .join(ChecklistQuestion, ChecklistQuestion.checklist_id == ChecklistAnswer.checklist_id)
            .outerjoin(
                ChecklistQuestionAnswer,
                and_(
                    ChecklistQuestionAnswer.answer_id == ChecklistAnswer.id,
                    ChecklistQuestionAnswer.question_id == ChecklistQuestion.id,
                ),
            )
            .filter(ChecklistAnswer.id.in_(normalized_ids))
            .order_by(ChecklistAnswer.id.asc(), ChecklistQuestion.order.asc(), ChecklistQuestion.id.asc())
            .all()
        )

        for row in rows:
            attempt_id = int(row.attempt_id)
            state = score_state.get(attempt_id)
            if not state:
                continue

            answer_raw = row.response_value
            answer_str = "" if answer_raw is None else str(answer_raw)

            m_q = _as_dict(row.qmeta)
            m_cols: Dict[str, Any] = {}
            if row.qweight is not None:
                m_cols["weight"] = row.qweight
            meta_all = _merge_meta(m_q, m_cols)

            weight = _extract_weight(meta_all)
            if weight is None:
                continue

            state["has_scored_questions"] = True
            qtype = (row.qtype or "").lower().strip()
            score: Optional[float] = None

            if qtype in {"yesno", "boolean", "bool", "yn"}:
                s = answer_str.strip().lower()
                score = weight if s in {"yes", "да", "true", "1"} else 0.0
            elif qtype in {"scale", "rating"}:
                try:
                    val = float(answer_str) if answer_str.strip() != "" else 0.0
                except Exception:
                    val = 0.0
                scale_max = _extract_scale_max(meta_all) or 5.0
                mx = scale_max if (scale_max and scale_max > 0) else 5.0
                ratio = val / mx if mx else 0.0
                ratio = max(0.0, min(1.0, ratio))
                score = weight * ratio
            else:
                score = None

            state["total_max_acc"] += weight
            state["total_score_acc"] += max(0.0, score) if score is not None else 0.0

        result: Dict[int, AttemptScoreSummary] = {}
        for attempt_id, state in score_state.items():
            is_scored = bool(state["is_scored"])
            total_score: Optional[float] = None
            total_max: Optional[float] = None
            percent: Optional[float] = None
            total_max_acc = float(state["total_max_acc"] or 0.0)
            total_score_acc = float(state["total_score_acc"] or 0.0)
            has_scored_questions = bool(state["has_scored_questions"])

            if is_scored and has_scored_questions and total_max_acc > 0:
                total_score = round(total_score_acc, 2)
                total_max = round(total_max_acc, 2)
                percent = round((total_score_acc / total_max_acc) * 100, 2)

            result[attempt_id] = AttemptScoreSummary(
                attempt_id=attempt_id,
                is_scored=is_scored,
                total_score=total_score,
                total_max=total_max,
                percent=percent,
            )

        return result
