-- ─────────────────────────────────────────────────────────────
-- Olist Marketplace · Schema para Supabase
-- Ejecutar en: Supabase Dashboard → SQL Editor → New query
-- ─────────────────────────────────────────────────────────────
-- Estrategia:
--   • RLS habilitado en todas las tablas.
--   • Policy "allow_anon_read" permite SELECT al rol anon
--     (la app de Streamlit usa anon_key y solo lee).
--   • service_role bypassa RLS automáticamente → el loader
--     puede insertar sin policies extra.
-- ─────────────────────────────────────────────────────────────

-- Drop en orden inverso de dependencias (idempotente)
drop table if exists olist_order_reviews   cascade;
drop table if exists olist_order_payments  cascade;
drop table if exists olist_order_items     cascade;
drop table if exists olist_orders          cascade;
drop table if exists olist_products        cascade;
drop table if exists olist_sellers         cascade;
drop table if exists olist_customers       cascade;
drop table if exists product_category_name_translation cascade;


-- ── DIMENSIONES INDEPENDIENTES ──────────────────────────────
create table olist_customers (
    customer_id              text primary key,
    customer_unique_id       text not null,
    customer_zip_code_prefix integer,
    customer_city            text,
    customer_state           text
);
create index on olist_customers (customer_unique_id);
create index on olist_customers (customer_state);

create table olist_sellers (
    seller_id              text primary key,
    seller_zip_code_prefix integer,
    seller_city            text,
    seller_state           text
);
create index on olist_sellers (seller_state);

create table product_category_name_translation (
    product_category_name         text primary key,
    product_category_name_english text not null
);

create table olist_products (
    product_id                 text primary key,
    product_category_name      text references product_category_name_translation(product_category_name),
    product_name_lenght        integer,  -- typo original del dataset, lo mantenemos
    product_description_lenght integer,
    product_photos_qty         integer,
    product_weight_g           integer,
    product_length_cm          integer,
    product_height_cm          integer,
    product_width_cm           integer
);
create index on olist_products (product_category_name);


-- ── HECHOS ──────────────────────────────────────────────────
create table olist_orders (
    order_id                      text primary key,
    customer_id                   text not null references olist_customers(customer_id),
    order_status                  text not null,
    order_purchase_timestamp      timestamptz not null,
    order_approved_at             timestamptz,
    order_delivered_carrier_date  timestamptz,
    order_delivered_customer_date timestamptz,
    order_estimated_delivery_date timestamptz
);
create index on olist_orders (customer_id);
create index on olist_orders (order_status);
create index on olist_orders (order_purchase_timestamp);

create table olist_order_items (
    order_id            text not null references olist_orders(order_id),
    order_item_id       integer not null,
    product_id          text not null references olist_products(product_id),
    seller_id           text not null references olist_sellers(seller_id),
    shipping_limit_date timestamptz,
    price               numeric(12,2),
    freight_value       numeric(12,2),
    primary key (order_id, order_item_id)
);
create index on olist_order_items (product_id);
create index on olist_order_items (seller_id);

create table olist_order_payments (
    order_id             text not null references olist_orders(order_id),
    payment_sequential   integer not null,
    payment_type         text,
    payment_installments integer,
    payment_value        numeric(12,2),
    primary key (order_id, payment_sequential)
);
create index on olist_order_payments (payment_type);

-- Reviews: review_id NO es único en el CSV original (hay duplicados),
-- por eso usamos (review_id, order_id) como PK compuesta.
create table olist_order_reviews (
    review_id               text not null,
    order_id                text not null references olist_orders(order_id),
    review_score            integer,
    review_comment_title    text,
    review_comment_message  text,
    review_creation_date    timestamptz,
    review_answer_timestamp timestamptz,
    primary key (review_id, order_id)
);
create index on olist_order_reviews (order_id);
create index on olist_order_reviews (review_score);


-- ── RLS + POLICIES (read-only para anon) ────────────────────
do $$
declare
    t text;
begin
    for t in
        select unnest(array[
            'olist_customers',
            'olist_sellers',
            'product_category_name_translation',
            'olist_products',
            'olist_orders',
            'olist_order_items',
            'olist_order_payments',
            'olist_order_reviews'
        ])
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
