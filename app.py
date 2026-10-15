
import time
import pandas as pd
import streamlit as st
import plotly.express as px
from influxdb_client import InfluxDBClient

# ==================================================
# 1. CONFIGURACIÓN
# ==================================================
st.set_page_config(
    page_title="IoT | Centro de monitoreo",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
TOKEN = "5FESPQw5t4qA4GgZmyeZ9mu7u1sbtauo4Hh8tjRi1E8sdrIgzXAX5ESk4n5MmcpAjJWEGgEKklFX0LNasnUmng=="
ORG = "miguelcmo"
BUCKET = "iot_telemetry_data"

# ==================================================
# 2. ESTILOS VISUALES
# ==================================================
st.markdown("""
<style>
    .stApp {
        background-color: #F4F7FB;
    }

    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E0E7F0;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3 {
        color: #172B4D !important;
        letter-spacing: -0.3px;
    }

    p, label, .stCaption {
        color: #52627A;
    }

    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #DFE7F1;
        border-radius: 12px;
        padding: 15px 18px;
        box-shadow: 0 3px 10px rgba(26, 45, 75, 0.04);
    }

    div[data-testid="stMetricLabel"] {
        color: #52627A !important;
        font-size: 13px;
    }

    div[data-testid="stMetricValue"] {
        color: #172B4D !important;
        font-size: 27px;
        font-weight: 700;
    }

    div[data-testid="stPlotlyChart"] {
        background: #FFFFFF;
        border: 1px solid #DFE7F1;
        border-radius: 12px;
        padding: 5px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #DFE7F1;
        border-radius: 10px;
        overflow: hidden;
    }

    .subtitle {
        color: #52627A !important;
        font-size: 14px;
        margin-top: -8px;
        margin-bottom: 20px;
    }

    .status-card {
        background: #E8F7EF;
        border: 1px solid #B7E4CA;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 12px 0 22px 0;
        color: #17663D !important;
        font-size: 13px;
    }

    .status-card b {
        color: #14532D !important;
    }

    .footer {
        text-align: center;
        color: #64748B !important;
        font-size: 12px;
        padding-top: 25px;
    }

    div.stButton > button {
        border-radius: 9px;
        min-height: 42px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ==================================================
# 3. ENCABEZADO
# ==================================================
st.title("🌐 Centro de monitoreo IoT")

st.markdown(
    '<p class="subtitle">'
    'Monitoreo de temperatura y humedad a partir de los datos '
    'registrados por los sensores.'
    '</p>',
    unsafe_allow_html=True
)

# ==================================================
# 4. BARRA LATERAL
# ==================================================
with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    st.caption("Personaliza la consulta de los sensores.")

    rangos = {
        "Última hora": "-1h",
        "Últimas 6 horas": "-6h",
        "Últimas 12 horas": "-12h",
        "Últimas 24 horas": "-24h",
        "Últimos 7 días": "-7d"
    }

    rango_nombre = st.selectbox(
        "Periodo de consulta",
        list(rangos.keys()),
        index=3
    )

    time_range = rangos[rango_nombre]

    refresh = st.selectbox(
        "Actualización automática",
        options=[0, 10, 30, 60],
        format_func=lambda x: (
            "Desactivada" if x == 0
            else f"Cada {x} segundos"
        ),
        index=0
    )

    st.divider()

    if st.button("🔄 Consultar ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("FUENTE DE DATOS")
    st.write("InfluxDB Cloud")
    st.caption(f"Bucket: {BUCKET}")
    st.caption("Variables: temperatura y humedad")

# ==================================================
# 5. CONSULTA A INFLUXDB
# ==================================================
@st.cache_data(ttl=10)
def load_data(time_range):
    query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: {time_range})
      |> filter(fn: (r) =>
          r["_field"] == "temperature" or
          r["_field"] == "humidity"
      )
      |> pivot(
          rowKey: ["_time"],
          columnKey: ["_field"],
          valueColumn: "_value"
      )
      |> keep(columns: ["_time", "temperature", "humidity"])
      |> sort(columns: ["_time"])
    '''

    with InfluxDBClient(
        url=URL,
        token=TOKEN,
        org=ORG
    ) as client:
        result = client.query_api().query_data_frame(query)

    if isinstance(result, list):
        frames = [frame for frame in result if not frame.empty]

        if not frames:
            return pd.DataFrame()

        df = pd.concat(frames, ignore_index=True)
    else:
        df = result

    if df.empty or "_time" not in df.columns:
        return pd.DataFrame()

    for column in ["temperature", "humidity"]:
        if column not in df.columns:
            df[column] = float("nan")

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df["_time"] = pd.to_datetime(
        df["_time"],
        utc=True,
        errors="coerce"
    )

    df = df.dropna(subset=["_time"])
    df = df.sort_values("_time")
    df = df.drop_duplicates(
        subset=["_time"],
        keep="last"
    )

    return df[["_time", "temperature", "humidity"]]


# ==================================================
# 6. CARGAR Y VALIDAR LOS DATOS
# ==================================================
try:
    with st.spinner("Consultando los sensores..."):
        df = load_data(time_range)

except Exception as error:
    st.error("No fue posible consultar los datos de InfluxDB.")
    st.exception(error)
    st.stop()

if df.empty:
    st.warning(
        "No hay datos disponibles en el periodo seleccionado. "
        "Prueba con un intervalo de tiempo más amplio."
    )
    st.stop()

temperaturas = df["temperature"].dropna()
humedades = df["humidity"].dropna()

ultima_temp = (
    temperaturas.iloc[-1]
    if not temperaturas.empty else None
)

ultima_hum = (
    humedades.iloc[-1]
    if not humedades.empty else None
)

# ==================================================
# 7. INDICADORES PRINCIPALES
# ==================================================
st.subheader("Resumen de mediciones")

st.caption(
    f"Periodo: {rango_nombre} · "
    f"{len(df):,} registros con marca de tiempo"
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "🌡️ Temperatura actual",
        f"{ultima_temp:.2f} °C"
        if ultima_temp is not None else "Sin datos"
    )

with col2:
    st.metric(
        "💧 Humedad actual",
        f"{ultima_hum:.2f} %"
        if ultima_hum is not None else "Sin datos"
    )

with col3:
    st.metric(
        "Temperatura promedio",
        f"{temperaturas.mean():.2f} °C"
        if not temperaturas.empty else "Sin datos"
    )

with col4:
    st.metric(
        "Humedad promedio",
        f"{humedades.mean():.2f} %"
        if not humedades.empty else "Sin datos"
    )

st.markdown(
    '<div class="status-card">'
    '<b>● Consulta completada</b> &nbsp; '
    'Se muestran la última lectura disponible y los promedios '
    'calculados para el periodo seleccionado.'
    '</div>',
    unsafe_allow_html=True
)

# ==================================================
# 8. CONFIGURACIÓN DE LAS GRÁFICAS
# ==================================================
def configurar_grafica(fig, titulo, eje_y):
    fig.update_layout(
        height=300,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Arial, sans-serif",
            size=13,
            color="#263449"
        ),
        title=dict(
            text=titulo,
            font=dict(size=18, color="#172B4D")
        ),
        margin=dict(l=25, r=20, t=60, b=35),
        hovermode="x unified",
        showlegend=False,
        xaxis=dict(
            title=dict(
                text="Fecha y hora",
                font=dict(color="#263449")
            ),
            tickfont=dict(color="#263449", size=11),
            showgrid=True,
            gridcolor="#E5EAF2",
            linecolor="#D9E1EC"
        ),
        yaxis=dict(
            title=dict(
                text=eje_y,
                font=dict(color="#263449")
            ),
            tickfont=dict(color="#263449", size=12),
            showgrid=True,
            gridcolor="#E5EAF2",
            linecolor="#D9E1EC",
            zeroline=False
        )
    )

    return fig


# ==================================================
# 9. EVOLUCIÓN TEMPORAL DE LOS SENSORES
# ==================================================
st.subheader("Evolución de los sensores")

st.markdown(
    '<p class="subtitle">'
    'Explora cada variable por separado para identificar cambios '
    'y comparar las mediciones a lo largo del tiempo.'
    '</p>',
    unsafe_allow_html=True
)

tab_temp, tab_hum, tab_promedios = st.tabs([
    "🌡️ Temperatura",
    "💧 Humedad",
    "📊 Promedios cada 10 minutos"
])

# ---------------- TEMPERATURA ----------------
with tab_temp:
    temp_df = df.dropna(subset=["temperature"])

    if temp_df.empty:
        st.info("No hay mediciones de temperatura.")
    else:
        fig_temp = px.line(
            temp_df,
            x="_time",
            y="temperature",
            labels={
                "_time": "Fecha y hora",
                "temperature": "Temperatura (°C)"
            }
        )

        fig_temp.update_traces(
            line=dict(color="#E87532", width=2.5),
            hovertemplate=(
                "%{x|%d/%m/%Y %H:%M}<br>"
                "Temperatura: %{y:.2f} °C"
                "<extra></extra>"
            )
        )

        fig_temp = configurar_grafica(
            fig_temp,
            "Temperatura a lo largo del tiempo",
            "Temperatura (°C)"
        )

        st.plotly_chart(
            fig_temp,
            use_container_width=True
        )

        minimo, maximo, promedio = (
            temperaturas.min(),
            temperaturas.max(),
            temperaturas.mean()
        )

        a, b, c = st.columns(3)
        a.metric("Temperatura mínima", f"{minimo:.2f} °C")
        b.metric("Temperatura máxima", f"{maximo:.2f} °C")
        c.metric("Temperatura promedio", f"{promedio:.2f} °C")

# ---------------- HUMEDAD ----------------
with tab_hum:
    hum_df = df.dropna(subset=["humidity"])

    if hum_df.empty:
        st.info("No hay mediciones de humedad.")
    else:
        fig_hum = px.line(
            hum_df,
            x="_time",
            y="humidity",
            labels={
                "_time": "Fecha y hora",
                "humidity": "Humedad (%)"
            }
        )

        fig_hum.update_traces(
            line=dict(color="#2388C9", width=2.5),
            hovertemplate=(
                "%{x|%d/%m/%Y %H:%M}<br>"
                "Humedad: %{y:.2f} %"
                "<extra></extra>"
            )
        )

        fig_hum = configurar_grafica(
            fig_hum,
            "Humedad a lo largo del tiempo",
            "Humedad (%)"
        )

        st.plotly_chart(
            fig_hum,
            use_container_width=True
        )

        minimo, maximo, promedio = (
            humedades.min(),
            humedades.max(),
            humedades.mean()
        )

        a, b, c = st.columns(3)
        a.metric("Humedad mínima", f"{minimo:.2f} %")
        b.metric("Humedad máxima", f"{maximo:.2f} %")
        c.metric("Humedad promedio", f"{promedio:.2f} %")

# ==================================================
# 10. PROMEDIOS POR INTERVALO DE 10 MINUTOS
# ==================================================
df_resampled = (
    df.set_index("_time")[["temperature", "humidity"]]
    .resample("10min")
    .mean()
    .dropna(how="all")
    .reset_index()
)

with tab_promedios:
    st.markdown("#### Resumen por intervalos")
    st.caption(
        "Cada fila representa el promedio de las lecturas disponibles "
        "durante un intervalo de 10 minutos."
    )

    if df_resampled.empty:
        st.info("No hay datos suficientes para calcular promedios.")
    else:
        resumen = df_resampled.rename(columns={
            "_time": "Fecha y hora",
            "temperature": "Temperatura promedio (°C)",
            "humidity": "Humedad promedio (%)"
        })

        resumen["Fecha y hora"] = (
            resumen["Fecha y hora"]
            .dt.strftime("%d/%m/%Y %H:%M")
        )

        st.dataframe(
            resumen,
            use_container_width=True,
            hide_index=True,
            height=350,
            column_config={
                "Temperatura promedio (°C)": st.column_config.NumberColumn(
                    format="%.2f °C"
                ),
                "Humedad promedio (%)": st.column_config.NumberColumn(
                    format="%.2f %%"
                )
            }
        )

        st.download_button(
            "⬇️ Descargar promedios CSV",
            data=resumen.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="promedios_iot.csv",
            mime="text/csv"
        )

# ==================================================
# 11. ÚLTIMAS 50 LECTURAS ORIGINALES
# ==================================================
st.divider()

with st.expander("📋 Consultar las últimas 50 lecturas originales"):
    datos = df.tail(50).copy()

    datos = datos.rename(columns={
        "_time": "Fecha y hora",
        "temperature": "Temperatura (°C)",
        "humidity": "Humedad (%)"
    })

    datos["Fecha y hora"] = (
        datos["Fecha y hora"]
        .dt.strftime("%d/%m/%Y %H:%M:%S")
    )

    datos = datos.sort_values(
        "Fecha y hora",
        ascending=False
    )

    st.dataframe(
        datos,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Temperatura (°C)": st.column_config.NumberColumn(
                format="%.2f °C"
            ),
            "Humedad (%)": st.column_config.NumberColumn(
                format="%.2f %%"
            )
        }
    )

    st.download_button(
        "⬇️ Descargar lecturas originales CSV",
        data=datos.to_csv(
            index=False
        ).encode("utf-8-sig"),
        file_name="lecturas_iot.csv",
        mime="text/csv"
    )

# ==================================================
# 12. PIE DE PÁGINA
# ==================================================
st.markdown(
    '<div class="footer">'
    'Centro de monitoreo IoT · Temperatura y humedad · InfluxDB Cloud'
    '</div>',
    unsafe_allow_html=True
)

# ==================================================
# 13. ACTUALIZACIÓN AUTOMÁTICA
# ==================================================
if refresh > 0:
    time.sleep(refresh)
    st.rerun()


