"""
Seed script: Add one product to every subcategory that doesn't already have one.
Includes appropriate variants, discount slabs, and dummy images.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models.category import Category, SubCategory
from app.models.product import Product, ProductVariant, DiscountSlab, ProductImage

db = SessionLocal()

# ── Helpers ──────────────────────────────────────────────────────────
def add_product(sub_id, name, desc, price, variants=None, discounts=None, image_url=None):
    """Create product + variants + discount slabs + image in one shot."""
    existing = db.query(Product).filter(
        Product.subcategory_id == sub_id, Product.is_active == True
    ).first()
    if existing:
        print(f"  SKIP sub_id={sub_id} — already has '{existing.name}'")
        return

    p = Product(
        name=name,
        description=desc,
        subcategory_id=sub_id,
        base_price=price,
        has_variants=bool(variants),
        is_active=True,
    )
    db.add(p)
    db.flush()  # get p.id

    # Image
    if image_url:
        db.add(ProductImage(product_id=p.id, image_url=image_url, is_primary=True, sort_order=0))

    # Variants
    if variants:
        for v in variants:
            db.add(ProductVariant(
                product_id=p.id,
                variant_type=v["type"],
                variant_value=v["value"],
                price_adjustment=v.get("adj", 0),
                stock=v.get("stock", 100),
                sku=v.get("sku"),
            ))

    # Discount slabs
    if discounts:
        for d in discounts:
            db.add(DiscountSlab(
                product_id=p.id,
                min_quantity=d["min"],
                discount_percentage=d["pct"],
            ))

    print(f"  ADD sub_id={sub_id} — '{name}' (₹{price}) | {len(variants or [])} variants | {len(discounts or [])} slabs")


# ── Standard discount tiers ──────────────────────────────────────────
BULK_DISCOUNTS = [
    {"min": 10, "pct": 5},
    {"min": 30, "pct": 10},
    {"min": 50, "pct": 15},
    {"min": 100, "pct": 20},
]

PRINT_DISCOUNTS = [
    {"min": 50, "pct": 5},
    {"min": 100, "pct": 10},
    {"min": 250, "pct": 15},
    {"min": 500, "pct": 20},
    {"min": 1000, "pct": 25},
]

SMALL_BULK = [
    {"min": 25, "pct": 5},
    {"min": 50, "pct": 10},
    {"min": 100, "pct": 15},
]

# ── Dummy images (Unsplash-sourced, reliable placeholders) ───────────
IMG = {
    "cap": "https://images.unsplash.com/photo-1588850561407-ed78c334e67a?w=600&h=600&fit=crop",
    "formal_shirt": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=600&h=600&fit=crop",
    "polo": "https://images.unsplash.com/photo-1625910513413-5fc66e60b986?w=600&h=600&fit=crop",
    "sweatshirt": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=600&h=600&fit=crop",
    "tshirt": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&h=600&fit=crop",
    "mug": "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=600&h=600&fit=crop",
    "sipper": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&h=600&fit=crop",
    "badge": "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=600&h=600&fit=crop",
    "id_card": "https://images.unsplash.com/photo-1578670812003-60745e2c2ea9?w=600&h=600&fit=crop",
    "lanyard": "https://images.unsplash.com/photo-1590402494682-cd3fb53b1f70?w=600&h=600&fit=crop",
    "booklet": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=600&h=600&fit=crop",
    "brochure": "https://images.unsplash.com/photo-1586075010923-2dd4570fb338?w=600&h=600&fit=crop",
    "photo_frame": "https://images.unsplash.com/photo-1513519245088-0e12902e35ca?w=600&h=600&fit=crop",
    "gift_cert": "https://images.unsplash.com/photo-1549465220-1a8b9238f4e1?w=600&h=600&fit=crop",
    "greeting_card": "https://images.unsplash.com/photo-1607344645866-009c320b63e0?w=600&h=600&fit=crop",
    "loyalty_card": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=600&h=600&fit=crop",
    "menu_card": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&h=600&fit=crop",
    "folder": "https://images.unsplash.com/photo-1586953208270-767889db7920?w=600&h=600&fit=crop",
    "poster": "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=600&h=600&fit=crop",
    "banner": "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=600&h=600&fit=crop",
    "standee": "https://images.unsplash.com/photo-1588412079929-790b9f593d8e?w=600&h=600&fit=crop",
    "signage": "https://images.unsplash.com/photo-1563906267088-b029e7101114?w=600&h=600&fit=crop",
    "table_sign": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=600&h=600&fit=crop",
    "sticker": "https://images.unsplash.com/photo-1572375992501-4b0892d50c69?w=600&h=600&fit=crop",
    "video_standee": "https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=600&h=600&fit=crop",
    "calendar": "https://images.unsplash.com/photo-1506784365847-bbad939e9335?w=600&h=600&fit=crop",
    "diary": "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=600&h=600&fit=crop",
    "metal_pen": "https://images.unsplash.com/photo-1585336261022-680e295ce3fe?w=600&h=600&fit=crop",
    "notebook": "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=600&h=600&fit=crop",
    "pen_set": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=600&h=600&fit=crop",
    "premium_pen": "https://images.unsplash.com/photo-1585336261022-680e295ce3fe?w=600&h=600&fit=crop",
    "ballpoint": "https://images.unsplash.com/photo-1585336261022-680e295ce3fe?w=600&h=600&fit=crop",
    "roller_pen": "https://images.unsplash.com/photo-1585336261022-680e295ce3fe?w=600&h=600&fit=crop",
    "fountain_pen": "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=600&h=600&fit=crop",
    "promo_pen": "https://images.unsplash.com/photo-1585336261022-680e295ce3fe?w=600&h=600&fit=crop",
    "bookmark": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=600&h=600&fit=crop",
    "courier_bag": "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=600&h=600&fit=crop",
    "wrapping": "https://images.unsplash.com/photo-1513885535751-8b9238bd345a?w=600&h=600&fit=crop",
    "hangtag": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=600&h=600&fit=crop",
    "kraft_bag": "https://images.unsplash.com/photo-1567016432779-094069958ea5?w=600&h=600&fit=crop",
    "sleeve": "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=600&h=600&fit=crop",
    "tube": "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=600&h=600&fit=crop",
    "pillow_pack": "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=600&h=600&fit=crop",
    "pizza_box": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&h=600&fit=crop",
    "pouch": "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=600&h=600&fit=crop",
    "biz_card": "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=600&h=600&fit=crop",
    "envelope": "https://images.unsplash.com/photo-1579547945413-497e1b99dac0?w=600&h=600&fit=crop",
    "letterhead": "https://images.unsplash.com/photo-1586953208270-767889db7920?w=600&h=600&fit=crop",
    "stamp": "https://images.unsplash.com/photo-1584727638096-042c45049ebe?w=600&h=600&fit=crop",
    "label_sticker": "https://images.unsplash.com/photo-1572375992501-4b0892d50c69?w=600&h=600&fit=crop",
    "kiosk": "https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=600&h=600&fit=crop",
    "laptop_bag": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&h=600&fit=crop",
    "design_kit": "https://images.unsplash.com/photo-1586075010923-2dd4570fb338?w=600&h=600&fit=crop",
    "gadget": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=600&h=600&fit=crop",
    "giveaway": "https://images.unsplash.com/photo-1513885535751-8b9238bd345a?w=600&h=600&fit=crop",
}

# ── Size variants for apparel ────────────────────────────────────────
def apparel_sizes(adjustments=None):
    adjs = adjustments or {"S": 0, "M": 0, "L": 0, "XL": 50, "XXL": 100}
    return [{"type": "size", "value": s, "adj": a, "stock": 80} for s, a in adjs.items()]

def apparel_colors(*colors):
    return [{"type": "color", "value": c, "adj": 0, "stock": 60} for c in colors]


# ══════════════════════════════════════════════════════════════════════
#  CATEGORY 1: APPAREL (multi_qty — size + color variants)
# ══════════════════════════════════════════════════════════════════════
print("\n── Apparel ──")

# sub_id=1 Caps — already has product
# sub_id=2 Formal Shirts
add_product(2, "Premium Cotton Formal Shirt", "Crisp wrinkle-free cotton formal shirt with custom embroidery. Perfect for corporate teams and events.", 899,
    variants=apparel_sizes({"S": 0, "M": 0, "L": 0, "XL": 50, "XXL": 100}) + apparel_colors("White", "Light Blue", "Grey"),
    discounts=BULK_DISCOUNTS, image_url=IMG["formal_shirt"])

# sub_id=3 Polo T-Shirts
add_product(3, "Classic Polo T-Shirt with Logo", "Pique cotton polo with custom logo embroidery on chest. Ideal for corporate outings and brand events.", 599,
    variants=apparel_sizes() + apparel_colors("Navy", "White", "Black", "Red"),
    discounts=BULK_DISCOUNTS, image_url=IMG["polo"])

# sub_id=4 Sweatshirt
add_product(4, "Fleece Pullover Sweatshirt", "Premium 300 GSM fleece sweatshirt with custom print. Warm, comfortable, and brand-ready.", 1199,
    variants=apparel_sizes({"S": 0, "M": 0, "L": 0, "XL": 100, "XXL": 150}) + apparel_colors("Black", "Grey Melange", "Navy"),
    discounts=BULK_DISCOUNTS, image_url=IMG["sweatshirt"])

# sub_id=5 T-Shirts — already has product


# ══════════════════════════════════════════════════════════════════════
#  CATEGORY 2: DRINKWARE (single_select — capacity + color)
# ══════════════════════════════════════════════════════════════════════
print("\n── DrinkWare ──")

# sub_id=6 Mugs
add_product(6, "Custom Printed Ceramic Mug", "Premium 330ml ceramic mug with full-color sublimation printing. Microwave and dishwasher safe.", 249,
    variants=[
        {"type": "capacity", "value": "250ml", "adj": 0, "stock": 200},
        {"type": "capacity", "value": "330ml", "adj": 30, "stock": 200},
        {"type": "capacity", "value": "450ml", "adj": 70, "stock": 150},
        {"type": "color", "value": "White", "adj": 0, "stock": 200},
        {"type": "color", "value": "Black", "adj": 20, "stock": 150},
        {"type": "color", "value": "Red", "adj": 20, "stock": 100},
        {"type": "color", "value": "Blue", "adj": 20, "stock": 100},
    ],
    discounts=BULK_DISCOUNTS, image_url=IMG["mug"])

# sub_id=7 Sipper Bottle — already has products


# ══════════════════════════════════════════════════════════════════════
#  CATEGORY 3: IDENTITY ESSENTIALS (single_select — material/size)
# ══════════════════════════════════════════════════════════════════════
print("\n── Identity Essentials ──")

# sub_id=8 Badges
add_product(8, "Custom Metal Name Badge", "Brushed metal name badge with magnetic or pin-back attachment. Full-color UV printing.", 149,
    variants=[
        {"type": "material", "value": "Brushed Silver", "adj": 0, "stock": 300},
        {"type": "material", "value": "Brushed Gold", "adj": 30, "stock": 200},
        {"type": "material", "value": "Matte Black", "adj": 20, "stock": 200},
        {"type": "size", "value": "Standard (70x25mm)", "adj": 0, "stock": 300},
        {"type": "size", "value": "Large (80x30mm)", "adj": 20, "stock": 200},
        {"type": "attachment", "value": "Magnetic", "adj": 30, "stock": 250},
        {"type": "attachment", "value": "Pin-back", "adj": 0, "stock": 250},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["badge"])

# sub_id=9 ID Cards & Card Holders
add_product(9, "PVC ID Card with Lanyard Slot", "Durable PVC ID card with full-color double-sided print. Includes barcode/QR code support.", 45,
    variants=[
        {"type": "finish", "value": "Matte", "adj": 0, "stock": 500},
        {"type": "finish", "value": "Glossy", "adj": 5, "stock": 500},
        {"type": "thickness", "value": "Standard (0.76mm)", "adj": 0, "stock": 500},
        {"type": "thickness", "value": "Thick (0.84mm)", "adj": 8, "stock": 300},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["id_card"])

# sub_id=10 Lanyards
add_product(10, "Sublimation Printed Lanyard", "Full-color sublimation printed polyester lanyard with safety breakaway clip.", 35,
    variants=[
        {"type": "width", "value": "15mm", "adj": 0, "stock": 500},
        {"type": "width", "value": "20mm", "adj": 5, "stock": 500},
        {"type": "width", "value": "25mm", "adj": 10, "stock": 400},
        {"type": "clip", "value": "J-Hook", "adj": 0, "stock": 500},
        {"type": "clip", "value": "Lobster Claw", "adj": 5, "stock": 400},
        {"type": "clip", "value": "Bulldog Clip", "adj": 8, "stock": 300},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["lanyard"])


# ══════════════════════════════════════════════════════════════════════
#  CATEGORY 4: MARKETING ESSENTIALS (multi_qty — paper/size)
# ══════════════════════════════════════════════════════════════════════
print("\n── Marketing Essentials ──")

# sub_id=11 Booklets
add_product(11, "Saddle-Stitch Booklet", "Custom printed booklet with saddle-stitch binding. Full color on premium paper.", 85,
    variants=[
        {"type": "pages", "value": "8 Pages", "adj": 0, "stock": 500},
        {"type": "pages", "value": "16 Pages", "adj": 40, "stock": 400},
        {"type": "pages", "value": "24 Pages", "adj": 70, "stock": 300},
        {"type": "paper", "value": "130 GSM Matte", "adj": 0, "stock": 500},
        {"type": "paper", "value": "170 GSM Glossy", "adj": 20, "stock": 400},
        {"type": "size", "value": "A5", "adj": 0, "stock": 500},
        {"type": "size", "value": "A4", "adj": 30, "stock": 400},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["booklet"])

# sub_id=12 Brochures & Flyers
add_product(12, "Tri-Fold Brochure", "Premium tri-fold brochure on coated paper. Vivid CMYK printing with optional spot UV finish.", 12,
    variants=[
        {"type": "paper", "value": "170 GSM Matte Art", "adj": 0, "stock": 1000},
        {"type": "paper", "value": "250 GSM Glossy Art", "adj": 4, "stock": 800},
        {"type": "paper", "value": "300 GSM Premium", "adj": 8, "stock": 500},
        {"type": "size", "value": "A4 (folds to DL)", "adj": 0, "stock": 1000},
        {"type": "size", "value": "A3 (folds to A4)", "adj": 5, "stock": 500},
        {"type": "finish", "value": "None", "adj": 0, "stock": 1000},
        {"type": "finish", "value": "Spot UV", "adj": 3, "stock": 500},
        {"type": "finish", "value": "Soft Touch Lamination", "adj": 5, "stock": 400},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["brochure"])

# sub_id=13 Photo Frames
add_product(13, "Acrylic Desktop Photo Frame", "Crystal-clear acrylic photo frame with custom brand engraving. Magnetic closure design.", 350,
    variants=[
        {"type": "size", "value": "4x6 inch", "adj": 0, "stock": 200},
        {"type": "size", "value": "5x7 inch", "adj": 50, "stock": 150},
        {"type": "size", "value": "6x8 inch", "adj": 100, "stock": 100},
        {"type": "material", "value": "Clear Acrylic", "adj": 0, "stock": 200},
        {"type": "material", "value": "Frosted Acrylic", "adj": 30, "stock": 150},
    ],
    discounts=SMALL_BULK, image_url=IMG["photo_frame"])

# sub_id=14 Gift Certificates
add_product(14, "Custom Gift Certificate", "Premium printed gift certificate on textured card stock with foil stamping and unique serial numbers.", 25,
    variants=[
        {"type": "paper", "value": "300 GSM Textured", "adj": 0, "stock": 500},
        {"type": "paper", "value": "350 GSM Linen", "adj": 8, "stock": 300},
        {"type": "finish", "value": "Gold Foil Border", "adj": 10, "stock": 400},
        {"type": "finish", "value": "Silver Foil Border", "adj": 10, "stock": 400},
        {"type": "finish", "value": "No Foil", "adj": 0, "stock": 500},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["gift_cert"])

# sub_id=15 Greeting Cards
add_product(15, "Custom Greeting Card with Envelope", "Full-color printed greeting card on premium card stock. Includes matching envelope.", 30,
    variants=[
        {"type": "size", "value": "A6 (105x148mm)", "adj": 0, "stock": 500},
        {"type": "size", "value": "A5 (148x210mm)", "adj": 10, "stock": 400},
        {"type": "paper", "value": "300 GSM Matte", "adj": 0, "stock": 500},
        {"type": "paper", "value": "350 GSM Textured", "adj": 8, "stock": 300},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["greeting_card"])

# sub_id=16 Loyalty Cards
add_product(16, "PVC Loyalty Reward Card", "Durable PVC loyalty card with custom numbering, barcode, and scratch panel option.", 18,
    variants=[
        {"type": "finish", "value": "Glossy", "adj": 0, "stock": 1000},
        {"type": "finish", "value": "Matte", "adj": 0, "stock": 1000},
        {"type": "finish", "value": "Frosted", "adj": 5, "stock": 500},
        {"type": "feature", "value": "Standard", "adj": 0, "stock": 1000},
        {"type": "feature", "value": "With Scratch Panel", "adj": 3, "stock": 500},
        {"type": "feature", "value": "With Magnetic Stripe", "adj": 8, "stock": 300},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["loyalty_card"])

# sub_id=17 Menus & Rate Cards
add_product(17, "Restaurant Menu Card", "Custom printed menu card on water-resistant coated paper. Available in multiple folds.", 45,
    variants=[
        {"type": "paper", "value": "250 GSM Matte Coated", "adj": 0, "stock": 500},
        {"type": "paper", "value": "300 GSM Glossy Coated", "adj": 8, "stock": 400},
        {"type": "paper", "value": "Waterproof Synthetic", "adj": 25, "stock": 200},
        {"type": "fold", "value": "Single Sheet", "adj": 0, "stock": 500},
        {"type": "fold", "value": "Bi-fold", "adj": 10, "stock": 400},
        {"type": "fold", "value": "Tri-fold", "adj": 15, "stock": 300},
        {"type": "size", "value": "A4", "adj": 0, "stock": 500},
        {"type": "size", "value": "A3", "adj": 15, "stock": 300},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["menu_card"])

# sub_id=18 Presentation Folders
add_product(18, "Corporate Presentation Folder", "Sturdy presentation folder with business card slot and custom full-color print. 350 GSM board.", 75,
    variants=[
        {"type": "paper", "value": "350 GSM Art Board", "adj": 0, "stock": 300},
        {"type": "paper", "value": "400 GSM Rigid Board", "adj": 20, "stock": 200},
        {"type": "finish", "value": "Glossy Lamination", "adj": 0, "stock": 300},
        {"type": "finish", "value": "Matte Lamination", "adj": 0, "stock": 300},
        {"type": "finish", "value": "Soft Touch + Spot UV", "adj": 15, "stock": 200},
        {"type": "pockets", "value": "Single Pocket", "adj": 0, "stock": 300},
        {"type": "pockets", "value": "Double Pocket", "adj": 10, "stock": 200},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["folder"])

# sub_id=19 Posters
add_product(19, "Large Format Poster Print", "High-resolution poster printing on premium paper. Vivid colors with optional lamination.", 35,
    variants=[
        {"type": "size", "value": "A3 (297x420mm)", "adj": 0, "stock": 500},
        {"type": "size", "value": "A2 (420x594mm)", "adj": 20, "stock": 400},
        {"type": "size", "value": "A1 (594x841mm)", "adj": 50, "stock": 300},
        {"type": "size", "value": "A0 (841x1189mm)", "adj": 100, "stock": 200},
        {"type": "paper", "value": "170 GSM Matte Art", "adj": 0, "stock": 500},
        {"type": "paper", "value": "250 GSM Glossy Art", "adj": 10, "stock": 400},
        {"type": "finish", "value": "No Lamination", "adj": 0, "stock": 500},
        {"type": "finish", "value": "Gloss Lamination", "adj": 10, "stock": 400},
        {"type": "finish", "value": "Matte Lamination", "adj": 10, "stock": 400},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["poster"])


# ══════════════════════════════════════════════════════════════════════
#  CATEGORY 5: SIGNS & DISPLAYS (multi_qty — size/material)
# ══════════════════════════════════════════════════════════════════════
print("\n── Signs & Displays ──")

# sub_id=20 Banners
add_product(20, "Vinyl Roll-Up Banner", "Premium 440 GSM vinyl banner with full-color eco-solvent print. UV and water resistant.", 450,
    variants=[
        {"type": "size", "value": "2x5 ft", "adj": 0, "stock": 200},
        {"type": "size", "value": "3x6 ft", "adj": 150, "stock": 150},
        {"type": "size", "value": "4x8 ft", "adj": 350, "stock": 100},
        {"type": "material", "value": "Vinyl (440 GSM)", "adj": 0, "stock": 200},
        {"type": "material", "value": "Flex (280 GSM)", "adj": -50, "stock": 200},
        {"type": "material", "value": "Star Flex (340 GSM)", "adj": -20, "stock": 150},
    ],
    discounts=SMALL_BULK, image_url=IMG["banner"])

# sub_id=21 Display Standees
add_product(21, "Retractable Roll-Up Standee", "Premium retractable banner stand with aluminum base. Includes carry bag and full-color print.", 1200,
    variants=[
        {"type": "size", "value": "2x5 ft", "adj": 0, "stock": 100},
        {"type": "size", "value": "2.5x6 ft", "adj": 200, "stock": 80},
        {"type": "size", "value": "3x6 ft", "adj": 350, "stock": 60},
        {"type": "material", "value": "PVC Print", "adj": 0, "stock": 100},
        {"type": "material", "value": "Fabric Print", "adj": 200, "stock": 60},
    ],
    discounts=SMALL_BULK, image_url=IMG["standee"])

# sub_id=22 Signages
add_product(22, "Acrylic LED Signage Board", "Custom laser-cut acrylic signage with LED backlight. Wall-mount ready with power adapter.", 2500,
    variants=[
        {"type": "size", "value": "1x1 ft", "adj": 0, "stock": 50},
        {"type": "size", "value": "2x1 ft", "adj": 800, "stock": 40},
        {"type": "size", "value": "3x1 ft", "adj": 1500, "stock": 30},
        {"type": "size", "value": "4x2 ft", "adj": 3000, "stock": 20},
        {"type": "material", "value": "Clear Acrylic", "adj": 0, "stock": 50},
        {"type": "material", "value": "Frosted Acrylic", "adj": 200, "stock": 40},
        {"type": "led", "value": "White LED", "adj": 0, "stock": 50},
        {"type": "led", "value": "Warm White LED", "adj": 100, "stock": 40},
        {"type": "led", "value": "RGB LED", "adj": 400, "stock": 30},
    ],
    discounts=[{"min": 5, "pct": 5}, {"min": 10, "pct": 10}, {"min": 25, "pct": 15}],
    image_url=IMG["signage"])

# sub_id=23 Table Top Signs
add_product(23, "Acrylic Table Top Stand", "L-shaped acrylic table stand with custom print insert. Perfect for restaurants and reception desks.", 180,
    variants=[
        {"type": "size", "value": "A6 (105x148mm)", "adj": 0, "stock": 300},
        {"type": "size", "value": "A5 (148x210mm)", "adj": 30, "stock": 250},
        {"type": "size", "value": "A4 (210x297mm)", "adj": 60, "stock": 200},
        {"type": "style", "value": "L-Shape", "adj": 0, "stock": 300},
        {"type": "style", "value": "T-Shape", "adj": 20, "stock": 200},
        {"type": "style", "value": "Tent Style", "adj": 10, "stock": 250},
    ],
    discounts=SMALL_BULK, image_url=IMG["table_sign"])

# sub_id=24 Stickers & Decals
add_product(24, "Custom Die-Cut Vinyl Sticker", "Weatherproof die-cut vinyl sticker with full-color print. Indoor/outdoor use.", 8,
    variants=[
        {"type": "size", "value": "2x2 inch", "adj": 0, "stock": 2000},
        {"type": "size", "value": "3x3 inch", "adj": 3, "stock": 1500},
        {"type": "size", "value": "4x4 inch", "adj": 6, "stock": 1000},
        {"type": "size", "value": "6x6 inch", "adj": 12, "stock": 500},
        {"type": "material", "value": "Glossy Vinyl", "adj": 0, "stock": 2000},
        {"type": "material", "value": "Matte Vinyl", "adj": 0, "stock": 1500},
        {"type": "material", "value": "Transparent Vinyl", "adj": 3, "stock": 1000},
        {"type": "material", "value": "Holographic", "adj": 8, "stock": 500},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["sticker"])

# sub_id=25 Video Display Standees
add_product(25, "Digital Video Standee (10\" Screen)", "Floor-standing digital standee with 10-inch LCD screen. USB media playback with loop.", 8500,
    variants=[
        {"type": "screen", "value": "10 inch LCD", "adj": 0, "stock": 20},
        {"type": "screen", "value": "15 inch LCD", "adj": 3000, "stock": 15},
        {"type": "screen", "value": "21 inch LCD", "adj": 7000, "stock": 10},
        {"type": "frame", "value": "Black Frame", "adj": 0, "stock": 20},
        {"type": "frame", "value": "Silver Frame", "adj": 200, "stock": 15},
        {"type": "frame", "value": "Custom Branded Wrap", "adj": 500, "stock": 10},
    ],
    discounts=[{"min": 3, "pct": 5}, {"min": 5, "pct": 10}, {"min": 10, "pct": 15}],
    image_url=IMG["video_standee"])


# ══════════════════════════════════════════════════════════════════════
#  CATEGORY 6: PENS & NOTEBOOKS (multi_qty)
# ══════════════════════════════════════════════════════════════════════
print("\n── Pens & Notebooks ──")

# sub_id=26 Calendar
add_product(26, "Custom Desk Calendar", "12-month desk calendar with custom artwork. Wire-O binding on premium paper.", 120,
    variants=[
        {"type": "size", "value": "A5 Tent", "adj": 0, "stock": 300},
        {"type": "size", "value": "A4 Wall", "adj": 30, "stock": 250},
        {"type": "paper", "value": "170 GSM Matte", "adj": 0, "stock": 300},
        {"type": "paper", "value": "250 GSM Glossy", "adj": 20, "stock": 250},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["calendar"])

# sub_id=27 Executive Diaries
add_product(27, "Premium Executive Diary", "Italian PU leather bound diary with ribbon bookmark, pen loop, and customizable cover.", 450,
    variants=[
        {"type": "size", "value": "A5", "adj": 0, "stock": 200},
        {"type": "size", "value": "B5", "adj": 50, "stock": 150},
        {"type": "size", "value": "A4", "adj": 100, "stock": 100},
        {"type": "color", "value": "Black", "adj": 0, "stock": 200},
        {"type": "color", "value": "Brown", "adj": 0, "stock": 150},
        {"type": "color", "value": "Navy", "adj": 0, "stock": 100},
        {"type": "color", "value": "Burgundy", "adj": 20, "stock": 80},
        {"type": "pages", "value": "192 Pages", "adj": 0, "stock": 200},
        {"type": "pages", "value": "256 Pages", "adj": 40, "stock": 150},
    ],
    discounts=SMALL_BULK, image_url=IMG["diary"])

# sub_id=28 Metal Pens
add_product(28, "Engraved Metal Ballpoint Pen", "Premium metal barrel pen with laser engraving. Smooth writing with German ink refill.", 180,
    variants=[
        {"type": "color", "value": "Silver", "adj": 0, "stock": 300},
        {"type": "color", "value": "Gold", "adj": 30, "stock": 200},
        {"type": "color", "value": "Matte Black", "adj": 20, "stock": 250},
        {"type": "color", "value": "Rose Gold", "adj": 40, "stock": 150},
        {"type": "engraving", "value": "Single Side", "adj": 0, "stock": 300},
        {"type": "engraving", "value": "Double Side", "adj": 30, "stock": 200},
    ],
    discounts=BULK_DISCOUNTS, image_url=IMG["metal_pen"])

# sub_id=29 Notebooks — already has product

# sub_id=30 Pen Gift Set
add_product(30, "Executive Pen & Diary Gift Set", "Matching metal pen and leather diary in a premium gift box. Custom branding on all items.", 850,
    variants=[
        {"type": "color", "value": "Black Set", "adj": 0, "stock": 100},
        {"type": "color", "value": "Brown Set", "adj": 0, "stock": 80},
        {"type": "color", "value": "Navy Set", "adj": 0, "stock": 60},
        {"type": "box", "value": "Standard Box", "adj": 0, "stock": 100},
        {"type": "box", "value": "Magnetic Premium Box", "adj": 100, "stock": 60},
    ],
    discounts=SMALL_BULK, image_url=IMG["pen_set"])

# sub_id=31 Premium Pens
add_product(31, "Premium Stainless Steel Pen", "Heavyweight stainless steel pen with precision tip. Custom laser engraving with lifetime warranty.", 550,
    variants=[
        {"type": "color", "value": "Brushed Steel", "adj": 0, "stock": 150},
        {"type": "color", "value": "Gunmetal", "adj": 30, "stock": 100},
        {"type": "color", "value": "Chrome", "adj": 50, "stock": 80},
        {"type": "tip", "value": "Fine (0.5mm)", "adj": 0, "stock": 150},
        {"type": "tip", "value": "Medium (0.7mm)", "adj": 0, "stock": 150},
    ],
    discounts=SMALL_BULK, image_url=IMG["premium_pen"])

# sub_id=32 Ball Point Pen
add_product(32, "Branded Ballpoint Pen", "Reliable click-action ballpoint pen with custom pad print. Bulk-friendly pricing.", 15,
    variants=[
        {"type": "color", "value": "Blue Body", "adj": 0, "stock": 2000},
        {"type": "color", "value": "Black Body", "adj": 0, "stock": 2000},
        {"type": "color", "value": "White Body", "adj": 0, "stock": 1500},
        {"type": "color", "value": "Red Body", "adj": 0, "stock": 1000},
        {"type": "ink", "value": "Blue Ink", "adj": 0, "stock": 2000},
        {"type": "ink", "value": "Black Ink", "adj": 0, "stock": 2000},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["ballpoint"])

# sub_id=33 Roller Ball Pen
add_product(33, "Roller Ball Pen with Grip", "Smooth-flow roller ball pen with rubberized grip. Custom logo printing on barrel.", 45,
    variants=[
        {"type": "color", "value": "Black", "adj": 0, "stock": 500},
        {"type": "color", "value": "Silver", "adj": 10, "stock": 400},
        {"type": "color", "value": "Blue", "adj": 0, "stock": 400},
        {"type": "ink", "value": "Black Ink", "adj": 0, "stock": 500},
        {"type": "ink", "value": "Blue Ink", "adj": 0, "stock": 500},
    ],
    discounts=BULK_DISCOUNTS, image_url=IMG["roller_pen"])

# sub_id=34 Fountain Pen
add_product(34, "Classic Fountain Pen", "Elegant brass fountain pen with iridium nib. Comes with converter and cartridge. Custom engraving available.", 750,
    variants=[
        {"type": "nib", "value": "Fine Nib", "adj": 0, "stock": 80},
        {"type": "nib", "value": "Medium Nib", "adj": 0, "stock": 80},
        {"type": "nib", "value": "Broad Nib", "adj": 20, "stock": 50},
        {"type": "color", "value": "Classic Black", "adj": 0, "stock": 80},
        {"type": "color", "value": "Deep Blue", "adj": 0, "stock": 60},
        {"type": "color", "value": "Burgundy", "adj": 30, "stock": 40},
    ],
    discounts=[{"min": 5, "pct": 5}, {"min": 10, "pct": 10}, {"min": 25, "pct": 15}],
    image_url=IMG["fountain_pen"])

# sub_id=35 Promotional Pens
add_product(35, "Budget Promotional Pen", "Lightweight promotional pen with single-color logo print. Best for events and giveaways.", 8,
    variants=[
        {"type": "color", "value": "Blue", "adj": 0, "stock": 5000},
        {"type": "color", "value": "Black", "adj": 0, "stock": 5000},
        {"type": "color", "value": "Red", "adj": 0, "stock": 3000},
        {"type": "color", "value": "Green", "adj": 0, "stock": 2000},
        {"type": "color", "value": "White", "adj": 0, "stock": 3000},
    ],
    discounts=[
        {"min": 100, "pct": 5},
        {"min": 250, "pct": 10},
        {"min": 500, "pct": 15},
        {"min": 1000, "pct": 20},
        {"min": 5000, "pct": 30},
    ],
    image_url=IMG["promo_pen"])


# ══════════════════════════════════════════════════════════════════════
#  CATEGORY 7: PACKAGING (multi_qty — size/material)
# ══════════════════════════════════════════════════════════════════════
print("\n── Packaging ──")

# sub_id=36 Bookmarks
add_product(36, "Custom Printed Bookmark", "Premium card stock bookmark with full-color print. Optional lamination and tassel.", 8,
    variants=[
        {"type": "paper", "value": "300 GSM Art Card", "adj": 0, "stock": 2000},
        {"type": "paper", "value": "350 GSM Textured", "adj": 3, "stock": 1000},
        {"type": "finish", "value": "Glossy Lamination", "adj": 0, "stock": 2000},
        {"type": "finish", "value": "Matte Lamination", "adj": 0, "stock": 1500},
        {"type": "finish", "value": "With Tassel", "adj": 5, "stock": 1000},
        {"type": "size", "value": "2x6 inch", "adj": 0, "stock": 2000},
        {"type": "size", "value": "2x7 inch", "adj": 2, "stock": 1000},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["bookmark"])

# sub_id=37 Courier Bags
add_product(37, "Branded Courier Bag", "Tamper-proof courier bag with custom print. Self-sealing adhesive strip and POD pocket.", 12,
    variants=[
        {"type": "size", "value": "6x8 inch", "adj": 0, "stock": 2000},
        {"type": "size", "value": "8x10 inch", "adj": 3, "stock": 1500},
        {"type": "size", "value": "10x12 inch", "adj": 5, "stock": 1000},
        {"type": "size", "value": "12x16 inch", "adj": 8, "stock": 800},
        {"type": "material", "value": "Standard (60 micron)", "adj": 0, "stock": 2000},
        {"type": "material", "value": "Premium (80 micron)", "adj": 3, "stock": 1000},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["courier_bag"])

# sub_id=38 Gift Wrapping Paper
add_product(38, "Custom Gift Wrapping Paper", "Full-color printed gift wrapping paper on 80 GSM art paper. Available in sheets or rolls.", 15,
    variants=[
        {"type": "format", "value": "Sheet (50x70cm)", "adj": 0, "stock": 2000},
        {"type": "format", "value": "Roll (50cm x 5m)", "adj": 40, "stock": 500},
        {"type": "paper", "value": "80 GSM Art Paper", "adj": 0, "stock": 2000},
        {"type": "paper", "value": "100 GSM Kraft", "adj": 5, "stock": 1000},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["wrapping"])

# sub_id=39 HangTags
add_product(39, "Custom Printed Hang Tag", "Premium hang tag with custom shape die-cut. Full-color print with optional string/ribbon.", 5,
    variants=[
        {"type": "paper", "value": "300 GSM Art Card", "adj": 0, "stock": 3000},
        {"type": "paper", "value": "350 GSM Kraft", "adj": 2, "stock": 2000},
        {"type": "paper", "value": "400 GSM Textured", "adj": 4, "stock": 1000},
        {"type": "size", "value": "Small (5x3cm)", "adj": 0, "stock": 3000},
        {"type": "size", "value": "Medium (7x4cm)", "adj": 2, "stock": 2000},
        {"type": "size", "value": "Large (9x5cm)", "adj": 4, "stock": 1000},
        {"type": "attachment", "value": "No String", "adj": 0, "stock": 3000},
        {"type": "attachment", "value": "Cotton String", "adj": 2, "stock": 2000},
        {"type": "attachment", "value": "Satin Ribbon", "adj": 5, "stock": 1000},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["hangtag"])

# sub_id=40 Kraft Paper Bags
add_product(40, "Branded Kraft Paper Bag", "Recycled kraft paper bag with twisted rope handle. Custom logo print in up to 3 colors.", 18,
    variants=[
        {"type": "size", "value": "Small (20x15x8cm)", "adj": 0, "stock": 1000},
        {"type": "size", "value": "Medium (25x20x10cm)", "adj": 5, "stock": 800},
        {"type": "size", "value": "Large (32x25x12cm)", "adj": 10, "stock": 600},
        {"type": "size", "value": "XL (40x30x15cm)", "adj": 18, "stock": 400},
        {"type": "color", "value": "Natural Brown", "adj": 0, "stock": 1000},
        {"type": "color", "value": "White", "adj": 3, "stock": 800},
        {"type": "color", "value": "Black", "adj": 5, "stock": 500},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["kraft_bag"])

# sub_id=41 Packaging Sleeves
add_product(41, "Custom Packaging Sleeve", "Printed card stock sleeve for product packaging. Full-wrap printing with fold and tuck design.", 12,
    variants=[
        {"type": "paper", "value": "300 GSM Art Card", "adj": 0, "stock": 1000},
        {"type": "paper", "value": "350 GSM E-Flute", "adj": 5, "stock": 500},
        {"type": "size", "value": "Small (fits 10x5cm box)", "adj": 0, "stock": 1000},
        {"type": "size", "value": "Medium (fits 15x8cm box)", "adj": 4, "stock": 800},
        {"type": "size", "value": "Large (fits 20x12cm box)", "adj": 8, "stock": 500},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["sleeve"])

# sub_id=42 Packaging Tube
add_product(42, "Branded Cardboard Tube", "Rigid cardboard tube with custom-printed label wrap and end caps. Great for posters and certificates.", 35,
    variants=[
        {"type": "diameter", "value": "2 inch", "adj": 0, "stock": 500},
        {"type": "diameter", "value": "3 inch", "adj": 10, "stock": 400},
        {"type": "length", "value": "12 inch", "adj": 0, "stock": 500},
        {"type": "length", "value": "18 inch", "adj": 10, "stock": 400},
        {"type": "length", "value": "24 inch", "adj": 20, "stock": 300},
        {"type": "cap", "value": "Plastic End Cap", "adj": 0, "stock": 500},
        {"type": "cap", "value": "Metal End Cap", "adj": 15, "stock": 300},
    ],
    discounts=SMALL_BULK, image_url=IMG["tube"])

# sub_id=43 Pillow Packs
add_product(43, "Custom Pillow Pack Box", "Pillow-shaped favor box with full-color print. Perfect for sweets, small gifts, and samples.", 10,
    variants=[
        {"type": "size", "value": "Small (10x7x3cm)", "adj": 0, "stock": 1500},
        {"type": "size", "value": "Medium (14x10x4cm)", "adj": 3, "stock": 1000},
        {"type": "size", "value": "Large (18x13x5cm)", "adj": 6, "stock": 500},
        {"type": "paper", "value": "300 GSM Art Card", "adj": 0, "stock": 1500},
        {"type": "paper", "value": "Kraft Card", "adj": 2, "stock": 1000},
        {"type": "finish", "value": "Glossy", "adj": 0, "stock": 1500},
        {"type": "finish", "value": "Matte", "adj": 0, "stock": 1000},
        {"type": "finish", "value": "Gold Foil Accent", "adj": 5, "stock": 500},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["pillow_pack"])

# sub_id=44 Pizza Boxes
add_product(44, "Branded Pizza Box", "Corrugated pizza box with custom full-color print. Food-safe coating inside.", 22,
    variants=[
        {"type": "size", "value": "7 inch (Personal)", "adj": 0, "stock": 1000},
        {"type": "size", "value": "10 inch (Medium)", "adj": 5, "stock": 800},
        {"type": "size", "value": "12 inch (Large)", "adj": 8, "stock": 600},
        {"type": "size", "value": "14 inch (Family)", "adj": 12, "stock": 400},
        {"type": "material", "value": "E-Flute Corrugated", "adj": 0, "stock": 1000},
        {"type": "material", "value": "B-Flute (Extra Sturdy)", "adj": 5, "stock": 500},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["pizza_box"])

# sub_id=45 Stand Up Pouches
add_product(45, "Custom Printed Stand-Up Pouch", "Laminated stand-up pouch with zip lock closure. Food-grade material with custom print.", 8,
    variants=[
        {"type": "size", "value": "100g (10x15cm)", "adj": 0, "stock": 2000},
        {"type": "size", "value": "250g (14x20cm)", "adj": 3, "stock": 1500},
        {"type": "size", "value": "500g (18x26cm)", "adj": 6, "stock": 1000},
        {"type": "size", "value": "1kg (22x32cm)", "adj": 10, "stock": 500},
        {"type": "material", "value": "Metallized", "adj": 0, "stock": 2000},
        {"type": "material", "value": "Clear Window", "adj": 2, "stock": 1500},
        {"type": "material", "value": "Kraft Paper", "adj": 3, "stock": 1000},
        {"type": "closure", "value": "Zip Lock", "adj": 0, "stock": 2000},
        {"type": "closure", "value": "Zip Lock + Tear Notch", "adj": 2, "stock": 1000},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["pouch"])


# ══════════════════════════════════════════════════════════════════════
#  CATEGORY 8: BUSINESS ESSENTIALS (single_select — paper/finish)
# ══════════════════════════════════════════════════════════════════════
print("\n── Business Essentials ──")

# sub_id=46 Business Cards — already has product

# sub_id=47 Envelopes
add_product(47, "Custom Printed Envelope", "Premium business envelope with full-color custom print. Self-seal adhesive strip.", 8,
    variants=[
        {"type": "size", "value": "DL (110x220mm)", "adj": 0, "stock": 2000},
        {"type": "size", "value": "C5 (162x229mm)", "adj": 3, "stock": 1500},
        {"type": "size", "value": "C4 (229x324mm)", "adj": 6, "stock": 1000},
        {"type": "paper", "value": "100 GSM White Wove", "adj": 0, "stock": 2000},
        {"type": "paper", "value": "120 GSM Laid Texture", "adj": 3, "stock": 1000},
        {"type": "paper", "value": "120 GSM Kraft", "adj": 2, "stock": 1000},
        {"type": "window", "value": "No Window", "adj": 0, "stock": 2000},
        {"type": "window", "value": "With Window", "adj": 2, "stock": 1000},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["envelope"])

# sub_id=48 Letter Heads
add_product(48, "Corporate Letterhead", "Premium letterhead on high-quality bond paper. Full-color print with optional watermark.", 6,
    variants=[
        {"type": "paper", "value": "100 GSM Bond Paper", "adj": 0, "stock": 2000},
        {"type": "paper", "value": "120 GSM Premium Bond", "adj": 2, "stock": 1500},
        {"type": "paper", "value": "120 GSM Laid Texture", "adj": 3, "stock": 1000},
        {"type": "feature", "value": "Standard Print", "adj": 0, "stock": 2000},
        {"type": "feature", "value": "With Watermark", "adj": 3, "stock": 1000},
    ],
    discounts=PRINT_DISCOUNTS, image_url=IMG["letterhead"])

# sub_id=49 Rubber Stamps
add_product(49, "Custom Self-Inking Rubber Stamp", "High-quality self-inking stamp with custom design. Up to 10,000 impressions per ink pad.", 350,
    variants=[
        {"type": "size", "value": "Small (38x14mm)", "adj": 0, "stock": 300},
        {"type": "size", "value": "Medium (58x22mm)", "adj": 50, "stock": 250},
        {"type": "size", "value": "Large (76x38mm)", "adj": 100, "stock": 200},
        {"type": "size", "value": "Round (40mm dia)", "adj": 80, "stock": 150},
        {"type": "ink_color", "value": "Blue", "adj": 0, "stock": 300},
        {"type": "ink_color", "value": "Black", "adj": 0, "stock": 300},
        {"type": "ink_color", "value": "Red", "adj": 0, "stock": 200},
        {"type": "ink_color", "value": "Green", "adj": 5, "stock": 100},
    ],
    discounts=SMALL_BULK, image_url=IMG["stamp"])


# ══════════════════════════════════════════════════════════════════════
#  CATEGORY 9: LABELS & STICKERS
# ══════════════════════════════════════════════════════════════════════
print("\n── Labels & Stickers ──")

# sub_id=50 Stickers & Decals
add_product(50, "Custom Label Sticker Roll", "Self-adhesive label sticker on roll. Thermal or inkjet printing with custom die-cut shapes.", 3,
    variants=[
        {"type": "size", "value": "1x1 inch", "adj": 0, "stock": 5000},
        {"type": "size", "value": "2x1 inch", "adj": 1, "stock": 4000},
        {"type": "size", "value": "2x2 inch", "adj": 2, "stock": 3000},
        {"type": "size", "value": "3x2 inch", "adj": 3, "stock": 2000},
        {"type": "material", "value": "White Paper", "adj": 0, "stock": 5000},
        {"type": "material", "value": "Glossy Paper", "adj": 1, "stock": 3000},
        {"type": "material", "value": "Clear BOPP", "adj": 3, "stock": 2000},
        {"type": "material", "value": "Silver Foil", "adj": 5, "stock": 1000},
        {"type": "shape", "value": "Rectangle", "adj": 0, "stock": 5000},
        {"type": "shape", "value": "Round", "adj": 0, "stock": 3000},
        {"type": "shape", "value": "Oval", "adj": 1, "stock": 2000},
        {"type": "shape", "value": "Custom Die-Cut", "adj": 3, "stock": 1000},
    ],
    discounts=[
        {"min": 100, "pct": 5},
        {"min": 500, "pct": 10},
        {"min": 1000, "pct": 15},
        {"min": 5000, "pct": 25},
        {"min": 10000, "pct": 30},
    ],
    image_url=IMG["label_sticker"])


# ══════════════════════════════════════════════════════════════════════
#  CATEGORY 10: OUTDOOR SOLUTIONS
# ══════════════════════════════════════════════════════════════════════
print("\n── Outdoor Solutions ──")

# sub_id=51 Kiosks
add_product(51, "Portable Promotional Kiosk", "Lightweight aluminum frame kiosk with custom printed fabric panels. Easy assembly in under 10 minutes.", 15000,
    variants=[
        {"type": "size", "value": "3x3 ft Counter", "adj": 0, "stock": 15},
        {"type": "size", "value": "4x6 ft Booth", "adj": 5000, "stock": 10},
        {"type": "size", "value": "6x6 ft Full Booth", "adj": 12000, "stock": 8},
        {"type": "material", "value": "Polyester Fabric", "adj": 0, "stock": 15},
        {"type": "material", "value": "PVC Panels", "adj": 2000, "stock": 10},
        {"type": "accessory", "value": "Standard (frame + panels)", "adj": 0, "stock": 15},
        {"type": "accessory", "value": "With LED Lighting", "adj": 3000, "stock": 10},
        {"type": "accessory", "value": "With Counter + Shelf", "adj": 4000, "stock": 8},
    ],
    discounts=[{"min": 2, "pct": 5}, {"min": 5, "pct": 10}, {"min": 10, "pct": 15}],
    image_url=IMG["kiosk"])


# ══════════════════════════════════════════════════════════════════════
#  CATEGORY 11: BAGS (multi_qty — size/color)
# ══════════════════════════════════════════════════════════════════════
print("\n── Bags ──")

# sub_id=52 Laptop Bags
add_product(52, "Branded Laptop Backpack", "Water-resistant laptop backpack with padded compartment. Custom logo embroidery and multiple pockets.", 1800,
    variants=[
        {"type": "size", "value": "14 inch Laptop", "adj": 0, "stock": 100},
        {"type": "size", "value": "15.6 inch Laptop", "adj": 100, "stock": 80},
        {"type": "size", "value": "17 inch Laptop", "adj": 200, "stock": 50},
        {"type": "color", "value": "Black", "adj": 0, "stock": 100},
        {"type": "color", "value": "Grey", "adj": 0, "stock": 80},
        {"type": "color", "value": "Navy", "adj": 0, "stock": 60},
    ],
    discounts=SMALL_BULK, image_url=IMG["laptop_bag"])

# sub_id=53 Design Kit
add_product(53, "Brand Design Kit Bag", "Custom canvas messenger bag bundled with design essentials. Perfect for client onboarding and team kits.", 2200,
    variants=[
        {"type": "material", "value": "Canvas", "adj": 0, "stock": 60},
        {"type": "material", "value": "Faux Leather", "adj": 300, "stock": 40},
        {"type": "color", "value": "Natural Canvas", "adj": 0, "stock": 60},
        {"type": "color", "value": "Black", "adj": 50, "stock": 50},
        {"type": "color", "value": "Brown", "adj": 50, "stock": 40},
    ],
    discounts=SMALL_BULK, image_url=IMG["design_kit"])


# ══════════════════════════════════════════════════════════════════════
#  CATEGORY 12: BUSINESS GIFTS & GIVEAWAYS
# ══════════════════════════════════════════════════════════════════════
print("\n── Business Gifts & Giveaways ──")

# sub_id=54 Gadgets
add_product(54, "Wireless Charging Pad with Logo", "Slim wireless charging pad with custom full-color UV print. Compatible with Qi-enabled devices.", 650,
    variants=[
        {"type": "color", "value": "Black", "adj": 0, "stock": 200},
        {"type": "color", "value": "White", "adj": 0, "stock": 150},
        {"type": "color", "value": "Bamboo Finish", "adj": 100, "stock": 100},
        {"type": "power", "value": "5W Standard", "adj": 0, "stock": 200},
        {"type": "power", "value": "10W Fast Charge", "adj": 80, "stock": 150},
        {"type": "power", "value": "15W Ultra Fast", "adj": 150, "stock": 100},
    ],
    discounts=BULK_DISCOUNTS, image_url=IMG["gadget"])

# sub_id=55 Giveaways Under ₹99
add_product(55, "Custom Keychain with Logo", "Acrylic/metal keychain with custom logo print or engraving. Lightweight and durable.", 35,
    variants=[
        {"type": "material", "value": "Acrylic (Clear)", "adj": 0, "stock": 1000},
        {"type": "material", "value": "Metal (Silver)", "adj": 15, "stock": 500},
        {"type": "material", "value": "Metal (Gold)", "adj": 20, "stock": 400},
        {"type": "material", "value": "Wooden", "adj": 10, "stock": 500},
        {"type": "material", "value": "PVC Rubber", "adj": 5, "stock": 800},
        {"type": "shape", "value": "Round", "adj": 0, "stock": 1000},
        {"type": "shape", "value": "Rectangle", "adj": 0, "stock": 800},
        {"type": "shape", "value": "Custom Shape", "adj": 10, "stock": 500},
    ],
    discounts=[
        {"min": 50, "pct": 5},
        {"min": 100, "pct": 10},
        {"min": 250, "pct": 15},
        {"min": 500, "pct": 20},
        {"min": 1000, "pct": 25},
    ],
    image_url=IMG["giveaway"])


# ── Commit ───────────────────────────────────────────────────────────
db.commit()
db.close()
print("\n✅ Done! All subcategories now have at least one product with variants, discount slabs, and images.")
