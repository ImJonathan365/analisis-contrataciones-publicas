from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from django.conf import settings
from sqlalchemy import create_engine


@dataclass
class ForecastResult:
    monthly_series: pd.DataFrame
    detail_table: pd.DataFrame
    kpis: dict
    out_of_control: bool


def _fetch_base_data() -> pd.DataFrame:
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
    engine = create_engine(connection_string)

    query = """
        SELECT
            FECHA_APERTURA,
            CANTIDAD_SOLICITADA,
            PRECIO_UNITARIO_ESTIMADO,
            TIPO_MONEDA,
            TIPO_CAMBIO_USD
        FROM public_contracts
    """
    df = pd.read_sql(query, con=engine)
    return df


def _prepare_monthly_series(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.replace(["N/A", "N/D", "n/a", "n/d", "", " "], pd.NA, inplace=True)

    cleaned["FECHA_APERTURA"] = pd.to_datetime(
        cleaned["FECHA_APERTURA"],
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce",
    )
    cleaned = cleaned.dropna(subset=["FECHA_APERTURA"])

    cleaned["CANTIDAD_SOLICITADA"] = pd.to_numeric(cleaned["CANTIDAD_SOLICITADA"], errors="coerce").fillna(0)
    cleaned["PRECIO_UNITARIO_ESTIMADO"] = pd.to_numeric(cleaned["PRECIO_UNITARIO_ESTIMADO"], errors="coerce").fillna(0)
    cleaned["TIPO_CAMBIO_USD"] = pd.to_numeric(cleaned["TIPO_CAMBIO_USD"], errors="coerce").fillna(1)

    cleaned["GASTO_CRC"] = cleaned["CANTIDAD_SOLICITADA"] * cleaned["PRECIO_UNITARIO_ESTIMADO"]
    usd_mask = cleaned["TIPO_MONEDA"].astype(str).str.upper().eq("USD")
    cleaned.loc[usd_mask, "GASTO_CRC"] = cleaned.loc[usd_mask, "GASTO_CRC"] * cleaned.loc[usd_mask, "TIPO_CAMBIO_USD"]

    monthly = (
        cleaned.groupby(cleaned["FECHA_APERTURA"].dt.to_period("M"))["GASTO_CRC"]
        .sum()
        .reset_index()
        .rename(columns={"FECHA_APERTURA": "PERIODO", "GASTO_CRC": "REAL"})
        .sort_values("PERIODO")
        .reset_index(drop=True)
    )
    monthly["PERIODO"] = monthly["PERIODO"].astype(str)
    return monthly


def _simple_moving_average(values: np.ndarray, window: int) -> np.ndarray:
    result = np.full(len(values), np.nan)
    for idx in range(window, len(values)):
        result[idx] = values[idx - window:idx].mean()
    return result


def _weighted_moving_average(values: np.ndarray, weights: Iterable[float]) -> np.ndarray:
    raw_weights = np.array(list(weights), dtype=float)
    normalized = raw_weights / raw_weights.sum()
    window = len(normalized)

    result = np.full(len(values), np.nan)
    for idx in range(window, len(values)):
        segment = values[idx - window:idx]
        recent_first = segment[::-1]
        result[idx] = float(np.dot(recent_first, normalized))
    return result


def _simple_exponential_smoothing(values: np.ndarray, alpha: float) -> np.ndarray:
    result = np.full(len(values), np.nan)
    if len(values) == 0:
        return result
    result[0] = values[0]
    for idx in range(1, len(values)):
        result[idx] = result[idx - 1] + alpha * (values[idx - 1] - result[idx - 1])
    return result


def _compute_metrics(real: pd.Series, forecast: pd.Series) -> tuple[pd.Series, dict]:
    errors = real - forecast
    abs_errors = errors.abs()

    # Evita division por cero en MAPE para periodos con valor real 0.
    safe_real = real.replace(0, np.nan)
    ape = (abs_errors / safe_real) * 100

    metrics = {
        "mad": float(abs_errors.mean()),
        "mse": float((errors**2).mean()),
        "mape": float(ape.mean(skipna=True)),
        "bias": float(errors.mean()),
    }
    return errors, metrics


def _tracking_signal(errors: pd.Series) -> pd.Series:
    rsfe = errors.cumsum()
    mad_dynamic = errors.abs().expanding().mean()
    return rsfe / mad_dynamic.replace(0, np.nan)


def build_forecast_report(window: int, weights: list[float], alpha: float) -> ForecastResult:
    base_df = _fetch_base_data()
    monthly = _prepare_monthly_series(base_df)

    values = monthly["REAL"].to_numpy(dtype=float)
    monthly["F_PMS"] = _simple_moving_average(values, window)
    monthly["F_PMP"] = _weighted_moving_average(values, weights)
    monthly["F_SES"] = _simple_exponential_smoothing(values, alpha)

    detail = monthly.copy()
    detail["ERROR_PMS"], pms_metrics = _compute_metrics(detail["REAL"], detail["F_PMS"])
    detail["ERROR_PMP"], pmp_metrics = _compute_metrics(detail["REAL"], detail["F_PMP"])
    detail["ERROR_SES"], ses_metrics = _compute_metrics(detail["REAL"], detail["F_SES"])

    # SCEP/RSFE y Senal de Rastreo para SES como metodo base de control.
    detail["SCEP"] = detail["ERROR_SES"].fillna(0).cumsum()
    detail["DMA"] = detail["ERROR_SES"].abs().expanding().mean()
    detail["TS"] = _tracking_signal(detail["ERROR_SES"].fillna(0))

    last_ts = float(detail["TS"].dropna().iloc[-1]) if not detail["TS"].dropna().empty else 0.0
    out_of_control = abs(last_ts) > 4

    kpis = {
        "pms": pms_metrics,
        "pmp": pmp_metrics,
        "ses": ses_metrics,
        "last_ts": last_ts,
        "limit": 4.0,
    }

    return ForecastResult(
        monthly_series=monthly,
        detail_table=detail,
        kpis=kpis,
        out_of_control=out_of_control,
    )
