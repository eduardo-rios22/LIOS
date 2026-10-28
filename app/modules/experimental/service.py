"""Experiment rules, balanced assignment, and the R export.

The scenario matrix and the error rounds stay aligned with static/index.html.
"""

import csv
import io
import random
import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.experimental.models import Participant, RoundLog

CONDITIONS = ("C1", "C2", "C3", "C4")
# 0-based indexes: rounds 3, 6 and 9 invert the consistent alternative in C3 and C4.
ERROR_ROUND_INDEXES = frozenset({2, 5, 8})
CONDITION_FLAGS = {
    "C1": {"error": False, "explain": False},
    "C2": {"error": False, "explain": True},
    "C3": {"error": True, "explain": False},
    "C4": {"error": True, "explain": True},
}
ROUNDS = [
    {"risk": 3, "liq": 3, "horizon": 12, "a": (7, 2, 4, 12), "b": (11, 4, 2, 24)},
    {"risk": 2, "liq": 4, "horizon": 18, "a": (12, 4, 2, 30), "b": (6.5, 2, 5, 12)},
    {"risk": 3, "liq": 3, "horizon": 24, "a": (7.2, 2, 4, 18), "b": (13, 5, 1, 36)},
    {"risk": 4, "liq": 2, "horizon": 24, "a": (8.2, 3, 3, 18), "b": (14, 5, 1, 36)},
    {"risk": 2, "liq": 3, "horizon": 12, "a": (10.5, 4, 2, 24), "b": (5.8, 1, 4, 12)},
    {"risk": 3, "liq": 4, "horizon": 18, "a": (6.7, 2, 5, 12), "b": (12.4, 4, 2, 30)},
    {"risk": 4, "liq": 3, "horizon": 36, "a": (9.3, 3, 4, 24), "b": (15.1, 5, 1, 48)},
    {"risk": 3, "liq": 3, "horizon": 24, "a": (13.2, 5, 2, 36), "b": (7.8, 2, 4, 18)},
    {"risk": 2, "liq": 4, "horizon": 12, "a": (6.1, 2, 5, 12), "b": (11.8, 4, 2, 24)},
    {"risk": 3, "liq": 3, "horizon": 18, "a": (12.9, 5, 1, 36), "b": (7.4, 2, 4, 12)},
]
CSV_COLUMNS = [
    "session_id",
    "condition",
    "round",
    "chosen",
    "recommended",
    "consistent",
    "error",
    "accepted",
    "duration_seconds",
    "iu1",
    "iu2",
    "iu3",
    "iu_mean",
    "check_error",
    "check_explanation",
    "error_factor",
    "explanation_factor",
    "age",
    "country",
    "experience",
    "completed",
]

_assign_lock = threading.Lock()


class ExperimentError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _fits(alternative: tuple, scenario: dict) -> bool:
    return (
        alternative[1] <= scenario["risk"]
        and alternative[2] >= scenario["liq"]
        and alternative[3] <= scenario["horizon"]
    )


def consistent_choice(round_index: int) -> str:
    scenario = ROUNDS[round_index]
    return "A" if _fits(scenario["a"], scenario) else "B"


def recommended_choice(condition: str, round_index: int) -> str:
    consistent = consistent_choice(round_index)
    if CONDITION_FLAGS[condition]["error"] and round_index in ERROR_ROUND_INDEXES:
        return "B" if consistent == "A" else "A"
    return consistent


def _assign_condition(db: Session) -> str:
    counts = {code: 0 for code in CONDITIONS}
    rows = db.execute(
        select(Participant.condition, func.count(Participant.id)).group_by(Participant.condition)
    ).all()
    for condition, count in rows:
        if condition in counts:
            counts[condition] = int(count)
    minimum = min(counts.values())
    pool = [code for code in CONDITIONS if counts[code] == minimum]
    return random.choice(pool)


