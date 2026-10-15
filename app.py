
import time
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from influxdb_client import InfluxDBClient

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------
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

# --------------------------------------------------
# DISEÑO VISUAL
# --------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background-color: #F5F7FB;
    }

    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E5EAF2;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    h1, h2, h3 {
        color: #172B4D !important;
        letter-spacing: -0.4px;
    }

    p, label, .stCaption {
        color: #52627A;
    }

    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E3E9F2;
        padding: 20px 22px;
        border-radius: 14px;
        box-shadow: 0 3px 12px rgba(26, 45, 75, 0.04);
    }

    div[data-testid="stMetricLabel"] {
        color: #66758A;
        font-size: 14px;
    }

    div[data-testid="stMetricValue"] {
        color: #172B4D;
        font-size: 30px;
        font-weight: 700;
    }

    div[data-testid="stPlotlyChart"] {
        background: #FFFFFF;
        border: 1px solid #E3E9F2;
        border-radius: 14px;
        padding: 10px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #E3E9F2;
        border-radius: 12px;
        overflow: hidden;
    }

    .section-description {
        color: #66758A;
        font-size: 14px;
        margin-top: -8px;
        margin-bottom: 18px;
    }

    .status-card {
        background: #FFFFFF;
        border: 1px solid #E3E9F2;
        border-radius: 12px;
        padding: 14px 18px;
        margin: 10px 0 20px 0;
    }

    .footer {
        text-align: center;
        color: #8491A5;
        font-size: 12px;
        padding-top: 30px;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# ENCABEZADO
# --------------------------------------------------
st.title("🌐 Centro de monitoreo IoT")
st.markdown(
    '<p class="section-description">'
    'Visualización de las condiciones ambientales registradas por los sensores.'
    '</p>',
    unsafe_allow_html=True
)

# --------------------------------------------------
# BARRA LATERAL
# --------------------------------------------------
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
        format_func=lambda x: "Desactivada" if x == 0
        else f"Cada {x} segundos",
        index=0
    )

    st.divider()

    if st.button("🔄 Consultar ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption("FUENTE DE DATOS")
    st.write("InfluxDB Cloud")
    st.caption(f"Bucket: {BUCKET}")
    st.caption("Variables: temperatura y humedad")

# --------------------------------------------------
# CONSULTA A INFLUXDB
# --------------------------------------------------
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

    # Evitar problemas si una variable no tiene registros
    for column in ["temperature", "humidity"]:
        if column not in df.columns:
            df[column] = float("nan")
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["_time"] = pd.to_datetime(df["_time"], utc=True)
    df = df.dropna(subset=["_time"])
    df = df.sort_values("_time").drop_duplicates(
        subset=["_time"], keep="last"
    )

    return df[["_time", "temperature", "humidity"]]


# --------------------------------------------------
# CARGA Y VALIDACIÓN
# --------------------------------------------------
try:
    with st.spinner("Consultando datos de los sensores..."):
        df = load_data(time_range)

except Exception as error:
    st.error("No fue posible consultar InfluxDB.")
    st.exception(error)
    st.stop()

if df.empty:
    st.warning(
        "No hay lecturas disponibles para el periodo seleccionado. "
        "Prueba con un intervalo más amplio."
    )
    st.stop()

# Datos disponibles por variable
temperaturas = df["temperature"].dropna()
humedades = df["humidity"].dropna()

ultima_temp = temperaturas.iloc[-1] if not temperaturas.empty else None
ultima_hum = humedades.iloc[-1] if not humedades.empty else None

# --------------------------------------------------
# INDICADORES PRINCIPALES
# --------------------------------------------------
st.subheader("Resumen de mediciones")
st.caption(
    f"Periodo seleccionado: {rango_nombre} · "
    f"{len(df):,} registros con marcas de tiempo"
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "🌡️ Temperatura actual",
        f"{ultima_temp:.2f} °C" if ultima_temp is not None else "Sin datos"
    )

with c2:
    st.metric(
        "💧 Humedad actual",
        f"{ultima_hum:.2f} %" if ultima_hum is not None else "Sin datos"
    )

with c3:
    st.metric(
        "Temperatura promedio",
        f"{temperaturas.mean():.2f} °C"
        if not temperaturas.empty else "Sin datos"
    )

with c4:
    st.metric(
        "Humedad promedio",
        f"{humedades.mean():.2f} %"
        if not humedades.empty else "Sin datos"
    )

st.markdown(
    '<div class="status-card">'
    '🟢 <b>Consulta completada</b> · '
    'Los indicadores corresponden a la última lectura disponible '
    'y a los promedios del periodo seleccionado.'
    '</div>',
    unsafe_allow_html=True
)

# --------------------------------------------------
# FUNCIONES PARA GRÁFICAS
# --------------------------------------------------
def configurar_grafica(fig, titulo, eje_y):
    fig.update_layout(
        title=dict(
            text=titulo,
            font=dict(size=19, color="#172B4D")
        ),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Arial, sans-serif",
            color="#52627A",
            size=12
        ),
        margin=dict(l=20, r=20, t=65, b=25),
        height=350,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(
            title="Fecha y hora",
            showgrid=True,
            gridcolor="#E9EEF5",
            linecolor="#D9E1EC"
        ),
        yaxis=dict(
            title=eje_y,
            showgrid=True,
            gridcolor="#E9EEF5",
            linecolor="#D9E1EC",
            zeroline=False
        )
    )
    return fig


