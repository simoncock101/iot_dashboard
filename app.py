
import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px

# ---------------------------
# CONFIG (ORIGINAL)
# ---------------------------
url = "https://us-east-1-1.aws.cloud2.influxdata.com"
token = "5FESPQw5t4qA4GgZmyeZ9mu7u1sbtauo4Hh8tjRi1E8sdrIgzXAX5ESk4n5MmcpAjJWEGgEKklFX0LNasnUmng=="
org = "miguelcmo"
bucket = "iot_telemetry_data"

# ---------------------------
# STREAMLIT UI
# ---------------------------
st.set_page_config(
    page_title="IoT Dashboard",
    page_icon="🌡️",
    layout="wide"
)

# ---------------------------
# VISUAL STYLE
# ---------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.stApp {
    background-color: #F4F7FB;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

[data-testid="stHeader"] {
    background: rgba(244, 247, 251, 0.9);
}

[data-testid="stSidebar"] {
    background-color: #FFFFFF;
    border-right: 1px solid #E5EAF2;
}

.main-title {
    color: #17233C;
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: -1px;
    margin-bottom: 4px;
}

.subtitle {
    color: #78859B;
    font-size: 0.98rem;
    margin-bottom: 25px;
}

.section-title {
    color: #17233C;
    font-size: 1.2rem;
    font-weight: 700;
    margin-top: 18px;
    margin-bottom: 12px;
}

.metric-card {
    background: #FFFFFF;
    border: 1px solid #E5EAF2;
    border-radius: 16px;
    padding: 20px;
    min-height: 135px;
    box-shadow: 0 4px 15px rgba(25, 42, 70, 0.035);
}

.metric-label {
    color: #78859B;
    font-size: 0.84rem;
    font-weight: 600;
    margin-bottom: 14px;
}

.metric-value {
    color: #17233C;
    font-size: 1.75rem;
    font-weight: 800;
    letter-spacing: -0.7px;
}

.metric-unit {
    font-size: 0.95rem;
    font-weight: 600;
    color: #78859B;
}

[data-testid="stPlotlyChart"] {
    background: #FFFFFF;
    border: 1px solid #E5EAF2;
    border-radius: 16px;
    padding: 10px;
    box-shadow: 0 4px 15px rgba(25, 42, 70, 0.035);
}

[data-testid="stDataFrame"] {
    border: 1px solid #E5EAF2;
    border-radius: 12px;
    overflow: hidden;
}

.sidebar-note {
    color: #78859B;
    font-size: 0.84rem;
    line-height: 1.7;
}

.footer {
    color: #98A2B3;
    text-align: center;
    font-size: 0.78rem;
    padding: 28px 0 10px 0;
}

