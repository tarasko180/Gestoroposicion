import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

st.set_page_config(page_title="Gestor de Repasos y Cante - Oposición", layout="wide", page_icon="⏱️")

st.title("⏱️ Gestor de Repasos y Cante - Curva del Olvido")
st.markdown("Plataforma interactiva para planificar repeticiones espaciadas, cronometrar cantes y evaluar evolución.")

INTERVALOS = [1, 2, 4, 8, 16, 32] # Días para la curva del olvido: 1er, 2do, 3ro, 4to, 5to, 6to repaso

# Inicialización de los temas en la memoria de la sesión
if 'temas_db' not in st.session_state:
    st.session_state.temas_db = [
        {
            "id": 1, 
            "tema": "T1 Constitución Española", 
            "fecha_inicio": date(2026, 9, 1),
            "historial": [
                {"n": 1, "fecha": date(2026, 9, 2), "nota": 9.5, "duracion_min": 15.0, "obs": "Excelente estructura y articulado."},
                {"n": 2, "fecha": date(2026, 9, 4), "nota": 9.0, "duracion_min": 14.2, "obs": "Sin fallos significativos."},
                {"n": 3, "fecha": date(2026, 9, 8), "nota": 9.0, "duracion_min": 14.0, "obs": "Dominado con fluidez."}
            ]
        },
        {
            "id": 2, 
            "tema": "T39 LO 4/00 Ley de Extranjería", 
            "fecha_inicio": date(2026, 9, 1),
            "historial": [
                {"n": 1, "fecha": date(2026, 9, 2), "nota": 4.5, "duracion_min": 12.5, "obs": "Primer cante, dudas en artículos."},
                {"n": 2, "fecha": date(2026, 9, 4), "nota": 7.0, "duracion_min": 10.2, "obs": "Mejora sustancial en la exposición."},
                {"n": 3, "fecha": date(2026, 9, 8), "nota": 7.0, "duracion_min": 9.5, "obs": "Buena fluidez general."}
            ]
        }
    ]

# Pestañas principales
tab1, tab2, tab3, tab4 = st.tabs([
    "📌 Dashboard & Semáforo", 
    "➕ Añadir Nuevo Tema", 
    "🎙️ Modo Simulacro (Cante)", 
    "📊 Evolución & Notas"
])

# --- TAB 1: DASHBOARD & SEMÁFORO DE ALERTAS ---
with tab1:
    st.subheader("📋 Estado Diario del Temario")
    hoy = date.today()
    
    if not st.session_state.temas_db:
        st.warning("No hay temas registrados aún. Ve a la pestaña '➕ Añadir Nuevo Tema' para empezar.")
    else:
        filas_dashboard = []
        for t in st.session_state.temas_db:
            hist = t["historial"]
            num_repasos = len(hist)
            
            # Cálculo de la próxima fecha según repetición espaciada
            if num_repasos > 0:
                ultima_fecha = hist[-1]["fecha"]
                dias_sumar = INTERVALOS[min(num_repasos, len(INTERVALOS)-1)]
                proximo_repaso = ultima_fecha + timedelta(days=dias_sumar)
                notas = [h["nota"] for h in hist if h["nota"] is not None]
                media_nota = round(sum(notas) / len(notas), 2) if notas else 0.0
            else:
                proximo_repaso = t["fecha_inicio"] + timedelta(days=1)
                media_nota = 0.0

            # Estado por colores
            if proximo_repaso == hoy:
                estado = "🟢 TOCA HOY"
            elif proximo_repaso < hoy:
                dias_atraso = (hoy - proximo_repaso).days
                estado = f"🔴 ATRASADO ({dias_atraso} d)"
            elif proximo_repaso == hoy + timedelta(days=1):
                estado = "🟡 MAÑANA"
            else:
                estado = f"⚪ {proximo_repaso.strftime('%d/%m/%Y')}"

            filas_dashboard.append({
                "Tema": t["tema"],
                "Fecha Estudio Inicial": t["fecha_inicio"].strftime('%d/%m/%Y'),
                "Repasos Completados": f"{num_repasos} / 6",
                "Próximo Repaso": proximo_repaso.strftime('%d/%m/%Y'),
                "Estado Alerta": estado,
                "Nota Media": media_nota if num_repasos > 0 else "-"
            })

        df_dash = pd.DataFrame(filas_dashboard)
        
        # Filtros rápidos
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_estado = st.multiselect(
                "Filtrar por estado:",
                options=["🟢 TOCA HOY", "🔴 ATRASADO", "🟡 MAÑANA", "Todos"],
                default=["🟢 TOCA HOY", "🔴 ATRASADO"]
            )
        
        if "Todos" not in filtro_estado and filtro_estado:
            df_dash = df_dash[df_dash["Estado Alerta"].apply(lambda x: any(e in x for e in filtro_estado))]

        st.dataframe(df_dash, use_container_width=True)

