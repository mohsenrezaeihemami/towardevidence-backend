import json
from datetime import datetime
from typing import Dict, Any, Tuple

import openai
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.models.record import Record
from app.models.file import File
from app.models.decision import Decision, DecisionStage, DecisionOutcome
from app.models.audit import AuditEvent, ActorType

openai.api_key = settings.OPENAI_API_KEY

SYSTEM_PROMPT = """
You are a professional systematic reviewer (PRISMA 2020, Cochrane).
You are screening TITLE and ABSTRACT records according to a given protocol configuration.
You are NOT a chatbot; you are a decision engine.
Conservative behavior:
- If key information is missing, prefer UNCLEAR rather than inventing details.
- Always explain your reasoning in structured, concise reasons.
- Always provide at least one verbatim quote used for the decision.
"""


USER_TEMPLATE = """
Protocol configuration (JSON):

{protocol_json}

Record metadata:
Title: {title}
Year: {year}
Language: {language}

Abstract:
{abstract}

Task:
Decide whether this record should be INCLUDED, EXCLUDED, or marked UNCLEAR with respect to the protocol.

Rules:
- Use ONLY information from title and abstract.
- If publication year or language clearly violate the protocol, you may EXCLUDE.
- If critical information (population, intervention, outcome, design) is missing or ambiguous, mark UNCLEAR.
- Always provide at least one verbatim quote from the title or abstract that supports your decision.
- Quote location is either "Title" or "Abstract".

Return ONLY valid JSON with this schema:

{
  "decision": "include" | "exclude" | "unclear",
  "reasons": [string],
  "verbatim_quote": string,
  "quote_location": "Title" | "Abstract",
  "qc_flag": boolean,
  "human_action_required": boolean
}
"""


def _apply_simple_guards(record: Record, protocol_config: Dict[str, Any]) -> Tuple[str | None, list[str]]:
    reasons: list[str] = []
    decision: str | None = None

    # Year guard
    yw = (protocol_config or {}).get("year_window") or {}
    if yw.get("enabled") and record.year is not None:
        min_y = yw.get("min")
        max_y = yw.get("max")
        if min_y is not None and record.year < min_y:
            decision = "exclude"
            reasons.append(f"Publication year {record.year} is below minimum {min_y} in protocol.")
        if max_y is not None and record.year > max_y:
            decision = "exclude"
            reasons.append(f"Publication year {record.year} is above maximum {max_y} in protocol.")

    # Language guard
    lang_cfg = (protocol_config or {}).get("language") or {}
    if lang_cfg.get("enabled") and record.language:
        allowed = lang_cfg.get("allow") or []
        if allowed:
            allowed_upper = [a.upper() for a in allowed]
            if record.language.upper() not in allowed_upper:
                decision = "exclude"
                reasons.append(
                    f"Language {record.language} not in allowed languages {allowed} in protocol."
                )

    return decision, reasons


def _run_llm_for_record(project: Project, record: Record) -> Dict[str, Any]:
    protocol_json = json.dumps(project.protocol_config or {}, indent=2)
    user_prompt = USER_TEMPLATE.format(
        protocol_json=protocol_json,
        title=record.title or "",
        year=record.year or "",
        language=record.language or "",
        abstract=record.abstract or "",
    )

    if not settings.OPENAI_API_KEY:
        return {
            "decision": "unclear",
            "reasons": ["OPENAI_API_KEY is not configured; LLM not called."],
            "verbatim_quote": "",
            "quote_location": "Abstract",
            "qc_flag": True,
            "human_action_required": True,
            "_model_name": "none",
        }

    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = resp.choices[0].message["content"]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "decision": "unclear",
            "reasons": ["Model did not return valid JSON."],
            "verbatim_quote": "",
            "quote_location": "Abstract",
            "qc_flag": True,
            "human_action_required": True,
        }
    data["_model_name"] = getattr(resp, "model", "gpt-4o")
    return data


