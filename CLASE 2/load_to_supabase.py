"""
Olist → Supabase · Cargador one-shot
─────────────────────────────────────────────────────────────
Lee los 8 CSVs de `data/olist/` e inserta los registros en
las tablas de Supabase definidas en `supabase_schema.sql`.

Prerrequisitos:
  1. Ejecutar `supabase_schema.sql` en el SQL Editor del dashboard.
  2. Tener el archivo `.env` en esta misma carpeta con
     SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.
  3. `pip install -r requirements.txt`

Uso:
  python load_to_supabase.py            # carga las 8 tablas
  python load_to_supabase.py customers  # carga solo una tabla
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

# Forzar UTF-8 en stdout para que los emojis no rompan en consola Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# ── Configuración ───────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
if not URL or not KEY:
    sys.exit("❌ Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en .env")

DATA_DIR = Path(__file__).parent / "data" / "olist"
BATCH_SIZE = 500  # supabase-py recomienda < 1000 filas por request

supabase = create_client(URL, KEY)


# ── Helpers ─────────────────────────────────────────────────
def to_records(df: pd.DataFrame) -> list[dict]:
    """DF → lista de dicts JSON-safe. Convierte NaN/NaT → None y
    timestamps → ISO 8601 string (lo que Supabase espera)."""
    out = df.copy()
    for col in out.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        out[col] = out[col].dt.strftime("%Y-%m-%d %H:%M:%S").where(out[col].notna(), None)
    out = out.astype(object).where(pd.notnull(out), None)
    return out.to_dict(orient="records")


def nullable_int(s: pd.Series) -> pd.Series:
    """Convierte float-con-NaN → Int64 (nullable) para que el JSON
    no mande 1234.0 sino 1234 (y los NaN se serialicen como None)."""
    return s.astype("Int64")


def upsert_chunked(table: str, df: pd.DataFrame, on_conflict: str) -> None:
    """Upsert paginado. on_conflict = lista de columnas PK separadas por coma."""
    records = to_records(df)
    total = len(records)
    n_batches = math.ceil(total / BATCH_SIZE)
    print(f"📤 {table}: {total:,} filas en {n_batches} batches")
    t0 = time.time()
    for i in range(n_batches):
        chunk = records[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        try:
            supabase.table(table).upsert(chunk, on_conflict=on_conflict).execute()
        except Exception as e:
            print(f"   ❌ batch {i+1}/{n_batches} falló: {e}")
            print(f"      muestra del primer registro: {chunk[0] if chunk else 'vacío'}")
            raise
        if (i + 1) % 10 == 0 or i + 1 == n_batches:
            elapsed = time.time() - t0
            rate = (i + 1) * BATCH_SIZE / elapsed if elapsed > 0 else 0
            print(f"   ✓ {i+1}/{n_batches} batches  ({rate:,.0f} rows/s)")
    print(f"   ✅ {table} completo en {time.time()-t0:.1f}s\n")


# ── Loaders por tabla ───────────────────────────────────────
def load_customers() -> None:
    df = pd.read_csv(DATA_DIR / "olist_customers_dataset.csv")
    df["customer_zip_code_prefix"] = nullable_int(df["customer_zip_code_prefix"])
    upsert_chunked("olist_customers", df, on_conflict="customer_id")


def load_sellers() -> None:
    df = pd.read_csv(DATA_DIR / "olist_sellers_dataset.csv")
    df["seller_zip_code_prefix"] = nullable_int(df["seller_zip_code_prefix"])
    upsert_chunked("olist_sellers", df, on_conflict="seller_id")


def load_category_translation() -> None:
    df = pd.read_csv(DATA_DIR / "product_category_name_translation.csv", encoding="utf-8-sig")

    # El dataset original de Olist tiene categorías (p. ej. 'pc_gamer') que
    # aparecen en products pero NO en este archivo de traducción.
    # Para no romper el FK, añadimos esas huérfanas usando el nombre PT
    # como fallback del nombre EN.
    products = pd.read_csv(DATA_DIR / "olist_products_dataset.csv", usecols=["product_category_name"])
    used_categories = set(products["product_category_name"].dropna().unique())
    known_categories = set(df["product_category_name"])
    missing = used_categories - known_categories
    if missing:
        print(f"⚠️  {len(missing)} categoría(s) sin traducción oficial → uso PT como fallback EN: {sorted(missing)}")
        df_extra = pd.DataFrame({
            "product_category_name": sorted(missing),
            "product_category_name_english": sorted(missing),
        })
        df = pd.concat([df, df_extra], ignore_index=True)

    upsert_chunked("product_category_name_translation", df, on_conflict="product_category_name")


def load_products() -> None:
    df = pd.read_csv(DATA_DIR / "olist_products_dataset.csv")
    int_cols = [
        "product_name_lenght", "product_description_lenght", "product_photos_qty",
        "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm",
    ]
    for c in int_cols:
        df[c] = nullable_int(df[c])
    upsert_chunked("olist_products", df, on_conflict="product_id")


def load_orders() -> None:
    df = pd.read_csv(
        DATA_DIR / "olist_orders_dataset.csv",
        parse_dates=[
            "order_purchase_timestamp", "order_approved_at",
            "order_delivered_carrier_date", "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    )
    upsert_chunked("olist_orders", df, on_conflict="order_id")


def load_order_items() -> None:
    df = pd.read_csv(
        DATA_DIR / "olist_order_items_dataset.csv",
        parse_dates=["shipping_limit_date"],
    )
    df["order_item_id"] = nullable_int(df["order_item_id"])
    upsert_chunked("olist_order_items", df, on_conflict="order_id,order_item_id")


def load_order_payments() -> None:
    df = pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv")
    df["payment_sequential"] = nullable_int(df["payment_sequential"])
    df["payment_installments"] = nullable_int(df["payment_installments"])
    upsert_chunked("olist_order_payments", df, on_conflict="order_id,payment_sequential")


def load_order_reviews() -> None:
    df = pd.read_csv(
        DATA_DIR / "olist_order_reviews_dataset.csv",
        parse_dates=["review_creation_date", "review_answer_timestamp"],
    )
    df["review_score"] = nullable_int(df["review_score"])
    # PK compuesta (review_id, order_id) — desduplicamos por si acaso
    before = len(df)
    df = df.drop_duplicates(subset=["review_id", "order_id"], keep="first")
    if len(df) < before:
        print(f"⚠️  reviews: {before - len(df):,} duplicados (review_id, order_id) descartados")
    upsert_chunked("olist_order_reviews", df, on_conflict="review_id,order_id")


# ── Orquestación ────────────────────────────────────────────
LOADERS = {
    "customers":            load_customers,
    "sellers":              load_sellers,
    "category_translation": load_category_translation,
    "products":             load_products,
    "orders":               load_orders,
    "order_items":          load_order_items,
    "order_payments":       load_order_payments,
    "order_reviews":        load_order_reviews,
}

# Orden de dependencias (FKs)
ORDER = [
    "customers", "sellers", "category_translation", "products",
    "orders", "order_items", "order_payments", "order_reviews",
]


def main() -> None:
    targets = sys.argv[1:] or ORDER
    unknown = [t for t in targets if t not in LOADERS]
    if unknown:
        sys.exit(f"❌ Tabla(s) desconocida(s): {unknown}\n   Disponibles: {list(LOADERS)}")

    print(f"🛒 Olist → Supabase ({URL})")
    print(f"   Tablas a cargar: {targets}\n")
    t0 = time.time()
    for name in targets:
        LOADERS[name]()
    print(f"🎉 Listo en {time.time()-t0:.1f}s totales.")


if __name__ == "__main__":
    main()
