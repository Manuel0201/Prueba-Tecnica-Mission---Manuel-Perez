import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# -------------------------------
# 📌 Cargar los datos
# -------------------------------
ruta_datos = Path(__file__).parent.parent / "data" / "observaciones.csv"

st.set_page_config(
    page_title="Dashboard IVV",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Dashboard – Índice de Volatilidad de Viajes (IVV)")

if not ruta_datos.exists():
    st.error("❌ No se encontró el archivo de datos. Ejecuta primero el pipeline.")
else:
    # Cargar CSV
    df = pd.read_csv(ruta_datos)

    # Convertir columnas de fecha
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"])

    # -------------------------------
    # 📌 Filtros en la barra lateral
    # -------------------------------
    ciudades = st.sidebar.multiselect(
        "🌍 Selecciona las ciudades:",
        options=df["ciudad"].unique(),
        default=df["ciudad"].unique()
    )

    df_filtrado = df[df["ciudad"].isin(ciudades)]

    # -------------------------------
    # 📌 Mostrar tabla de datos
    # -------------------------------
    st.subheader("📋 Datos de Observaciones")
    st.dataframe(df_filtrado.tail(20))

    # -------------------------------
    # 📊 Gráfico de línea – IVV en el tiempo
    # -------------------------------
    if "ivv" in df_filtrado.columns:
        fig_ivv = px.line(
            df_filtrado,
            x="fecha",
            y="ivv",
            color="ciudad",
            title="📈 Evolución del IVV por ciudad"
        )
        st.plotly_chart(fig_ivv, use_container_width=True)

    # -------------------------------
    # 🌡️ Gráfico de temperatura
    # -------------------------------
    if "temperatura_c" in df_filtrado.columns:
        fig_temp = px.line(
            df_filtrado,
            x="fecha",
            y="temperatura_c",
            color="ciudad",
            title="🌡️ Temperatura por ciudad"
        )
        st.plotly_chart(fig_temp, use_container_width=True)

    # -------------------------------
    # 💱 Gráfico de tasa de cambio
    # -------------------------------
    if "tasa_cambio_usd" in df_filtrado.columns:
        fig_divisa = px.line(
            df_filtrado,
            x="fecha",
            y="tasa_cambio_usd",
            color="ciudad",
            title="💱 Tasa de cambio frente al USD"
        )
        st.plotly_chart(fig_divisa, use_container_width=True)

    # -------------------------------
    # 🌍 Mapa de las ciudades
    # -------------------------------
    if {"latitud", "longitud"}.issubset(df_filtrado.columns):
        fig_mapa = px.scatter_mapbox(
            df_filtrado,
            lat="latitud",
            lon="longitud",
            color="ciudad",
            size_max=15,
            zoom=1,
            mapbox_style="open-street-map",
            title="🗺️ Mapa de ciudades monitoreadas"
        )
        st.plotly_chart(fig_mapa, use_container_width=True)

