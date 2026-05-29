-- ─────────────────────────────────────────────────────────────
-- Schema · Adidas vs Nike (catálogo de sneakers)
-- ─────────────────────────────────────────────────────────────
-- Pegar y ejecutar en:
--   https://supabase.com/dashboard/project/mmdgtrimakoicobsqlra/sql/new
--
-- Esto:
--   1. Dropea las 8 tablas Olist (si existen) — reinicio limpio.
--   2. Dropea brands/products si existen — re-ejecutable.
--   3. Crea brands (5 filas) y products (3,268 filas) con FK.
--   4. Habilita RLS + policy read-only para anon (la app usa anon).
-- ─────────────────────────────────────────────────────────────

begin;

-- ── Reset Olist ─────────────────────────────────────────────
drop table if exists olist_order_reviews            cascade;
drop table if exists olist_order_payments           cascade;
drop table if exists olist_order_items              cascade;
drop table if exists olist_orders                   cascade;
drop table if exists olist_products                 cascade;
drop table if exists olist_sellers                  cascade;
drop table if exists olist_customers                cascade;
drop table if exists product_category_name_translation cascade;

-- ── Reset Adidas vs Nike (idempotente) ──────────────────────
drop table if exists products cascade;
drop table if exists brands   cascade;


-- ── Brands (5 filas — incluye normalización del typo) ──────
create table brands (
    brand_id     smallserial primary key,
    brand_code   text unique not null,   -- 'adidas_originals', 'nike', …
    brand_name   text not null,          -- 'Adidas ORIGINALS', 'Nike'
    parent_brand text not null           -- 'Adidas' | 'Nike'  ← agrupa Adidas-vs-Nike
);


-- ── Products (3,268 filas — el catálogo) ────────────────────
-- Surrogate PK porque el "Product ID" original tiene 88 re-listados
-- idénticos dentro de la misma marca; el usuario pidió conservarlos
-- todos (no dedupe).
create table products (
    product_id        bigserial primary key,
    product_code      text not null,                                 -- el "Product ID" del CSV
    brand_id          smallint not null references brands(brand_id),
    product_name      text not null,
    description       text,
    listing_price_inr integer,                                       -- NULL = out of stock (0 del CSV)
    sale_price_inr    integer not null,
    discount_pct      smallint not null check (discount_pct between 0 and 100),
    rating            numeric(2,1) check (rating between 0 and 5),
    reviews_count     integer not null default 0,
    last_visited      timestamptz
);
create index on products (brand_id);
create index on products (discount_pct);
create index on products (rating);
create index on products (sale_price_inr);
create index on products (product_code);


-- ── RLS + policy read-only para anon ────────────────────────
do $$
declare
    t text;
begin
    for t in
        select unnest(array['brands', 'products']::text[])
    loop
        execute format('alter table %I enable row level security', t);
        execute format(
            'create policy "allow_anon_read" on %I for select to anon using (true)',
            t
        );
        execute format(
            'create policy "allow_authenticated_read" on %I for select to authenticated using (true)',
            t
        );
    end loop;
end $$;

commit;


-- ── Verificación ────────────────────────────────────────────
select 'brands'   as tabla, count(*) as filas from brands
union all
select 'products' as tabla, count(*) as filas from products;
