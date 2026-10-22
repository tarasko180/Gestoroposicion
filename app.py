import copy
import json
import os
import shutil
from datetime import date, datetime, timedelta
from glob import glob
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Gestor de Repasos y Cante - Oposición", layout="wide", page_icon="👮‍♂️")

# ---------------------------------------------------------------------------
# RUTAS (todo se guarda junto a este archivo, en tu propio ordenador)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "temas_data.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
BACKUP_DIR = os.path.join(BASE_DIR, "copias_automaticas")
MAX_COPIAS = 30

# ---------------------------------------------------------------------------
# CONFIGURACIÓN AJUSTABLE
# ---------------------------------------------------------------------------
CONFIG_DEFAULT = {
    # Días entre repasos. El último valor se repite indefinidamente (mantenimiento).
    "intervalos": [1, 2, 4, 7, 10, 14],
    "zona_horaria": "Europe/Madrid",
    # Fecha del examen (opcional, "YYYY-MM-DD"). Si se indica, los intervalos se
    # acortan automáticamente a medida que se acerca el examen.
    "fecha_examen": None,
    # Nota por debajo de la cual el tema vuelve al intervalo inicial.
    "umbral_repetir": 5.0,
    # Nota a partir de la cual el tema avanza al siguiente intervalo.
    # Entre ambos umbrales se repite el mismo intervalo (no avanza).
    "umbral_avanzar": 7.0,
}
# Proporción del tiempo restante hasta el examen que se usa como intervalo máximo
# (la investigación de Cepeda et al., 2008, sitúa el intervalo óptimo en torno al 10-20 %).
PROPORCION_EXAMEN = 0.15


def escribir_json(ruta, datos):
    """Escritura atómica: primero a un temporal y luego se reemplaza, para no corromper el archivo."""
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ruta)


def cargar_config():
    cfg = dict(CONFIG_DEFAULT)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


if "cfg" not in st.session_state:
    st.session_state.cfg = cargar_config()
cfg = st.session_state.cfg


def hoy():
    """Fecha de hoy según la zona horaria configurada."""
    try:
        return datetime.now(ZoneInfo(cfg["zona_horaria"])).date()
    except Exception:
        return date.today()


st.title("👮‍♂️ Gestor de Repasos y Cante - Curva del Olvido (Policía Local)")
st.markdown("Repetición espaciada adaptativa: el intervalo depende de la nota obtenida y se recalcula desde la fecha real de cada cante.")

if "aviso" in st.session_state:
    st.success(st.session_state.pop("aviso"))

# ---------------------------------------------------------------------------
# DATOS POR DEFECTO
# ---------------------------------------------------------------------------
TEMAS_DEFAULT = [
    {
        "id": 1,
        "tema": "T1 Constitución Española",
        "fecha_inicio": "2026-09-01",
        "historial": [
            {"n": 1, "fecha": "2026-09-02", "nota": 9.5, "duracion_min": 15.0, "obs": "Excelente estructura y articulado."},
            {"n": 2, "fecha": "2026-09-04", "nota": 9.0, "duracion_min": 14.2, "obs": "Sin fallos significativos."},
            {"n": 3, "fecha": "2026-09-08", "nota": 9.0, "duracion_min": 14.0, "obs": "Dominado con fluidez."},
        ],
        "proximo_repaso_manual": None,
    },
    {
        "id": 2,
        "tema": "T39 LO 4/00 Ley de Extranjería",
        "fecha_inicio": "2026-09-01",
        "historial": [
            {"n": 1, "fecha": "2026-09-02", "nota": 4.5, "duracion_min": 12.5, "obs": "Primer cante, dudas en artículos."},
            {"n": 2, "fecha": "2026-09-04", "nota": 7.0, "duracion_min": 10.2, "obs": "Mejora sustancial en la exposición."},
            {"n": 3, "fecha": "2026-09-08", "nota": 7.0, "duracion_min": 9.5, "obs": "Buena fluidez general."},
        ],
        "proximo_repaso_manual": None,
    },
]


def parse_dates(data):
    for t in data:
        if isinstance(t["fecha_inicio"], str):
            t["fecha_inicio"] = datetime.strptime(t["fecha_inicio"], "%Y-%m-%d").date()
        if t.get("proximo_repaso_manual") and isinstance(t["proximo_repaso_manual"], str):
            t["proximo_repaso_manual"] = datetime.strptime(t["proximo_repaso_manual"], "%Y-%m-%d").date()
        for h in t["historial"]:
            if isinstance(h["fecha"], str):
                h["fecha"] = datetime.strptime(h["fecha"], "%Y-%m-%d").date()
    return data


