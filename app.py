import streamlit as st
import pandas as pd
from datetime import date, timedelta
import time

st.set_page_config(page_title="Gestor de Repasos y Cante", layout="wide", page_icon="⏱️")

st.title("⏱️ Gestor de Repasos - Curva del Olvido y Cante")
st.markdown("Plataforma interactiva para el seguimiento de temas, cronómetro de cante y notas en tiempo real.")

# Inicialización de la base de datos simulada en sesión (conectar a Supabase en producción)
if 'temas_db' not in st.session_state:
    st.session_state.temas_db = pd.DataFrame([
        {
            "id": 1, "tema": "T39 LO 4/00", "fecha_inicio": date(2026, 9, 1),
            "repaso_actual": 3,
            "historial": [
                {"n": 1, "fecha": date(2026, 9, 2), "nota": 4.5, "duracion_min": 12.5, "obs": "Primer cante, dudas en arts."},
                {"n": 2, "fecha": date(2026, 9, 4), "nota": 7.0, "duracion_min": 10.2, "obs": "Mejora en estructura."},
                {"n": 3, "fecha": date(2026, 9, 8), "nota": 7.0, "duracion_min": 9.5, "obs": "Buena fluidez."}
            ]
        },
        {
            "id": 2, "tema": "T1 Constitución", "fecha_inicio": date(2026, 9, 1),
            "repaso_actual": 3,
            "historial": [
                {"n": 1, "fecha": date(2026, 9, 2), "nota": 9.5, "duracion_min": 15.0, "obs": "Excelente memoria."},
                {"n": 2, "fecha": date(2026, 9, 4), "nota": 9.0, "duracion_min": 14.2, "obs": "Sin fallos."},
                {"n": 3, "fecha": date(2026, 9, 8), "nota": 9.0, "duracion_min": 14.0, "obs": "Dominado."}
            ]
        }
    ])

INTERVALOS = [1, 2, 4, 8, 16, 32] # Días para repetición espaciada

# Pestañas principales
tab1, tab2, tab3 = st.tabs(["📌 Dashboard de Repasos", "🎙️ Modo Simulacro / Cante", "📊 Analítica de Evolución"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Estado de Temas y Alertas")
    
    hoy = date.today()
    filas_dashboard = []

    for idx, row in st.session_state.temas_db.iterrows():
        hist = row["historial"]
        num_repasos = len(hist)
        
        if num_repasos > 0:
            ultima_fecha = hist[-1]["fecha"]
            siguiente_intervalo = INTERVALOS[min(num_repasos, len(INTERVALOS)-1)]
            proximo_repaso = ultima_fecha + timedelta(days=siguiente_intervalo)
            notas = [h["nota"] for h in hist if h["nota"] is not None]
            media_nota = round(sum(notas) / len(notas), 2) if notas else 0.0
        else:
            proximo_repaso = row["fecha_inicio"] + timedelta(days=1)
            media_nota = 0.0

        # Determinación de alertas visuales (Verde / Rojo / Gris)
        if proximo_repaso == hoy:
            estado = "🟢 HOY"
        elif proximo_repaso < hoy:
            estado = f"🔴 ATRASADO ({ (hoy - proximo_repaso).days } d)"
        else:
            estado = f"⚪ Pendiente ({proximo_repaso.strftime('%d/%m/%Y')})"

        filas_dashboard.append({
            "Tema": row["tema"],
            "Fecha Inicio": row["fecha_inicio"],
            "Repasos Hechos": num_repasos,
            "Próximo Repaso": proximo_repaso,
            "Estado": estado,
            "Media Nota": media_nota
        })

    df_display = pd.DataFrame(filas_dashboard)
    st.dataframe(df_display, use_container_width=True)

# --- TAB 2: MODO SIMULACRO (PENSADO PARA EL MÓVIL DE TU PAREJA) ---
with tab2:
    st.subheader("🎙️ Evaluación de Cante en Vivo")
    st.info("Diseñado para que tu pareja pueda cronometrar y evaluar mientras cantas el tema.")
    
    tema_sel = st.selectbox("Selecciona el Tema a cantar:", st.session_state.temas_db["tema"].tolist())
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("### ⏱️ Cronómetro")
        tiempo_manual = st.number_input("Duración del cante (minutos):", min_value=0.0, max_value=120.0, value=10.0, step=0.5)
        
    with col_c2:
        st.markdown("### 📝 Calificación y Observaciones")
        nota_cante = st.slider("Nota del cante (0 - 10):", min_value=0.0, max_value=10.0, value=7.0, step=0.25)
        observaciones = st.text_area("Anotaciones / Puntos a mejorar:", placeholder="Ej. Ha faltado especificar el articulado en el bloque 2.")

    if st.button("✅ Registrar Cante y Actualizar Curva"):
        # Actualización de datos
        idx = st.session_state.temas_db[st.session_state.temas_db["tema"] == tema_sel].index[0]
        nuevo_hist = st.session_state.temas_db.at[idx, "historial"]
        
        nuevo_hist.append({
            "n": len(nuevo_hist) + 1,
            "fecha": date.today(),
            "nota": nota_cante,
            "duracion_min": tiempo_manual,
            "obs": observaciones
        })
        
        st.session_state.temas_db.at[idx, "historial"] = nuevo_hist
        st.success(f"¡Cante guardado correctamente! Nota: {nota_cante} | Duración: {tiempo_manual} min.")

# --- TAB 3: EVOLUCIÓN Y ESTADÍSTICAS ---
with tab3:
    st.subheader("📈 Evolución del Rendimiento")
    tema_stats = st.selectbox("Selecciona tema para analizar:", st.session_state.temas_db["tema"].tolist(), key="stats_sel")
    
    row_tema = st.session_state.temas_db[st.session_state.temas_db["tema"] == tema_stats].iloc[0]
    hist_df = pd.DataFrame(row_tema["historial"])
    
    if not hist_df.empty:
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Nota Media", f"{hist_df['nota'].mean():.2f} / 10")
        col_m2.metric("Última Nota", f"{hist_df['nota'].iloc[-1]} / 10")
        col_m3.metric("Tiempo Medio de Cante", f"{hist_df['duracion_min'].mean():.1f} min")

        st.line_chart(hist_df.set_index("n")[["nota"]])
        st.write("#### Historial detallado de repeticiones:")
        st.table(hist_df)
    else:
        st.write("Aún no se han registrado cantes para este tema.")
