import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# 1. CARGAR DATOS MENSUALES
# ---------------------------------------------------------------------------
input_path = "data/processed/gasto_mensual.csv"

df = pd.read_csv(input_path)
df["PERIODO"] = pd.to_datetime(df["PERIODO"])
df = df.sort_values("PERIODO").reset_index(drop=True)

# Serie de tiempo principal: monto total mensual en CRC
demanda = df["MONTO_TOTAL_CRC"].values
periodos = df["PERIODO"].values
n = len(demanda)

print(f"Períodos disponibles: {n} meses ({df['PERIODO'].iloc[0].strftime('%Y-%m')} → "
      f"{df['PERIODO'].iloc[-1].strftime('%Y-%m')})\n")

# ---------------------------------------------------------------------------
# 2. MÉTODO 1 — PROMEDIO MÓVIL SUAVIZADO (ventana = 3)
# ---------------------------------------------------------------------------
VENTANA = 3  # Parámetro: número de períodos para el promedio móvil

pronostico_pm = np.full(n, np.nan)

# El pronóstico para el período t es el promedio de los 3 períodos anteriores
for t in range(VENTANA, n):
    pronostico_pm[t] = np.mean(demanda[t - VENTANA:t])

# Proyección de los 6 meses siguientes:
# Cada mes proyectado usa los últimos 3 valores conocidos (reales + proyectados)
proyeccion_pm = []
ultimos_valores = list(demanda[-VENTANA:])  # últimos 3 reales

for _ in range(6):
    siguiente = np.mean(ultimos_valores[-VENTANA:])
    proyeccion_pm.append(siguiente)
    ultimos_valores.append(siguiente)

print("=== PROMEDIO MÓVIL (ventana=3) — Pronósticos en período de prueba ===")
for t in range(VENTANA, n):
    error = demanda[t] - pronostico_pm[t]
    print(f"  {pd.Timestamp(periodos[t]).strftime('%Y-%m')} | "
          f"Real: {demanda[t]:>18,.0f} CRC | "
          f"Pronóstico: {pronostico_pm[t]:>18,.0f} CRC | "
          f"Error: {error:>+18,.0f}")

# ---------------------------------------------------------------------------
# 3. MÉTODO 2 — SUAVIZAMIENTO EXPONENCIAL SIMPLE (SES)
# ---------------------------------------------------------------------------
ALPHA = 0.3  # Parámetro de suavización: 0 < α < 1
             # α cercano a 1 = más peso a datos recientes
             # α cercano a 0 = más suavización / inercia

pronostico_ses = np.full(n, np.nan)

# Inicialización: el primer pronóstico es igual al primer valor real
pronostico_ses[0] = demanda[0]

# Fórmula SES: F(t) = α * D(t-1) + (1 - α) * F(t-1)
for t in range(1, n):
    pronostico_ses[t] = ALPHA * demanda[t - 1] + (1 - ALPHA) * pronostico_ses[t - 1]

# Proyección de los 6 meses siguientes:
# El último pronóstico se propaga hacia adelante aplicando la misma fórmula
f_ultimo = pronostico_ses[-1]
proyeccion_ses = []
d_ultimo = demanda[-1]

for _ in range(6):
    f_siguiente = ALPHA * d_ultimo + (1 - ALPHA) * f_ultimo
    proyeccion_ses.append(f_siguiente)
    d_ultimo = f_siguiente  # la proyección se trata como demanda en el siguiente paso
    f_ultimo = f_siguiente

print(f"\n=== SUAVIZAMIENTO EXPONENCIAL SIMPLE (α={ALPHA}) — Pronósticos ===")
for t in range(1, n):
    error = demanda[t] - pronostico_ses[t]
    print(f"  {pd.Timestamp(periodos[t]).strftime('%Y-%m')} | "
          f"Real: {demanda[t]:>18,.0f} CRC | "
          f"Pronóstico: {pronostico_ses[t]:>18,.0f} CRC | "
          f"Error: {error:>+18,.0f}")

# ---------------------------------------------------------------------------
# 4. FECHAS DE LAS PROYECCIONES (próximos 6 meses)
# ---------------------------------------------------------------------------
ultimo_periodo = df["PERIODO"].iloc[-1]
fechas_proyeccion = pd.date_range(
    start=ultimo_periodo + pd.DateOffset(months=1),
    periods=6,
    freq="MS"
)

# ---------------------------------------------------------------------------
# 5. IMPRIMIR PROYECCIONES
# ---------------------------------------------------------------------------
print("\n=== PROYECCIÓN — PRÓXIMOS 6 MESES ===")
print(f"{'Período':<12} {'Promedio Móvil (CRC)':>25} {'Exp. Simple (CRC)':>25}")
print("-" * 65)
for i, fecha in enumerate(fechas_proyeccion):
    print(f"{fecha.strftime('%Y-%m'):<12} "
          f"{proyeccion_pm[i]:>25,.0f} "
          f"{proyeccion_ses[i]:>25,.0f}")

# ---------------------------------------------------------------------------
# 6. EXPORTAR RESULTADOS PARA EL SCRIPT 03
# ---------------------------------------------------------------------------
# Tabla con reales vs. pronósticos (período de prueba, excluye inicialización)
inicio_pm  = VENTANA  # primer índice con pronóstico PM válido
inicio_ses = 1        # primer índice con pronóstico SES válido

# Usamos el rango común para comparar ambos métodos
inicio_comun = max(inicio_pm, inicio_ses)

resultados = pd.DataFrame({
    "PERIODO":         [pd.Timestamp(p).strftime("%Y-%m") for p in periodos[inicio_comun:]],
    "REAL":            demanda[inicio_comun:],
    "PRONOSTICO_PM":   pronostico_pm[inicio_comun:],
    "PRONOSTICO_SES":  pronostico_ses[inicio_comun:],
})
resultados["ERROR_PM"]  = resultados["REAL"] - resultados["PRONOSTICO_PM"]
resultados["ERROR_SES"] = resultados["REAL"] - resultados["PRONOSTICO_SES"]

output_resultados   = "data/processed/pronosticos_vs_real.csv"
resultados.to_csv(output_resultados, index=False)

# Tabla de proyecciones futuras
proyecciones = pd.DataFrame({
    "PERIODO":        [f.strftime("%Y-%m") for f in fechas_proyeccion],
    "PROYECCION_PM":  proyeccion_pm,
    "PROYECCION_SES": proyeccion_ses,
})
output_proyecciones = "data/processed/proyecciones_6_meses.csv"
proyecciones.to_csv(output_proyecciones, index=False)

print(f"\nArchivos guardados:")
print(f"  → {output_resultados}")
print(f"  → {output_proyecciones}")
print("\n✓ Script 02 completado.")