def serialize_data(data):
    salida = []
    for t in data:
        manual = t.get("proximo_repaso_manual")
        salida.append({
            "id": t["id"],
            "tema": t["tema"],
            "fecha_inicio": t["fecha_inicio"].strftime("%Y-%m-%d") if isinstance(t["fecha_inicio"], (date, datetime)) else t["fecha_inicio"],
            "proximo_repaso_manual": manual.strftime("%Y-%m-%d") if isinstance(manual, (date, datetime)) else manual,
            "historial": [
                {
                    "n": h["n"],
                    "fecha": h["fecha"].strftime("%Y-%m-%d") if isinstance(h["fecha"], (date, datetime)) else h["fecha"],
                    "nota": h["nota"],
                    "duracion_min": h["duracion_min"],
                    "obs": h["obs"],
                }
                for h in t["historial"]
            ],
        })
    return salida


def cargar_datos():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return parse_dates(json.load(f))
        except Exception as e:
            st.error(f"No se pudo leer temas_data.json ({e}). Se conserva como temas_data.json.corrupto.")
            os.replace(DATA_FILE, DATA_FILE + ".corrupto")
            copias = sorted(glob(os.path.join(BACKUP_DIR, "temas_*.json")))
            if copias:
                try:
                    with open(copias[-1], "r", encoding="utf-8") as f:
                        st.warning(f"Se ha recuperado la copia automática más reciente: {os.path.basename(copias[-1])}")
                        return parse_dates(json.load(f))
                except Exception:
                    pass
    return parse_dates(copy.deepcopy(TEMAS_DEFAULT))


if "temas_db" not in st.session_state:
    st.session_state.temas_db = cargar_datos()


