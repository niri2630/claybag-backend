from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    icon = Column(String, default="category", nullable=False)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    # "multi_qty" = per-variant quantity (apparel), "single_select" = pick one per group (paper, bottles)
    variant_mode = Column(String, default="multi_qty", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subcategories = relationship("SubCategory", back_populates="category", cascade="all, delete-orphan")


class SubCategory(Base):
    __tablename__ = "subcategories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    category = relationship("Category", back_populates="subcategories")
    products = relationship("Product", back_populates="subcategory", cascade="all, delete-orphan")