def start_session(db: Session, *, age: int, country: str, experience: str, consent: bool) -> Participant:
    if not consent:
        raise ExperimentError(400, "Se requiere consentimiento.")
    if experience != "sí":
        raise ExperimentError(400, "Se requiere al menos una inversión financiera personal.")
    country = country.strip()
    if not country:
        raise ExperimentError(400, "Indica el país de residencia.")

    with _assign_lock:
        participant = Participant(
            session_id=str(uuid.uuid4()),
            condition=_assign_condition(db),
            age=age,
            country=country,
            experience=experience,
            consent=True,
            status="in_progress",
        )
        db.add(participant)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(participant)
        return participant


def _get_participant(db: Session, session_id: str) -> Participant:
    participant = db.scalar(select(Participant).where(Participant.session_id == session_id))
    if participant is None:
        raise ExperimentError(404, "Sesión no encontrada.")
    return participant


def log_round(
    db: Session,
    *,
    session_id: str,
    round_number: int,
    chosen: str,
    duration_seconds: int,
) -> RoundLog:
    participant = _get_participant(db, session_id)
    if participant.status == "completed":
        raise ExperimentError(409, "La sesión ya está completada.")

    existing = db.scalar(
        select(RoundLog).where(
            RoundLog.participant_id == participant.id,
            RoundLog.round_number == round_number,
        )
    )
    if existing is not None:
        if existing.chosen == chosen:
            return existing
        raise ExperimentError(409, "La ronda ya fue registrada con otra elección.")

    logged = db.scalar(
        select(func.count()).select_from(RoundLog).where(RoundLog.participant_id == participant.id)
    )
    expected = int(logged or 0) + 1
    if round_number != expected:
        raise ExperimentError(409, "La ronda no sigue el orden del experimento.")

    round_index = round_number - 1
    recommended = recommended_choice(participant.condition, round_index)
    consistent = consistent_choice(round_index)
    row = RoundLog(
        participant_id=participant.id,
        round_number=round_number,
        chosen=chosen,
        recommended=recommended,
        consistent=consistent,
        is_error=recommended != consistent,
        accepted=chosen == recommended,
        duration_seconds=duration_seconds,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ExperimentError(409, "La ronda ya fue registrada.") from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(row)
    return row


def finish_session(
    db: Session,
    *,
    session_id: str,
    iu1: int,
    iu2: int,
    iu3: int,
    check_error: int,
    check_explanation: int,
) -> Participant:
    participant = _get_participant(db, session_id)
    if participant.status == "completed":
        return participant

    logged = db.scalar(
        select(func.count()).select_from(RoundLog).where(RoundLog.participant_id == participant.id)
    )
    if int(logged or 0) != len(ROUNDS):
        raise ExperimentError(409, "Faltan rondas por registrar.")

    participant.iu1 = iu1
    participant.iu2 = iu2
    participant.iu3 = iu3
    participant.check_error = check_error
    participant.check_explanation = check_explanation
    participant.status = "completed"
    participant.completed_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(participant)
    return participant


def _r_bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def _blank(value: int | None) -> int | str:
    return "" if value is None else value


def build_csv(db: Session) -> str:
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    rows = db.execute(
        select(RoundLog, Participant)
        .join(Participant, RoundLog.participant_id == Participant.id)
        .order_by(Participant.id, RoundLog.round_number)
    ).all()
    for round_log, participant in rows:
        flags = CONDITION_FLAGS[participant.condition]
        if None not in (participant.iu1, participant.iu2, participant.iu3):
            iu_mean = f"{(participant.iu1 + participant.iu2 + participant.iu3) / 3:.3f}"
        else:
            iu_mean = ""
        writer.writerow(
            [
                participant.session_id,
                participant.condition,
                round_log.round_number,
                round_log.chosen,
                round_log.recommended,
                round_log.consistent,
                _r_bool(round_log.is_error),
                _r_bool(round_log.accepted),
                round_log.duration_seconds,
                _blank(participant.iu1),
                _blank(participant.iu2),
                _blank(participant.iu3),
                iu_mean,
                _blank(participant.check_error),
                _blank(participant.check_explanation),
                1 if flags["error"] else 0,
                1 if flags["explain"] else 0,
                participant.age,
                participant.country,
                participant.experience,
                _r_bool(participant.status == "completed"),
            ]
        )
    return buffer.getvalue()
