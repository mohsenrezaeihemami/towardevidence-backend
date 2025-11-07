import rispy
from sqlalchemy.orm import Session
from typing import List
from app.models.record import Record
from app.models.file import File
from app.models.project import Project

def _compute_metadata_quality(title, abstract, year, language) -> float:
    score = 0
    total = 4
    if title:
        score += 1
    if abstract:
        score += 1
    if year:
        score += 1
    if language:
        score += 1
    return score / total if total else 0.0

def import_ris_for_file(db: Session, file: File) -> int:
    project = db.get(Project, file.project_id)
    if not project:
        raise ValueError("Project not found for this file")

    with open(file.path, "r", encoding="utf-8") as f:
        entries: List[dict] = rispy.load(f)

    count = 0
    for idx, entry in enumerate(entries):
        title = entry.get("title")
        abstract = entry.get("abstract")
        year = None
        if "year" in entry:
            try:
                year = int(entry["year"])
            except Exception:
                year = None
        language = entry.get("language")
        journal = entry.get("journal_name") or entry.get("journal_name_full")
        doi = entry.get("doi")
        authors = None
        if "authors" in entry and isinstance(entry["authors"], list):
            authors = "; ".join(entry["authors"])

        record = Record(
            file_id=file.id,
            order_index=idx,
            title=title,
            abstract=abstract,
            year=year,
            language=language,
            sample_size=None,
            doi=doi,
            journal=journal,
            authors=authors,
            metadata_quality=_compute_metadata_quality(title, abstract, year, language),
        )
        db.add(record)
        count += 1

    db.commit()
    return count
