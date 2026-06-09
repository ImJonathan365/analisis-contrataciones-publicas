from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from django.conf import settings
from scipy.optimize import linprog
from sqlalchemy import create_engine


@dataclass
class LinearProgramReport:
    year: int
    budget_cap: float
    allocation_target: float
    pymes_min_ratio: float
    institutional_min_ratio: float
    monthly_budget_rows: list[dict]
    cost_rows: list[dict]
    variable_rows: list[dict]
    sensitivity_rows: list[dict]
    objective_value: float
    status: str
    message: str


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
    print("[pl] Opening MySQL engine for linear programming module...")
    base_query = """
        SELECT
            FECHA_APERTURA,
            TIPO_PROCEDIMIENTO,
            INSTITUCION,
            PAGO_ADELANTADO_PYMES,
            PRECIO_UNITARIO_ESTIMADO,
            CANTIDAD_SOLICITADA,
            TIPO_MONEDA,
            TIPO_CAMBIO_USD
        FROM public_contracts
    """

    fallback_query = """
        SELECT
            FECHA_APERTURA,
            TIPO_PROCEDIMIENTO,
            INSTITUCION,
            PAGO_ADELANTADO_PYMES,
            PRECIO_UNITARIO_ESTIMADO,
            CANTIDAD_SOLICITADA,
            TIPO_MONEDA,
            TIPO_CAMBIO_USD
        FROM contrataciones_hacienda
    """

    try:
        print("[pl] Opening MySQL engine and reading public_contracts...")
        df = pd.read_sql(base_query, con=engine)
        print(f"[pl] Raw data loaded from public_contracts: rows={len(df):,}, columns={list(df.columns)}")
        return df
    except Exception:
        print("[pl] public_contracts query failed, trying contrataciones_hacienda...")
        df = pd.read_sql(fallback_query, con=engine)
        print(f"[pl] Raw data loaded from contrataciones_hacienda: rows={len(df):,}, columns={list(df.columns)}")
        return df


def _prepare_base(df: pd.DataFrame) -> pd.DataFrame:
    print(f"[pl] Preparing dataframe with initial rows={len(df):,}")
    cleaned = df.copy()
    cleaned.replace(["N/A", "N/D", "n/a", "n/d", "", " "], pd.NA, inplace=True)

    print("[pl] Converting FECHA_APERTURA, numeric columns, and categorical fields...")
    cleaned["FECHA_APERTURA"] = pd.to_datetime(
        cleaned["FECHA_APERTURA"],
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce",
    )
    cleaned["PRECIO_UNITARIO_ESTIMADO"] = pd.to_numeric(cleaned["PRECIO_UNITARIO_ESTIMADO"], errors="coerce")
    cleaned["CANTIDAD_SOLICITADA"] = pd.to_numeric(cleaned["CANTIDAD_SOLICITADA"], errors="coerce")
    cleaned["TIPO_CAMBIO_USD"] = pd.to_numeric(cleaned["TIPO_CAMBIO_USD"], errors="coerce").fillna(1)
    cleaned["TIPO_PROCEDIMIENTO"] = cleaned["TIPO_PROCEDIMIENTO"].astype(str).str.strip()
    cleaned["INSTITUCION"] = cleaned["INSTITUCION"].astype(str).str.strip()
    cleaned["PAGO_ADELANTADO_PYMES"] = cleaned["PAGO_ADELANTADO_PYMES"].astype(str).str.upper().str.strip()

    cleaned = cleaned.dropna(
        subset=[
            "FECHA_APERTURA",
            "TIPO_PROCEDIMIENTO",
            "INSTITUCION",
            "PRECIO_UNITARIO_ESTIMADO",
            "CANTIDAD_SOLICITADA",
        ]
    )
    print(f"[pl] Rows after critical dropna: {len(cleaned):,}")
    cleaned["ANIO"] = cleaned["FECHA_APERTURA"].dt.year.astype(int)
    cleaned["MONTO_CRC"] = cleaned["CANTIDAD_SOLICITADA"] * cleaned["PRECIO_UNITARIO_ESTIMADO"]
    usd_mask = cleaned["TIPO_MONEDA"].astype(str).str.upper().eq("USD")
    cleaned.loc[usd_mask, "MONTO_CRC"] = cleaned.loc[usd_mask, "MONTO_CRC"] * cleaned.loc[usd_mask, "TIPO_CAMBIO_USD"]
    print(f"[pl] Years available after cleaning: {sorted(cleaned['ANIO'].dropna().astype(int).unique().tolist())}")
    print(f"[pl] Total MONTO_CRC aggregated sample: {cleaned['MONTO_CRC'].head(5).tolist()}")
    return cleaned


