import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.modules.experimental import service
from app.modules.experimental.schemas import (
    FinishRequest,
    FinishResponse,
    RoundRequest,
    RoundResponse,
    StartRequest,
    StartResponse,
)
from app.modules.experimental.service import ExperimentError

router = APIRouter()


def _call(action):
    try:
        return action()
    except ExperimentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _token_ok(token: str) -> bool:
    expected = settings.ADMIN_EXPORT_TOKEN
    if len(token) != len(expected):
        return False
    return secrets.compare_digest(token, expected)


@router.post("/start", response_model=StartResponse)
def start(payload: StartRequest, db: Session = Depends(get_db)) -> StartResponse:
    participant = _call(
        lambda: service.start_session(
            db,
            age=payload.age,
            country=payload.country,
            experience=payload.experience,
            consent=payload.consent,
        )
    )
    return StartResponse(session_id=participant.session_id, condition=participant.condition)


@router.post("/round", response_model=RoundResponse)
def record_round(payload: RoundRequest, db: Session = Depends(get_db)) -> RoundResponse:
    row = _call(
        lambda: service.log_round(
            db,
            session_id=payload.session_id,
            round_number=payload.round,
            chosen=payload.chosen,
            duration_seconds=payload.duration_seconds,
        )
    )
    return RoundResponse(
        session_id=payload.session_id,
        round=row.round_number,
        chosen=row.chosen,
        recommended=row.recommended,
        consistent=row.consistent,
        error=row.is_error,
        accepted=row.accepted,
    )


@router.post("/finish", response_model=FinishResponse)
def finish(payload: FinishRequest, db: Session = Depends(get_db)) -> FinishResponse:
    _call(
        lambda: service.finish_session(
            db,
            session_id=payload.session_id,
            iu1=payload.iu1,
            iu2=payload.iu2,
            iu3=payload.iu3,
            check_error=payload.check_error,
            check_explanation=payload.check_explanation,
        )
    )
    return FinishResponse(ok=True)


@router.get("/admin/export-csv")
def export_csv(token: str = Query(...), db: Session = Depends(get_db)) -> Response:
    if not _token_ok(token):
        raise HTTPException(status_code=401, detail="Token inválido.")
    csv_text = service.build_csv(db)
    return Response(
        content=csv_text.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="lios_experiment.csv"'},
    )
