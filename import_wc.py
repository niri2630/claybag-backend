"""
Import WooCommerce CSV export into ClayBag Neon database.
- Keeps existing categories/subcategories, adds new ones as needed
- Deletes all existing products, variants, images, discount slabs
- Imports all parent products (simple + variable) with images, variants, discount slabs
"""

import csv
import re
import sys
from sqlalchemy import create_engine, text

DB_URL = "postgresql://neondb_owner:npg_ydrmonOZU8k1@ep-purple-mountain-a16t05a3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
CSV_PATH = "/Users/itishree/Downloads/wc-product-export-4-4-2026-1775297230843.csv"

engine = create_engine(DB_URL)


def slugify(name):
    s = name.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')


def g(row, key):
    """Safe getter - always returns string, never None."""
    val = row.get(key)
    return val if val is not None else ""


def parse_csv():
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_category_map(conn):
    """Build mapping: category_name -> id"""
    rows = conn.execute(text("SELECT id, name FROM categories")).fetchall()
    return {r[1]: r[0] for r in rows}


def get_subcategory_map(conn):
    """Build mapping: (category_id, subcategory_name) -> id"""
    rows = conn.execute(text("SELECT id, name, category_id FROM subcategories")).fetchall()
    return {(r[2], r[1]): r[0] for r in rows}


# Icon mapping for new categories
NEW_CAT_ICONS = {
    "Calendar": "calendar_month",
    "Design Kit": "palette",
    "Event Merchandise": "celebration",
    "New Arrival": "new_releases",
    "Paper Bags": "shopping_bag",
    "Gifts Under Rs 99": "savings",
}


def ensure_categories(conn, all_rows):
    """Create any missing categories and subcategories from CSV data."""
    cat_map = get_category_map(conn)
    sub_map = get_subcategory_map(conn)

    # Collect all category > subcategory pairs
    cat_sub_pairs = set()
    top_level_cats = set()

    for r in all_rows:
        cats_str = r.get("Categories", "")
        if not cats_str:
            continue
        for cat_path in cats_str.split(","):
            cat_path = cat_path.strip()
            if " > " in cat_path:
                parent, child = cat_path.split(" > ", 1)
                parent = parent.strip()
                child = child.strip()
                cat_sub_pairs.add((parent, child))
                top_level_cats.add(parent)
            else:
                top_level_cats.add(cat_path)

    # Category name normalization for matching
    cat_name_map = {}
    for name in cat_map:
        cat_name_map[name.lower()] = name

    # Create missing top-level categories
    for cat_name in sorted(top_level_cats):
        norm = cat_name.lower().strip()
        # Try to match existing
        if norm in cat_name_map:
            continue
        # Check exact match
        if cat_name in cat_map:
            continue
        # Special mappings
        if norm == "outdoor solution":
            cat_name_map[norm] = "Outdoor Solutions"
            continue
        if norm == "shirts":
            cat_name_map[norm] = "Apparel"
            continue

        # Create new category
        icon = NEW_CAT_ICONS.get(cat_name, "category")
        slug = slugify(cat_name)
        result = conn.execute(
            text("INSERT INTO categories (name, slug, icon, is_active) VALUES (:n, :s, :i, true) RETURNING id"),
            {"n": cat_name, "s": slug, "i": icon}
        )
        new_id = result.fetchone()[0]
        cat_map[cat_name] = new_id
        cat_name_map[norm] = cat_name
        print(f"  + Created category: {cat_name} (id={new_id})")

    conn.commit()
    cat_map = get_category_map(conn)

    # Rebuild normalized map
    cat_name_map = {}
    for name in cat_map:
        cat_name_map[name.lower()] = name

    # Create missing subcategories
    sub_map = get_subcategory_map(conn)
    for parent_name, child_name in sorted(cat_sub_pairs):
        # Resolve parent
        norm_parent = parent_name.lower().strip()
        if norm_parent == "outdoor solution":
            norm_parent = "outdoor solutions"
        if norm_parent == "shirts":
            norm_parent = "apparel"

        actual_parent = cat_name_map.get(norm_parent)
        if not actual_parent:
            print(f"  ! Parent not found: {parent_name}")
            continue

        cat_id = cat_map[actual_parent]

        # Check if subcategory exists (case-insensitive)
        existing = False
        for (cid, sname), sid in sub_map.items():
            if cid == cat_id and sname.lower() == child_name.lower().rstrip('.'):
                existing = True
                break

        if existing:
            continue

        # Create subcategory
        slug = slugify(child_name.rstrip('.'))
        clean_name = child_name.rstrip('.')
        result = conn.execute(
            text("INSERT INTO subcategories (name, slug, category_id, is_active) VALUES (:n, :s, :c, true) RETURNING id"),
            {"n": clean_name, "s": slug, "c": cat_id}
        )
        new_id = result.fetchone()[0]
        sub_map[(cat_id, clean_name)] = new_id
        print(f"  + Created subcategory: {clean_name} under {actual_parent} (id={new_id})")

    conn.commit()
    return get_category_map(conn), get_subcategory_map(conn)