def get_available_years() -> list[int]:
    df = _prepare_base(_read_contracts_base())
    years = sorted(df["ANIO"].dropna().astype(int).unique().tolist())
    print(f"[pl] Available years: {years}")
    return years


def _monthly_summary(df: pd.DataFrame, year: int) -> list[dict]:
    year_df = df[df["ANIO"] == year].copy()
    print(f"[pl] Building monthly summary for year={year}, rows={len(year_df):,}")
    monthly = (
        year_df
        .groupby(year_df["FECHA_APERTURA"].dt.to_period("M"))["MONTO_CRC"]
        .sum()
        .reset_index()
        .rename(columns={"FECHA_APERTURA": "PERIODO", "MONTO_CRC": "MONTO_TOTAL_CRC"})
        .sort_values("PERIODO")
    )
    monthly["PERIODO"] = monthly["PERIODO"].astype(str)
    print(f"[pl] Monthly summary rows: {monthly.to_dict('records')}")
    return monthly.to_dict("records")


def _build_category_frame(df: pd.DataFrame, year: int) -> pd.DataFrame:
    year_df = df[df["ANIO"] == year].copy()
    print(f"[pl] Building category frame for year={year}, rows={len(year_df):,}")
    total_by_type = year_df.groupby("TIPO_PROCEDIMIENTO")["MONTO_CRC"].sum().sort_values(ascending=False)
    print(f"[pl] Total by type before grouping: {total_by_type.to_dict()}")

    if total_by_type.empty:
        print("[pl] Category frame empty because total_by_type is empty.")
        return pd.DataFrame()

    top_types = total_by_type.head(6).index.tolist()
    print(f"[pl] Top procedure types selected: {top_types}")
    year_df["TIPO_GRUPO"] = np.where(year_df["TIPO_PROCEDIMIENTO"].isin(top_types), year_df["TIPO_PROCEDIMIENTO"], "OTROS")

    category = (
        year_df.groupby("TIPO_GRUPO")
        .agg(
            MONTO_TOTAL_CRC=("MONTO_CRC", "sum"),
            REGISTROS=("MONTO_CRC", "size"),
            PROMEDIO_MONTO=("MONTO_CRC", "mean"),
            PYMES_MONTO=("MONTO_CRC", lambda s: s[year_df.loc[s.index, "PAGO_ADELANTADO_PYMES"].eq("S")].sum()),
        )
        .reset_index()
    )
    print(f"[pl] Category base rows: {category.to_dict('records')}")

    key_institutions = (
        year_df.groupby("INSTITUCION")["MONTO_CRC"].sum().sort_values(ascending=False).head(5).index.tolist()
    )
    print(f"[pl] Key institutions selected for coverage: {key_institutions}")
    inst_coverage = (
        year_df.assign(ES_CLAVE=year_df["INSTITUCION"].isin(key_institutions))
        .groupby("TIPO_GRUPO")
        .apply(lambda g: float(g.loc[g["ES_CLAVE"], "MONTO_CRC"].sum()) / float(g["MONTO_CRC"].sum()) if float(g["MONTO_CRC"].sum()) else 0.0)
        .rename("COBERTURA_INSTITUCIONAL")
        .reset_index()
    )
    category = category.merge(inst_coverage, on="TIPO_GRUPO", how="left")

    global_mean = float(year_df["MONTO_CRC"].mean()) if not year_df.empty else 1.0
    category["COEF_OBJETIVO"] = category["PROMEDIO_MONTO"] / global_mean if global_mean else 1.0
    category["PYMES_RATIO"] = category["PYMES_MONTO"] / category["MONTO_TOTAL_CRC"].replace(0, np.nan)
    category["PYMES_RATIO"] = category["PYMES_RATIO"].fillna(0.0)
    category["PYMES_RATIO"] = category["PYMES_RATIO"].clip(lower=0.0, upper=1.0)
    category["COBERTURA_INSTITUCIONAL"] = category["COBERTURA_INSTITUCIONAL"].fillna(0.0).clip(lower=0.0, upper=1.0)
    category["TIPO_GRUPO"] = category["TIPO_GRUPO"].astype(str)
    print(f"[pl] Category frame final rows: {category.to_dict('records')}")
    return category.sort_values("MONTO_TOTAL_CRC", ascending=False).reset_index(drop=True)