def guardar_todo():
    """Guarda en local de forma inmediata y mantiene una copia automática por día."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.exists(DATA_FILE):
        destino = os.path.join(BACKUP_DIR, f"temas_{hoy().strftime('%Y%m%d')}.json")
        if not os.path.exists(destino):
            shutil.copy2(DATA_FILE, destino)
        for viejo in sorted(glob(os.path.join(BACKUP_DIR, "temas_*.json")))[:-MAX_COPIAS]:
            os.remove(viejo)
    escribir_json(DATA_FILE, serialize_data(st.session_state.temas_db))


# ---------------------------------------------------------------------------
# CÁLCULO DE LA PRÓXIMA FECHA (adaptativo según la nota)
# ---------------------------------------------------------------------------
def calcular_paso(historial):
    """Posición actual en la escala de intervalos, según el rendimiento de cada cante."""
    paso = 0
    for h in historial:
        nota = h["nota"]
        if nota is None or nota >= cfg["umbral_avanzar"]:
            paso += 1
        elif nota < cfg["umbral_repetir"]:
            paso = 0
        # Entre ambos umbrales: se mantiene el mismo paso.
    return paso


def calcular_proxima_fecha(historial, fecha_inicio, fecha_manual=None):
    if fecha_manual is not None:
        return fecha_manual
    if not historial:
        return fecha_inicio + timedelta(days=cfg["intervalos"][0])

    ultima_fecha = historial[-1]["fecha"]
    intervalos = cfg["intervalos"]
    dias = intervalos[min(calcular_paso(historial), len(intervalos) - 1)]

    if cfg.get("fecha_examen"):
        try:
            restantes = (date.fromisoformat(cfg["fecha_examen"]) - ultima_fecha).days
            if restantes > 0:
                dias = min(dias, max(1, round(restantes * PROPORCION_EXAMEN)))
        except ValueError:
            pass
    return ultima_fecha + timedelta(days=dias)


# ---------------------------------------------------------------------------
# BARRA LATERAL
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("🛡️ Estado de Protección")
    st.success("💾 Guardado automático en local")
    st.caption(f"Archivo: {DATA_FILE}")
    st.caption(f"Copias diarias (últimas {MAX_COPIAS}): {BACKUP_DIR}")
    st.caption(f"Hoy en la app: {hoy().strftime('%d/%m/%Y')} ({cfg['zona_horaria']})")

    with st.expander("⚙️ Ajustes de repaso y hora"):
        with st.form("form_config"):
            txt_int = st.text_input(
                "Intervalos en días (separados por comas):",
                value=", ".join(str(i) for i in cfg["intervalos"]),
                help="El último intervalo se repite indefinidamente en la fase de mantenimiento.",
            )
            zona = st.text_input("Zona horaria:", value=cfg["zona_horaria"], help="Ejemplos: Europe/Madrid, Atlantic/Canary")
            usar_examen = st.checkbox("Tengo fecha de examen", value=bool(cfg.get("fecha_examen")))
            fecha_ex = st.date_input(
                "Fecha del examen:",
                value=date.fromisoformat(cfg["fecha_examen"]) if cfg.get("fecha_examen") else hoy() + timedelta(days=120),
            )
            u_rep = st.number_input("Nota por debajo de la cual se reinicia el tema:", 0.0, 10.0, float(cfg["umbral_repetir"]), 0.25)
            u_av = st.number_input("Nota a partir de la cual se avanza de intervalo:", 0.0, 10.0, float(cfg["umbral_avanzar"]), 0.25)

            if st.form_submit_button("Guardar ajustes"):
                try:
                    nuevos = [int(x.strip()) for x in txt_int.split(",") if x.strip()]
                    if not nuevos or any(n < 1 for n in nuevos):
                        raise ValueError("Los intervalos deben ser enteros positivos.")
                    ZoneInfo(zona.strip())
                    if u_rep > u_av:
                        raise ValueError("El umbral de reinicio no puede superar al de avance.")
                    cfg.update({
                        "intervalos": nuevos,
                        "zona_horaria": zona.strip(),
                        "fecha_examen": fecha_ex.isoformat() if usar_examen else None,
                        "umbral_repetir": float(u_rep),
                        "umbral_avanzar": float(u_av),
                    })
                    escribir_json(CONFIG_FILE, cfg)
                    st.success("Ajustes guardados.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ajustes no válidos: {e}")

    st.markdown("---")
    st.markdown("**Copia manual (opcional):**")
    st.download_button(
        label="📥 Descargar copia (.json)",
        data=json.dumps(serialize_data(st.session_state.temas_db), ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"backup_oposicion_{hoy().strftime('%Y_%m_%d')}.json",
        mime="application/json",
        use_container_width=True,
    )

    if "up_key" not in st.session_state:
        st.session_state.up_key = 0
    subido = st.file_uploader("📤 Restaurar copia (.json)", type=["json"], key=f"uploader_{st.session_state.up_key}")
    if subido is not None:
        try:
            st.session_state.temas_db = parse_dates(json.load(subido))
            guardar_todo()
            st.session_state.up_key += 1
            st.rerun()
        except Exception as e:
            st.error(f"Error al cargar copia: {e}")

# ---------------------------------------------------------------------------
# PESTAÑAS
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📌 Dashboard & Semáforo",
    "➕ Añadir Nuevo Tema",
    "🎙️ Modo Simulacro (Cante)",
    "🛠️ Modificar / Ajustar Fechas y Cantes",
    "📊 Evolución & Notas",
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("📋 Estado Diario del Temario")
    fecha_hoy = hoy()

    if not st.session_state.temas_db:
        st.warning("No hay temas registrados.")
    else:
        filas = []
        for t in st.session_state.temas_db:
            hist = t["historial"]
            n = len(hist)
            proximo = calcular_proxima_fecha(hist, t["fecha_inicio"], t.get("proximo_repaso_manual"))
            notas = [h["nota"] for h in hist if h["nota"] is not None]
            media = round(sum(notas) / len(notas), 2) if notas else "-"

            if proximo == fecha_hoy:
                estado = "🟢 TOCA HOY"
            elif proximo < fecha_hoy:
                estado = f"🔴 ATRASADO ({(fecha_hoy - proximo).days} d)"
            elif proximo == fecha_hoy + timedelta(days=1):
                estado = "🟡 MAÑANA"
            else:
                estado = f"⚪ {proximo.strftime('%d/%m/%Y')}"

            en_mantenimiento = calcular_paso(hist) >= len(cfg["intervalos"]) - 1 and n > 0
            fase = f"♻️ Mantenimiento (#{n})" if en_mantenimiento else f"Vuelta #{n}"

            filas.append((proximo, {
                "Tema": t["tema"],
                "Fecha Estudio Inicial": t["fecha_inicio"].strftime("%d/%m/%Y"),
                "Fase de Cante": fase,
                "Cantes Realizados": n,
                "Última Nota": hist[-1]["nota"] if hist else "-",
                "Próximo Repaso": proximo.strftime("%d/%m/%Y"),
                "Estado Alerta": estado,
                "Nota Media": media,
            }))

        filas.sort(key=lambda x: x[0])
        df_dash = pd.DataFrame([f for _, f in filas])

        opciones = ["🟢 TOCA HOY", "🔴 ATRASADO", "🟡 MAÑANA", "⚪ FUTURO"]
        filtro = st.multiselect("Filtrar por estado:", options=opciones, default=opciones)
        emojis = tuple(o.split()[0] for o in filtro)
        df_dash = df_dash[df_dash["Estado Alerta"].apply(lambda x: x.startswith(emojis))] if emojis else df_dash.iloc[0:0]

        st.dataframe(df_dash, use_container_width=True)

# --- TAB 2: AÑADIR NUEVO TEMA ---
with tab2:
    st.subheader("➕ Incorporar Nuevo Tema al Calendario")

    with st.form("form_nuevo_tema", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            nuevo_nombre = st.text_input("Nombre o Código del Tema:", placeholder="Ej: T25 Inmovilización y retirada de vehículos")
        with c2:
            nueva_fecha_inicio = st.date_input("Fecha de estudio inicial:", value=hoy())

        if st.form_submit_button("🚀 Añadir Tema a la Lista"):
            if nuevo_nombre.strip() == "":
                st.error("Por favor, introduce el nombre del tema.")
            elif nuevo_nombre.strip() in [t["tema"] for t in st.session_state.temas_db]:
                st.error("Ya existe un tema con ese nombre.")
            else:
                nuevo_id = max([t["id"] for t in st.session_state.temas_db], default=0) + 1
                st.session_state.temas_db.append({
                    "id": nuevo_id,
                    "tema": nuevo_nombre.strip(),
                    "fecha_inicio": nueva_fecha_inicio,
                    "historial": [],
                    "proximo_repaso_manual": None,
                })
                guardar_todo()
                st.toast(f"✅ ¡Tema '{nuevo_nombre}' guardado!", icon="🎉")
                st.rerun()

    st.markdown("---")
    st.subheader("📚 Listado Completo de Temas")
    resumen = [
        {"ID": t["id"], "Tema": t["tema"], "Fecha Inicial": t["fecha_inicio"].strftime("%d/%m/%Y"), "Total Cantes": len(t["historial"])}
        for t in st.session_state.temas_db
    ]
    st.table(pd.DataFrame(resumen))

# --- TAB 3: MODO SIMULACRO / CANTE ---
with tab3:
    st.subheader("🎙️ Modo Simulacro de Cante")

    if not st.session_state.temas_db:
        st.warning("No hay temas disponibles.")
    else:
        nombres = [t["tema"] for t in st.session_state.temas_db]

        with st.form("form_registrar_cante", clear_on_submit=True):
            tema_cantar = st.selectbox("Selecciona el tema a registrar/cantar:", nombres)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### ⏱️ Fecha y Tiempo del Cante")
                fecha_cante = st.date_input("🗓️ Fecha real del cante:", value=hoy())
                duracion = st.number_input("Duración del cante (minutos):", min_value=0.0, max_value=120.0, value=12.0, step=0.5)
            with c2:
                st.markdown("### 📝 Evaluación de tu Pareja")
                nota_c = st.slider("Nota asignada (0.0 a 10.0):", min_value=0.0, max_value=10.0, value=7.5, step=0.25)
                obs_c = st.text_area("Anotaciones / Feedback:", placeholder="Ej: Excelente dicción.")

            if st.form_submit_button("💾 REGISTRAR CANTE Y RECALCULAR"):
                idx = next(i for i, t in enumerate(st.session_state.temas_db) if t["tema"] == tema_cantar)
                hist = st.session_state.temas_db[idx]["historial"]
                hist.append({"n": len(hist) + 1, "fecha": fecha_cante, "nota": nota_c, "duracion_min": duracion, "obs": obs_c})

                hist = sorted(hist, key=lambda x: x["fecha"])
                for i_h, h_item in enumerate(hist):
                    h_item["n"] = i_h + 1

                st.session_state.temas_db[idx]["historial"] = hist
                st.session_state.temas_db[idx]["proximo_repaso_manual"] = None
                guardar_todo()

                proxima = calcular_proxima_fecha(hist, st.session_state.temas_db[idx]["fecha_inicio"])
                st.session_state["aviso"] = f"🎉 Cante #{len(hist)} guardado. Próximo repaso: {proxima.strftime('%d/%m/%Y')}."
                st.rerun()

# --- TAB 4: MODIFICAR / AJUSTAR FECHAS Y CANTES ---
with tab4:
    st.subheader("🛠️ Gestión de Imprevistos, Edición y Borrado")

    if not st.session_state.temas_db:
        st.warning("No hay temas registrados.")
    else:
        nombres = [t["tema"] for t in st.session_state.temas_db]
        tema_mod = st.selectbox("Selecciona el Tema a gestionar:", nombres, key="sel_mod_tema")

        idx_t = next(i for i, t in enumerate(st.session_state.temas_db) if t["tema"] == tema_mod)
        t_obj = st.session_state.temas_db[idx_t]
        tid = t_obj["id"]

        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.markdown("### 🗓️ Ajustar Próxima Fecha por Imprevisto")
            defecto = calcular_proxima_fecha(t_obj["historial"], t_obj["fecha_inicio"], t_obj.get("proximo_repaso_manual"))
            nueva_manual = st.date_input("Nueva fecha programada para el cante:", value=defecto, key=f"fecha_manual_{tid}")

            if st.button("📌 Reagendar Próximo Cante"):
                st.session_state.temas_db[idx_t]["proximo_repaso_manual"] = nueva_manual
                guardar_todo()
                st.toast("✅ Fecha actualizada", icon="🗓️")
                st.rerun()

        with col_m2:
            st.markdown("### 🗑️ Modificar / Eliminar Cantes")
            hist = t_obj["historial"]

            if not hist:
                st.info("Sin cantes registrados.")
            else:
                opciones = [f"Repaso #{h['n']} - Fecha: {h['fecha'].strftime('%d/%m/%Y')} - Nota: {h['nota']}" for h in hist]
                sel = st.selectbox("Selecciona cante:", opciones, key=f"sel_cante_{tid}")
                idx_c = opciones.index(sel)
                cante = hist[idx_c]
                k = f"{tid}_{idx_c}"

                with st.expander("✏️ Editar cante", expanded=True):
                    ed_fecha = st.date_input("Fecha:", value=cante["fecha"], key=f"ed_f_{k}")
                    ed_nota = st.slider("Nota:", 0.0, 10.0, float(cante["nota"] or 0.0), 0.25, key=f"ed_n_{k}")
                    ed_min = st.number_input("Duración (min):", 0.0, 120.0, float(cante["duracion_min"] or 0.0), 0.5, key=f"ed_m_{k}")
                    ed_obs = st.text_area("Observaciones:", value=cante["obs"] or "", key=f"ed_o_{k}")

                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("💾 Guardar Cambios", key=f"btn_save_{k}"):
                            hist[idx_c] = {"n": cante["n"], "fecha": ed_fecha, "nota": ed_nota, "duracion_min": ed_min, "obs": ed_obs}
                            hist = sorted(hist, key=lambda x: x["fecha"])
                            for i_h, h_item in enumerate(hist):
                                h_item["n"] = i_h + 1
                            st.session_state.temas_db[idx_t]["historial"] = hist
                            st.session_state.temas_db[idx_t]["proximo_repaso_manual"] = None
                            guardar_todo()
                            st.toast("✅ Cante modificado", icon="💾")
                            st.rerun()
                    with b2:
                        if st.button("❌ Eliminar Cante", key=f"btn_del_{k}"):
                            hist.pop(idx_c)
                            for new_i, item in enumerate(hist):
                                item["n"] = new_i + 1
                            st.session_state.temas_db[idx_t]["historial"] = hist
                            st.session_state.temas_db[idx_t]["proximo_repaso_manual"] = None
                            guardar_todo()
                            st.toast("🗑️ Cante eliminado", icon="🗑️")
                            st.rerun()

# --- TAB 5: EVOLUCIÓN & NOTAS ---
with tab5:
    st.subheader("📊 Análisis de Evolución por Tema")
    if not st.session_state.temas_db:
        st.warning("Sin datos.")
    else:
        nombres = [t["tema"] for t in st.session_state.temas_db]
        tema_analisis = st.selectbox("Elige tema:", nombres, key="sel_analisis")

        obj_tema = next(t for t in st.session_state.temas_db if t["tema"] == tema_analisis)
        df_hist = pd.DataFrame(obj_tema["historial"])

        if not df_hist.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Nota Media Global", f"{df_hist['nota'].mean():.2f} / 10")
            m2.metric("Último Cante", f"{df_hist['nota'].iloc[-1]} / 10")
            m3.metric("Tiempo Medio de Cante", f"{df_hist['duracion_min'].mean():.1f} min")

            st.markdown("#### Progreso de Calificaciones")
            st.line_chart(df_hist.set_index("n")[["nota"]])

            st.markdown("#### Registro Histórico Completo")
            st.dataframe(
                df_hist[["n", "fecha", "nota", "duracion_min", "obs"]].rename(columns={
                    "n": "Nº Repaso", "fecha": "Fecha", "nota": "Nota", "duracion_min": "Minutos", "obs": "Observaciones",
                }),
                use_container_width=True,
            )
        else:
            st.info("Este tema no tiene cantes registrados.")
