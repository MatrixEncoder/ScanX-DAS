"""
targets.py — CRUD API routes for Target management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend import models
from backend.schemas import TargetCreate, TargetOut

router = APIRouter(prefix="/targets", tags=["Targets"])


@router.get("/", response_model=List[TargetOut])
def list_targets(db: Session = Depends(get_db)):
    return db.query(models.Target).order_by(models.Target.created_at.desc()).all()


@router.post("/", response_model=TargetOut, status_code=201)
def create_target(payload: TargetCreate, db: Session = Depends(get_db)):
    url = payload.base_url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    data = payload.model_dump()
    data["base_url"] = url
    target = models.Target(**data)
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.get("/{target_id}", response_model=TargetOut)
def get_target(target_id: int, db: Session = Depends(get_db)):
    target = db.query(models.Target).filter(models.Target.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@router.put("/{target_id}", response_model=TargetOut)
def update_target(target_id: int, payload: TargetCreate, db: Session = Depends(get_db)):
    target = db.query(models.Target).filter(models.Target.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    data = payload.model_dump(exclude_none=True)
    if "base_url" in data:
        url = data["base_url"].strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        data["base_url"] = url
    for field, value in data.items():
        setattr(target, field, value)
    db.commit()
    db.refresh(target)
    return target


@router.delete("/{target_id}", status_code=204)
def delete_target(target_id: int, db: Session = Depends(get_db)):
    target = db.query(models.Target).filter(models.Target.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    db.delete(target)
    db.commit()
