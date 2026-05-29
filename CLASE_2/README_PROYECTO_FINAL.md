# Proyecto Final · Olist Marketplace Insights

**Curso:** Herramientas de Visualización para la Inteligencia de Negocios
**Maestría en Analítica**
**Dashboard:** [app_olist.py](app_olist.py)
**Herramienta:** Streamlit + Plotly (Python)

---

## 1. Propósito y audiencia

**Problema:** el comité ejecutivo de Olist (marketplace brasileño de e-commerce) necesita un instrumento único de monitoreo retrospectivo del marketplace que combine la performance comercial (GMV, ticket, volumen), la salud operativa (tiempos de entrega, satisfacción del cliente) y el riesgo de portafolio (concentración de sellers, mix de categorías) para tomar decisiones sobre crecimiento, logística y category management.

**Audiencia primaria:** CEO, COO de logística, head de category management. Audiencia secundaria: equipos de operaciones y análisis.

**Decisiones que habilita:**
- Renegociar tarifas y SLAs de freight en estados con peor on-time.
- Priorizar inversión en categorías con alto GMV y alta satisfacción ("estrellas").
- Diseñar un programa de captación en el long-tail de sellers para reducir dependencia.
- Anticipar shifts en el mix de pagos (boleto vs tarjeta) para tesorería.

---

## 2. Tres preguntas de negocio (una por tab)

1. **Tab Crecimiento** — ¿Cómo evoluciona el GMV mensual y qué porción del crecimiento viene de volumen vs. ticket promedio?
2. **Tab Logística & Satisfacción** — ¿En qué estados y rangos de tiempo de entrega se concentran los problemas que arrastran las reseñas?
3. **Tab Categorías & Sellers** — ¿Qué categorías y qué concentración de sellers explican el GMV, y cuál es el riesgo de long-tail?

---

## 3. Origen de los datos

| Campo | Valor |
|---|---|
| Dataset | Brazilian E-Commerce Public Dataset by Olist |
| Fuente oficial | https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce |
| Mirror operativo (sin auth) | https://github.com/olist/work-at-olist-data/tree/master/datasets |
| Publicador | Olist Store (Brasil) |
| Licencia | CC BY-NC-SA 4.0 |
| Período cubierto | sep 2016 – oct 2018 |
| Fecha de descarga | Mayo 2026 |
| Granularidad | Pedido + línea de pedido (multi-tabla) |

**Tipo de fuente:** datos reales y públicos del marketplace Olist, anonimizados por el publicador (sin PII; `customer_unique_id` es hash).

---

## 4. Cómo descargar los datos

Descargar manualmente los **8 CSVs** y colocarlos en `CLASE_2/data/olist/` (la app no descarga nada por sí sola). Click derecho sobre cada link → *Guardar enlace como…*:

1. https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/olist_orders_dataset.csv
2. https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/olist_order_items_dataset.csv
3. https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/olist_order_payments_dataset.csv
4. https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/olist_order_reviews_dataset.csv
5. https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/olist_customers_dataset.csv
6. https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/olist_products_dataset.csv
7. https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/olist_sellers_dataset.csv
8. https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/product_category_name_translation.csv

Se omite `olist_geolocation_dataset.csv` (~61 MB de lat/long zip-prefix) porque el grano *estado* — ya disponible en `customers` y `sellers` — es suficiente para el análisis ejecutivo.

Si la app no encuentra los archivos, muestra un mensaje claro indicando qué falta y de dónde descargarlo.

---

## 5. Cómo ejecutar

```powershell
cd "c:\Users\samue\Desktop\ANALAITICA\CLASE_2"
pip install -r ..\requirements.txt
streamlit run app_olist.py
```

El dashboard abre en http://localhost:8501. Primer arranque: ~5-10 s para el merge cacheado. Posteriores: instantáneos.

---

## 6. Proceso de adquisición y transformación (ETL)

Implementado en [app_olist.py](app_olist.py) dentro de dos funciones cacheadas (`load_orders`, `load_items`).

### Paso 1 — Lectura
Lectura directa con `pandas.read_csv` parseando fechas (`order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date`, `review_creation_date`, `review_answer_timestamp`).

