from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import List

from app.core.database import SessionLocal
from app.models.project import Project
from app.models.file import File
from app.models.record import Record
from app.models.decision import Decision, DecisionStage

router = APIRouter(prefix="/export", tags=["Export"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _build_ris_for_record(record: Record, decision: Decision | None, stage: DecisionStage) -> str:
    lines: list[str] = []

    lines.append("TY  - JOUR")

    if record.authors:
        for author in record.authors.split(";"):
            author = author.strip()
            if author:
                lines.append(f"AU  - {author}")

    if record.title:
        lines.append(f"TI  - {record.title}")

    if record.abstract:
        lines.append(f"AB  - {record.abstract}")

    if record.year:
        lines.append(f"PY  - {record.year}")

    if record.language:
        lines.append(f"LA  - {record.language}")

    if record.journal:
        lines.append(f"JO  - {record.journal}")

    if getattr(record, "doi", None):
        lines.append(f"DO  - {record.doi}")

    if decision:
        stage_label = "Title/Abstract" if stage == DecisionStage.title_abstract else "Full-text"
        lines.append(
            f"N1  - Decision ({stage_label}): {decision.decision.value if decision.decision else 'N/A'}"
        )
        if decision.reasons:
            joined_reasons = "; ".join(decision.reasons)
            lines.append(f"N1  - Reasons: {joined_reasons}")
        if decision.verbatim_quote:
            lines.append(f"N1  - Quote: {decision.verbatim_quote}")
        if decision.quote_location:
            lines.append(f"N1  - Quote location: {decision.quote_location}")
        lines.append(f"N1  - QC flag: {decision.qc_flag}")

    lines.append("ER  -")

    return "\n".join(lines)

@router.get("/ris")
def export_ris_with_decisions(
    project_id: str = Query(...),
    stage: str = Query("title_abstract"),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        stage_enum = DecisionStage(stage)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid stage")

    records: List[Record] = (
        db.query(Record)
        .join(File, Record.file_id == File.id)
        .filter(File.project_id == project_id)
        .order_by(Record.order_index)
        .all()
    )

    if not records:
        raise HTTPException(status_code=400, detail="No records found for this project")

    ris_records: list[str] = []

    for rec in records:
        dec = (
            db.query(Decision)
            .filter(
                Decision.record_id == rec.id,
                Decision.stage == stage_enum,
            )
            .order_by(Decision.created_at.desc())
            .first()
        )

        ris_rec_text = _build_ris_for_record(rec, dec, stage_enum)
        ris_records.append(ris_rec_text)

    content = "\n\n".join(ris_records) + "\n"
    filename = f"towardevidence_{project_id}_{stage}.ris"

    return Response(
        content=content,
        media_type="application/x-research-info-systems",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
