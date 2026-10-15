
import time
import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px

# ==================================================
# CONFIGURACIÓN ORIGINAL
# ==================================================
url = "https://us-east-1-1.aws.cloud2.influxdata.com"
token = "5FESPQw5t4qA4GgZmyeZ9mu7u1sbtauo4Hh8tjRi1E8sdrIgzXAX5ESk4n5MmcpAjJWEGgEKklFX0LNasnUmng=="
org = "miguelcmo"
bucket = "iot_telemetry_data"

# ==================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==================================================
st.set_page_config(
    page_title="Monitor IoT",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================================================
# DISEÑO VISUAL
# ==================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.stApp {
    background: #F5F7FB;
    font-family: 'Inter', sans-serif;
    color: #25334A;
}

[data-testid="stHeader"] {
    background: rgba(245,247,251,0.95);
}

[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid #E1E7F0;
}

h1, h2, h3 {
    color: #17233C !important;
}

.main-header {
    font-size: 2.15rem;
    font-weight: 800;
    letter-spacing: -1px;
    color: #17233C;
    margin-bottom: 4px;
}

.subtitle {
    color: #526078;
    font-size: 1rem;
    margin-bottom: 22px;
}

.section-title {
    font-size: 1.25rem;
    font-weight: 750;
    color: #17233C;
    margin-top: 20px;
    margin-bottom: 5px;
}

.section-description {
    font-size: 0.9rem;
    color: #526078;
    margin-bottom: 14px;
}

.metric-card {
    background: #FFFFFF;
    border: 1px solid #E0E7F0;
    border-radius: 15px;
    padding: 18px;
    min-height: 135px;
    box-shadow: 0 3px 12px rgba(23,35,60,0.035);
}

.metric-label {
    font-size: 0.84rem;
    font-weight: 600;
    color: #526078;
    margin-bottom: 12px;
}

.metric-value {
    font-size: 1.7rem;
    font-weight: 800;
    color: #17233C;
    line-height: 1.3;
}

.metric-description {
    font-size: 0.78rem;
    color: #64748B;
    margin-top: 9px;
}

.info-panel {
    background: #FFFFFF;
    border: 1px solid #E0E7F0;
    border-radius: 12px;
    padding: 14px 16px;
    color: #344258;
    font-size: 0.9rem;
    margin-bottom: 12px;
}

[data-testid="stPlotlyChart"] {
    background: #FFFFFF;
    border: 1px solid #E0E7F0;
    border-radius: 14px;
    padding: 8px;
    box-shadow: 0 3px 12px rgba(23,35,60,0.025);
}

[data-testid="stDataFrame"] {
    border: 1px solid #E0E7F0;
    border-radius: 12px;
    overflow: hidden;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
    color: #344258;
}

.footer {
    text-align: center;
    color: #64748B;
    font-size: 0.8rem;
    padding: 25px 0 10px;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# BARRA LATERAL
# ==================================================
with st.sidebar:
    st.markdown("## 🌐 Monitor IoT")
    st.caption("Panel de monitoreo ambiental")

    st.divider()

    st.markdown("### ⚙️ Configuración")

    time_range = st.selectbox(
        "Período de consulta",
        ["-1h", "-6h", "-12h", "-24h", "-7d"],
        index=3,
        format_func=lambda x: {
            "-1h": "Última hora",
            "-6h": "Últimas 6 horas",
            "-12h": "Últimas 12 horas",
            "-24h": "Últimas 24 horas",
            "-7d": "Últimos 7 días"
        }[x]
    )

    refresh = st.slider(
        "Actualizar cada (segundos)",
        min_value=0,
        max_value=60,
        value=10,
        step=5,
        help="Selecciona 0 para desactivar la actualización automática."
    )

    if refresh == 0:
        st.caption("Actualización automática desactivada")
    else:
        st.caption(f"Actualización cada {refresh} segundos")

    st.divider()

    st.markdown("### 📡 Fuente de datos")
    st.caption("InfluxDB Cloud")
    st.caption("Variables: temperatura y humedad")
    st.caption(f"Bucket: {bucket}")

    st.divider()

    if st.button("🔄 Consultar ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ==================================================
# ENCABEZADO
# ==================================================
st.markdown(
    '<div class="main-header">🌡️ Monitor de temperatura y humedad</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Consulta las lecturas de tus sensores, compara los promedios '
    'y revisa cómo cambian las condiciones con el tiempo.'
    '</div>',
    unsafe_allow_html=True
)

# ==================================================
# CARGA DE DATOS
# ==================================================
@st.cache_data(ttl=10)
def load_data(time_range):
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

    with InfluxDBClient(
        url=url,
        token=token,
        org=org
    ) as client:
        result = client.query_api().query_data_frame(query)

    if isinstance(result, list):
        frames = [frame for frame in result if not frame.empty]

        if not frames:
            return pd.DataFrame()

        df = pd.concat(frames, ignore_index=True)
    else:
        df = result

    if df.empty:
        return pd.DataFrame()

    df["_time"] = pd.to_datetime(df["_time"], errors="coerce")

    for column in ["temperature", "humidity"]:
        if column not in df.columns:
            df[column] = float("nan")

        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    df = df.dropna(subset=["_time"])
    df = df.sort_values("_time").reset_index(drop=True)

    return df


# ==================================================
# ESTILO DE GRÁFICOS
# ==================================================
def style_chart(fig, title, y_title, color):
    fig.update_traces(
        line=dict(color=color, width=2.8),
        connectgaps=False
    )

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=19, color="#17233C"),
            x=0.03,
            xanchor="left"
        ),
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Arial, sans-serif",
            size=13,
            color="#25334A"
        ),
        margin=dict(l=20, r=20, t=70, b=30),
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(
            title="Fecha y hora",
            tickfont=dict(size=12, color="#344258"),
            title_font=dict(size=13, color="#25334A"),
            showgrid=False,
            automargin=True
        ),
        yaxis=dict(
            title=y_title,
            tickfont=dict(size=12, color="#344258"),
            title_font=dict(size=13, color="#25334A"),
            gridcolor="#E1E7F0",
            zeroline=False,
            automargin=True
        )
    )

    return fig


