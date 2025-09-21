import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Título del dashboard
st.title("Prueba Técnica – Demo RPA con API Pública")

# Consumir una API pública de ejemplo (OpenWeather no requiere cuenta para ciudades fijas)
url = "https://api.coindesk.com/v1/bpi/currentprice.json"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    bitcoin_price = data["bpi"]["USD"]["rate_float"]

    st.metric("Precio Bitcoin (USD)", f"${bitcoin_price:,.2f}")

    # Ejemplo con datos ficticios
    df = pd.DataFrame({
        "Día": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        "Transacciones": [120, 90, 150, 80, 200]
    })

    fig = px.bar(df, x="Día", y="Transacciones", title="Transacciones procesadas")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("No se pudo obtener datos de la API")

