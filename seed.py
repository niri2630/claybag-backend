"""
Run once after migrations to seed categories, subcategories, dummy products, and create the admin user.
Usage: python seed.py
"""
from app.database import SessionLocal
from app.models.category import Category, SubCategory
from app.models.product import Product, ProductImage
from app.models.user import User
from app.core.security import hash_password

SEED_DATA = {
    "Apparel": ["Caps", "Formal Shirts", "Polo T-Shirts", "Sweatshirt", "T-Shirts"],
    "DrinkWare": ["Mugs", "Sipper Bottle"],
    "Identity Essentials": ["Badges", "ID Cards & Card Holders", "Lanyards"],
    "Marketing Essentials": ["Booklets", "Brochures & Flyers", "Photo Frames", "Gift Certificates", "Greeting Cards", "Loyalty Cards", "Menus & Rate Cards", "Presentation Folders", "Posters"],
    "Signs & Displays": ["Banners", "Display Standees", "Signages", "Table Top Signs", "Stickers & Decals", "Video Display Standees"],
    "Pens & Notebooks": ["Calendar", "Executive Diaries", "Metal Pens", "Notebooks", "Pen Gift Set", "Premium Pens", "Ball Point Pen", "Roller Ball Pen", "Fountain Pen", "Promotional Pens"],
    "Packaging": ["Bookmarks", "Courier Bags", "Gift Wrapping Paper", "HangTags", "Kraft Paper Bags", "Packaging Sleeves", "Packaging Tube", "Pillow Packs", "Pizza Boxes", "Stand Up Pouches"],
    "Business Essentials": ["Business Cards", "Envelopes", "Letter Heads", "Rubber Stamps"],
    "Labels & Stickers": ["Stickers & Decals"],
    "Outdoor Solutions": ["Kiosks"],
    "Bags": ["Laptop Bags", "Design Kit"],
    "Business Gifts & Giveaways": ["Gadgets", "Giveaways Under ₹99"],
}

# Dummy products: 4 placeholder products to demonstrate the admin panel
DUMMY_PRODUCTS = [
    {
        "name": "Premium Cotton Crew-Neck T-Shirt",
        "description": "Ultra-soft 180 GSM ring-spun cotton tee with a relaxed architectural fit. Pre-shrunk fabric ensures lasting comfort. Perfect for brand customization with screen printing or embroidery.",
        "base_price": 499,
        "subcategory_name": "T-Shirts",
        "has_variants": True,
        "image_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&h=600&fit=crop",
    },
    {
        "name": "Insulated Stainless Steel Sipper Bottle",
        "description": "Double-wall vacuum insulated 750ml bottle. Keeps beverages hot for 12 hours or cold for 24. Leakproof lid with one-hand operation. Powder-coated finish ideal for laser engraving.",
        "base_price": 899,
        "subcategory_name": "Sipper Bottle",
        "has_variants": False,
        "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&h=600&fit=crop",
    },
    {
        "name": "Executive Leather-Bound Notebook",
        "description": "A5 hardcover notebook with 192 pages of 100 GSM acid-free paper. Features a magnetic closure, ribbon bookmark, and expandable inner pocket. Embossing-ready cover.",
        "base_price": 650,
        "subcategory_name": "Notebooks",
        "has_variants": False,
        "image_url": "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=600&h=600&fit=crop",
    },
    {
        "name": "Matte Laminated Business Cards (100 pcs)",
        "description": "350 GSM art-card stock with spot UV and matte lamination. Full-color CMYK printing on both sides. Rounded or sharp corners available. Minimum order: 1 box of 100.",
        "base_price": 299,
        "subcategory_name": "Business Cards",
        "has_variants": False,
        "image_url": "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=600&h=600&fit=crop",
    },
]


def slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("&", "and").replace("₹", "rs").replace("'", "").replace(",", "")


def main():
    db = SessionLocal()
    try:
        # ── Seed Categories & SubCategories ──────────────────────────
        sub_map = {}  # subcategory name -> SubCategory object
        for cat_name, subs in SEED_DATA.items():
            cat_slug = slugify(cat_name)
            cat = db.query(Category).filter(Category.slug == cat_slug).first()
            if not cat:
                cat = Category(name=cat_name, slug=cat_slug)
                db.add(cat)
                db.flush()
                print(f"  Created category: {cat_name}")

            for sub_name in subs:
                sub_slug = slugify(sub_name)
                # ensure unique slug
                existing = db.query(SubCategory).filter(SubCategory.slug == sub_slug).first()
                if existing:
                    sub_slug = f"{cat_slug}-{sub_slug}"
                sub = db.query(SubCategory).filter(SubCategory.slug == sub_slug).first()
                if not sub:
                    sub = SubCategory(name=sub_name, slug=sub_slug, category_id=cat.id)
                    db.add(sub)
                    db.flush()
                    print(f"    Created subcategory: {sub_name}")
                sub_map[sub_name] = sub

        # ── Admin user ───────────────────────────────────────────────
        if not db.query(User).filter(User.email == "admin@claybag.com").first():
            db.add(User(
                name="Admin",
                email="admin@claybag.com",
                password_hash=hash_password("admin123"),
                is_admin=True,
            ))
            print("Created admin user: admin@claybag.com / admin123")

        # ── Dummy Products ───────────────────────────────────────────
        for p_data in DUMMY_PRODUCTS:
            existing = db.query(Product).filter(Product.name == p_data["name"]).first()
            if existing:
                print(f"  Product already exists: {p_data['name']}")
                continue

            sub = sub_map.get(p_data["subcategory_name"])
            if not sub:
                print(f"  WARNING: SubCategory '{p_data['subcategory_name']}' not found, skipping product '{p_data['name']}'")
                continue

            product = Product(
                name=p_data["name"],
                description=p_data["description"],
                base_price=p_data["base_price"],
                subcategory_id=sub.id,
                has_variants=p_data["has_variants"],
                is_active=True,
            )
            db.add(product)
            db.flush()

            # Add a product image
            img = ProductImage(
                product_id=product.id,
                image_url=p_data["image_url"],
                is_primary=True,
                sort_order=0,
            )
            db.add(img)
            print(f"  Created product: {p_data['name']} (sub: {p_data['subcategory_name']})")

        db.commit()
        print("\nSeeding complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