def resolve_subcategory(categories_str, cat_map, sub_map):
    """Given a WC categories string, find the best subcategory_id."""
    cat_name_norm = {}
    for name in cat_map:
        cat_name_norm[name.lower()] = name

    if not categories_str:
        return None

    # Prefer most specific (subcategory) match
    for cat_path in categories_str.split(","):
        cat_path = cat_path.strip()
        if " > " in cat_path:
            parent, child = cat_path.split(" > ", 1)
            parent = parent.strip()
            child = child.strip().rstrip('.')

            # Resolve parent
            norm_p = parent.lower()
            if norm_p == "outdoor solution":
                norm_p = "outdoor solutions"
            if norm_p == "shirts":
                norm_p = "apparel"

            actual_parent = cat_name_norm.get(norm_p)
            if not actual_parent:
                continue
            cat_id = cat_map[actual_parent]

            # Find subcategory (case-insensitive)
            for (cid, sname), sid in sub_map.items():
                if cid == cat_id and sname.lower() == child.lower():
                    return sid

    return None


def clear_products(conn):
    """Delete all products, variants, images, discount slabs."""
    conn.execute(text("DELETE FROM discount_slabs"))
    conn.execute(text("DELETE FROM product_images"))
    conn.execute(text("DELETE FROM product_variants"))
    # Also clear order items and reviews referencing products
    conn.execute(text("DELETE FROM reviews"))
    conn.execute(text("DELETE FROM order_items"))
    conn.execute(text("DELETE FROM orders"))
    conn.execute(text("DELETE FROM products"))
    conn.commit()
    print("  Cleared all existing products, variants, images, discount slabs, orders, reviews")