def screen_record_title_abstract(db: Session, project: Project, record: Record) -> Decision:
    proto_cfg = project.protocol_config or {}
    guard_decision, guard_reasons = _apply_simple_guards(record, proto_cfg)

    if guard_decision is not None:
        dec = Decision(
            record_id=record.id,
            stage=DecisionStage.title_abstract,
            decision=DecisionOutcome(guard_decision),
            reasons=guard_reasons,
            verbatim_quote=None,
            quote_location=None,
            qc_flag=False,
            created_by="SYSTEM_RULES",
            created_at=datetime.utcnow(),
            model_name="rules_only",
            prompt_version="ta_rules_v1",
        )
        db.add(dec)
        db.commit()
        db.refresh(dec)

        audit = AuditEvent(
            decision_id=dec.id,
            record_id=record.id,
            project_id=project.id,
            actor_type=ActorType.SYSTEM,
            actor_id="SYSTEM_RULES",
            action="RULES_TA_DECISION",
            model_name="rules_only",
            prompt_version="ta_rules_v1",
            request_payload={"record_id": record.id},
            response_payload={"decision": guard_decision, "reasons": guard_reasons},
        )
        db.add(audit)
        db.commit()
        return dec

    data = _run_llm_for_record(project, record)
    decision_value = data.get("decision", "unclear")
    if decision_value not in ["include", "exclude", "unclear"]:
        decision_value = "unclear"

    reasons = data.get("reasons") or []
    if not isinstance(reasons, list):
        reasons = [str(reasons)]

    verbatim_quote = data.get("verbatim_quote") or ""
    quote_location = data.get("quote_location") or "Abstract"
    qc_flag = bool(data.get("qc_flag", False))
    model_name = data.get("_model_name", "gpt-4o")

    dec = Decision(
        record_id=record.id,
        stage=DecisionStage.title_abstract,
        decision=DecisionOutcome(decision_value),
        reasons=reasons,
        verbatim_quote=verbatim_quote,
        quote_location=quote_location,
        qc_flag=qc_flag,
        created_by="AI",
        created_at=datetime.utcnow(),
        model_name=model_name,
        prompt_version="ta_llm_v1",
    )
    db.add(dec)
    db.commit()
    db.refresh(dec)

    audit = AuditEvent(
        decision_id=dec.id,
        record_id=record.id,
        project_id=project.id,
        actor_type=ActorType.AI,
        actor_id="AI_TA",
        action="LLM_TA_DECISION",
        model_name=model_name,
        prompt_version="ta_llm_v1",
        request_payload={"record_id": record.id},
        response_payload=data,
    )
    db.add(audit)
    db.commit()

    return dec


def run_title_abstract_screening_for_project(db: Session, project_id: str) -> Dict[str, Any]:
    project = db.get(Project, project_id)
    if not project:
        raise ValueError("Project not found")

    records = (
        db.query(Record)
        .join(File, Record.file_id == File.id)
        .filter(File.project_id == project_id)
        .all()
    )

    total = 0
    skipped_already_decided = 0
    by_rules = 0
    by_llm = 0

    for rec in records:
        total += 1
        existing = (
            db.query(Decision)
            .filter(
                Decision.record_id == rec.id,
                Decision.stage == DecisionStage.title_abstract,
            )
            .order_by(Decision.created_at.desc())
            .first()
        )
        if existing:
            skipped_already_decided += 1
            continue

        before_count = db.query(Decision).count()
        dec = screen_record_title_abstract(db, project, rec)
        after_count = db.query(Decision).count()

        if after_count == before_count + 1 and dec.model_name == "rules_only":
            by_rules += 1
        else:
            by_llm += 1

    return {
        "project_id": project_id,
        "total_records_seen": total,
        "skipped_already_decided": skipped_already_decided,
        "screened_by_rules": by_rules,
        "screened_by_llm": by_llm,
    }
