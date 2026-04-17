from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    referred_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    orders = relationship("Order", back_populates="user")
    addresses = relationship("Address", back_populates="user", order_by="Address.is_default.desc()")
    company_profile = relationship("CompanyProfile", back_populates="user", uselist=False)
    wallet = relationship("Wallet", back_populates="user", uselist=False)
    referral_code = relationship("ReferralCode", back_populates="user", uselist=False)
    referrals_made = relationship("Referral", back_populates="referrer", foreign_keys="[Referral.referrer_id]")