def import_products(conn, all_rows, cat_map, sub_map):
    """Import all products from CSV."""
    # Separate parents and variations
    parents = [r for r in all_rows if r.get("Type") in ("variable", "simple")]
    variations = [r for r in all_rows if r.get("Type") == "variation"]

    # Build SKU -> variations mapping
    var_by_parent = {}
    for v in variations:
        parent_sku = g(v, "Parent").strip()
        if parent_sku:
            if parent_sku not in var_by_parent:
                var_by_parent[parent_sku] = []
            var_by_parent[parent_sku].append(v)

    imported = 0
    skipped = 0

    for row in parents:
        name = g(row, "Name").strip()
        if not name:
            skipped += 1
            continue

        sku = g(row, "SKU").strip()
        prod_type = g(row, "Type").strip()
        price_str = g(row, "Regular price").strip()
        categories_str = g(row, "Categories")
        description = g(row, "Short description").strip()
        images_str = g(row, "Images").strip()

        # Resolve subcategory
        sub_id = resolve_subcategory(categories_str, cat_map, sub_map)
        if not sub_id:
            # Try to find any category match
            skipped += 1
            continue

        # Determine base price
        base_price = 0
        if price_str:
            try:
                base_price = float(price_str)
            except ValueError:
                pass

        # For variable products without a price, get from first variation
        if base_price == 0 and prod_type == "variable" and sku in var_by_parent:
            for v in var_by_parent[sku]:
                vp = g(v, "Regular price").strip()
                if vp:
                    try:
                        base_price = float(vp)
                        break
                    except ValueError:
                        pass

        # Determine variant mode
        has_variants = prod_type == "variable"
        attr_count = 0
        for i in range(1, 4):
            val = row.get(f"Attribute {i} name") or ""
            if val.strip():
                attr_count += 1
        variant_mode = "single_select" if attr_count >= 2 else "multi_qty"

        # Simple products with attributes are also variant products
        if prod_type == "simple" and attr_count > 0:
            has_variants = True

        # Clean description (remove HTML/shortcodes)
        description = re.sub(r'\[.*?\]', '', description)
        description = re.sub(r'<[^>]+>', '', description)
        description = description.strip()
        if len(description) > 2000:
            description = description[:2000]

        # Insert product
        result = conn.execute(
            text("""INSERT INTO products (name, description, subcategory_id, base_price, is_active, has_variants, variant_mode)
                    VALUES (:name, :desc, :sub, :price, true, :hv, :vm) RETURNING id"""),
            {"name": name, "desc": description or None, "sub": sub_id, "price": base_price,
             "hv": has_variants, "vm": variant_mode}
        )
        product_id = result.fetchone()[0]

        # Insert images
        if images_str:
            for idx, img_url in enumerate(images_str.split(",")):
                img_url = img_url.strip()
                if img_url:
                    conn.execute(
                        text("INSERT INTO product_images (product_id, image_url, is_primary, sort_order) VALUES (:pid, :url, :primary, :sort)"),
                        {"pid": product_id, "url": img_url, "primary": idx == 0, "sort": idx}
                    )

        # Insert variants
        if prod_type == "variable" and sku in var_by_parent:
            # Use variation rows
            for v in var_by_parent[sku]:
                v_price = g(v, "Regular price").strip()
                v_sku = g(v, "SKU").strip()

                for i in range(1, 4):
                    attr_name = g(v, f"Attribute {i} name").strip()
                    attr_val = g(v, f"Attribute {i} value(s)").strip()
                    if attr_name and attr_val:
                        price_adj = 0
                        if v_price:
                            try:
                                price_adj = float(v_price) - base_price
                            except ValueError:
                                pass

                        # Check if this variant type+value combo already exists for this product
                        existing = conn.execute(
                            text("SELECT id FROM product_variants WHERE product_id = :pid AND variant_type = :vt AND variant_value = :vv"),
                            {"pid": product_id, "vt": attr_name.lower().replace('product-color', 'color').replace('paper-type', 'paper'), "vv": attr_val}
                        ).fetchone()

                        if not existing:
                            conn.execute(
                                text("""INSERT INTO product_variants (product_id, variant_type, variant_value, price_adjustment, stock, sku)
                                        VALUES (:pid, :vt, :vv, :pa, 9999, :sku)"""),
                                {"pid": product_id,
                                 "vt": attr_name.lower().replace('product-color', 'color').replace('paper-type', 'paper'),
                                 "vv": attr_val,
                                 "pa": round(price_adj, 2),
                                 "sku": v_sku or None}
                            )

        elif prod_type == "simple" and attr_count > 0:
            # Simple product with attributes - create variants from attribute values
            for i in range(1, 4):
                attr_name = g(row, f"Attribute {i} name").strip()
                attr_vals = g(row, f"Attribute {i} value(s)").strip()
                if attr_name and attr_vals:
                    for val in attr_vals.split(","):
                        val = val.strip()
                        if val:
                            conn.execute(
                                text("""INSERT INTO product_variants (product_id, variant_type, variant_value, price_adjustment, stock, sku)
                                        VALUES (:pid, :vt, :vv, 0, 9999, NULL)"""),
                                {"pid": product_id,
                                 "vt": attr_name.lower().replace('product-color', 'color').replace('paper-type', 'paper'),
                                 "vv": val}
                            )

        # Insert discount slabs
        for i in range(1, 9):
            qty_str = g(row, f"Meta: _wcj_wholesale_price_level_min_qty_{i}").strip()
            disc_str = g(row, f"Meta: _wcj_wholesale_price_level_discount_{i}").strip()
            if qty_str and disc_str:
                try:
                    qty = int(float(qty_str))
                    disc = float(disc_str)
                    if qty > 0 and disc > 0:
                        conn.execute(
                            text("INSERT INTO discount_slabs (product_id, min_quantity, discount_percentage) VALUES (:pid, :qty, :disc)"),
                            {"pid": product_id, "qty": qty, "disc": disc}
                        )
                except ValueError:
                    pass

        imported += 1
        if imported % 50 == 0:
            conn.commit()
            print(f"  ... imported {imported} products")

    conn.commit()
    print(f"\n  Imported {imported} products, skipped {skipped}")
    return imported


def main():
    print("=== ClayBag WooCommerce Import ===\n")

    print("1. Reading CSV...")
    all_rows = parse_csv()
    print(f"   {len(all_rows)} rows read\n")

    with engine.connect() as conn:
        print("2. Ensuring categories & subcategories...")
        cat_map, sub_map = ensure_categories(conn, all_rows)
        print(f"   {len(cat_map)} categories, {len(sub_map)} subcategories\n")

        print("3. Clearing existing products...")
        clear_products(conn)

        print("\n4. Importing products...")
        count = import_products(conn, all_rows, cat_map, sub_map)

        print(f"\n=== Done! {count} products imported ===")


if __name__ == "__main__":
    main()
