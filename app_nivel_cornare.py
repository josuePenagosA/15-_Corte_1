"""
App de Streamlit — Nivel de ríos/quebradas (CORNARE / MARCO)
Estación Fijada: Código 20 - Río Venus (Puerto Venus, Nariño)
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------------------------------------------------------
# Información de la Estación (Fijada según MARCO - CORNARE)
# ------------------------------------------------------------------
CODIGO_ESTACION = "20"
NOMBRE_ESTACION = "Estación Hidrometeorológica - Río Venus"
MUNICIPIO = "Nariño"
CORREGIMIENTO = "Puerto Venus"
CORRIENTE = "Río Venus"
PARAMETROS_ESTACION = "Nivel, Precipitación"

# Coordenadas de Puerto Venus, Nariño (Antioquia)
LAT_ESTACION = 5.6262
LON_ESTACION = -75.1633

API_BASE_URL = "https://marco.cornare.gov.co/api/v1/estaciones"

LLAVE_FECHA = "level_date"
LLAVE_VALOR = "level"
CANDIDATOS_LAT = ["lat", "latitude", "latitud"]
CANDIDATOS_LON = ["lng", "lon", "longitude", "longitud"]

st.set_page_config(
    page_title=f"Estación {CODIGO_ESTACION} - Río Venus", 
    page_icon="🌊", 
    layout="wide"
)

# ------------------------------------------------------------------
# Funciones de consulta
# ------------------------------------------------------------------
def obtener_serie_nivel(codigo_estacion, desde, hasta, calidad=1, timeout=30):
    url = f"{API_BASE_URL}/{codigo_estacion}/nivel"
    params = {"desde": desde, "hasta": hasta, "calidad": calidad}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout, verify=False)
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"HTTP {resp.status_code}"
    except requests.exceptions.RequestException as e:
        return None, f"Error de red: {e}"


def obtener_todas_las_paginas(datos_json, timeout=30):
    registros = list(datos_json.get("values", []))
    siguiente_url = datos_json.get("next")
    while siguiente_url:
        try:
            resp = requests.get(siguiente_url, timeout=timeout, verify=False)
        except requests.exceptions.RequestException:
            break
        if resp.status_code != 200:
            break
        pagina = resp.json()
        registros.extend(pagina.get("values", []))
        siguiente_url = pagina.get("next")
    return registros


def detectar_coordenadas(datos_json):
    """Busca lat/lon en las llaves raíz de la respuesta. Si no las encuentra, usa las del corregimiento Puerto Venus."""
    if not isinstance(datos_json, dict):
        return LAT_ESTACION, LON_ESTACION, False

    lat = next((datos_json[k] for k in CANDIDATOS_LAT if k in datos_json), None)
    lon = next((datos_json[k] for k in CANDIDATOS_LON if k in datos_json), None)

    if lat is not None and lon is not None:
        try:
            return float(lat), float(lon), True
        except (TypeError, ValueError):
            pass
    return LAT_ESTACION, LON_ESTACION, False


def calcular_indice_calidad(df):
    """Índice simple (0-100) combinando completitud de la serie y proporción de outliers."""
    if df.empty or len(df) < 2:
        return 0.0, 0, 0

    df_idx = df.set_index("fecha")
    frecuencia_tipica = df["fecha"].diff().dropna().mode()
    if len(frecuencia_tipica) == 0:
        return 0.0, 0, 0
    frecuencia_tipica = frecuencia_tipica[0]

    rango_completo = pd.date_range(start=df_idx.index.min(), end=df_idx.index.max(), freq=frecuencia_tipica)
    esperados = len(rango_completo)
    huecos = esperados - len(df_idx)
    completitud = max(0.0, 1 - (huecos / esperados)) if esperados > 0 else 0.0

    Q1, Q3 = df["nivel"].quantile(0.25), df["nivel"].quantile(0.75)
    IQR = Q3 - Q1
    lim_inf, lim_sup = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
    es_outlier = (df["nivel"] < lim_inf) | (df["nivel"] > lim_sup) | (df["nivel"] < 0)
    proporcion_outliers = es_outlier.mean()

    indice = (completitud * 0.7 + (1 - proporcion_outliers) * 0.3) * 100
    return round(indice, 1), int(huecos), int(es_outlier.sum())


# ------------------------------------------------------------------
# Sidebar — Parámetros
# ------------------------------------------------------------------
st.sidebar.header("⚙️ Configuración del Análisis")
nombre_estudiante = st.sidebar.text_input("Nombre del estudiante", "Tu Nombre Aquí")

# Mostrar estación fijada en el Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📍 Estación Consultada")
st.sidebar.info(
    f"**Código:** {CODIGO_ESTACION}\n\n"
    f"**Nombre:** {NOMBRE_ESTACION}\n\n"
    f"**Municipio:** {MUNICIPIO}\n\n"
    f"**Corregimiento:** {CORREGIMIENTO}\n\n"
    f"**Corriente:** {CORRIENTE}"
)

st.sidebar.markdown("---")
fecha_desde = st.sidebar.date_input("Desde", pd.to_datetime("2026-08-23")).strftime("%Y-%m-%d")
fecha_hasta = st.sidebar.date_input("Hasta", pd.to_datetime("2026-08-30")).strftime("%Y-%m-%d")
calidad = st.sidebar.selectbox("Calidad", [1, 0], index=0, help="1 = solo datos validados")
consultar = st.sidebar.button("🔍 Consultar Estación 20", type="primary")

# ------------------------------------------------------------------
# Encabezado Principal
# ------------------------------------------------------------------
st.title(f"🌊 Monitoreo del {CORRIENTE} — Estación Código {CODIGO_ESTACION}")
st.caption(f"Estudiante: **{nombre_estudiante}** · Sistema MARCO - CORNARE")

# Ficha informativa de la estación
with st.container():
    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
    col_info1.markdown(f"**Municipio:** {MUNICIPIO}")
    col_info2.markdown(f"**Corregimiento:** {CORREGIMIENTO}")
    col_info3.markdown(f"**Parámetros:** {PARAMETROS_ESTACION}")
    col_info4.markdown("**Estado:** 🟢 `SEGURO`")

st.markdown("---")

# ------------------------------------------------------------------
# Consulta y procesamiento
# ------------------------------------------------------------------
if consultar:
    with st.spinner(f"Consultando la API para la Estación {CODIGO_ESTACION} ({CORRIENTE})..."):
        datos_crudos, error = obtener_serie_nivel(CODIGO_ESTACION, fecha_desde, fecha_hasta, calidad)

    if error:
        st.error(f"❌ Error al consultar la estación {CODIGO_ESTACION}: {error}")
    else:
        registros = obtener_todas_las_paginas(datos_crudos)

        if not registros:
            st.warning(f"No hay registros de nivel para la Estación {CODIGO_ESTACION} ({CORRIENTE}) en el rango de fechas seleccionado.")
        else:
            df = pd.DataFrame(registros)
            df = df.rename(columns={LLAVE_FECHA: "fecha", LLAVE_VALOR: "nivel"})
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            df["nivel"] = pd.to_numeric(df["nivel"], errors="coerce")
            df = df.dropna(subset=["fecha", "nivel"]).sort_values("fecha").reset_index(drop=True)

            lat, lon, coords_reales = detectar_coordenadas(datos_crudos)
            indice_calidad, huecos, n_outliers = calcular_indice_calidad(df)

            # --- Métricas principales de la estación ---
            st.subheader(f"📊 Resumen de Lecturas en {CORRIENTE}")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Lecturas Registradas", len(df))
            col2.metric("Nivel Promedio", f"{df['nivel'].mean():.2f} m")
            col3.metric("Índice de Calidad", f"{indice_calidad} / 100")
            col4.metric("Outliers Detectados", n_outliers)

            # --- Gráfico de la serie ---
            st.subheader(f"📈 Serie Temporal del Nivel - {CORRIENTE} (Puerto Venus)")
            st.line_chart(df.set_index("fecha")["nivel"])

            # --- Mapa de la estación ---
            st.subheader(f"📍 Ubicación de la Estación Código {CODIGO_ESTACION} (Puerto Venus, {MUNICIPIO})")
            if not coords_reales:
                st.caption("Ubicación geográfica aproximada del Corregimiento Puerto Venus, Nariño (Antioquia).")
            st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=12)

            # --- Detalle de calidad ---
            with st.expander("ℹ️ Detalle de la calidad de datos de la Estación 20"):
                st.write(f"- Huecos de reporte detectados en {CORRIENTE}: **{huecos}**")
                st.write(f"- Outliers (método IQR / valores negativos): **{n_outliers}** de {len(df)} lecturas")
                st.write("El índice combina la completitud de la serie (70%) y la proporción de datos válidos (30%).")

            # --- Tabla y descarga ---
            with st.expander("📋 Ver datos crudos de la estación"):
                st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Descargar CSV - Estación 20 Río Venus", 
                csv, 
                file_name=f"estacion_20_rio_venus_{fecha_desde}_a_{fecha_hasta}.csv", 
                mime="text/csv"
            )
else:
    st.info(f"Selecciona el rango
