# Análisis y Pronóstico de las Contrataciones Públicas en Costa Rica mediante Métodos Cuantitativos

Este repositorio contiene el sistema web desarrollado en **Python** utilizando el framework **Django** para el proyecto final del curso *IF7200 Métodos Cuantitativos para la Toma de Decisiones*, correspondiente al I Semestre 2026 en la Universidad de Costa Rica (Sede del Atlántico, Recinto de Guápiles).

El sistema automatiza el procesamiento, análisis y optimización matemática de los datos abiertos proporcionados por el Ministerio de Hacienda de Costa Rica sobre los procesos de contratación pública durante el periodo 2022-2024.

## 👥 Integrantes y Dedicación

| Nombre | Carné | Dedicación |
|---|---|---|
| Jonathan Moreno Fajardo | C35380 | [Insertar horas] horas |
| Luis Rivera López | C36589 | [Insertar horas] horas |

**Docente:** Licda. Yorleni Umaña Ávila

---

## 🚀 Módulos del Sistema

El sistema está organizado en cuatro módulos independientes dentro de `apps/`:

### 1. `contracts/` — Contratos y Análisis Descriptivo
Carga masiva del CSV del Ministerio de Hacienda (hasta 82 MB con Pandas eficiente), tratamiento de valores nulos e inconsistentes (`N/D`), y generación de métricas como gasto total por periodo, distribución por institución y tipos de licitación. Incluye comandos Django personalizados para la importación de datos.

### 2. `forecasting/` — Pronósticos y Señal de Rastreo
Modelos de series temporales sobre el gasto mensual agregado:
- **Promedio Móvil Suavizado** y **Suavizamiento Exponencial Simple** con proyección a 6 meses.
- Evaluación de precisión paso a paso: MAD (Desviación Media Absoluta), RSFE (Error Acumulado) y **Señal de Rastreo** para detección de sesgo matemático.

### 3. `inventory/` — Control de Inventarios
Simulación de la demanda de adquisiciones públicas mediante el modelo de **Lote Económico de Pedido (EOQ)**, cálculo de costos de mantenimiento y pedido, y puntos de reorden (ROP).

### 4. `optimization/` — Programación Lineal
Formulación y resolución de modelos de optimización con `SciPy` / `PuLP` para maximizar el impacto social del presupuesto o minimizar los costos totales de adquisición.

---

## 🛠️ Tecnologías Utilizadas

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Framework Web | Django 5.0+ |
| Análisis de Datos | Pandas, NumPy |
| Optimización | SciPy / PuLP |
| Base de Datos | SQLite (desarrollo local) |

---

## ⚙️ Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone https://github.com/ImJonathan365/analisis-contrataciones-publicas.git
cd analisis-contrataciones-publicas
```

### 2. Crear y activar el entorno virtual
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Colocar el archivo de datos
Ubica el archivo CSV del Ministerio de Hacienda en:
```
data/raw/<nombre-del-archivo>.csv
```

### 5. Aplicar migraciones y ejecutar el servidor
```bash
python manage.py migrate
python manage.py runserver
```

---

## 📦 Estructura del Repositorio

```text
analisis-contrataciones-publicas/
│
├── apps/                           # Módulos de la aplicación Django
│   ├── common/
│   │   └── utils/                  # Utilidades compartidas entre módulos
│   │
│   ├── contracts/                  # Módulo: análisis descriptivo y limpieza
│   │   ├── management/
│   │   │   └── commands/           # Comandos Django para importación masiva de datos
│   │   ├── services/               # Lógica de limpieza y cálculo de métricas
│   │   └── tests/
│   │
│   ├── forecasting/                # Módulo: pronósticos y señal de rastreo
│   │   ├── services/               # Promedio Móvil, Exp. Simple, MAD, RSFE
│   │   └── tests/
│   │
│   ├── inventory/                  # Módulo: control de inventarios (EOQ, ROP)
│   │   ├── services/
│   │   └── tests/
│   │
│   └── optimization/               # Módulo: programación lineal
│       ├── services/               # Modelos de optimización con SciPy/PuLP
│       └── tests/
│
├── config/                         # Configuración global del proyecto Django
│                                   # (settings.py, urls.py, wsgi.py)
│
├── data/
│   ├── raw/                        # Archivo CSV original (no versionado en git)
│   └── processed/                  # Datos procesados y limpios
│
├── docs/                           # Documentación adicional del proyecto
│
├── scripts/                        # Scripts de análisis independiente (exploración)
│
├── static/
│   ├── css/
│   └── js/
│
├── templates/                      # Plantillas HTML del sistema web
│
├── manage.py                       # Comando de administración de Django
├── requirements.txt                # Dependencias del proyecto
├── .gitignore
└── README.md
```

---

## 📊 Fuente de Datos

**Ministerio de Hacienda de Costa Rica** — Datos Abiertos de Contrataciones Públicas (2022–2024).
- Formato: CSV (~84 MB)
- Cobertura: Contratos adjudicados a nivel nacional por institución pública

