"""
EcoMuni AI — FastAPI Backend (main.py) — FIXED
Fixes applied:
  1. SDK: reverted from google-genai (2026 SDK) to google-generativeai (stable)
     - google-genai Client() does NOT accept http_options headers; that was fabricated
     - "Bearer {api_key}" injection on an AIza* key causes 401 — keys are NOT Bearer tokens
  2. PIL Image can't be passed directly to generate_content; use inline_data bytes instead
  3. /api/leaderboard response keys unified: locality_name/cumulative_velocity_score/total_resolved
     (frontend app.py reads locality_name; old code returned "locality" and "score")
  4. /api/resolve returns full report dict (ReportOut) so frontend can read velocity_points
  5. severity_score guard: if None, default to 1 before division to avoid TypeError
  6. python-dotenv import made optional so it doesn't crash if not installed
  7. Added missing verified_at / resolved_at fields to ReportOut
  8. requirements.txt updated to use correct SDK package name
"""

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional — env vars can be set in shell

import json
import random
import base64
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    create_engine, Column, Integer, Float, String,
    Boolean, DateTime, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

import cv2
import numpy as np
from PIL import Image
import io

# ── Correct stable SDK ──────────────────────────────────────────────────────
import google.generativeai as genai

# ---------------------------------------------------------------------------
# Logging & Config
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("ecomuni")

DATABASE_URL = "sqlite:///./ecomuni.db"
GEMINI_MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Database Schema
# ---------------------------------------------------------------------------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Report(Base):
    __tablename__ = "reports"
    id             = Column(Integer, primary_key=True, index=True)
    latitude       = Column(Float, nullable=False)
    longitude      = Column(Float, nullable=False)
    citizen_id     = Column(String(255), nullable=False, index=True)
    locality_name  = Column(String(255), nullable=True)
    # Base64-encoded image so data survives ephemeral-filesystem deploys
    image_base64   = Column(Text, nullable=True)
    issue_category = Column(String(100), nullable=True)
    severity_score = Column(Integer, nullable=True)
    is_verified    = Column(Boolean, default=False, nullable=False)
    is_resolved    = Column(Boolean, default=False, nullable=False)
    reported_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    verified_at    = Column(DateTime, nullable=True)
    resolved_at    = Column(DateTime, nullable=True)
    municipal_draft = Column(Text, nullable=True)
    materials_json  = Column(Text, nullable=True)
    velocity_points = Column(Integer, default=0, nullable=False)
    raw_analysis    = Column(Text, nullable=True)