</style>
""", unsafe_allow_html=True)

# ---------------------------
# HEADER
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
# SIDEBAR (ORIGINAL OPTIONS)
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
# DATA FUNCTION (ORIGINAL)
# ---------------------------
@st.cache_data(ttl=10)
def load_data(time_range):
    client = InfluxDBClient(url=url, token=token, org=org)
    query_api = client.query_api()

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: {time_range})
      |> filter(fn: (r) => r["_field"] == "temperature" or r["_field"] == "humidity")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: ["_time", "temperature", "humidity"])
    '''

    result = query_api.query_data_frame(query)

    if isinstance(result, list):
        df = pd.concat(result)
    else:
        df = result

    if df.empty:
        return df

    df["_time"] = pd.to_datetime(df["_time"])
    df = df.sort_values("_time")

    return df

# ---------------------------
# LOAD DATA (ORIGINAL)
# ---------------------------
df = load_data(time_range)

# ---------------------------
# METRICS (SAME VALUES)
# ---------------------------
if not df.empty:
    st.markdown(
        '<div class="section-title">Resumen general</div>',
        unsafe_allow_html=True
    )

    col1, col2, col3, col4 = st.columns(4)

    metrics = [
        (col1, "🌡️", "Temperatura actual",
         df["temperature"].iloc[-1], "°C"),
        (col2, "💧", "Humedad actual",
         df["humidity"].iloc[-1], "%"),
        (col3, "📈", "Temperatura promedio",
         df["temperature"].mean(), "°C"),
        (col4, "📊", "Humedad promedio",
         df["humidity"].mean(), "%")
    ]

    for col, emoji, label, value, unit in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{emoji} {label}</div>
                <div class="metric-value">
                    {value:.2f}
                    <span class="metric-unit">{unit}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ---------------------------
# CHARTS (SAME DATA)
# ---------------------------
if not df.empty:

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
            "variable": "Sensor",
            "temperature": "Temperatura (°C)",
            "humidity": "Humedad (%)"
        },
        color_discrete_map={
            "temperature": "#F08A4B",
            "humidity": "#4385F5"
        }
    )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Inter, sans-serif",
            color="#526078",
            size=12
        ),
        title=dict(
            font=dict(size=17, color="#17233C"),
            x=0.02
        ),
        margin=dict(l=20, r=20, t=65, b=20),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        xaxis=dict(
            title="Fecha y hora",
            showgrid=False
        ),
        yaxis=dict(
            title="Lectura",
            gridcolor="#EDF1F6",
            zeroline=False
        )
    )

    fig.update_traces(line=dict(width=2.5))

    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------
    # RESAMPLING (ORIGINAL)
    # ---------------------------
    st.markdown(
        '<div class="section-title">⏱️ Promedio cada 10 minutos</div>',
        unsafe_allow_html=True
    )

    # Asegurar tipos numéricos
    df["temperature"] = pd.to_numeric(
        df["temperature"], errors="coerce"
    )
    df["humidity"] = pd.to_numeric(
        df["humidity"], errors="coerce"
    )

    # Asegurar datetime index
    df["_time"] = pd.to_datetime(df["_time"])

    # Promedio cada 10 minutos
    df_resampled = (
        df.set_index("_time")[["temperature", "humidity"]]
        .resample("10min")
        .mean()
        .dropna()
    )

    fig2 = px.line(
        df_resampled,
        x=df_resampled.index,
        y=["temperature", "humidity"],
        title="Promedio de lecturas por intervalo",
        labels={
            "x": "Fecha y hora",
            "value": "Promedio",
            "variable": "Sensor",
            "temperature": "Temperatura (°C)",
            "humidity": "Humedad (%)"
        },
        color_discrete_map={
            "temperature": "#F08A4B",
            "humidity": "#4385F5"
        }
    )

    fig2.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Inter, sans-serif",
            color="#526078",
            size=12
        ),
        title=dict(
            font=dict(size=17, color="#17233C"),
            x=0.02
        ),
        margin=dict(l=20, r=20, t=65, b=20),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        xaxis=dict(
            title="Fecha y hora",
            showgrid=False
        ),
        yaxis=dict(
            title="Promedio",
            gridcolor="#EDF1F6",
            zeroline=False
        )
    )

    fig2.update_traces(line=dict(width=2.5))

    st.plotly_chart(fig2, use_container_width=True)

    # ---------------------------
    # RAW DATA (ORIGINAL)
    # ---------------------------
    st.markdown(
        '<div class="section-title">📋 Datos crudos</div>',
        unsafe_allow_html=True
    )

    st.dataframe(
        df.tail(50),
        use_container_width=True
    )

else:
    st.warning("No hay datos disponibles en este rango de tiempo")

# ---------------------------
# FOOTER
# ---------------------------
st.markdown(
    '<div class="footer">IoT Telemetry · Monitoreo ambiental</div>',
    unsafe_allow_html=True
)

# ---------------------------
# AUTO REFRESH
# ---------------------------
if refresh > 0:
    import time
    time.sleep(refresh)
    st.rerun()