### Paso 2 — Agregaciones previas al join
- **Pagos** → un pedido puede tener varios pagos (split). Se agrega a nivel `order_id`: `payment_value` sumado, `payment_installments` máximo, `payment_type` del pago más grande.
- **Reviews** → un pedido puede tener varias reseñas. Se ordena por `review_creation_date` y se queda con la primera por `order_id`.
- **Items** → un pedido tiene varias líneas. Se agrega a nivel `order_id`: `price` y `freight_value` sumados, `n_items` conteo, categoría principal por moda, estado del seller principal por moda.

### Paso 3 — Merges en estrella sobre `orders`
```
orders
  ⟕ customers           on customer_id
  ⟕ order_payments_agg  on order_id
  ⟕ order_reviews_dedup on order_id
  ⟕ order_items_agg     on order_id
```
Resultado: `df_orders` con ~99 k filas y ~25 columnas (1 fila por pedido).

Adicionalmente se construye un `df_items` (1 fila por línea de pedido, ~112 k filas) que se usa solo en la Tab 3 para la Pareto de sellers.

---

## 7. Variables utilizadas y derivadas

### Variables base (del dataset)
- Identificadores: `order_id`, `customer_id`, `customer_unique_id`, `seller_id`, `product_id`.
- Geográficas: `customer_state`, `customer_city`, `seller_state`.
- Temporales: `order_purchase_timestamp`, `order_estimated_delivery_date`, `order_delivered_customer_date`.
- Comerciales: `price`, `freight_value`, `payment_value`, `payment_type`, `payment_installments`.
- Producto: `product_category_name`, `product_category_name_english`.
- Calidad: `review_score`, `order_status`.

### Variables derivadas (calculadas en `load_orders()`)
| Variable | Fórmula | Uso |
|---|---|---|
| `revenue` | `items_price_sum + items_freight_sum` | Proxy de GMV (KPI principal y todas las tabs) |
| `delivery_delay_days` | `delivered_customer_date - estimated_delivery_date` (días) | Logística (Tab 2) |
| `actual_delivery_days` | `delivered_customer_date - purchase_timestamp` (días) | Heatmap entrega × review (Tab 2) |
| `on_time_flag` | `1 si delay ≤ 0, else 0` (solo `status='delivered'`) | KPI on-time, barras por estado |
| `freight_ratio` | `items_freight_sum / items_price_sum` | Análisis de eficiencia logística |
| `order_month` | `purchase_timestamp` truncado a mes | Series temporales (Tab 1) |
| `review_bucket` | Cut: Detractor (1-2) · Neutral (3) · Promoter (4-5) | Segmentación de satisfacción |
| `delivery_speed_bucket` | Cut: ≤3d · 4–7d · 8–14d · 15–30d · 30d+ | Eje X del heatmap (Tab 2) |
| `category_en` | `product_category_name_english` con fallback al portugués | Etiquetas legibles en gráficos |
| `line_revenue` | `price + freight_value` (en `df_items`) | Pareto de sellers (Tab 3) |

---

## 8. Registros excluidos y tratamiento

| Caso | Decisión | Justificación |
|---|---|---|
| Pedidos cancelados / unavailable | Se conservan en `df_orders` pero el sidebar filtra por defecto `order_status='delivered'` | Permite al ejecutivo ver "negocio cerrado" sin perder la capacidad de quitar el filtro para auditar pérdidas. |
| Pedidos delivered sin `delivered_customer_date` (~2.9 %) | `on_time_flag = NaN`, excluidos de `.mean()` | Imposible calcular on-time sin la fecha; mejor NaN que asumir. |
| Reviews duplicadas por pedido | `drop_duplicates(keep='first')` por `review_creation_date` ascendente | Primera reseña refleja la experiencia inicial del comprador. |
| Pagos split en varios métodos | Suma de `payment_value`, `max(installments)`, `payment_type` del pago dominante | Mantiene fidelidad financiera y representatividad del método principal. |
| Outliers en `freight_ratio` | Solo se clipan al 99-pct **en visualizaciones**, nunca en agregados | No distorsionar totales por un pedido extremo. |
| Sep 2016 (4 pedidos) y Sep-Oct 2018 (parciales) | Rango default del sidebar arranca en 2017-01-01 y termina 2018-08-31 | Evita distorsionar series mensuales con meses de cobertura incompleta. Documentado en footnote del insight-box. |
| Geolocation (1 M filas, ~61 MB) | Excluido del modelo | Grano lat/long innecesario al nivel ejecutivo; estado ya disponible en `customers`/`sellers`. |
| PII | El dataset original ya está anonimizado por Olist | No se realizan transformaciones adicionales; se cita la licencia. |

