
import time
import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px

# ---------------------------
# CONFIGURACIÓN ORIGINAL
# ---------------------------
url = "https://us-east-1-1.aws.cloud2.influxdata.com"

# Conserva aquí tu token actual
token = "PEGA_AQUI_TU_TOKEN_EXISTENTE"

org = "miguelcmo"
bucket = "iot_telemetry_data"

# ---------------------------
# CONFIGURACIÓN STREAMLIT
# ---------------------------
st.set_page_config(
    page_title="IoT Dashboard",
    page_icon="🌡️",
    layout="wide"
)

# ---------------------------
# ESTILOS VISUALES
# ---------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.stApp {
    background-color: #F4F7FB;
    color: #263449;
    font-family: 'Inter', Arial, sans-serif;
}

[data-testid="stHeader"] {
    background: rgba(244, 247, 251, 0.95);
}

[data-testid="stSidebar"] {
    background-color: #FFFFFF;
    border-right: 1px solid #DCE3ED;
}

/* Títulos principales */
h1, h2, h3 {
    color: #17233C !important;
    font-weight: 700 !important;
}

.main-title {
    color: #17233C;
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: -1px;
    margin-bottom: 4px;
}

.subtitle {
    color: #596981 !important;
    font-size: 0.98rem;
    margin-bottom: 25px;
}

.section-title {
    color: #17233C;
    font-size: 1.2rem;
    font-weight: 700;
    margin-top: 20px;
    margin-bottom: 12px;
}

/* Barra lateral */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
    color: #344258 !important;
}

.sidebar-note {
    color: #596981 !important;
    font-size: 0.84rem;
    line-height: 1.7;
}

/* Tarjetas de métricas */
.metric-card {
    background: #FFFFFF;
    border: 1px solid #DCE3ED;
    border-radius: 16px;
    padding: 20px;
    min-height: 135px;
    box-shadow: 0 4px 15px rgba(25, 42, 70, 0.04);
}

.metric-label {
    color: #526078;
    font-size: 0.84rem;
    font-weight: 600;
    margin-bottom: 14px;
}

.metric-value {
    color: #17233C;
    font-size: 1.65rem;
    font-weight: 800;
    letter-spacing: -0.5px;
}

.metric-unit {
    font-size: 0.95rem;
    font-weight: 600;
    color: #526078;
}

/* Gráficos */
[data-testid="stPlotlyChart"] {
    background: #FFFFFF;
    border: 1px solid #DCE3ED;
    border-radius: 16px;
    padding: 10px;
    box-shadow: 0 4px 15px rgba(25, 42, 70, 0.04);
}

/* Tabla */
[data-testid="stDataFrame"] {
    border: 1px solid #DCE3ED;
    border-radius: 12px;
    overflow: hidden;
}

