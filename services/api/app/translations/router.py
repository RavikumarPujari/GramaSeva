import hashlib
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.issues import TranslationRecord
from workers.adapters.translation.adapter import translation_adapter, MODEL_ID, MODEL_VERSION

router = APIRouter(prefix="/translations", tags=["Multilingual Translations"])

class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source_language: str = Field(default="en")
    target_language: str = Field(default="kn")

class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    is_machine_translated: bool
    model_id: str
    model_version: str
    disclaimer: str

@router.post("", response_model=TranslationResponse)
def translate_text(
    req: TranslationRequest,
    db: Session = Depends(get_db),
):
    """
    Dynamic machine translation for complaints and evidence (README Section 7.1F, 12.2).
    - Preserves original user text unchanged.
    - Explicitly labels translations as 'Machine translated'.
    - Provides cached lookup by text SHA-256 and language pair.
    """
    src = req.source_language.lower()[:2]
    tgt = req.target_language.lower()[:2]
    text_hash = hashlib.sha256(f"{src}:{tgt}:{req.text}".encode("utf-8")).hexdigest()

    # Check database cache
    record = (
        db.query(TranslationRecord)
        .filter(
            TranslationRecord.source_text_hash == text_hash,
            TranslationRecord.source_language == src,
            TranslationRecord.target_language == tgt,
        )
        .first()
    )

    if record:
        return TranslationResponse(
            original_text=record.original_text,
            translated_text=record.translated_text,
            source_language=record.source_language,
            target_language=record.target_language,
            is_machine_translated=record.is_machine_translated,
            model_id=record.model_id,
            model_version=MODEL_VERSION,
            disclaimer="Machine translated. Official decisions use verified original text.",
        )

    # Perform translation via IndicTrans2 adapter
    result = translation_adapter.translate(req.text, source_lang=src, target_lang=tgt)

    # Persist in cache
    new_record = TranslationRecord(
        source_text_hash=text_hash,
        source_language=src,
        target_language=tgt,
        original_text=req.text,
        translated_text=result["translated_text"],
        model_id=MODEL_ID,
        is_machine_translated=True,
    )
    db.add(new_record)
    db.commit()

    return TranslationResponse(
        original_text=req.text,
        translated_text=result["translated_text"],
        source_language=src,
        target_language=tgt,
        is_machine_translated=True,
        model_id=MODEL_ID,
        model_version=MODEL_VERSION,
        disclaimer=result.get("disclaimer") or "Machine translated. Official decisions use verified original text.",
    )
