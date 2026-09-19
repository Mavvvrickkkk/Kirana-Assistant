import json
from database import get_db
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from models import VoiceCommand
from pipeline.voice_pipeline import VoicePipeline
from schemas import VoiceCommandProposal
from services.inventory_service import InventoryService
from services.normalizer import ProductNormalizer
from sqlalchemy.orm import Session

router = APIRouter()
pipeline = VoicePipeline()
normalizer = ProductNormalizer()


@router.post("/process", response_model=VoiceCommandProposal)
async def process_voice_or_text(
    file: UploadFile = File(None),
    text: str = Form(None),
    db: Session = Depends(get_db),
):
    if not file and not text:
        raise HTTPException(status_code=400, detail="Provide either audio file or text input.")
    audio_bytes = await file.read() if file else None
    return pipeline.process_command(db, audio_bytes=audio_bytes, text=text)


@router.post("/{command_id}/confirm")
def confirm_voice_command(command_id: str, db: Session = Depends(get_db)):
    cmd = db.query(VoiceCommand).filter(VoiceCommand.id == command_id).first()
    if not cmd:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if cmd.status != "PENDING_CONFIRMATION":
        raise HTTPException(
            status_code=400, detail=f"Command is in state '{cmd.status}', cannot confirm."
        )

    proposal = json.loads(cmd.proposal_json)
    resolved_lines = proposal.get("resolved_lines", [])

    # Validate all lines before committing
    for line in resolved_lines:
        if line.get("needs_clarification") or not line.get("product_id"):
            raise HTTPException(
                status_code=400,
                detail="Cannot commit ambiguous or invalid proposal line",
            )

    # C3 FIX: Use atomic commit — all lines succeed or all rollback
    try:
        InventoryService.commit_proposal_atomic(
            db,
            proposal_lines=resolved_lines,
            intent=proposal["intent"],
            command_id=command_id,
        )
    except ValueError as e:
        cmd.status = "REJECTED"
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))

    # Learn confirmed aliases for faster future lookup (after successful commit)
    for line in resolved_lines:
        normalizer.learn_alias(
            product_id=line["product_id"],
            alias=line["product_mention"],
            db=db,
            language=proposal.get("language", "en"),
        )

    cmd.status = "CONFIRMED"
    db.commit()

    return {"status": "SUCCESS", "message": "Transaction committed successfully"}


@router.post("/{command_id}/cancel")
def cancel_voice_command(command_id: str, db: Session = Depends(get_db)):
    cmd = db.query(VoiceCommand).filter(VoiceCommand.id == command_id).first()
    if not cmd:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if cmd.status not in ("PENDING_CONFIRMATION", "NEEDS_CLARIFICATION"):
        raise HTTPException(
            status_code=400, detail=f"Command is in state '{cmd.status}', cannot cancel."
        )

    cmd.status = "CANCELLED"
    db.commit()
    return {"status": "CANCELLED"}