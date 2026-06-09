import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# 1. CARGAR RESULTADOS DEL SCRIPT 02
# ---------------------------------------------------------------------------
df = pd.read_csv("data/processed/pronosticos_vs_real.csv")

periodos    = df["PERIODO"].values
real        = df["REAL"].values
error_pm    = df["ERROR_PM"].values     # Real - Pronóstico (Promedio Móvil)
error_ses   = df["ERROR_SES"].values    # Real - Pronóstico (Exp. Simple)
n           = len(df)

# ---------------------------------------------------------------------------
# 2. FUNCIÓN DE CÁLCULO PASO A PASO
# ---------------------------------------------------------------------------

def calcular_tracking_signal(errores: np.ndarray, periodos: np.ndarray) -> pd.DataFrame:
    """
    Calcula MAD, RSFE y Señal de Rastreo acumulados período a período.

    Parámetros:
        errores  : array de errores (Real - Pronóstico) por período
        periodos : array de etiquetas de período (strings)

    Retorna:
        DataFrame con columnas: PERIODO, ERROR, ABS_ERROR, RSFE, MAD, TS
    """
    registros = []
    rsfe_acum  = 0.0
    sum_abs    = 0.0

    for t, (periodo, e) in enumerate(zip(periodos, errores), start=1):
        rsfe_acum += e
        sum_abs   += abs(e)
        mad        = sum_abs / t
        ts         = rsfe_acum / mad if mad != 0 else 0.0

        registros.append({
            "PERIODO":    periodo,
            "REAL":       real[t - 1],
            "ERROR":      e,
            "ABS_ERROR":  abs(e),
            "RSFE":       rsfe_acum,
            "MAD":        mad,
            "TS":         ts,
            "SESGO":      "⚠ SESGO" if abs(ts) >= 4 else "✓ OK",
        })

    return pd.DataFrame(registros)

# ---------------------------------------------------------------------------
# 3. CALCULAR PARA PROMEDIO MÓVIL
# ---------------------------------------------------------------------------
ts_pm = calcular_tracking_signal(error_pm, periodos)

print("=" * 90)
print("SEÑAL DE RASTREO — PROMEDIO MÓVIL SUAVIZADO")
print("=" * 90)
print(f"{'Período':<10} {'Real':>20} {'Error':>18} {'|Error|':>15} "
      f"{'RSFE':>18} {'MAD':>15} {'TS':>8} {'Estado':>10}")
print("-" * 90)
for _, row in ts_pm.iterrows():
    print(f"{row['PERIODO']:<10} "
          f"{row['REAL']:>20,.0f} "
          f"{row['ERROR']:>+18,.0f} "
          f"{row['ABS_ERROR']:>15,.0f} "
          f"{row['RSFE']:>+18,.0f} "
          f"{row['MAD']:>15,.0f} "
          f"{row['TS']:>8.2f} "
          f"{row['SESGO']:>10}")

mad_final_pm  = ts_pm["MAD"].iloc[-1]
rsfe_final_pm = ts_pm["RSFE"].iloc[-1]
ts_final_pm   = ts_pm["TS"].iloc[-1]

print(f"\nRESUMEN FINAL — Promedio Móvil:")
print(f"  MAD  = {mad_final_pm:,.0f} CRC")
print(f"  RSFE = {rsfe_final_pm:+,.0f} CRC")
print(f"  TS   = {ts_final_pm:.4f}  →  {'⚠ SESGO DETECTADO (|TS| ≥ 4)' if abs(ts_final_pm) >= 4 else '✓ Modelo bajo control (|TS| < 4)'}")

# ---------------------------------------------------------------------------
# 4. CALCULAR PARA SUAVIZAMIENTO EXPONENCIAL SIMPLE
# ---------------------------------------------------------------------------
ts_ses = calcular_tracking_signal(error_ses, periodos)

print("\n" + "=" * 90)
print("SEÑAL DE RASTREO — SUAVIZAMIENTO EXPONENCIAL SIMPLE")
print("=" * 90)
print(f"{'Período':<10} {'Real':>20} {'Error':>18} {'|Error|':>15} "
      f"{'RSFE':>18} {'MAD':>15} {'TS':>8} {'Estado':>10}")
print("-" * 90)
for _, row in ts_ses.iterrows():
    print(f"{row['PERIODO']:<10} "
          f"{row['REAL']:>20,.0f} "
          f"{row['ERROR']:>+18,.0f} "
          f"{row['ABS_ERROR']:>15,.0f} "
          f"{row['RSFE']:>+18,.0f} "
          f"{row['MAD']:>15,.0f} "
          f"{row['TS']:>8.2f} "
          f"{row['SESGO']:>10}")

mad_final_ses  = ts_ses["MAD"].iloc[-1]
rsfe_final_ses = ts_ses["RSFE"].iloc[-1]
ts_final_ses   = ts_ses["TS"].iloc[-1]

print(f"\nRESUMEN FINAL — Suavizamiento Exponencial Simple:")
print(f"  MAD  = {mad_final_ses:,.0f} CRC")
print(f"  RSFE = {rsfe_final_ses:+,.0f} CRC")
print(f"  TS   = {ts_final_ses:.4f}  →  {'⚠ SESGO DETECTADO (|TS| ≥ 4)' if abs(ts_final_ses) >= 4 else '✓ Modelo bajo control (|TS| < 4)'}")

# ---------------------------------------------------------------------------
# 5. COMPARACIÓN ENTRE MODELOS
# ---------------------------------------------------------------------------
print("\n" + "=" * 55)
print("COMPARACIÓN DE PRECISIÓN ENTRE MODELOS")
print("=" * 55)
print(f"{'Métrica':<30} {'Prom. Móvil':>12} {'Exp. Simple':>12}")
print("-" * 55)
print(f"{'MAD final (CRC)':<30} {mad_final_pm:>12,.0f} {mad_final_ses:>12,.0f}")
print(f"{'RSFE final (CRC)':<30} {rsfe_final_pm:>+12,.0f} {rsfe_final_ses:>+12,.0f}")
print(f"{'Señal de Rastreo (TS)':<30} {ts_final_pm:>12.4f} {ts_final_ses:>12.4f}")
mejor_mad = "Prom. Móvil" if mad_final_pm < mad_final_ses else "Exp. Simple"
print(f"\n  Modelo más preciso (menor MAD): {mejor_mad}")

# ---------------------------------------------------------------------------
# 6. EXPORTAR TABLAS DE CONTROL
# ---------------------------------------------------------------------------
output_pm  = "data/processed/tracking_signal_pm.csv"
output_ses = "data/processed/tracking_signal_ses.csv"

ts_pm.to_csv(output_pm, index=False)
ts_ses.to_csv(output_ses, index=False)

print(f"\nArchivos guardados:")
print(f"  → {output_pm}")
print(f"  → {output_ses}")
print("\n✓ Script 03 completado.")
