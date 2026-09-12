import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

st.set_page_config(page_title="Gestor de Repasos y Cante - Oposición", layout="wide", page_icon="👮‍♂️")

st.title("👮‍♂️ Gestor de Repasos y Cante - Curva del Olvido (Policía Local)")
st.markdown("Sistema inteligente de repetición espaciada continua: 6 repasos exponenciales (+1d, +2d, +4d, +8d, +16d, +32d) y mantenimiento indefinido continuo alternando cada 16 y 32 días.")

# Definición de intervalos iniciales y mantenimiento indefinido
INTERVALOS_INICIALES = [1, 2, 4, 8, 16, 32]

def calcular_proxima_fecha(historial, fecha_inicio, fecha_manual=None):
    if fecha_manual is not None:
        return fecha_manual
    
    num_repasos = len(historial)
    if num_repasos == 0:
        return fecha_inicio + timedelta(days=1)
    
    ultima_fecha = historial[-1]["fecha"]
    
    if num_repasos <= 6:
        # Repasos iniciales del 1 al 6
        dias = INTERVALOS_INICIALES[num_repasos - 1]
    else:
        # Repasos indefinidos post-6º cante: alternancia entre 16 y 32 días
        dias = 16 if (num_repasos % 2 != 0) else 32
        
    return ultima_fecha + timedelta(days=dias)

# Inicialización de la base de datos de temas en la sesión
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
            ],
            "proximo_repaso_manual": None
        },
        {
            "id": 2, 
            "tema": "T39 LO 4/00 Ley de Extranjería", 
            "fecha_inicio": date(2026, 9, 1),
            "historial": [
                {"n": 1, "fecha": date(2026, 9, 2), "nota": 4.5, "duracion_min": 12.5, "obs": "Primer cante, dudas en artículos."},
                {"n": 2, "fecha": date(2026, 9, 4), "nota": 7.0, "duracion_min": 10.2, "obs": "Mejora sustancial en la exposición."},
                {"n": 3, "fecha": date(2026, 9, 8), "nota": 7.0, "duracion_min": 9.5, "obs": "Buena fluidez general."}
            ],
            "proximo_repaso_manual": None
        }
    ]

# Pestañas de la aplicación
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📌 Dashboard & Semáforo", 
    "➕ Añadir Nuevo Tema", 
    "🎙️ Modo Simulacro (Cante)", 
    "🛠️ Modificar / Ajustar Fechas y Cantes",
    "📊 Evolución & Notas"
])

# --- TAB 1: DASHBOARD & SEMÁFORO ---
with tab1:
    st.subheader("📋 Estado Diario del Temario (Repasos Iniciales y Mantenimiento)")
    hoy = date.today()
    
    if not st.session_state.temas_db:
        st.warning("No hay temas registrados aún. Ve a la pestaña '➕ Añadir Nuevo Tema' para empezar.")
    else:
        filas_dashboard = []
        for t in st.session_state.temas_db:
            hist = t["historial"]
            num_repasos = len(hist)
            proximo_repaso = calcular_proxima_fecha(hist, t["fecha_inicio"], t.get("proximo_repaso_manual"))

            notas = [h["nota"] for h in hist if h["nota"] is not None]
            media_nota = round(sum(notas) / len(notas), 2) if notas else 0.0

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

            fase_txt = f"Vuelta #{num_repasos}" if num_repasos <= 6 else f"♻️ Mantenimiento (#{num_repasos})"

            filas_dashboard.append({
                "Tema": t["tema"],
                "Fecha Estudio Inicial": t["fecha_inicio"].strftime('%d/%m/%Y'),
                "Fase de Cante": fase_txt,
                "Cantes Realizados": num_repasos,
                "Próximo Repaso": proximo_repaso.strftime('%d/%m/%Y'),
                "Estado Alerta": estado,
                "Nota Media": media_nota if num_repasos > 0 else "-"
            })

        df_dash = pd.DataFrame(filas_dashboard)
        
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

