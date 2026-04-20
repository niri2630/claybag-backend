from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.address import Address
from app.models.user import User
from app.schemas.address import AddressCreate, AddressUpdate, AddressOut
from app.core.security import get_current_user, get_current_admin

router = APIRouter(prefix="/addresses", tags=["addresses"])


@router.get("", response_model=List[AddressOut])
def list_addresses(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """List all addresses for the current user (default first)."""
    return (
        db.query(Address)
        .filter(Address.user_id == current_user.id)
        .order_by(Address.is_default.desc(), Address.created_at.desc())
        .all()
    )


@router.post("", response_model=AddressOut, status_code=201)
def create_address(data: AddressCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Create a new address. If marked default, unset other defaults."""
    if data.is_default:
        db.query(Address).filter(
            Address.user_id == current_user.id, Address.is_default == True
        ).update({"is_default": False})

    # If this is the user's first address, make it default
    existing_count = db.query(Address).filter(Address.user_id == current_user.id).count()
    if existing_count == 0:
        data.is_default = True

    addr = Address(user_id=current_user.id, **data.model_dump())
    db.add(addr)
    db.commit()
    db.refresh(addr)
    return addr


@router.put("/{address_id}", response_model=AddressOut)
def update_address(address_id: int, data: AddressUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Update an existing address."""
    addr = db.query(Address).filter(Address.id == address_id, Address.user_id == current_user.id).first()
    if not addr:
        raise HTTPException(404, "Address not found")

    update_data = data.model_dump(exclude_unset=True)

    # If setting as default, unset others
    if update_data.get("is_default"):
        db.query(Address).filter(
            Address.user_id == current_user.id, Address.is_default == True, Address.id != address_id
        ).update({"is_default": False})

    for key, value in update_data.items():
        setattr(addr, key, value)

    db.commit()
    db.refresh(addr)
    return addr


@router.delete("/{address_id}", status_code=204)
def delete_address(address_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Delete an address."""
    addr = db.query(Address).filter(Address.id == address_id, Address.user_id == current_user.id).first()
    if not addr:
        raise HTTPException(404, "Address not found")
    db.delete(addr)
    db.commit()


# ── Admin endpoints ─────────────────────────────────────────────────────────
# Let admins manage any user's addresses from the admin panel.

@router.get("/admin/user/{user_id}", response_model=List[AddressOut])
def admin_list_user_addresses(user_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Admin: list all addresses for any user."""
    if not db.query(User).filter(User.id == user_id).first():
        raise HTTPException(404, "User not found")
    return (
        db.query(Address)
        .filter(Address.user_id == user_id)
        .order_by(Address.is_default.desc(), Address.created_at.desc())
        .all()
    )


@router.post("/admin/user/{user_id}", response_model=AddressOut, status_code=201)
def admin_create_address(user_id: int, data: AddressCreate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Admin: create an address for any user."""
    if not db.query(User).filter(User.id == user_id).first():
        raise HTTPException(404, "User not found")
    if data.is_default:
        db.query(Address).filter(
            Address.user_id == user_id, Address.is_default == True
        ).update({"is_default": False})
    # If user has no addresses, make this default
    if db.query(Address).filter(Address.user_id == user_id).count() == 0:
        data.is_default = True
    addr = Address(user_id=user_id, **data.model_dump())
    db.add(addr)
    db.commit()
    db.refresh(addr)
    return addr


@router.put("/admin/{address_id}", response_model=AddressOut)
def admin_update_address(address_id: int, data: AddressUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Admin: update any user's address."""
    addr = db.query(Address).filter(Address.id == address_id).first()
    if not addr:
        raise HTTPException(404, "Address not found")
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("is_default"):
        db.query(Address).filter(
            Address.user_id == addr.user_id, Address.is_default == True, Address.id != address_id
        ).update({"is_default": False})
    for k, v in update_data.items():
        setattr(addr, k, v)
    db.commit()
    db.refresh(addr)
    return addr


@router.delete("/admin/{address_id}", status_code=204)
def admin_delete_address(address_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """Admin: delete any user's address."""
    addr = db.query(Address).filter(Address.id == address_id).first()
    if not addr:
        raise HTTPException(404, "Address not found")
    db.delete(addr)
    db.commit()
