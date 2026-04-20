from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.company_profile import CompanyProfile
from app.schemas.company_profile import CompanyProfileCreate, CompanyProfileUpdate, CompanyProfileOut
from app.core.security import get_current_user, get_current_admin

router = APIRouter(prefix="/company-profile", tags=["company-profile"])


@router.get("/me", response_model=CompanyProfileOut)
def get_my_company_profile(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Get the current user's company profile."""
    profile = db.query(CompanyProfile).filter(CompanyProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(404, "Company profile not found")
    return profile


@router.post("", response_model=CompanyProfileOut)
def create_company_profile(data: CompanyProfileCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a company profile for the current user."""
    existing = db.query(CompanyProfile).filter(CompanyProfile.user_id == current_user.id).first()
    if existing:
        raise HTTPException(400, "Company profile already exists. Use PUT to update.")
    profile = CompanyProfile(user_id=current_user.id, **data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("", response_model=CompanyProfileOut)
def update_company_profile(data: CompanyProfileUpdate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Update the current user's company profile (creates if not exists)."""
    profile = db.query(CompanyProfile).filter(CompanyProfile.user_id == current_user.id).first()
    if not profile:
        # Auto-create if not exists
        profile = CompanyProfile(user_id=current_user.id, **data.model_dump(exclude_unset=True))
        db.add(profile)
    else:
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(profile, k, v)
    db.commit()
    db.refresh(profile)
    return profile


# --- Admin endpoints ---

@router.get("/all", response_model=List[CompanyProfileOut])
def list_all_company_profiles(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Admin: list all company profiles."""
    return db.query(CompanyProfile).all()


@router.get("/user/{user_id}", response_model=CompanyProfileOut)
def get_user_company_profile(user_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Admin: get a specific user's company profile."""
    profile = db.query(CompanyProfile).filter(CompanyProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(404, "Company profile not found for this user")
    return profile


@router.put("/user/{user_id}", response_model=CompanyProfileOut)
def admin_update_user_company_profile(user_id: int, data: CompanyProfileUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Admin: update (or create) a company profile for any user."""
    # Verify user exists
    from app.models.user import User
    if not db.query(User).filter(User.id == user_id).first():
        raise HTTPException(404, "User not found")
    profile = db.query(CompanyProfile).filter(CompanyProfile.user_id == user_id).first()
    if not profile:
        # Auto-create — requires both company_name and business_type (they're nullable=False on model)
        payload = data.model_dump(exclude_unset=True)
        if not payload.get("company_name") or not payload.get("business_type"):
            raise HTTPException(400, "company_name and business_type are required to create a profile")
        profile = CompanyProfile(user_id=user_id, **payload)
        db.add(profile)
    else:
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(profile, k, v)
    db.commit()
    db.refresh(profile)
    return profile