# --------------------------------------------------
# EVOLUCIÓN TEMPORAL
# --------------------------------------------------
st.subheader("Evolución de los sensores")
st.markdown(
    '<p class="section-description">'
    'Cada punto representa una medición registrada. '
    'Las variables tienen escalas independientes para facilitar su lectura.'
    '</p>',
    unsafe_allow_html=True
)

tab_temp, tab_hum, tab_resumen = st.tabs([
    "🌡️ Temperatura",
    "💧 Humedad",
    "📊 Promedios cada 10 minutos"
])

with tab_temp:
    if temperaturas.empty:
        st.info("No hay mediciones de temperatura.")
    else:
        temp_df = df.dropna(subset=["temperature"])

        fig_temp = px.line(
            temp_df,
            x="_time",
            y="temperature",
            markers=True,
            labels={
                "_time": "Fecha y hora",
                "temperature": "Temperatura (°C)"
            }
        )

        fig_temp.update_traces(
            line=dict(color="#E87532", width=2.5),
            marker=dict(size=5, color="#E87532"),
            hovertemplate="%{x|%d/%m/%Y %H:%M}<br>"
                          "Temperatura: %{y:.2f} °C<extra></extra>"
        )

        fig_temp = configurar_grafica(
            fig_temp,
            "Temperatura a lo largo del tiempo",
            "Temperatura (°C)"
        )

        st.plotly_chart(fig_temp, use_container_width=True)

        st.caption(
            f"Mínimo: {temperaturas.min():.2f} °C · "
            f"Máximo: {temperaturas.max():.2f} °C · "
            f"Promedio: {temperaturas.mean():.2f} °C"
        )

with tab_hum:
    if humedades.empty:
        st.info("No hay mediciones de humedad.")
    else:
        hum_df = df.dropna(subset=["humidity"])

        fig_hum = px.line(
            hum_df,
            x="_time",
            y="humidity",
            markers=True,
            labels={
                "_time": "Fecha y hora",
                "humidity": "Humedad (%)"
            }
        )

        fig_hum.update_traces(
            line=dict(color="#2388C9", width=2.5),
            marker=dict(size=5, color="#2388C9"),
            hovertemplate="%{x|%d/%m/%Y %H:%M}<br>"
                          "Humedad: %{y:.2f} %<extra></extra>"
        )

        fig_hum = configurar_grafica(
            fig_hum,
            "Humedad a lo largo del tiempo",
            "Humedad (%)"
        )

        st.plotly_chart(fig_hum, use_container_width=True)

        st.caption(
            f"Mínimo: {humedades.min():.2f} % · "
            f"Máximo: {humedades.max():.2f} % · "
            f"Promedio: {humedades.mean():.2f} %"
        )

# --------------------------------------------------
# PROMEDIOS CADA 10 MINUTOS
# --------------------------------------------------
df_resampled = (
    df.set_index("_time")[["temperature", "humidity"]]
    .resample("10min")
    .mean()
    .dropna(how="all")
    .reset_index()
)

with tab_resumen:
    st.markdown("#### Promedio de las mediciones por intervalo")
    st.caption(
        "Se agrupan las lecturas en intervalos de 10 minutos. "
        "La tabla permite comparar los dos indicadores con sus unidades."
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
            resumen["Fecha y hora"].dt.strftime("%d/%m/%Y %H:%M")
        )

        st.dataframe(
            resumen,
            use_container_width=True,
            hide_index=True,
            height=400,
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
            data=resumen.to_csv(index=False).encode("utf-8-sig"),
            file_name="promedios_iot.csv",
            mime="text/csv"
        )

# --------------------------------------------------
# TABLA DE DATOS ORIGINALES
# --------------------------------------------------
st.divider()
with st.expander("📋 Consultar las últimas 50 lecturas originales"):
    datos = df.tail(50).copy()

    datos = datos.rename(columns={
        "_time": "Fecha y hora",
        "temperature": "Temperatura (°C)",
        "humidity": "Humedad (%)"
    })

    datos["Fecha y hora"] = (
        datos["Fecha y hora"].dt.strftime("%d/%m/%Y %H:%M:%S")
    )

    st.dataframe(
        datos.sort_values("Fecha y hora", ascending=False),
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
        data=datos.to_csv(index=False).encode("utf-8-sig"),
        file_name="lecturas_iot.csv",
        mime="text/csv"
    )

# --------------------------------------------------
# PIE DE PÁGINA Y ACTUALIZACIÓN
# --------------------------------------------------
st.markdown(
    '<div class="footer">'
    'Centro de monitoreo IoT · Temperatura y humedad · InfluxDB Cloud'
    '</div>',
    unsafe_allow_html=True
)

if refresh > 0:
    time.sleep(refresh)
    st.rerun()