# --- TAB 2: AÑADIR NUEVO TEMA ---
with tab2:
    st.subheader("➕ Incorporar Nuevo Tema al Calendario")
    
    with st.form("form_nuevo_tema", clear_on_submit=True):
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            nuevo_nombre = st.text_input("Nombre o Código del Tema:", placeholder="Ej: T25 Inmovilización y retirada de vehículos")
        with col_n2:
            nueva_fecha_inicio = st.date_input("Fecha de estudio inicial:", value=date.today())
        
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
                    "historial": [],
                    "proximo_repaso_manual": None
                })
                st.toast(f"✅ ¡Tema '{nuevo_nombre}' guardado con éxito!", icon="🎉")
                st.success(f"¡Tema '{nuevo_nombre}' registrado!")
                st.rerun()

    st.markdown("---")
    st.subheader("📚 Listado Completo de Temas")
    temas_resumen = [{"ID": t["id"], "Tema": t["tema"], "Fecha Inicial": t["fecha_inicio"].strftime('%d/%m/%Y'), "Total Cantes": len(t["historial"])} for t in st.session_state.temas_db]
    st.table(pd.DataFrame(temas_resumen))

# --- TAB 3: MODO SIMULACRO / CANTE ---
with tab3:
    st.subheader("🎙️ Modo Simulacro de Cante (Evaluación en Vivo o Registro Retroactivo)")
    st.info("💡 Si realizaste el cante hace unos días y no pudiste anotarlo en su momento, selecciona la fecha real en la que cantaste para que la curva del olvido se re-calcule con exactitud.")
    
    if not st.session_state.temas_db:
        st.warning("No hay temas disponibles.")
    else:
        nombres_temas = [t["tema"] for t in st.session_state.temas_db]
        
        with st.form("form_registrar_cante", clear_on_submit=True):
            tema_cantar = st.selectbox("Selecciona el tema a registrar/cantar:", nombres_temas)
            
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.markdown("### ⏱️ Fecha y Tiempo del Cante")
                fecha_cante_real = st.date_input("🗓️ Fecha real del cante:", value=date.today(), help="Puedes cambiar esta fecha si cantaste el tema días atrás.")
                duracion_cante = st.number_input("Duración del cante (minutos):", min_value=0.0, max_value=120.0, value=12.0, step=0.5)
            
            with col_c2:
                st.markdown("### 📝 Evaluación de tu Pareja")
                nota_c = st.slider("Nota asignada (0.0 a 10.0):", min_value=0.0, max_value=10.0, value=7.5, step=0.25)
                obs_c = st.text_area("Anotaciones / Feedback:", placeholder="Ej: Excelente dicción, precisar bien la ordenanza municipal.")

            btn_registrar_cante = st.form_submit_button("💾 REGISTRAR CANTE Y RECALCULAR CURVA")
            
            if btn_registrar_cante:
                idx = next(i for i, t in enumerate(st.session_state.temas_db) if t["tema"] == tema_cantar)
                hist = st.session_state.temas_db[idx]["historial"]
                
                num_nuevo = len(hist) + 1
                hist.append({
                    "n": num_nuevo,
                    "fecha": fecha_cante_real,
                    "nota": nota_c,
                    "duracion_min": duracion_cante,
                    "obs": obs_c
                })
                # Reordenar historial por fecha por si se introdujo un cante con fecha pasada
                hist = sorted(hist, key=lambda x: x["fecha"])
                for i_h, h_item in enumerate(hist):
                    h_item["n"] = i_h + 1
                
                st.session_state.temas_db[idx]["historial"] = hist
                st.session_state.temas_db[idx]["proximo_repaso_manual"] = None
                
                proxima = calcular_proxima_fecha(hist, st.session_state.temas_db[idx]["fecha_inicio"])
                
                st.toast(f"✅ CANTE #{num_nuevo} REGISTRADO ({fecha_cante_real.strftime('%d/%m/%Y')}): {tema_cantar} - Nota: {nota_c}", icon="📝")
                st.success(f"🎉 ¡Cante registrado con fecha {fecha_cante_real.strftime('%d/%m/%Y')}! La curva se ha recalculado automáticamente. Próximo cante programado: {proxima.strftime('%d/%m/%Y')}.")

