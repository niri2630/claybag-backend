from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=True)
    description = Column(Text, nullable=True)
    specifications = Column(Text, nullable=True)  # Product specs (JSON or plain text)
    use_cases = Column(Text, nullable=True)        # Target use cases
    materials = Column(Text, nullable=True)        # Material/build details
    delivery_info = Column(Text, nullable=True)    # Custom delivery notes
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"), nullable=False)
    base_price = Column(Float, nullable=False)
    compare_price = Column(Float, nullable=True)  # Original/MRP price shown as strikethrough (like Amazon)
    is_active = Column(Boolean, default=True)
    has_variants = Column(Boolean, default=False)  # sizes, colors, etc.
    is_featured = Column(Boolean, default=False)   # show in hot sellers on homepage
    min_order_qty = Column(Integer, nullable=True)   # MOQ — null means no minimum (1 unit OK)
    moq_unit = Column(String, nullable=True, default="pcs")  # Unit label for MOQ: "pcs", "sq.in", "kg", etc.
    pricing_mode = Column(String, nullable=True, default="per_unit")  # "per_unit" (default) or "per_area" (L x B x Qty)
    branding_info = Column(Text, nullable=True)       # Printing/branding methods (embroidery, screen print, etc.)
    branding_methods = Column(Text, nullable=True)    # JSON array of branding method tags
    size_chart_url = Column(String, nullable=True)    # URL to size chart image (for apparel)
    hsn_code = Column(String(10), nullable=True, index=True)  # HSN classification code for GST
    gst_rate = Column(Float, nullable=True)  # Override default GST rate (e.g. 5, 12, 18, 28). Null = use settings.DEFAULT_GST_RATE
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
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)  # tag image to a specific variant (e.g. color)
    image_url = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    product = relationship("Product", back_populates="images")
    variant = relationship("ProductVariant")


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
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)  # null = applies to all variants
    min_quantity = Column(Integer, nullable=False)
    # Legacy percentage-based discount (kept for backward compat with existing data)
    discount_percentage = Column(Float, nullable=True, default=0.0)
    # New: flat price-per-unit (INR). If set, overrides discount_percentage.
    # Example: "above 24 pcs it is ₹340" → min_quantity=25, price_per_unit=340
    price_per_unit = Column(Float, nullable=True)

    product = relationship("Product", back_populates="discount_slabs")
    variant = relationship("ProductVariant")