# ==================================================
# MOSTRAR DASHBOARD
# ==================================================
try:
    df = load_data(time_range)

except Exception as e:
    st.error("No se pudieron consultar los datos de InfluxDB.")
    with st.expander("Ver detalle del error"):
        st.exception(e)
    st.stop()


if df.empty:
    st.warning(
        "No hay lecturas en el período seleccionado. "
        "Prueba con un período más amplio o consulta nuevamente."
    )

else:
    temp = df["temperature"].dropna()
    humidity = df["humidity"].dropna()

    # ----------------------------------------------
    # 1. RESUMEN GENERAL
    # ----------------------------------------------
    st.markdown(
        '<div class="section-title">1. Resumen general</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-description">'
        'Estos números resumen las últimas lecturas y el promedio '
        'del período que seleccionaste.'
        '</div>',
        unsafe_allow_html=True
    )

    metrics = [
        (
            "🌡️",
            "Última temperatura",
            temp.iloc[-1] if not temp.empty else None,
            "°C",
            "Lectura más reciente disponible"
        ),
        (
            "💧",
            "Última humedad",
            humidity.iloc[-1] if not humidity.empty else None,
            "%",
            "Lectura más reciente disponible"
        ),
        (
            "📊",
            "Temperatura promedio",
            temp.mean() if not temp.empty else None,
            "°C",
            "Promedio del período seleccionado"
        ),
        (
            "📊",
            "Humedad promedio",
            humidity.mean() if not humidity.empty else None,
            "%",
            "Promedio del período seleccionado"
        )
    ]

    cols = st.columns(4)

    for col, (emoji, label, value, unit, description) in zip(cols, metrics):
        with col:
            value_text = (
                f"{value:.2f} {unit}"
                if value is not None and pd.notna(value)
                else "Sin datos"
            )

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{emoji} {label}</div>
                    <div class="metric-value">{value_text}</div>
                    <div class="metric-description">{description}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # ----------------------------------------------
    # 2. TEMPERATURA
    # ----------------------------------------------
    st.markdown(
        '<div class="section-title">2. Temperatura</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-description">'
        'La temperatura se mide en grados Celsius (°C). '
        'La línea muestra cómo cambia a lo largo del tiempo.'
        '</div>',
        unsafe_allow_html=True
    )

    if not temp.empty:
        temperature_df = df.dropna(subset=["temperature"])

        fig_temp = px.line(
            temperature_df,
            x="_time",
            y="temperature",
            labels={
                "_time": "Fecha y hora",
                "temperature": "Temperatura (°C)"
            }
        )

        fig_temp = style_chart(
            fig_temp,
            "Evolución de la temperatura",
            "Temperatura (°C)",
            "#E87532"
        )

        st.plotly_chart(
            fig_temp,
            use_container_width=True
        )

        st.markdown(
            f"""
            <div class="info-panel">
                <b>Cómo leerlo:</b> el eje horizontal muestra el tiempo.
                El eje vertical muestra la temperatura en °C.
                La línea sube cuando la temperatura aumenta y baja
                cuando disminuye. El promedio del período es
                <b>{temp.mean():.2f} °C</b>.
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("No hay lecturas de temperatura para mostrar.")

    # ----------------------------------------------
    # 3. HUMEDAD
    # ----------------------------------------------
    st.markdown(
        '<div class="section-title">3. Humedad</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-description">'
        'La humedad relativa se expresa en porcentaje (%). '
        'Este gráfico permite ver si aumenta o disminuye con el tiempo.'
        '</div>',
        unsafe_allow_html=True
    )

    if not humidity.empty:
        humidity_df = df.dropna(subset=["humidity"])

        fig_humidity = px.line(
            humidity_df,
            x="_time",
            y="humidity",
            labels={
                "_time": "Fecha y hora",
                "humidity": "Humedad (%)"
            }
        )

        fig_humidity = style_chart(
            fig_humidity,
            "Evolución de la humedad",
            "Humedad (%)",
            "#2868D8"
        )

        st.plotly_chart(
            fig_humidity,
            use_container_width=True
        )

        st.markdown(
            f"""
            <div class="info-panel">
                <b>Cómo leerlo:</b> el eje horizontal muestra el tiempo.
                El eje vertical indica la humedad relativa en porcentaje.
                El promedio del período es
                <b>{humidity.mean():.2f} %</b>.
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("No hay lecturas de humedad para mostrar.")

    # ----------------------------------------------
    # 4. PROMEDIOS CADA 10 MINUTOS
    # ----------------------------------------------
    st.markdown(
        '<div class="section-title">4. Tendencia por intervalos</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-description">'
        'Para facilitar la lectura, agrupamos las mediciones en '
        'intervalos de 10 minutos y calculamos el promedio de cada uno.'
        '</div>',
        unsafe_allow_html=True
    )

    df_resampled = (
        df.set_index("_time")[["temperature", "humidity"]]
        .resample("10min")
        .mean()
        .dropna(how="all")
    )

    if not df_resampled.empty:
        col_temp, col_humidity = st.columns(2)

        with col_temp:
            st.markdown("#### 🌡️ Temperatura promedio")

            smooth_temp = (
                df_resampled["temperature"]
                .dropna()
                .rename("Temperatura (°C)")
                .reset_index()
            )

            if not smooth_temp.empty:
                fig_smooth_temp = px.line(
                    smooth_temp,
                    x="_time",
                    y="Temperatura (°C)",
                    labels={
                        "_time": "Fecha y hora",
                        "Temperatura (°C)": "Temperatura (°C)"
                    }
                )

                fig_smooth_temp = style_chart(
                    fig_smooth_temp,
                    "Cada 10 minutos",
                    "Temperatura (°C)",
                    "#E87532"
                )

                st.plotly_chart(
                    fig_smooth_temp,
                    use_container_width=True
                )
            else:
                st.info("Sin promedios de temperatura disponibles.")

        with col_humidity:
            st.markdown("#### 💧 Humedad promedio")

            smooth_humidity = (
                df_resampled["humidity"]
                .dropna()
                .rename("Humedad (%)")
                .reset_index()
            )

            if not smooth_humidity.empty:
                fig_smooth_humidity = px.line(
                    smooth_humidity,
                    x="_time",
                    y="Humedad (%)",
                    labels={
                        "_time": "Fecha y hora",
                        "Humedad (%)": "Humedad (%)"
                    }
                )

                fig_smooth_humidity = style_chart(
                    fig_smooth_humidity,
                    "Cada 10 minutos",
                    "Humedad (%)",
                    "#2868D8"
                )

                st.plotly_chart(
                    fig_smooth_humidity,
                    use_container_width=True
                )
            else:
                st.info("Sin promedios de humedad disponibles.")

    else:
        st.info("No hay suficientes datos para calcular los promedios.")

    # ----------------------------------------------
    # 5. DATOS RECIENTES
    # ----------------------------------------------
    st.markdown(
        '<div class="section-title">5. Datos recientes</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-description">'
        'Aquí puedes consultar las últimas 50 filas recibidas '
        'por la aplicación.'
        '</div>',
        unsafe_allow_html=True
    )

    table_df = (
        df.tail(50)
        .sort_values("_time", ascending=False)
        .rename(columns={
            "_time": "Fecha y hora",
            "temperature": "Temperatura (°C)",
            "humidity": "Humedad (%)"
        })
    )

    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fecha y hora": st.column_config.DatetimeColumn(
                "Fecha y hora",
                format="DD/MM/YYYY, HH:mm:ss"
            ),
            "Temperatura (°C)": st.column_config.NumberColumn(
                "Temperatura (°C)",
                format="%.2f"
            ),
            "Humedad (%)": st.column_config.NumberColumn(
                "Humedad (%)",
                format="%.2f"
            )
        }
    )

# ==================================================
# PIE DE PÁGINA
# ==================================================
st.markdown(
    '<div class="footer">'
    'Monitor IoT · Datos de temperatura y humedad'
    '</div>',
    unsafe_allow_html=True
)

# ==================================================
# ACTUALIZACIÓN AUTOMÁTICA
# ==================================================
if refresh > 0:
    time.sleep(refresh)
    st.rerun()

