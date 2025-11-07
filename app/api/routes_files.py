import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File as FastAPIFile, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.config import settings
from app.models.project import Project, ProtocolStatus
from app.models.file import File, FileType
from app.services.ris_importer import import_ris_for_file
from app.services.protocol_extractor import extract_protocol_config

router = APIRouter(prefix="/files", tags=["Files"])

UPLOAD_DIR = settings.UPLOAD_DIR

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/ris/upload")
async def upload_ris_file(
    project_id: str,
    db: Session = Depends(get_db),
    upload: UploadFile = FastAPIFile(...),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(upload.filename or "")[1] or ".ris"
    safe_name = f"ris_{project_id}_{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    contents = await upload.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    file_row = File(
        project_id=project.id,
        name=upload.filename or safe_name,
        type=FileType.ris,
        path=file_path,
    )
    db.add(file_row)
    db.commit()
    db.refresh(file_row)

    imported = import_ris_for_file(db, file_row)

    return {
        "file_id": file_row.id,
        "original_name": file_row.name,
        "imported_records": imported,
        "message": "RIS file uploaded and records imported.",
    }

@router.post("/protocol/upload")
async def upload_protocol_file(
    project_id: str,
    db: Session = Depends(get_db),
    upload: UploadFile = FastAPIFile(...),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(upload.filename or "")[1] or ".pdf"
    safe_name = f"protocol_{project_id}_{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    contents = await upload.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    file_row = File(
        project_id=project.id,
        name=upload.filename or safe_name,
        type=FileType.protocol,
        path=file_path,
    )
    db.add(file_row)
    db.commit()
    db.refresh(file_row)

    config = extract_protocol_config(file_path)
    project.protocol_config = config
    project.protocol_status = ProtocolStatus.extracted if config else ProtocolStatus.not_uploaded
    db.commit()
    db.refresh(project)

    return {
        "file_id": file_row.id,
        "project_id": project.id,
        "protocol_status": project.protocol_status,
        "protocol_config": config,
        "message": "Protocol uploaded and configuration extracted.",
    }
