
import time
import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px

# ---------------------------
# CONFIGURACIÓN
# ---------------------------
url = "https://us-east-1-1.aws.cloud2.influxdata.com"

# Guarda tu token en .streamlit/secrets.toml
token = st.secrets["influxdb"]["token"]

org = "miguelcmo"
bucket = "iot_telemetry_data"

st.set_page_config(
    page_title="IoT | Telemetry",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# ESTILO VISUAL
# ---------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background-color: #F5F7FB;
    }

    [data-testid="stHeader"] {
        background: rgba(245, 247, 251, 0.9);
    }

    [data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid #E5EAF2;
    }

    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #17233C;
    }

    .main-title {
        font-size: 2.15rem;
        font-weight: 800;
        color: #17233C;
        letter-spacing: -1.2px;
        margin-bottom: 4px;
    }

    .subtitle {
        color: #77839A;
        font-size: 0.98rem;
        margin-bottom: 24px;
    }

    .section-title {
        color: #17233C;
        font-size: 1.2rem;
        font-weight: 700;
        margin: 12px 0 14px 0;
    }

    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E7ECF3;
        border-radius: 16px;
        padding: 20px;
        min-height: 142px;
        box-shadow: 0 4px 16px rgba(25, 42, 70, 0.035);
    }

    .metric-label {
        color: #78859B;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 12px;
    }

    .metric-value {
        color: #17233C;
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.8px;
    }

    .metric-note {
        color: #8A96A9;
        font-size: 0.78rem;
        margin-top: 8px;
    }

    .metric-icon {
        font-size: 1.25rem;
        margin-right: 6px;
    }

    [data-testid="stPlotlyChart"] {
        background: #FFFFFF;
        border: 1px solid #E7ECF3;
        border-radius: 16px;
        padding: 10px 10px 2px 10px;
        box-shadow: 0 4px 16px rgba(25, 42, 70, 0.035);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #E7ECF3;
        border-radius: 12px;
        overflow: hidden;
    }

    div[data-testid="stAlert"] {
        border-radius: 12px;
    }

    .sidebar-caption {
        color: #7C899D;
        font-size: 0.82rem;
        line-height: 1.6;
    }

    .footer {
        color: #98A2B3;
        text-align: center;
        font-size: 0.78rem;
        padding: 24px 0 8px 0;
    }

    div[data-testid="stMetric"] {
        background: white;
        padding: 16px;
        border: 1px solid #E7ECF3;
        border-radius: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# BARRA LATERAL
# ---------------------------
with st.sidebar:
    st.markdown("## 🌐 IoT Monitor")
    st.markdown(
        '<p class="sidebar-caption">Panel de monitoreo ambiental</p>',
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown("### ⚙️ Configuración")

    time_range = st.selectbox(
        "Rango de tiempo",
        ["-1h", "-6h", "-12h", "-24h", "-7d"],
        index=3
    )

    refresh = st.slider(
        "Auto-refresh (segundos)",
        min_value=0,
        max_value=60,
        value=10,
        help="Usa 0 para desactivar la actualización automática."
    )

    st.divider()

    st.markdown("### 📡 Fuente de datos")
    st.markdown(
        '<p class="sidebar-caption">'
        'InfluxDB Cloud<br>'
        'Temperatura y humedad<br>'
        'Bucket: iot_telemetry_data'
        '</p>',
        unsafe_allow_html=True
    )

    st.divider()

    if refresh == 0:
        st.caption("⏸️ Actualización automática desactivada")
    else:
        st.caption(f"🔄 Actualización cada {refresh} segundos")

# ---------------------------
# ENCABEZADO
# ---------------------------
st.markdown(
    '<div class="main-title">IoT Telemetry Dashboard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Monitoreo de temperatura y humedad en tiempo real'
    '</div>',
    unsafe_allow_html=True
)

# ---------------------------
# CARGA DE DATOS
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
            frames = [frame for frame in result if not frame.empty]
            if not frames:
                return pd.DataFrame()
            df = pd.concat(frames, ignore_index=True)
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
            else:
                df[column] = float("nan")

        df = df.sort_values("_time")

        return df

    finally:
        client.close()

# ---------------------------
# VISUALIZACIÓN
# ---------------------------
try:
    df = load_data(time_range)

    if not df.empty:
        # Tarjetas de métricas
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
                if pd.notna(value):
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">
                            <span class="metric-icon">{emoji}</span>
                            {label}
                        </div>
                        <div class="metric-value">
                            {value:.2f}<span style="font-size:1rem">
                            {unit}</span>
                        </div>
                        <div class="metric-note">
                            Según los datos del período seleccionado
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info(f"{label}: sin datos")

        # Estilo compartido de los gráficos
        chart_layout = dict(
            template="plotly_white",
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            font=dict(
                family="Inter, sans-serif",
                color="#526078",
                size=12
            ),
            margin=dict(l=20, r=20, t=65, b=25),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0
            ),
            hovermode="x unified",
            xaxis=dict(
                title=None,
                showgrid=False,
                linecolor="#E7ECF3"
            ),
            yaxis=dict(
                title=None,
                gridcolor="#EDF1F6",
                zeroline=False
            )
        )

        # Gráfico principal
        st.markdown(
            '<div class="section-title">Evolución de los sensores</div>',
            unsafe_allow_html=True
        )

        chart_df = df.melt(
            id_vars=["_time"],
            value_vars=["temperature", "humidity"],
            var_name="Sensor",
            value_name="Valor"
        )

        chart_df["Sensor"] = chart_df["Sensor"].map({
            "temperature": "Temperatura (°C)",
            "humidity": "Humedad (%)"
        })

        fig = px.line(
            chart_df,
            x="_time",
            y="Valor",
            color="Sensor",
            color_discrete_map={
                "Temperatura (°C)": "#F08A4B",
                "Humedad (%)": "#4385F5"
            },
            labels={
                "_time": "Fecha y hora",
                "Valor": "Lectura",
                "Sensor": "Variable"
            }
        )

        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(
            title=dict(
                text="Temperatura y humedad",
                x=0.02,
                font=dict(size=17, color="#17233C")
            ),
            **chart_layout
        )

        st.plotly_chart(fig, use_container_width=True)

        # Promedios cada 10 minutos
        st.markdown(
            '<div class="section-title">Tendencia suavizada</div>',
            unsafe_allow_html=True
        )

        df_resampled = (
            df.set_index("_time")[["temperature", "humidity"]]
            .resample("10min")
            .mean()
            .dropna(how="all")
        )

        if not df_resampled.empty:
            smooth_df = (
                df_resampled
                .rename_axis("_time")
                .reset_index()
                .melt(
                    id_vars=["_time"],
                    value_vars=["temperature", "humidity"],
                    var_name="Sensor",
                    value_name="Valor"
                )
            )

            smooth_df["Sensor"] = smooth_df["Sensor"].map({
                "temperature": "Temperatura (°C)",
                "humidity": "Humedad (%)"
            })

            fig2 = px.line(
                smooth_df,
                x="_time",
                y="Valor",
                color="Sensor",
                color_discrete_map={
                    "Temperatura (°C)": "#F08A4B",
                    "Humedad (%)": "#4385F5"
                },
                labels={
                    "_time": "Fecha y hora",
                    "Valor": "Promedio",
                    "Sensor": "Variable"
                }
            )

            fig2.update_traces(line=dict(width=2.5))
            fig2.update_layout(
                title=dict(
                    text="Promedio de lecturas por cada 10 minutos",
                    x=0.02,
                    font=dict(size=17, color="#17233C")
                ),
                **chart_layout
            )

            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No hay suficientes datos para calcular los promedios.")

        # Tabla de datos
        st.markdown(
            '<div class="section-title">Datos recientes</div>',
            unsafe_allow_html=True
        )

        st.caption("Últimas 50 filas de la consulta seleccionada.")

        st.dataframe(
            df.tail(50).sort_values("_time", ascending=False),
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
            "No hay datos disponibles en este rango de tiempo. "
            "Prueba con un período más amplio."
        )

except Exception as e:
    st.error("No fue posible cargar los datos de InfluxDB.")
    st.caption(f"Detalle técnico: {e}")

st.markdown(
    '<div class="footer">IoT Telemetry · Monitoreo ambiental</div>',
    unsafe_allow_html=True
)

# ---------------------------
# AUTO-REFRESH
# ---------------------------
if refresh > 0:
    time.sleep(refresh)
    st.rerun()
