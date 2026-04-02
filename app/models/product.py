from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"), nullable=False)
    base_price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    has_variants = Column(Boolean, default=False)  # sizes, colors, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    subcategory = relationship("SubCategory", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    discount_slabs = relationship("DiscountSlab", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    image_url = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    product = relationship("Product", back_populates="images")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_type = Column(String, nullable=False)   # "size", "color", "material"
    variant_value = Column(String, nullable=False)  # "XL", "Red", "Cotton"
    price_adjustment = Column(Float, default=0.0)   # +/- on base_price
    stock = Column(Integer, default=0)
    sku = Column(String, nullable=True)

    product = relationship("Product", back_populates="variants")
    order_items = relationship("OrderItem", back_populates="variant")


class DiscountSlab(Base):
    __tablename__ = "discount_slabs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    min_quantity = Column(Integer, nullable=False)
    discount_percentage = Column(Float, nullable=False)

    product = relationship("Product", back_populates="discount_slabs")