---

## 9. Modelo de datos

```
                        ┌───────────────────┐
                        │    customers      │
                        │  customer_id PK   │
                        │  customer_state   │
                        └─────────┬─────────┘
                                  │ 1
                                  │
                          ┌───────▼────────┐                ┌──────────────────────┐
                          │     orders     │ 1 ── many ────►│  order_payments      │
                          │  order_id PK   │                │  payment_value       │
                          │  status, dates │                └──────────────────────┘
                          └───┬──────┬─────┘
                              │ 1    │ 1
                              │      │
                ┌─────────────┘      └──── many ──┐
                ▼                                  ▼
       ┌─────────────────┐                ┌──────────────────────┐
       │  order_reviews  │                │     order_items      │
       │  review_score   │                │  price, freight      │
       └─────────────────┘                │  product_id, seller  │
                                          └────────┬──────┬──────┘
                                                   │      │
                                          ┌────────▼─┐  ┌▼─────────┐
                                          │ products │  │ sellers  │
                                          └────┬─────┘  │ state    │
                                               │        └──────────┘
                                          ┌────▼──────────────────┐
                                          │ category_translation  │
                                          │  pt → en              │
                                          └───────────────────────┘
```

**Resultado del modelado:** dos DataFrames analíticos cacheados —
`df_orders` (hechos por pedido) y `df_items` (hechos por línea) — que actúan como tablas de hechos consolidadas. Las dimensiones (customer_state, primary_category_en, payment_type, order_status, delivery_speed_bucket, review_bucket) viven como columnas categóricas dentro del DataFrame, siguiendo el patrón "wide table" típico de pandas+Streamlit.

---

## 10. KPIs e indicadores

| # | KPI | Fórmula | Formato |
|---|---|---|---|
| 1 | **GMV** | `revenue.sum()` | `R$ 15.4M` |
| 2 | **Pedidos** | `order_id.nunique()` | `96,478` |
| 3 | **Ticket promedio** | `revenue.sum() / order_id.nunique()` | `R$ 160` |
| 4 | **On-time delivery %** | `on_time_flag.mean()` (solo delivered con fecha de entrega) | `92.3%` |
| 5 | **Review medio** | `review_score.mean()` | `4.09 ★` |

Cada KPI muestra un **delta vs. período anterior de igual duración** (▲/▼ en porcentaje) calculado dinámicamente sobre la ventana del sidebar.

---

## 11. Decisiones de visualización

| Sección | Gráfico | Por qué |
|---|---|---|
| Tab 1 — Evolución GMV/pedidos | Área cyan + línea violeta con eje secundario | Comparación de dos series de escala distinta; área enfatiza magnitud del GMV. |
| Tab 1 — Ticket vs volumen | Scatter con `size=GMV`, OLS | Separa visualmente si el crecimiento viene de más pedidos o de ticket mayor. |
| Tab 1 — Mix de pago | Área apilada al 100% | Muestra evolución de participaciones, no de valores absolutos. |
| Tab 2 — Entrega vs review | Heatmap de densidad (Inferno) | Revela la correlación: pedidos rápidos → 5★, lentos → 1★. |
| Tab 2 — On-time por estado | Barras horizontales ordenadas + línea de media | Ranking ascendente: los peores estados saltan al ojo del ejecutivo. |
| Tab 2 — Distribución reviews | Barras con escala rojo→verde | Color codifica calidad sin necesidad de leyenda. |
| Tab 3 — Cuadrante categorías | Scatter con cuadrantes en medianas | Patrón clásico exec: "estrellas" arriba-derecha, "problemas" arriba-izquierda. |
| Tab 3 — Pareto sellers | Barras + línea acumulada con anotaciones 50/80% | Visual estándar de concentración; las anotaciones cuentan la historia. |
| Tab 3 — Tabla categorías | DataFrame con gradiente condicional en review y on-time | Drill-down ordenado para análisis detallado fuera del exec view. |

