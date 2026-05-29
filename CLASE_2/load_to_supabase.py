"""
Loader · Adidas vs Nike → Supabase
─────────────────────────────────────────────────────────────
Lee `data/olist/Adidas_Vs_Nike_intentar_abrir.csv` (separador `*`)
e inserta en las 2 tablas de Supabase:
  · brands   (5 marcas, normaliza typo "Adidas Adidas ORIGINALS")
  · products (3,268 filas, conserva re-listados del scraping)

Prerrequisitos:
  1. Ejecutar `supabase_schema.sql` en el SQL Editor del dashboard.
  2. `.env` con SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY en esta carpeta.
  3. `pip install -r requirements.txt`

Uso:
  python load_to_supabase.py            # carga brands + products
  python load_to_supabase.py brands     # solo una tabla
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

# Forzar UTF-8 en stdout para que los emojis no rompan en Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# ── Configuración ───────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
if not URL or not KEY:
    sys.exit("❌ Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en .env")

CSV_PATH = Path(__file__).parent / "data" / "olist" / "Adidas_Vs_Nike_intentar_abrir.csv"
BATCH_SIZE = 500

supabase = create_client(URL, KEY)


# ── Helpers reutilizables ───────────────────────────────────
def to_records(df: pd.DataFrame) -> list[dict]:
    """DF → lista de dicts JSON-safe. NaN/NaT → None, datetime → ISO."""
    out = df.copy()
    for col in out.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        out[col] = out[col].dt.strftime("%Y-%m-%d %H:%M:%S").where(out[col].notna(), None)
    out = out.astype(object).where(pd.notnull(out), None)
    return out.to_dict(orient="records")


def insert_chunked(table: str, df: pd.DataFrame) -> None:
    """Insert paginado. NO usa upsert porque products usa surrogate PK
    auto-incremental: re-correr crearía filas duplicadas. Para re-cargar,
    primero corre `supabase_schema.sql` que dropea y recrea las tablas."""
    records = to_records(df)
    total = len(records)
    n_batches = math.ceil(total / BATCH_SIZE)
    print(f"📤 {table}: {total:,} filas en {n_batches} batches")
    t0 = time.time()
    for i in range(n_batches):
        chunk = records[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        try:
            supabase.table(table).insert(chunk).execute()
        except Exception as e:
            print(f"   ❌ batch {i+1}/{n_batches} falló: {e}")
            print(f"      muestra del primer registro: {chunk[0] if chunk else 'vacío'}")
            raise
        if (i + 1) % 5 == 0 or i + 1 == n_batches:
            elapsed = time.time() - t0
            rate = (i + 1) * BATCH_SIZE / elapsed if elapsed > 0 else 0
            print(f"   ✓ {i+1}/{n_batches} batches  ({rate:,.0f} rows/s)")
    print(f"   ✅ {table} completo en {time.time()-t0:.1f}s\n")


# ── Carga + transformación del CSV ──────────────────────────
def load_csv() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, sep="*")

    # Normalizar typo "Adidas Adidas ORIGINALS" → "Adidas ORIGINALS"
    df["Brand"] = df["Brand"].replace({"Adidas Adidas ORIGINALS": "Adidas ORIGINALS"})

    # Listing Price = 0 → NULL (out of stock en el CSV)
    df.loc[df["Listing Price"] == 0, "Listing Price"] = pd.NA

    # Last Visited → datetime
    df["Last Visited"] = pd.to_datetime(df["Last Visited"], errors="coerce")

    # Rating == 0 con Reviews == 0 → NULL en rating (no calificado aún)
    mask_no_rating = (df["Rating"] == 0) & (df["Reviews"] == 0)
    df.loc[mask_no_rating, "Rating"] = pd.NA

    return df


# ── Loaders por tabla ───────────────────────────────────────
def brand_code(brand_name: str) -> str:
    """'Adidas ORIGINALS' → 'adidas_originals'."""
    return brand_name.lower().replace("/", "_").replace("  ", " ").strip().replace(" ", "_")


def parent_of(brand_name: str) -> str:
    return "Nike" if brand_name.startswith("Nike") else "Adidas"


def load_brands() -> dict[str, int]:
    """Inserta las marcas únicas y devuelve mapping name → brand_id."""
    df = load_csv()
    brands_df = (
        df[["Brand"]].drop_duplicates().sort_values("Brand").reset_index(drop=True)
        .rename(columns={"Brand": "brand_name"})
    )
    brands_df["brand_code"] = brands_df["brand_name"].apply(brand_code)
    brands_df["parent_brand"] = brands_df["brand_name"].apply(parent_of)

    print(f"📦 Marcas detectadas: {len(brands_df)}")
    print(brands_df.to_string(index=False))
    print()

    insert_chunked("brands", brands_df[["brand_code", "brand_name", "parent_brand"]])

    # Leer back para obtener los brand_id asignados por Postgres
    resp = supabase.table("brands").select("brand_id, brand_name").execute()
    return {r["brand_name"]: r["brand_id"] for r in resp.data}


def load_products(brand_id_map: dict[str, int]) -> None:
    df = load_csv()
    df["brand_id"] = df["Brand"].map(brand_id_map)
    if df["brand_id"].isna().any():
        missing = df.loc[df["brand_id"].isna(), "Brand"].unique().tolist()
        raise RuntimeError(f"Brand sin mapping a brand_id: {missing}")

    products = pd.DataFrame({
        "product_code":      df["Product ID"],
        "brand_id":          df["brand_id"].astype("Int64"),
        "product_name":      df["Product Name"],
        "description":       df["Description"],
        "listing_price_inr": df["Listing Price"].astype("Int64"),
        "sale_price_inr":    df["Sale Price"].astype("Int64"),
        "discount_pct":      df["Discount"].astype("Int64"),
        "rating":            df["Rating"],
        "reviews_count":     df["Reviews"].astype("Int64"),
        "last_visited":      df["Last Visited"],
    })

    insert_chunked("products", products)


# ── Orquestación ────────────────────────────────────────────
LOADERS = ["brands", "products"]


def main() -> None:
    targets = sys.argv[1:] or LOADERS
    unknown = [t for t in targets if t not in LOADERS]
    if unknown:
        sys.exit(f"❌ Tabla(s) desconocida(s): {unknown}\n   Disponibles: {LOADERS}")

    print(f"👟 Adidas vs Nike → Supabase ({URL})")
    print(f"   Tablas a cargar: {targets}\n")
    t0 = time.time()

    brand_id_map: dict[str, int] = {}
    if "brands" in targets:
        brand_id_map = load_brands()
    if "products" in targets:
        if not brand_id_map:
            # cargar solo products → asume brands ya en Supabase
            resp = supabase.table("brands").select("brand_id, brand_name").execute()
            brand_id_map = {r["brand_name"]: r["brand_id"] for r in resp.data}
            if not brand_id_map:
                sys.exit("❌ No hay brands en Supabase. Corre primero el loader de brands.")
        load_products(brand_id_map)

    print(f"🎉 Listo en {time.time()-t0:.1f}s totales.")


if __name__ == "__main__":
    main()
