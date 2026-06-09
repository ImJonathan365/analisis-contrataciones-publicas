from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from django.conf import settings
from scipy.stats import norm
from sqlalchemy import create_engine


@dataclass
class ItemOption:
    code: str
    label: str


@dataclass
class InventoryReport:
    item_description: str
    demand_annual: float
    unit_cost_avg: float
    holding_cost_used: float
    q_opt: float
    annual_order_cost: float
    annual_holding_cost: float
    total_inventory_cost: float
    orders_per_year: float
    time_between_orders: float
    daily_demand: float
    reorder_point: float
    safety_stock: float
    comparison_rows: list[dict]
    saw_points: str


def _get_mysql_engine():
    mysql_cfg = getattr(settings, "MYSQL_ANALYTICS", None)
    if not mysql_cfg:
        db_cfg = settings.DATABASES.get("default", {})
        mysql_cfg = {
            "NAME": db_cfg.get("NAME", ""),
            "USER": db_cfg.get("USER", ""),
            "PASSWORD": db_cfg.get("PASSWORD", ""),
            "HOST": db_cfg.get("HOST", "127.0.0.1"),
            "PORT": db_cfg.get("PORT", "3306"),
        }

    connection_string = (
        f"mysql+mysqldb://{mysql_cfg['USER']}:{mysql_cfg['PASSWORD']}@"
        f"{mysql_cfg['HOST']}:{mysql_cfg['PORT']}/{mysql_cfg['NAME']}"
    )
    return create_engine(connection_string)


def _read_contracts_base() -> pd.DataFrame:
    engine = _get_mysql_engine()
    print("[inventory] Opening MySQL engine for inventory module...")
    base_query = """
        SELECT
            FECHA_APERTURA,
            CODIGO_IDENTIFICACION,
            DESCRIP_IDENTIFICACION,
            CANTIDAD_SOLICITADA,
            PRECIO_UNITARIO_ESTIMADO
        FROM public_contracts
    """

    fallback_query = """
        SELECT
            FECHA_APERTURA,
            CODIGO_IDENTIFICACION,
            DESCRIP_IDENTIFICACION,
            CANTIDAD_SOLICITADA,
            PRECIO_UNITARIO_ESTIMADO
        FROM contrataciones_hacienda
    """

    try:
        print("[inventory] Trying base query against table: public_contracts")
        return pd.read_sql(base_query, con=engine)
    except Exception:
        print("[inventory] public_contracts query failed, trying fallback table: contrataciones_hacienda")
        return pd.read_sql(fallback_query, con=engine)


def _prepare_base(df: pd.DataFrame) -> pd.DataFrame:
    print(f"[inventory] Raw dataframe loaded with {len(df):,} rows and columns: {list(df.columns)}")
    cleaned = df.copy()
    cleaned.replace(["N/A", "N/D", "n/a", "n/d", "", " "], pd.NA, inplace=True)

    print("[inventory] Converting FECHA_APERTURA, CANTIDAD_SOLICITADA, PRECIO_UNITARIO_ESTIMADO and CODIGO_IDENTIFICACION...")
    cleaned["FECHA_APERTURA"] = pd.to_datetime(
        cleaned["FECHA_APERTURA"],
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce",
    )
    cleaned["CANTIDAD_SOLICITADA"] = pd.to_numeric(cleaned["CANTIDAD_SOLICITADA"], errors="coerce")
    cleaned["PRECIO_UNITARIO_ESTIMADO"] = pd.to_numeric(cleaned["PRECIO_UNITARIO_ESTIMADO"], errors="coerce")
    cleaned["CODIGO_IDENTIFICACION"] = cleaned["CODIGO_IDENTIFICACION"].astype(str)

    cleaned = cleaned.dropna(
        subset=[
            "FECHA_APERTURA",
            "CODIGO_IDENTIFICACION",
            "DESCRIP_IDENTIFICACION",
            "CANTIDAD_SOLICITADA",
            "PRECIO_UNITARIO_ESTIMADO",
        ]
    )

    print(f"[inventory] Rows after dropna critical fields: {len(cleaned):,}")

    cleaned["ANIO"] = cleaned["FECHA_APERTURA"].dt.year
    print(f"[inventory] Available years after cleaning: {sorted(cleaned['ANIO'].dropna().astype(int).unique().tolist())}")
    return cleaned