---

## 12. Diseño visual

### Paleta y semántica del color
- **Cyan → Azul** (`#06b6d4 → #3b82f6`): valor monetario (GMV, ingresos).
- **Naranja → Rojo** (`#f97316 → #ef4444`): volumen + alertas / retrasos.
- **Amarillo → Ámbar** (`#eab308 → #f59e0b`): métricas neutras (ticket, atención media).
- **Verde** (`#22c55e`): on-time, promoters, salud operativa.
- **Violeta → Fucsia** (`#6366f1 → #a855f7`): branding, elementos secundarios sin connotación cuantitativa.
- **Rojo→Amarillo→Verde** divergente: escalas de calidad (on-time %, review_score).

El fondo oscuro radial reduce fatiga visual en sustentación con proyector y eleva el contraste de los colores semánticos.

### Jerarquía y distribución (patrón Z)
1. **Esquina superior izquierda**: marca ANALAITICA + filtros del sidebar.
2. **Banda superior central**: hero card con título y contexto temporal.
3. **Banda KPI** (5 columnas alineadas): primer punto de fijación tras el hero.
4. **Tabs** organizadas de lo más general (Crecimiento) a lo más específico (Categorías/Sellers).
5. **Cierre inferior**: insight-box con narrativa dinámica — el ojo termina con una conclusión accionable.

Cada sección dentro de una tab abre con un `section-title` con barra acentuada izquierda (violeta→fucsia), proporcionando ritmo visual constante y guía de scroll.

---

## 13. Interactividad

- **Sidebar**: rango de fechas, multiselect de estado, multiselect de categoría, multiselect de estado de pedido.
- **Filtros en cascada**: una sola máscara se aplica antes de las tabs; los 5 KPIs, los 9 gráficos y el insight-box recalculan en sincronía.
- **Tooltips Plotly**: cada gráfico tiene `hovertemplate` formateado con moneda BRL y porcentajes legibles.
- **Tabs**: navegación lateral entre las 3 preguntas de negocio.
- **Tabla interactiva**: ordenamiento por columna, gradiente condicional.
- **Delta dinámico en KPIs**: comparación automática contra el período inmediatamente anterior de igual duración.

---

## 14. Justificación de la herramienta (Streamlit)

- **Reproducibilidad**: el dashboard es código versionado (un solo `app_olist.py`), no un binario.
- **Costo**: 100% gratuito y open source; no requiere licencia de BI corporativo.
- **Personalización visual**: CSS custom permite replicar la identidad gráfica de Analaitica.
- **Flexibilidad analítica**: pandas + Plotly cubren cualquier transformación o gráfico avanzado sin "luchar" contra la herramienta.
- **Despliegue simple**: Streamlit Cloud / Hugging Face Spaces / self-hosted con un comando.

**Trade-off declarado:** Power BI / Tableau ofrecen mejor "self-service" para usuarios no técnicos. Para una audiencia ejecutiva con un único punto de entrega (este dashboard), Streamlit gana en control visual y mantenibilidad.

---

## 15. Riesgos y limitaciones para la sustentación

1. **Temporalidad del dataset (2016–2018):** enmarcado explícitamente como *análisis retrospectivo*, no como dashboard en vivo. Mencionado en el hero subtitle.
2. **Licencia CC BY-NC-SA 4.0:** atribución a Olist visible en el sidebar y en este README.
3. **Geolocation excluido:** justificado en sección 8 — grano estado es suficiente para el ejecutivo.
4. **Moneda BRL sin conversión:** se preserva la moneda original para evitar asumir tasas FX que distorsionarían comparaciones inter-período.
5. **Caché de Streamlit:** controlado vía `LOADER_VERSION` para invalidar cuando se tunea el loader.