# --- TAB 2: AÑADIR NUEVO TEMA AL PROGRAMA ---
with tab2:
    st.subheader("➕ Incorporar Nuevo Tema al Calendario de Repasos")
    st.markdown("Cada vez que estudies un tema nuevo por primera vez, regístralo aquí para que el algoritmo programe automáticamente sus 6 repasos de la curva del olvido.")
    
    with st.form("form_nuevo_tema", clear_on_submit=True):
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            nuevo_nombre = st.text_input("Nombre o Código del Tema:", placeholder="Ej: T25 Inmovilización y retirada de vehículos")
        with col_n2:
            nueva_fecha_inicio = st.date_input("Fecha de estudio inicial (Primera Vuelta):", value=date.today())
        
        btn_guardar_tema = st.form_submit_button("🚀 Añadir Tema a la Lista")
        
        if btn_guardar_tema:
            if nuevo_nombre.strip() == "":
                st.error("Por favor, introduce el nombre del tema.")
            else:
                nuevo_id = max([t["id"] for t in st.session_state.temas_db], default=0) + 1
                st.session_state.temas_db.append({
                    "id": nuevo_id,
                    "tema": nuevo_nombre.strip(),
                    "fecha_inicio": nueva_fecha_inicio,
                    "historial": []
                })
                st.success(f"✅ ¡Tema '{nuevo_nombre}' añadido con éxito! Los repasos han sido programados.")
                st.rerun()

    st.markdown("---")
    st.subheader("📚 Listado Completo de Temas Registrados")
    temas_resumen = [{"ID": t["id"], "Tema": t["tema"], "Fecha Inicial": t["fecha_inicio"].strftime('%d/%m/%Y'), "Repasos": len(t["historial"])} for t in st.session_state.temas_db]
    st.table(pd.DataFrame(temas_resumen))

# --- TAB 3: MODO SIMULACRO / CANTE (PARA TU PAREJA) ---
with tab3:
    st.subheader("🎙️ Modo Simulacro de Cante (Optimizado para Móvil/iPad)")
    st.info("Tu pareja selecciona el tema, activa el cronómetro durante la exposición, asigna la nota y escribe anotaciones de mejora.")
    
    if not st.session_state.temas_db:
        st.warning("No hay temas disponibles.")
    else:
        nombres_temas = [t["tema"] for t in st.session_state.temas_db]
        tema_cantar = st.selectbox("Selecciona el tema que vas a cantar:", nombres_temas)
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("### ⏱️ Registro de Tiempo")
            duracion_cante = st.number_input("Duración del cante (minutos):", min_value=0.0, max_value=120.0, value=12.0, step=0.5)
        
        with col_c2:
            st.markdown("### 📝 Evaluación de tu Pareja")
            nota_c = st.slider("Nota asignada (0.0 a 10.0):", min_value=0.0, max_value=10.0, value=7.5, step=0.25)
            obs_c = st.text_area("Anotaciones / Feedback:", placeholder="Ej: Muy buena entonación, falta precisar el artículo 15.")

        if st.button("💾 Registrar Cante y Actualizar Curva"):
            idx = next(i for i, t in enumerate(st.session_state.temas_db) if t["tema"] == tema_cantar)
            hist = st.session_state.temas_db[idx]["historial"]
            
            hist.append({
                "n": len(hist) + 1,
                "fecha": date.today(),
                "nota": nota_c,
                "duracion_min": duracion_cante,
                "obs": obs_c
            })
            st.session_state.temas_db[idx]["historial"] = hist
            st.success(f"🎉 ¡Cante del tema '{tema_cantar}' registrado! Nota: {nota_c} | Duración: {duracion_cante} min.")
            st.rerun()

# --- TAB 4: EVOLUCIÓN & ESTADÍSTICAS ---
with tab4:
    st.subheader("📊 Análisis de Evolución y Rendimiento por Tema")
    if not st.session_state.temas_db:
        st.warning("Sin datos.")
    else:
        nombres_temas = [t["tema"] for t in st.session_state.temas_db]
        tema_analisis = st.selectbox("Elige tema para ver la gráfica de progreso:", nombres_temas, key="sel_analisis")
        
        obj_tema = next(t for t in st.session_state.temas_db if t["tema"] == tema_analisis)
        df_hist = pd.DataFrame(obj_tema["historial"])
        
        if not df_hist.empty:
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("Nota Media", f"{df_hist['nota'].mean():.2f} / 10")
            c_m2.metric("Último Cante", f"{df_hist['nota'].iloc[-1]} / 10")
            c_m3.metric("Tiempo Medio de Cante", f"{df_hist['duracion_min'].mean():.1f} min")
            
            st.markdown("#### Progreso de Calificaciones por Repaso")
            st.line_chart(df_hist.set_index("n")[["nota"]])
            
            st.markdown("#### Registro Histórico de Simulacros")
            st.dataframe(df_hist[["n", "fecha", "nota", "duracion_min", "obs"]].rename(columns={
                "n": "Nº Repaso", "fecha": "Fecha", "nota": "Nota", "duracion_min": "Minutos", "obs": "Observaciones"
            }), use_container_width=True)
        else:
            st.info("Este tema aún no tiene cantes o repasos registrados.")