def get_item_options(limit: int = 300) -> list[ItemOption]:
    df = _prepare_base(_read_contracts_base())
    print(f"[inventory] Building item options from {len(df):,} cleaned rows")
    grouped = (
        df.groupby(["CODIGO_IDENTIFICACION", "DESCRIP_IDENTIFICACION"])["CANTIDAD_SOLICITADA"]
        .sum()
        .reset_index()
        .sort_values("CANTIDAD_SOLICITADA", ascending=False)
        .head(limit)
    )

    options = []
    for _, row in grouped.iterrows():
        code = str(row["CODIGO_IDENTIFICACION"])
        desc = str(row["DESCRIP_IDENTIFICACION"]).strip()
        label = f"{code} - {desc[:95]}"
        options.append(ItemOption(code=code, label=label))

    print(f"[inventory] Generated {len(options):,} item options; first option: {options[0].label if options else 'NONE'}")
    return options


def get_available_years() -> list[int]:
    df = _prepare_base(_read_contracts_base())
    years = sorted(df["ANIO"].dropna().astype(int).unique().tolist())
    print(f"[inventory] Available years returned to form: {years}")
    return years


def get_item_available_years(item_code: str) -> list[int]:
    df = _prepare_base(_read_contracts_base())
    item_df = df[df["CODIGO_IDENTIFICACION"] == str(item_code)].copy()
    years = sorted(item_df["ANIO"].dropna().astype(int).unique().tolist())
    print(f"[inventory] Available years for item_code={item_code!r}: {years}")
    return years


def resolve_item_search(item_query: str) -> tuple[str, str]:
    normalized_query = str(item_query).strip()
    if not normalized_query:
        raise ValueError("Debes seleccionar un producto para calcular.")

    if " - " in normalized_query:
        item_code, item_label = normalized_query.split(" - ", 1)
        item_code = item_code.strip()
        item_label = item_label.strip()
    else:
        item_code = normalized_query
        item_label = normalized_query

    print(f"[inventory] Resolved search query -> item_query={item_query!r}, item_code={item_code!r}, item_label={item_label!r}")
    return item_code, item_label


def get_default_item_option() -> ItemOption | None:
    options = get_item_options(limit=1)
    return options[0] if options else None


def _inventory_costs(demand_annual: float, q: float, order_cost: float, holding_cost: float) -> tuple[float, float, float]:
    order_annual = (demand_annual / q) * order_cost
    hold_annual = (q / 2.0) * holding_cost
    total = order_annual + hold_annual
    return order_annual, hold_annual, total


def _build_saw_points(q_opt: float, reorder_point: float) -> str:
    # Four cycles in a fixed SVG canvas.
    x_step = 50
    base_x = 20
    top_y = 20
    bottom_y = 130

    points = []
    x = base_x
    for _ in range(4):
        points.append(f"{x},{top_y}")
        x += x_step
        points.append(f"{x},{bottom_y}")
    points.append(f"{x + 20},{bottom_y}")
    return " ".join(points)