class Locality(Base):
    __tablename__ = "localities"
    id                        = Column(Integer, primary_key=True, index=True)
    locality_name             = Column(String(255), unique=True, nullable=False, index=True)
    cumulative_velocity_score = Column(Integer, default=0, nullable=False)
    total_resolved            = Column(Integer, default=0, nullable=False)
    last_updated              = Column(DateTime, default=lambda: datetime.now(timezone.utc))


Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(title="EcoMuni AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class ReportOut(BaseModel):
    id:             int
    latitude:       float
    longitude:      float
    citizen_id:     str
    locality_name:  Optional[str]
    image_base64:   Optional[str]
    issue_category: Optional[str]
    severity_score: Optional[int]
    is_verified:    bool
    is_resolved:    bool
    reported_at:    datetime
    verified_at:    Optional[datetime] = None   # FIX: was missing
    resolved_at:    Optional[datetime] = None   # FIX: was missing
    velocity_points: int
    municipal_draft: Optional[str]
    materials_json:  Optional[str]
    model_config = ConfigDict(from_attributes=True)


class LeaderboardEntry(BaseModel):
    rank:                     int
    locality_name:            str
    cumulative_velocity_score: int
    total_resolved:           int


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------
def check_synthid(file_bytes: bytes) -> bool:
    """Mock SynthID check — 95% pass rate."""
    return random.random() < 0.95


def preprocess_image_for_ai(file_bytes: bytes) -> bytes:
    """OpenCV median-blur denoising for low-light municipal photos."""
    try:
        nparr = np.frombuffer(file_bytes, np.uint8)
        img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return file_bytes
        denoised = cv2.medianBlur(img, 3)
        _, encoded = cv2.imencode('.jpg', denoised)
        return encoded.tobytes()
    except Exception as exc:
        logger.error("CV2 preprocessing failed: %s", exc)
        return file_bytes


# ── SYSTEM PROMPT (full EcoMuni schema) ─────────────────────────────────────
ECOMUNI_SYSTEM_PROMPT = """
You are EcoMuni AI, an expert civic issue analysis engine. Your sole function is to analyze
an image of a hyperlocal civic or environmental problem and return a single, raw, syntactically
perfect JSON object. Begin with { and end with }. No markdown, no code fences, no prose.

Classify into one of: POTHOLE, ROAD_CRACK, BROKEN_STREETLIGHT, GARBAGE_DUMP, OPEN_DRAIN,
SEWAGE_OVERFLOW, WATER_LOGGING, WATER_HYACINTH_BLOCKAGE, FALLEN_TREE, BROKEN_FOOTPATH,
ENCROACHMENT, AIR_POLLUTION_SOURCE, WATER_BODY_CONTAMINATION, ELECTRICAL_HAZARD,
ABANDONED_VEHICLE, GRAFFITI_VANDALISM, CONSTRUCTION_DEBRIS, DEAD_ANIMAL, OTHER.

Required JSON schema — output EXACTLY this structure:
{
  "issue_category": "string",
  "severity_score": 1-10,
  "estimated_materials_bom": ["item 1", "item 2"],
  "autonomous_municipal_draft": "Dear [MUNICIPAL_OFFICER_NAME],\\n\\nI, [CITIZEN_NAME] of [CITIZEN_ADDRESS], Ward [WARD_NUMBER], [MUNICIPALITY_NAME], write to formally report a civic issue..."
}

HARD RULES:
- severity_score must be an integer 1-10
- estimated_materials_bom must be an array of strings
- autonomous_municipal_draft must be a complete email string with placeholders
- Never refuse. Always return valid JSON.
""".strip()


def analyze_with_gemini(image_bytes: bytes) -> dict:
    """
    FIX 1: Uses google-generativeai (not google-genai).
    FIX 2: Sends image as inline_data bytes, not a PIL object.
    FIX 3: No bogus Bearer header — API keys are passed via api_key param only.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Create a .env file with GEMINI_API_KEY=AIza... "
            "or export it in your shell before running."
        )

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=ECOMUNI_SYSTEM_PROMPT,
    )

    # Pass image as raw bytes with explicit MIME — PIL objects are NOT supported
    image_part = {
        "mime_type": "image/jpeg",
        "data": image_bytes,           # bytes, not base64 string
    }

    response = model.generate_content(
        contents=[
            image_part,
            "Analyze this civic issue image and return the EcoMuni JSON."
        ],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=2048,
        ),
    )

    raw_text = response.text.strip()
    # Defensive strip of accidental markdown fences
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[-1]
        raw_text = raw_text.rsplit("```", 1)[0]

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned non-JSON: %s", raw_text[:400])
        raise ValueError(f"Gemini response was not valid JSON: {exc}") from exc


def upsert_locality(db: Session, locality_name: str, points_to_add: int = 0):
    record = db.query(Locality).filter(Locality.locality_name == locality_name).first()
    if not record:
        record = Locality(
            locality_name=locality_name,
            cumulative_velocity_score=points_to_add,
            total_resolved=1 if points_to_add > 0 else 0,
        )
        db.add(record)
    else:
        record.cumulative_velocity_score += points_to_add
        if points_to_add > 0:
            record.total_resolved += 1
        record.last_updated = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/report", response_model=ReportOut, status_code=201)
async def create_report(
    latitude:      float  = Form(...),
    longitude:     float  = Form(...),
    citizen_id:    str    = Form(...),
    locality_name: str    = Form("Default Ward"),
    image: UploadFile     = File(...),
    db: Session           = Depends(get_db),
):
    raw_bytes = await image.read()

    if not check_synthid(raw_bytes):
        raise HTTPException(
            status_code=422,
            detail={"error": "SYNTHID_REJECT", "message": "Image failed authenticity check."}
        )

    processed_bytes = preprocess_image_for_ai(raw_bytes)
    base64_str = f"data:image/jpeg;base64,{base64.b64encode(processed_bytes).decode()}"

    try:
        analysis = analyze_with_gemini(processed_bytes)
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail={"error": "CONFIG_ERROR", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=502, detail={"error": "PARSE_ERROR", "message": str(exc)})
    except Exception as exc:
        logger.exception("Gemini call failed")
        raise HTTPException(status_code=502, detail={"error": "AI_ERROR", "message": str(exc)})

    # FIX: guard against None severity before saving
    severity = analysis.get("severity_score")
    if not isinstance(severity, int) or not (1 <= severity <= 10):
        severity = 5  # safe default

    report = Report(
        latitude=latitude,
        longitude=longitude,
        citizen_id=citizen_id,
        locality_name=locality_name,
        image_base64=base64_str,
        issue_category=analysis.get("issue_category", "OTHER"),
        severity_score=severity,
        materials_json=json.dumps(analysis.get("estimated_materials_bom", [])),
        municipal_draft=json.dumps(analysis.get("autonomous_municipal_draft", "")),
        raw_analysis=json.dumps(analysis),
        is_verified=False,
        is_resolved=False,
        reported_at=datetime.now(timezone.utc),
        velocity_points=0,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    upsert_locality(db, locality_name, 0)

    logger.info("Report #%d created — %s sev=%d", report.id, report.issue_category, report.severity_score)
    return report


@app.post("/api/verify/{report_id}", response_model=ReportOut)
async def verify_report(
    report_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    if report.is_verified:
        raise HTTPException(status_code=409, detail={"error": "ALREADY_VERIFIED"})
    if not check_synthid(await image.read()):
        raise HTTPException(status_code=422, detail={"error": "SYNTHID_REJECT"})

    report.is_verified = True
    report.verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report  # FIX: return full ReportOut, not a bare dict


@app.post("/api/resolve/{report_id}", response_model=ReportOut)
async def resolve_report(
    report_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    if report.is_resolved:
        raise HTTPException(status_code=409, detail={"error": "ALREADY_RESOLVED"})
    if not check_synthid(await image.read()):
        raise HTTPException(status_code=422, detail={"error": "SYNTHID_REJECT"})

    now = datetime.now(timezone.utc)
    report.is_resolved = True
    report.resolved_at = now

    # FIX: guard None severity before multiplication
    severity = report.severity_score or 1
    reported_time = (
        report.reported_at.replace(tzinfo=timezone.utc)
        if report.reported_at.tzinfo is None
        else report.reported_at
    )
    hours = max(1.0, (now - reported_time).total_seconds() / 3600.0)
    points = int(round((severity * 1000) / hours))

    report.velocity_points = points
    db.commit()
    db.refresh(report)
    upsert_locality(db, report.locality_name or "UNKNOWN", points)

    logger.info("Report #%d resolved — %d velocity points → %s", report.id, points, report.locality_name)
    return report  # FIX: return full ReportOut so frontend gets velocity_points


@app.get("/api/leaderboard")
def get_leaderboard(limit: int = 15, db: Session = Depends(get_db)):
    """
    FIX: key names match what app.py reads:
      locality_name, cumulative_velocity_score, total_resolved, rank
    Old code returned 'locality', 'score', 'resolved' — mismatches caused
    blank leaderboard rows and KeyErrors in the frontend.
    """
    rows = (
        db.query(Locality)
        .order_by(Locality.cumulative_velocity_score.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": idx + 1,
            "locality_name": r.locality_name,
            "cumulative_velocity_score": r.cumulative_velocity_score,
            "total_resolved": r.total_resolved,
        }
        for idx, r in enumerate(rows)
    ]


@app.get("/api/reports", response_model=list[ReportOut])
def list_reports(limit: int = 200, locality: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Report)
    if locality:
        q = q.filter(Report.locality_name == locality)
    return q.order_by(Report.reported_at.desc()).limit(limit).all()


@app.get("/api/report/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    return report


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
