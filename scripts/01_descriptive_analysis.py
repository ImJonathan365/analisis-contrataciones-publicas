import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 1. CONEXIÓN A MYSQL
# ---------------------------------------------------------------------------
load_dotenv()

db_user     = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host     = os.getenv("DB_HOST", "127.0.0.1")
db_port     = os.getenv("DB_PORT", "3306")
db_name     = os.getenv("DB_NAME")

connection_string = (
    f"mysql+mysqldb://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)
engine = create_engine(connection_string)

print("Cargando datos desde MySQL...")
df = pd.read_sql("SELECT * FROM public_contracts", con=engine)
print(f"  → {len(df):,} filas cargadas.\n")

# ---------------------------------------------------------------------------
# 2. LIMPIEZA DE DATOS
# ---------------------------------------------------------------------------

# 2a. Reemplazar cadenas 'N/A' y 'N/D' por NaN real en todo el DataFrame
df.replace(["N/A", "N/D", "n/a", "n/d", "", " "], pd.NA, inplace=True)

# 2b. Eliminar filas sin institución, sin fecha de invitación o sin precio
filas_antes = len(df)
df.dropna(subset=["INSTITUCION", "FECHA_INVITACION", "PRECIO_UNITARIO_ESTIMADO"], inplace=True)
filas_despues = len(df)
print(f"Filas eliminadas por valores nulos críticos: {filas_antes - filas_despues:,}")

# 2c. Convertir fechas (formato: 'dd/mm/yyyy HH:MM:SS')
df["FECHA_INVITACION"] = pd.to_datetime(
    df["FECHA_INVITACION"], format="%d/%m/%Y %H:%M:%S", errors="coerce"
)
df.dropna(subset=["FECHA_INVITACION"], inplace=True)

# 2d. Asegurar tipos numéricos
df["CANTIDAD_SOLICITADA"]       = pd.to_numeric(df["CANTIDAD_SOLICITADA"], errors="coerce").fillna(0)
df["PRECIO_UNITARIO_ESTIMADO"]  = pd.to_numeric(df["PRECIO_UNITARIO_ESTIMADO"], errors="coerce").fillna(0)
df["TIPO_CAMBIO_USD"]           = pd.to_numeric(df["TIPO_CAMBIO_USD"], errors="coerce").fillna(1)

# ---------------------------------------------------------------------------
# 3. CÁLCULO DEL MONTO ESTIMADO EN CRC
# ---------------------------------------------------------------------------
# El dataset no contiene monto devengado directo; se estima como:
#   MONTO_CRC = CANTIDAD_SOLICITADA × PRECIO_UNITARIO_ESTIMADO
# Si la moneda es USD, se convierte a CRC multiplicando por TIPO_CAMBIO_USD.

df["MONTO_ESTIMADO_CRC"] = df["CANTIDAD_SOLICITADA"] * df["PRECIO_UNITARIO_ESTIMADO"]

mask_usd = df["TIPO_MONEDA"].str.upper() == "USD"
df.loc[mask_usd, "MONTO_ESTIMADO_CRC"] = (
    df.loc[mask_usd, "MONTO_ESTIMADO_CRC"] * df.loc[mask_usd, "TIPO_CAMBIO_USD"]
)

# ---------------------------------------------------------------------------
# 4. COLUMNAS DE PERÍODO
# ---------------------------------------------------------------------------
df["ANIO"]     = df["FECHA_INVITACION"].dt.year
df["MES"]      = df["FECHA_INVITACION"].dt.month
df["PERIODO"]  = df["FECHA_INVITACION"].dt.to_period("M")  # e.g. 2022-03

# ---------------------------------------------------------------------------
# 5. MÉTRICAS: GASTO TOTAL POR MES/AÑO
# ---------------------------------------------------------------------------
gasto_mensual = (
    df.groupby("PERIODO")
    .agg(
        MONTO_TOTAL_CRC=("MONTO_ESTIMADO_CRC", "sum"),
        CONTRATOS_DISTINTOS=("NRO_PROCEDIMIENTO", "nunique"),
        LINEAS_TOTALES=("NUMERO_LINEA", "count"),
    )
    .reset_index()
    .sort_values("PERIODO")
)

gasto_mensual["PERIODO"] = gasto_mensual["PERIODO"].astype(str)

print("\n=== GASTO ESTIMADO MENSUAL (CRC) ===")
print(gasto_mensual.to_string(index=False))

# ---------------------------------------------------------------------------
# 6. MÉTRICAS: VOLUMEN DE CONTRATOS POR INSTITUCIÓN
# ---------------------------------------------------------------------------
volumen_institucion = (
    df.groupby("INSTITUCION")
    .agg(
        MONTO_TOTAL_CRC=("MONTO_ESTIMADO_CRC", "sum"),
        CONTRATOS_DISTINTOS=("NRO_PROCEDIMIENTO", "nunique"),
    )
    .reset_index()
    .sort_values("MONTO_TOTAL_CRC", ascending=False)
)

print("\n=== TOP 20 INSTITUCIONES POR MONTO ESTIMADO (CRC) ===")
print(volumen_institucion.head(20).to_string(index=False))

# ---------------------------------------------------------------------------
# 7. MÉTRICAS: VOLUMEN POR TIPO DE PROCEDIMIENTO
# ---------------------------------------------------------------------------
volumen_tipo = (
    df.groupby("TIPO_PROCEDIMIENTO")
    .agg(
        MONTO_TOTAL_CRC=("MONTO_ESTIMADO_CRC", "sum"),
        CONTRATOS_DISTINTOS=("NRO_PROCEDIMIENTO", "nunique"),
    )
    .reset_index()
    .sort_values("MONTO_TOTAL_CRC", ascending=False)
)

print("\n=== GASTO POR TIPO DE PROCEDIMIENTO ===")
print(volumen_tipo.to_string(index=False))

# ---------------------------------------------------------------------------
# 8. EXPORTAR DATOS LIMPIOS PARA LOS SCRIPTS SIGUIENTES
# ---------------------------------------------------------------------------
output_mensual = "data/processed/gasto_mensual.csv"
output_limpio  = "data/processed/contratos_limpios.csv"

gasto_mensual.to_csv(output_mensual, index=False)
df.to_csv(output_limpio, index=False)

print(f"\nArchivos guardados:")
print(f"  → {output_mensual}")
print(f"  → {output_limpio}")
print("\n✓ Script 01 completado.")
