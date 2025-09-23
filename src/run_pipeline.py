# src/run_pipeline.py
import os
import json
import time
import logging
from datetime import datetime, date, timedelta
import requests
import pandas as pd

# ----------------- CONFIGURACIÓN -----------------
# Directorios donde se guardan los datos y logs
CARPETA_DATOS = os.path.join(os.path.dirname(__file__), "..", "data")
CARPETA_LOGS = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(CARPETA_DATOS, exist_ok=True)
os.makedirs(CARPETA_LOGS, exist_ok=True)

# Archivo de logs
ARCHIVO_LOG = os.path.join(CARPETA_LOGS, "pipeline.log")
logging.basicConfig(filename=ARCHIVO_LOG, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

# Lista de ciudades objetivo con coordenadas, zona horaria y moneda
CIUDADES = [
    {"ciudad": "New York", "lat": 40.7128, "lon": -74.0060, "zona_horaria": "America/New_York", "moneda": "USD"},
    {"ciudad": "London",   "lat": 51.5074, "lon": -0.1278,   "zona_horaria": "Europe/London",   "moneda": "GBP"},
    {"ciudad": "Tokyo",    "lat": 35.6895, "lon": 139.6917,  "zona_horaria": "Asia/Tokyo",      "moneda": "JPY"},
    {"ciudad": "Sao Paulo","lat": -23.5505,"lon": -46.6333,  "zona_horaria": "America/Sao_Paulo","moneda": "BRL"},
    {"ciudad": "Sydney",   "lat": -33.8688,"lon": 151.2093,  "zona_horaria": "Australia/Sydney","moneda": "AUD"},
]

# ----------------- FUNCIONES AUXILIARES -----------------
def consultar_con_reintentos(url, params=None, max_reintentos=3, espera=2, headers=None):
    """
    Hace una petición GET con reintentos.
    - max_reintentos: número de intentos
    - espera: tiempo incremental entre intentos
    """
    for intento in range(1, max_reintentos + 1):
        try:
            r = requests.get(url, params=params, timeout=12, headers=headers)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logging.warning(f"Error {e} en {url}, intento {intento}")
            if intento == max_reintentos:
                logging.error(f"Se agotaron los reintentos para {url}")
                return None
            time.sleep(espera * intento)

def consultar_clima(lat, lon):
    """
    Consulta el clima actual y pronóstico horario de una ciudad.
    Usamos Open-Meteo API (no requiere API Key).
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "hourly": "precipitation_probability,temperature_2m",
        "forecast_days": 1,
        "timezone": "auto"
    }
    return consultar_con_reintentos(url, params=params)

def consultar_cambio_divisa(moneda_destino):
    """
    Consulta el tipo de cambio USD → moneda local
    y calcula el % de variación con respecto al día anterior.
    """
    if moneda_destino.upper() == "USD":
        return {"tasa": 1.0, "variacion_pct": 0.0}
    hoy = date.today()
    ayer = hoy - timedelta(days=1)

    url_hoy = "https://api.exchangerate.host/latest"
    url_ayer = f"https://api.exchangerate.host/{ayer.isoformat()}"

    r_hoy = consultar_con_reintentos(url_hoy, params={"base": "USD", "symbols": moneda_destino})
    r_ayer = consultar_con_reintentos(url_ayer, params={"base": "USD", "symbols": moneda_destino})

    try:
        tasa_hoy = r_hoy["rates"][moneda_destino]
        tasa_ayer = r_ayer["rates"][moneda_destino]
        variacion = ((tasa_hoy / tasa_ayer) - 1) * 100 if tasa_ayer else 0.0
        return {"tasa": tasa_hoy, "variacion_pct": variacion}
    except Exception as e:
        logging.warning(f"Error en cambio de divisa: {e}")
        return {"tasa": None, "variacion_pct": None}

def consultar_hora_local(zona_horaria):
    """
    Consulta la hora local de una ciudad según su zona horaria.
    Usamos WorldTimeAPI.
    """
    url = f"http://worldtimeapi.org/api/timezone/{zona_horaria}"
    d = consultar_con_reintentos(url)
    if d and "datetime" in d:
        return d["datetime"]
    return None

def calcular_ivv(prob_lluvia, temperatura, variacion_divisa):
    """
    Calcula el Índice de Viabilidad de Viaje (IVV).
    Devuelve un puntaje 0-1 y un color.
    """
    # Score de lluvia
    p = prob_lluvia if prob_lluvia is not None else 0.0
    p_norm = min(max(p/100.0, 0.0), 1.0)

    # Score de temperatura: ideal 20°C
    t = temperatura if temperatura is not None else 20.0
    diferencia_temp = abs(t - 20.0)
    score_temp = max(0.0, 1.0 - (diferencia_temp / 40.0))

    # Score combinado de clima
    score_clima = 0.6 * score_temp + 0.4 * (1 - p_norm)

    # Score económico
    if variacion_divisa is None:
        score_divisa = 1.0
    else:
        c = variacion_divisa
        if c >= 0:
            score_divisa = 1.0
        else:
            score_divisa = max(0.0, 1.0 + c/10.0)

    # Puntaje final
    final = 0.7 * score_clima + 0.3 * score_divisa

    # Color
    if final >= 0.75:
        color = "verde"
    elif final >= 0.5:
        color = "amarillo"
    elif final >= 0.25:
        color = "naranja"
    else:
        color = "rojo"
    return round(final, 3), color

# ----------------- PIPELINE PRINCIPAL -----------------
def ejecutar_pipeline():
    logging.info("Inicio del pipeline")
    observaciones = []

    for c in CIUDADES:
        ciudad = c["ciudad"]
        lat = c["lat"]
        lon = c["lon"]
        zona = c["zona_horaria"]
        moneda = c["moneda"]

        logging.info(f"Procesando {ciudad}")

        # 1) Clima
        clima = consultar_clima(lat, lon)
        if not clima:
            logging.warning(f"No hay clima para {ciudad}")
            continue

        actual = clima.get("current_weather", {})
        temperatura = actual.get("temperature")
        viento = actual.get("windspeed")
        tiempo_obs = actual.get("time")

        # Probabilidad de lluvia
        prob_lluvia = None
        horario = clima.get("hourly", {})
        if "precipitation_probability" in horario:
            try:
                probs = [float(x) for x in horario.get("precipitation_probability", [])]
                prob_lluvia = max(probs) if probs else 0.0
            except Exception:
                prob_lluvia = None

        # 2) Divisa
        cambio = consultar_cambio_divisa(moneda)
        tasa = cambio.get("tasa")
        variacion = cambio.get("variacion_pct")

        # 3) Hora local
        hora_local = consultar_hora_local(zona)

        # 4) IVV
        score, color = calcular_ivv(prob_lluvia, temperatura, variacion)

        # Consolidar datos
        obs = {
            "timestamp_utc": datetime.utcnow().isoformat(),
            "ciudad": ciudad,
            "lat": lat,
            "lon": lon,
            "hora_local": hora_local,
            "temperatura_c": temperatura,
            "viento": viento,
            "prob_lluvia_pct": prob_lluvia,
            "moneda": moneda,
            "tasa_cambio_usd": tasa,
            "variacion_divisa_pct": variacion,
            "ivv_score": score,
            "ivv_color": color
        }
        observaciones.append(obs)
        logging.info(f"{ciudad}: ivv={score} color={color}")

        # Alertas
        alertas = []
        if prob_lluvia and prob_lluvia >= 70:
            alertas.append(f"⚠️ Lluvia alta ({prob_lluvia}%)")
        if variacion is not None and variacion <= -3:
            alertas.append(f"⚠️ Caída de moneda {variacion:.2f}%")

        if alertas:
            msg = f"ALERTAS para {ciudad} @ {datetime.utcnow().isoformat()}:\n" + "\n".join(alertas)
            logging.warning(msg)

    # ----------------- GUARDAR DATOS -----------------
    if observaciones:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(CARPETA_DATOS, f"observaciones_{ts}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(observaciones, f, ensure_ascii=False, indent=2)

        # Guardar CSV
        df = pd.DataFrame(observaciones)
        csv_path = os.path.join(CARPETA_DATOS, "observaciones.csv")
        if not os.path.exists(csv_path):
            df.to_csv(csv_path, index=False)
        else:
            df.to_csv(csv_path, index=False, mode="a", header=False)

        logging.info(f"Guardado {len(observaciones)} registros en {json_path} y {csv_path}")

    logging.info("Fin del pipeline")

# Punto de entrada
if __name__ == "__main__":
    ejecutar_pipeline()