# --- TAB 4: MODIFICAR / AJUSTAR FECHAS Y CANTES ---
with tab4:
    st.subheader("🛠️ Gestión de Imprevistos, Edición y Borrado de Cantes")
    
    if not st.session_state.temas_db:
        st.warning("No hay temas registrados.")
    else:
        nombres_temas = [t["tema"] for t in st.session_state.temas_db]
        tema_mod = st.selectbox("Selecciona el Tema a gestionar:", nombres_temas, key="sel_mod_tema")
        
        idx_t = next(i for i, t in enumerate(st.session_state.temas_db) if t["tema"] == tema_mod)
        t_obj = st.session_state.temas_db[idx_t]
        
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
            st.markdown("### 🗓️ Ajustar Próxima Fecha por Imprevisto")
            fecha_defecto = calcular_proxima_fecha(t_obj["historial"], t_obj["fecha_inicio"], t_obj.get("proximo_repaso_manual"))
            nueva_fecha_manual = st.date_input("Nueva fecha programada para el cante:", value=fecha_defecto, key="input_fecha_manual")
            
            if st.button("📌 Reagendar Próximo Cante"):
                st.session_state.temas_db[idx_t]["proximo_repaso_manual"] = nueva_fecha_manual
                st.toast("✅ Fecha del próximo cante actualizada", icon="🗓️")
                st.success(f"Próximo repaso de '{tema_mod}' fijado para el {nueva_fecha_manual.strftime('%d/%m/%Y')}.")
                st.rerun()

        with col_m2:
            st.markdown("### 🗑️ Modificar / Eliminar Cantes Registrados")
            hist = t_obj["historial"]
            
            if not hist:
                st.info("Este tema no tiene cantes registrados en su historial.")
            else:
                opciones_cantes = [f"Repaso #{h['n']} - Fecha: {h['fecha'].strftime('%d/%m/%Y')} - Nota: {h['nota']}" for h in hist]
                cante_sel_str = st.selectbox("Selecciona el cante a modificar o eliminar:", opciones_cantes)
                idx_cante = opciones_cantes.index(cante_sel_str)
                cante_obj = hist[idx_cante]
                
                with st.expander("✏️ Editar datos de este cante", expanded=True):
                    ed_fecha = st.date_input("Fecha del cante:", value=cante_obj["fecha"], key=f"ed_f_{idx_cante}")
                    ed_nota = st.slider("Nota:", min_value=0.0, max_value=10.0, value=float(cante_obj["nota"]), step=0.25, key=f"ed_n_{idx_cante}")
                    ed_min = st.number_input("Duración (min):", min_value=0.0, max_value=120.0, value=float(cante_obj["duracion_min"]), step=0.5, key=f"ed_m_{idx_cante}")
                    ed_obs = st.text_area("Observaciones:", value=cante_obj["obs"], key=f"ed_o_{idx_cante}")
                    
                    c_b1, c_b2 = st.columns(2)
                    with c_b1:
                        if st.button("💾 Guardar Cambios en Cante", key=f"btn_save_c_{idx_cante}"):
                            hist[idx_cante] = {
                                "n": cante_obj["n"],
                                "fecha": ed_fecha,
                                "nota": ed_nota,
                                "duracion_min": ed_min,
                                "obs": ed_obs
                            }
                            # Ordenar historial por fecha si se editó la fecha
                            hist = sorted(hist, key=lambda x: x["fecha"])
                            for i_h, h_item in enumerate(hist):
                                h_item["n"] = i_h + 1
                            st.session_state.temas_db[idx_t]["historial"] = hist
                            st.toast("✅ Cante modificado con éxito", icon="💾")
                            st.rerun()
                    
                    with c_b2:
                        if st.button("❌ Eliminar este Cante", key=f"btn_del_c_{idx_cante}"):
                            hist.pop(idx_cante)
                            for new_i, item in enumerate(hist):
                                item["n"] = new_i + 1
                            st.session_state.temas_db[idx_t]["historial"] = hist
                            st.toast("🗑️ Cante eliminado correctamente", icon="🗑️")
                            st.rerun()

# --- TAB 5: EVOLUCIÓN & NOTAS ---
with tab5:
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
            c_m1.metric("Nota Media Global", f"{df_hist['nota'].mean():.2f} / 10")
            c_m2.metric("Último Cante", f"{df_hist['nota'].iloc[-1]} / 10")
            c_m3.metric("Tiempo Medio de Cante", f"{df_hist['duracion_min'].mean():.1f} min")
            
            st.markdown("#### Progreso de Calificaciones por Repaso (Evolución Continua)")
            st.line_chart(df_hist.set_index("n")[["nota"]])
            
            st.markdown("#### Registro Histórico Completo de Cantes")
            st.dataframe(df_hist[["n", "fecha", "nota", "duracion_min", "obs"]].rename(columns={
                "n": "Nº Repaso", "fecha": "Fecha", "nota": "Nota", "duracion_min": "Minutos", "obs": "Observaciones"
            }), use_container_width=True)
        else:
            st.info("Este tema aún no tiene cantes o repasos registrados.")