/* Pie de página */
.footer {
    color: #596981;
    text-align: center;
    font-size: 0.8rem;
    padding: 28px 0 10px 0;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# ENCABEZADO
# ---------------------------
st.markdown(
    '<div class="main-title">🌡️ IoT Telemetry Dashboard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Monitoreo de temperatura y humedad en tiempo real'
    '</div>',
    unsafe_allow_html=True
)

# ---------------------------
# BARRA LATERAL
# ---------------------------
st.sidebar.markdown("## 🌐 IoT Monitor")

st.sidebar.markdown(
    '<div class="sidebar-note">Panel de monitoreo ambiental</div>',
    unsafe_allow_html=True
)

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ Configuración")

time_range = st.sidebar.selectbox(
    "Rango de tiempo",
    ["-1h", "-6h", "-12h", "-24h", "-7d"],
    index=3
)

refresh = st.sidebar.slider(
    "Auto-refresh (segundos)",
    0, 60, 10
)

st.sidebar.divider()
st.sidebar.markdown("### 📡 Fuente de datos")

st.sidebar.markdown(
    '<div class="sidebar-note">'
    'InfluxDB Cloud<br>'
    'Temperatura y humedad<br>'
    'Bucket: iot_telemetry_data'
    '</div>',
    unsafe_allow_html=True
)

# ---------------------------
# FUNCIÓN DE CARGA ORIGINAL
# ---------------------------
@st.cache_data(ttl=10)
def load_data(time_range):
    client = InfluxDBClient(
        url=url,
        token=token,
        org=org
    )

    try:
        query_api = client.query_api()

        query = f'''
        from(bucket: "{bucket}")
          |> range(start: {time_range})
          |> filter(fn: (r) =>
              r["_field"] == "temperature" or
              r["_field"] == "humidity")
          |> pivot(
              rowKey: ["_time"],
              columnKey: ["_field"],
              valueColumn: "_value"
          )
          |> keep(columns: ["_time", "temperature", "humidity"])
        '''

        result = query_api.query_data_frame(query)

        if isinstance(result, list):
            if not result:
                return pd.DataFrame()

            df = pd.concat(result, ignore_index=True)
        else:
            df = result

        if df.empty:
            return df

        df["_time"] = pd.to_datetime(df["_time"])

        for column in ["temperature", "humidity"]:
            if column in df.columns:
                df[column] = pd.to_numeric(
                    df[column], errors="coerce"
                )

        df = df.sort_values("_time")

        return df

    finally:
        client.close()

# ---------------------------
# CARGA DE DATOS
# ---------------------------
if token == "PEGA_AQUI_TU_TOKEN_EXISTENTE" or not token:
    st.error(
        "Pega tu token actual de InfluxDB en la variable token "
        "al inicio del código."
    )
    st.stop()

try:
    df = load_data(time_range)

except Exception as e:
    st.error("No se pudieron cargar los datos de InfluxDB.")
    with st.expander("Ver detalle del error"):
        st.exception(e)
    st.stop()

# ---------------------------
# MÉTRICAS
# ---------------------------
if not df.empty:
    st.markdown(
        '<div class="section-title">Resumen general</div>',
        unsafe_allow_html=True
    )

    col1, col2, col3, col4 = st.columns(4)

    temp = df["temperature"].dropna()
    humidity = df["humidity"].dropna()

    metrics = [
        (col1, "🌡️", "Temperatura actual",
         temp.iloc[-1] if not temp.empty else None, "°C"),
        (col2, "💧", "Humedad actual",
         humidity.iloc[-1] if not humidity.empty else None, "%"),
        (col3, "📈", "Temperatura promedio",
         temp.mean() if not temp.empty else None, "°C"),
        (col4, "📊", "Humedad promedio",
         humidity.mean() if not humidity.empty else None, "%")
    ]

    for col, emoji, label, value, unit in metrics:
        with col:
            display_value = (
                f'{value:.2f} <span class="metric-unit">{unit}</span>'
                if value is not None and pd.notna(value)
                else "Sin datos"
            )

            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{emoji} {label}</div>
                <div class="metric-value">{display_value}</div>
            </div>
            """, unsafe_allow_html=True)

# ---------------------------
# CONFIGURACIÓN COMPARTIDA
# DE LOS GRÁFICOS
# ---------------------------
chart_layout = dict(
    template="plotly_white",
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",

    font=dict(
        family="Arial, sans-serif",
        size=14,
        color="#263449"
    ),

    title=dict(
        font=dict(size=20, color="#17233C"),
        x=0.02
    ),

    margin=dict(l=35, r=25, t=75, b=40),

    hovermode="x unified",

    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        font=dict(size=13, color="#263449")
    ),

    xaxis=dict(
        title=dict(
            text="Fecha y hora",
            font=dict(size=14, color="#263449")
        ),
        tickfont=dict(size=12, color="#526078"),
        showgrid=False,
        automargin=True
    ),

    yaxis=dict(
        title=dict(
            text="Lectura",
            font=dict(size=14, color="#263449")
        ),
        tickfont=dict(size=12, color="#526078"),
        gridcolor="#DCE3ED",
        zeroline=False,
        automargin=True
    )
)

# ---------------------------
# GRÁFICOS
# ---------------------------
if not df.empty:

    # Gráfico de serie de tiempo
    st.markdown(
        '<div class="section-title">📈 Serie de tiempo</div>',
        unsafe_allow_html=True
    )

    fig = px.line(
        df,
        x="_time",
        y=["temperature", "humidity"],
        title="Temperatura y humedad",
        labels={
            "_time": "Fecha y hora",
            "value": "Lectura",
            "variable": "Sensor"
        },
        color_discrete_map={
            "temperature": "#E87532",
            "humidity": "#2868D8"
        }
    )

    fig.update_layout(**chart_layout)
    fig.update_traces(line=dict(width=2.5))

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ---------------------------
    # PROMEDIO CADA 10 MINUTOS
    # ---------------------------
    st.markdown(
        '<div class="section-title">'
        '⏱️ Promedio cada 10 minutos'
        '</div>',
        unsafe_allow_html=True
    )

    df["temperature"] = pd.to_numeric(
        df["temperature"], errors="coerce"
    )
    df["humidity"] = pd.to_numeric(
        df["humidity"], errors="coerce"
    )

    df["_time"] = pd.to_datetime(df["_time"])

    df_resampled = (
        df.set_index("_time")[["temperature", "humidity"]]
        .resample("10min")
        .mean()
        .dropna()
    )

    if not df_resampled.empty:
        fig2 = px.line(
            df_resampled,
            x=df_resampled.index,
            y=["temperature", "humidity"],
            title="Promedio de lecturas por intervalo",
            labels={
                "x": "Fecha y hora",
                "value": "Promedio",
                "variable": "Sensor"
            },
            color_discrete_map={
                "temperature": "#E87532",
                "humidity": "#2868D8"
            }
        )

        layout2 = chart_layout.copy()
        layout2["yaxis"] = dict(
            title=dict(
                text="Promedio",
                font=dict(size=14, color="#263449")
            ),
            tickfont=dict(size=12, color="#526078"),
            gridcolor="#DCE3ED",
            zeroline=False,
            automargin=True
        )

        fig2.update_layout(**layout2)
        fig2.update_traces(line=dict(width=2.5))

        st.plotly_chart(
            fig2,
            use_container_width=True
        )
    else:
        st.info("No hay datos suficientes para calcular los promedios.")

    # ---------------------------
    # DATOS CRUDOS
    # ---------------------------
    st.markdown(
        '<div class="section-title">📋 Datos crudos</div>',
        unsafe_allow_html=True
    )

    st.dataframe(
        df.tail(50),
        use_container_width=True,
        hide_index=True,
        column_config={
            "_time": st.column_config.DatetimeColumn(
                "Fecha y hora",
                format="DD/MM/YYYY, HH:mm:ss"
            ),
            "temperature": st.column_config.NumberColumn(
                "Temperatura (°C)",
                format="%.2f"
            ),
            "humidity": st.column_config.NumberColumn(
                "Humedad (%)",
                format="%.2f"
            )
        }
    )

else:
    st.warning(
        "No hay datos disponibles en este rango de tiempo."
    )

# ---------------------------
# PIE DE PÁGINA
# ---------------------------
st.markdown(
    '<div class="footer">'
    'IoT Telemetry · Monitoreo ambiental'
    '</div>',
    unsafe_allow_html=True
)

# ---------------------------
# ACTUALIZACIÓN AUTOMÁTICA
# ---------------------------
if refresh > 0:
    time.sleep(refresh)
    st.rerun()


