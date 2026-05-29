-- ─────────────────────────────────────────────────────────────
-- Reset · Olist Marketplace en Supabase
-- ─────────────────────────────────────────────────────────────
-- Pegar y ejecutar en:
--   https://supabase.com/dashboard/project/mmdgtrimakoicobsqlra/sql/new
--
-- Tira las 8 tablas Olist + sus FKs, índices y policies RLS.
-- Orden: hijos primero (FK-safe), padres después. CASCADE limpia
-- los rastros que queden.
-- ─────────────────────────────────────────────────────────────

begin;

drop table if exists olist_order_reviews            cascade;
drop table if exists olist_order_payments           cascade;
drop table if exists olist_order_items              cascade;
drop table if exists olist_orders                   cascade;
drop table if exists olist_products                 cascade;
drop table if exists olist_sellers                  cascade;
drop table if exists olist_customers                cascade;
drop table if exists product_category_name_translation cascade;

-- Verificación: el resultado debe ser 0 filas (ninguna tabla Olist queda)
select tablename
from pg_tables
where schemaname = 'public'
  and (tablename like 'olist_%' or tablename = 'product_category_name_translation');

commit;