def build_inventory_report(
    item_code: str,
    year: int,
    order_cost: float,
    holding_mode: str,
    holding_input: float,
    lead_time_days: float,
    work_days_year: int,
    include_safety_stock: bool,
    service_level: float,
) -> InventoryReport:
    df = _prepare_base(_read_contracts_base())
    print(f"[inventory] Building report for item_code={item_code!r}, year={year}")
    print(f"[inventory] Total cleaned rows available: {len(df):,}")
    item_df = df[(df["CODIGO_IDENTIFICACION"] == str(item_code)) & (df["ANIO"] == int(year))].copy()
    print(f"[inventory] Filtered rows for selected item/year: {len(item_df):,}")

    if not item_df.empty:
        print(f"[inventory] Filter sample - item codes: {item_df['CODIGO_IDENTIFICACION'].astype(str).head(5).tolist()}")
        print(f"[inventory] Filter sample - years: {item_df['ANIO'].head(5).tolist()}")
        print(f"[inventory] Filter sample - descriptions: {item_df['DESCRIP_IDENTIFICACION'].astype(str).head(3).tolist()}")

    if item_df.empty:
        item_years = get_item_available_years(item_code)
        print(f"[inventory] No rows for item/year combo. item_years={item_years}")
        print("[inventory] No rows matched the selected item/year. Raising ValueError.")
        if item_years:
            raise ValueError(
                f"No hay datos para el item/anio seleccionado. Años disponibles para este item: {item_years}"
            )
        raise ValueError("No hay datos para el item/anio seleccionado.")

    demand_annual = float(item_df["CANTIDAD_SOLICITADA"].sum())
    unit_cost_avg = float(item_df["PRECIO_UNITARIO_ESTIMADO"].mean())
    item_description = str(item_df["DESCRIP_IDENTIFICACION"].iloc[0])

    print(f"[inventory] Demand annual (D): {demand_annual}")
    print(f"[inventory] Average unit cost (C): {unit_cost_avg}")
    print(f"[inventory] Item description selected: {item_description}")

    if demand_annual <= 0:
        raise ValueError("La demanda anual calculada es cero. Selecciona otro item o anio.")

    if holding_mode == "percent":
        ratio = holding_input / 100.0 if holding_input > 1 else holding_input
        holding_cost = ratio * unit_cost_avg
        print(f"[inventory] Holding mode=percent, input={holding_input}, normalized ratio={ratio}, holding_cost={holding_cost}")
    else:
        holding_cost = holding_input
        print(f"[inventory] Holding mode=fixed, holding_cost={holding_cost}")

    if holding_cost <= 0:
        print("[inventory] Invalid holding_cost <= 0, raising ValueError.")
        raise ValueError("El costo de mantener debe ser mayor que cero.")

    # EOQ/CLE formula: Q* = sqrt((2*D*Co)/Ch)
    q_opt = math.sqrt((2.0 * demand_annual * order_cost) / holding_cost)
    print(f"[inventory] Q* computed: {q_opt}")

    annual_order_cost, annual_holding_cost, total_inventory_cost = _inventory_costs(
        demand_annual=demand_annual,
        q=q_opt,
        order_cost=order_cost,
        holding_cost=holding_cost,
    )

    print(f"[inventory] Annual order cost: {annual_order_cost}")
    print(f"[inventory] Annual holding cost: {annual_holding_cost}")
    print(f"[inventory] Total inventory cost: {total_inventory_cost}")

    orders_per_year = demand_annual / q_opt
    time_between_orders = work_days_year / orders_per_year
    print(f"[inventory] Orders per year: {orders_per_year}")
    print(f"[inventory] Time between orders (days): {time_between_orders}")

    daily_demand = demand_annual / work_days_year
    print(f"[inventory] Daily demand: {daily_demand}")

    safety_stock = 0.0
    if include_safety_stock:
        print("[inventory] Safety stock enabled; calculating sigma and Z value...")
        daily_series = (
            item_df.groupby(item_df["FECHA_APERTURA"].dt.date)["CANTIDAD_SOLICITADA"]
            .sum()
            .astype(float)
        )
        sigma_d = float(daily_series.std(ddof=1)) if len(daily_series) > 1 else 0.0
        z_value = float(norm.ppf(service_level))
        safety_stock = max(0.0, z_value * sigma_d * math.sqrt(lead_time_days))
        print(f"[inventory] sigma_d={sigma_d}, z_value={z_value}, safety_stock={safety_stock}")

    reorder_point = (daily_demand * lead_time_days) + safety_stock
    print(f"[inventory] Reorder point (ROP): {reorder_point}")

    comparison_rows = []
    for multiplier in [0.5, 0.75, 1.0, 1.25, 1.5]:
        q_test = max(0.0001, q_opt * multiplier)
        ord_cost, hold_cost, total_cost = _inventory_costs(
            demand_annual=demand_annual,
            q=q_test,
            order_cost=order_cost,
            holding_cost=holding_cost,
        )
        comparison_rows.append(
            {
                "label": f"{multiplier:.2f} x Q*",
                "q": q_test,
                "annual_order_cost": ord_cost,
                "annual_holding_cost": hold_cost,
                "total_cost": total_cost,
            }
        )
        print(f"[inventory] Comparison row {multiplier:.2f}x -> Q={q_test}, order={ord_cost}, hold={hold_cost}, total={total_cost}")

    print("[inventory] Inventory report completed successfully.")

    return InventoryReport(
        item_description=item_description,
        demand_annual=demand_annual,
        unit_cost_avg=unit_cost_avg,
        holding_cost_used=holding_cost,
        q_opt=q_opt,
        annual_order_cost=annual_order_cost,
        annual_holding_cost=annual_holding_cost,
        total_inventory_cost=total_inventory_cost,
        orders_per_year=orders_per_year,
        time_between_orders=time_between_orders,
        daily_demand=daily_demand,
        reorder_point=reorder_point,
        safety_stock=safety_stock,
        comparison_rows=comparison_rows,
        saw_points=_build_saw_points(q_opt=q_opt, reorder_point=reorder_point),
    )