def build_linear_programming_report(
    year: int,
    allocation_use_percent: float,
    pymes_min_percent: float,
    institutional_min_percent: float,
) -> LinearProgramReport:
    df = _prepare_base(_read_contracts_base())
    year_df = df[df["ANIO"] == int(year)].copy()
    print(f"[pl] Starting report build for year={year}")
    print(f"[pl] Total cleaned rows available={len(df):,}, rows for selected year={len(year_df):,}")
    if year_df.empty:
        raise ValueError("No hay datos disponibles para el anio seleccionado.")

    budget_cap = float(year_df["MONTO_CRC"].sum())
    allocation_target = budget_cap * (allocation_use_percent / 100.0)
    pymes_min_ratio = pymes_min_percent / 100.0
    institutional_min_ratio = institutional_min_percent / 100.0

    print(f"[pl] Budget cap={budget_cap}")
    print(f"[pl] Allocation target={allocation_target} ({allocation_use_percent}%)")
    print(f"[pl] PYMES min ratio={pymes_min_ratio}")
    print(f"[pl] Institutional min ratio={institutional_min_ratio}")

    monthly_budget_rows = _monthly_summary(df, year)
    category = _build_category_frame(df, year)
    if category.empty:
        raise ValueError("No se pudieron construir categorias para el modelo de PL.")

    print(f"[pl] Category dataframe columns={list(category.columns)}")
    print(f"[pl] Category dataframe size={len(category):,}")

    var_names = category["TIPO_GRUPO"].tolist()
    c = category["COEF_OBJETIVO"].to_numpy(dtype=float)
    pymes_share = category["PYMES_RATIO"].to_numpy(dtype=float)
    inst_share = category["COBERTURA_INSTITUCIONAL"].to_numpy(dtype=float)
    n = len(var_names)
    max_pymes_ratio = float(np.max(pymes_share)) if len(pymes_share) else 0.0
    max_inst_ratio = float(np.max(inst_share)) if len(inst_share) else 0.0

    print(f"[pl] Year={year}, budget_cap={budget_cap}, allocation_target={allocation_target}")
    print(f"[pl] Categories used in model: {var_names}")
    print(f"[pl] Objective coefficients: {c.tolist()}")
    print(f"[pl] PYMES shares: {pymes_share.tolist()}")
    print(f"[pl] Institutional shares: {inst_share.tolist()}")
    print(f"[pl] Max feasible PYMES ratio in year/category set: {max_pymes_ratio}")
    print(f"[pl] Max feasible institutional ratio in year/category set: {max_inst_ratio}")
    print(f"[pl] PYMES min threshold compare: min={pymes_share.min() if len(pymes_share) else 'NA'}, max={pymes_share.max() if len(pymes_share) else 'NA'}")
    print(f"[pl] Institutional min threshold compare: min={inst_share.min() if len(inst_share) else 'NA'}, max={inst_share.max() if len(inst_share) else 'NA'}")

    if len(pymes_share):
        print(f"[pl] PYMES feasibility quick check -> any share >= min? {bool((pymes_share >= pymes_min_ratio).any())}")
    if len(inst_share):
        print(f"[pl] Institutional feasibility quick check -> any share >= min? {bool((inst_share >= institutional_min_ratio).any())}")

    if pymes_min_ratio > max_pymes_ratio + 1e-12:
        raise ValueError(
            "Modelo inviable: la cuota minima PYMES solicitada excede el maximo historico posible "
            f"para el anio/categorias seleccionados. Solicitado={pymes_min_ratio:.4f}, maximo={max_pymes_ratio:.4f}."
        )

    if institutional_min_ratio > max_inst_ratio + 1e-12:
        raise ValueError(
            "Modelo inviable: la cuota minima institucional solicitada excede el maximo historico posible "
            f"para el anio/categorias seleccionados. Solicitado={institutional_min_ratio:.4f}, maximo={max_inst_ratio:.4f}."
        )

    a_ub = [
        np.ones(n, dtype=float),
        -np.ones(n, dtype=float),
        -(pymes_share - pymes_min_ratio),
        -(inst_share - institutional_min_ratio),
    ]
    b_ub = [budget_cap, -allocation_target, 0.0, 0.0]

    print(f"[pl] A_ub matrix: {np.vstack(a_ub).tolist()}")
    print(f"[pl] b_ub vector: {b_ub}")
    print(f"[pl] Bounds: {[(0, None)] * n}")

    res = linprog(c=c, A_ub=np.vstack(a_ub), b_ub=np.array(b_ub, dtype=float), bounds=[(0, None)] * n, method="highs")
    print(f"[pl] linprog success={res.success}, status={res.status}, message={res.message}")
    print(f"[pl] Solver raw x={getattr(res, 'x', None)}")
    print(f"[pl] Solver raw fun={getattr(res, 'fun', None)}")
    if hasattr(res, 'ineqlin'):
        print(f"[pl] Solver residuals={getattr(res.ineqlin, 'residual', None)}")
        print(f"[pl] Solver marginals={getattr(res.ineqlin, 'marginals', None)}")

    if not res.success:
        print("[pl] Model infeasible or not solved. Dumping diagnostic summary before raising error.")
        print(f"[pl] Diagnostic -> budget_cap={budget_cap}, allocation_target={allocation_target}, pymes_min_ratio={pymes_min_ratio}, institutional_min_ratio={institutional_min_ratio}")
        print(f"[pl] Diagnostic -> var_names={var_names}")
        print(f"[pl] Diagnostic -> c={c.tolist()}")
        print(f"[pl] Diagnostic -> pymes_share={pymes_share.tolist()}")
        print(f"[pl] Diagnostic -> inst_share={inst_share.tolist()}")
        raise ValueError(f"No fue posible resolver el modelo de PL: {res.message}")

    x = res.x
    objective_value = float(res.fun)
    residuals = np.array(res.ineqlin.residual, dtype=float)
    marginals = np.array(res.ineqlin.marginals, dtype=float)
    print(f"[pl] Objective value={objective_value}")
    print(f"[pl] Optimal x={x.tolist()}")
    print(f"[pl] Residuals={residuals.tolist()}")
    print(f"[pl] Marginals={marginals.tolist()}")

    variable_rows = []
    for idx, name in enumerate(var_names):
        variable_rows.append(
            {
                "variable": name,
                "valor_optimo": float(x[idx]),
                "coef_objetivo": float(c[idx]),
            }
        )

    constraint_rows = [
        {
            "restriccion": "Presupuesto historico maximo",
            "tipo": "<=",
            "rhs": budget_cap,
            "lhs": float(np.dot(np.ones(n), x)),
            "estado": "Activa" if abs(residuals[0]) < 1e-7 else "Inactiva",
            "holgura_excedente": float(residuals[0]),
            "precio_sombra": float(-marginals[0]),
        },
        {
            "restriccion": "Asignacion minima del presupuesto",
            "tipo": ">=",
            "rhs": allocation_target,
            "lhs": float(np.dot(np.ones(n), x)),
            "estado": "Activa" if abs(residuals[1]) < 1e-7 else "Inactiva",
            "holgura_excedente": float(residuals[1]),
            "precio_sombra": float(-marginals[1]),
        },
        {
            "restriccion": "Cuota minima PYMES",
            "tipo": ">=",
            "rhs": 0.0,
            "lhs": float(np.dot((pymes_share - pymes_min_ratio), x)),
            "estado": "Activa" if abs(residuals[2]) < 1e-7 else "Inactiva",
            "holgura_excedente": float(residuals[2]),
            "precio_sombra": float(-marginals[2]),
        },
        {
            "restriccion": "Cobertura minima instituciones clave",
            "tipo": ">=",
            "rhs": 0.0,
            "lhs": float(np.dot((inst_share - institutional_min_ratio), x)),
            "estado": "Activa" if abs(residuals[3]) < 1e-7 else "Inactiva",
            "holgura_excedente": float(residuals[3]),
            "precio_sombra": float(-marginals[3]),
        },
    ]

    cost_rows = category[["TIPO_GRUPO", "MONTO_TOTAL_CRC", "REGISTROS", "PROMEDIO_MONTO", "COEF_OBJETIVO", "PYMES_RATIO", "COBERTURA_INSTITUCIONAL"]].copy()
    cost_rows.rename(
        columns={
            "TIPO_GRUPO": "tipo_procedimiento",
            "MONTO_TOTAL_CRC": "monto_historico_crc",
            "REGISTROS": "registros",
            "PROMEDIO_MONTO": "promedio_monto_crc",
            "COEF_OBJETIVO": "coef_objetivo",
            "PYMES_RATIO": "pymes_ratio",
            "COBERTURA_INSTITUCIONAL": "cobertura_institucional",
        },
        inplace=True,
    )

    print(f"[pl] Variable rows: {variable_rows}")
    print(f"[pl] Sensitivity rows: {constraint_rows}")
    print(f"[pl] Cost rows count={len(cost_rows):,}")

    return LinearProgramReport(
        year=year,
        budget_cap=budget_cap,
        allocation_target=allocation_target,
        pymes_min_ratio=pymes_min_ratio,
        institutional_min_ratio=institutional_min_ratio,
        monthly_budget_rows=monthly_budget_rows,
        cost_rows=cost_rows.to_dict("records"),
        variable_rows=variable_rows,
        sensitivity_rows=constraint_rows,
        objective_value=objective_value,
        status="Optimo" if res.success else "No resuelto",
        message=res.message,
    )
