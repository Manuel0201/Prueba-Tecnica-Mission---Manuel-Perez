import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Título del dashboard
st.title("Prueba Técnica – Demo RPA con API Pública")

# API pública: datos curiosos de gatos
url = "https://catfact.ninja/fact"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    fact = data["fact"]

    st.subheader("Dato curioso 🐱")
    st.write(fact)

    # Datos de ejemplo para la gráfica
    df = pd.DataFrame({
        "Día": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        "Transacciones": [120, 90, 150, 80, 200]
    })

    fig = px.bar(df, x="Día", y="Transacciones", title="Transacciones procesadas")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("No se pudo obtener datos de la API")


