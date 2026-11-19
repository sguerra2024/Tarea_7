import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().with_name(".env"), override=False)

PACKAGE_SOURCE = Path(__file__).resolve().parent / "agente_triz" / "src"
if str(PACKAGE_SOURCE) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SOURCE))

from agente_triz import AgenteTRIZ, construir_prompt_solucion
from agente_triz.exportacion import FORMATOS, exportar_analisis
from agente_triz.principios import DESCRIPCIONES_PRINCIPIOS, PRINCIPIOS_INVENTIVOS
from agente_triz.vias import VIAS_SOLUCION

TIPOS_PROBLEMAS = {
    "Hogar y tareas diarias": "Cómo limpiar, cocinar, ordenar o hacer pequeñas reparaciones con menos esfuerzo.",
    "Tiempo y organización": "Cómo organizar pendientes, evitar olvidos y aprovechar mejor el día.",
    "Transporte y desplazamientos": "Cómo llevar objetos, hacer compras o llegar a un lugar con menos dificultades.",
    "Accesibilidad e inclusión": "Cómo facilitar que las personas con discapacidad suban y bajen de un autobús y utilicen servicios cotidianos.",
    "Trabajo y estudio": "Cómo concentrarse, aprender algo o simplificar una tarea repetitiva.",
    "Gastos y ahorro": "Cómo reducir gastos, ahorrar agua o energía y aprovechar lo que ya tenemos.",
    "Mejorar algo pero: Empeorar el sistema en otro punto": "Cómo mejorar un aspecto del sistema cuando esa mejora empeora otro.",
    "Otro problema": "Describe una dificultad de tu día a día que te gustaría resolver.",
}

ENLACE_INSPIRACION = "http://www.productioninspiration.com/"
AYUDA_CONTRADICCIONES = (
    "Técnica: al mejorar una característica, otra empeora. "
    "Física: el mismo elemento necesita propiedades opuestas. "
    "Identifica qué quieres mejorar y qué se deteriora. La matriz clásica "
    "sugiere principios inventivos para el par seleccionado."
)
SOLICITUD_LEAN = (
    "Complementa las vías TRIZ seleccionadas con recomendaciones de Lean "
    "Production. Distingue hipótesis de desperdicio de hechos observados y "
    "propón un piloto reversible con medición antes y después: tiempo de "
    "ciclo, retrabajo o calidad, según corresponda. No presupongas fallas "
    "ni garantices ahorros sin evidencia."
)
MIME_EXPORTACION = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def mostrar_exportacion(analisis: str) -> None:
    extension = st.selectbox(
        "Formato de exportación",
        list(FORMATOS),
        format_func=FORMATOS.__getitem__,
        key="formato_exportacion_triz",
    )
    nombre = f"Analisis_TRIZ{extension}"
    try:
        with TemporaryDirectory() as directorio:
            ruta = Path(directorio) / nombre
            exportar_analisis(ruta, analisis)
            contenido = ruta.read_bytes()
    except (ImportError, OSError, ValueError):
        st.error(f"No se pudo preparar la descarga en {FORMATOS[extension]}. El análisis sigue disponible.")
        return
    st.download_button(
        f"Descargar análisis en {FORMATOS[extension]}",
        data=contenido,
        file_name=nombre,
        mime=MIME_EXPORTACION[extension],
        on_click="ignore",
    )


@st.cache_data
def cargar_matriz_contradicciones():
    ruta_matriz = (
        Path(__file__).resolve().parent
        / "agente_triz"
        / "src"
        / "agente_triz"
        / "data"
        / "matriz_contradicciones_triz.json"
    )
    try:
        matriz_json = json.loads(ruta_matriz.read_text(encoding="utf-8"))
        parametros = matriz_json["parametros"]
        pares = matriz_json["matriz"]
        if not isinstance(parametros, list) or not isinstance(pares, list):
            raise ValueError("El formato de la matriz no contiene listas válidas.")
        nombres_parametros = {
            parametro["id"]: parametro["nombre"]
            for parametro in parametros
        }
        principios_por_par = {
            fila["parametro_a_mejorar"]: {
                conflicto["parametro_perjudicado"]: conflicto[
                    "principios_recomendados"
                ]
                for conflicto in fila["conflictos"]
            }
            for fila in pares
        }
        if len(nombres_parametros) != 39 or len(principios_por_par) != 39:
            raise ValueError("La matriz debe contener los 39 parámetros TRIZ.")
        return nombres_parametros, principios_por_par
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(
            f"No se pudo cargar la matriz clásica de contradicciones TRIZ: {exc}"
        ) from exc


def obtener_principios_recomendados(parametro_mejorar, parametro_perjudicado):
    """Devuelve los números de principios clásicos para una contradicción."""
    _, principios_por_par = cargar_matriz_contradicciones()
    return principios_por_par.get(parametro_mejorar, {}).get(
        parametro_perjudicado, []
    )


def cerrar_dialogo():
    st.session_state["dialogo_problema_abierto"] = False


@st.dialog(
    "Configurar asistencia con IA",
    width="large",
    on_dismiss=cerrar_dialogo,
)
def configurar_problema():
    seleccion = st.session_state.get("seleccion_problema", {})
    modo = st.radio(
        "Modo de asistencia",
        ["Exploración guiada con TRIZ", "Diálogo libre con agente IA (sin TRIZ)"],
        index=(
            1 if seleccion.get("modo") == "general" else 0
        ),
        horizontal=True,
    )
    if modo == "Exploración guiada con TRIZ":
        nombres_parametros, _ = cargar_matriz_contradicciones()
        ids_parametros = list(nombres_parametros)
    else:
        nombres_parametros = {}
        ids_parametros = []
    mejorar_guardado = seleccion.get("parametro_mejorar")
    perjudicado_guardado = seleccion.get("parametro_perjudicado")
    with st.form("configuracion_problema"):
        if modo == "Exploración guiada con TRIZ":
            tipos = list(TIPOS_PROBLEMAS)
            if not tipos:
                st.error("No hay tipos de problemas configurados. Agrega opciones en TIPOS_PROBLEMAS.")
                return
            tipo_guardado = seleccion.get("tipo")
            if tipo_guardado is not None and tipo_guardado not in TIPOS_PROBLEMAS:
                st.warning("El tipo guardado ya no está disponible. Selecciona uno de los tipos actuales.")
            st.write("Define el problema y elige una o varias vías para explorarlo.")
            tipo = st.selectbox(
                "Tipo de problema",
                tipos,
                index=tipos.index(tipo_guardado) if tipo_guardado in tipos else 0,
                help="\n\n".join(
                    f"{nombre}: {descripcion}"
                    for nombre, descripcion in TIPOS_PROBLEMAS.items()
                ),
            )
            st.caption(TIPOS_PROBLEMAS[tipo])
            st.markdown("### Parámetros de la contradicción (matriz TRIZ)")
            parametro_mejorar = st.selectbox(
                "Parámetro que quiero mejorar",
                ids_parametros,
                index=(
                    ids_parametros.index(mejorar_guardado)
                    if mejorar_guardado in ids_parametros
                    else 0
                ),
                format_func=lambda identificador: (
                    f"{identificador}. {nombres_parametros[identificador]}"
                ),
                help="Selecciona la característica del sistema que quieres mejorar.",
            )
            parametro_perjudicado = st.selectbox(
                "Parámetro que empeora",
                ids_parametros,
                index=(
                    ids_parametros.index(perjudicado_guardado)
                    if perjudicado_guardado in ids_parametros
                    else 1
                ),
                format_func=lambda identificador: (
                    f"{identificador}. {nombres_parametros[identificador]}"
                ),
                help="Selecciona la característica que se deteriora al mejorar la otra.",
            )
            descripcion = st.text_area(
                "Describe el problema",
                value=seleccion.get("descripcion", ""),
                placeholder="Qué ocurre, qué esperas conseguir y qué restricciones existen.",
            )
            st.markdown("### Vías de solución TRIZ")
            vias = []
            accion_mejorar = ""
            for clave, texto in VIAS_SOLUCION.items():
                if st.checkbox(
                    texto,
                    value=clave in seleccion.get("vias", []),
                    key=f"via_{clave}",
                ):
                    vias.append(clave)
                if clave == "contradicciones":
                    st.caption(AYUDA_CONTRADICCIONES)
                if clave == "problema_generico":
                    accion_mejorar = st.text_input(
                        "1.1 ¿Qué acción quiero mejorar?",
                        value=seleccion.get("accion_mejorar", ""),
                        placeholder="Por ejemplo: transportar, enfriar o reducir desperdicios.",
                    )
                    st.markdown(f"[Production Inspiration]({ENLACE_INSPIRACION})")
            incluir_lean = st.checkbox(
                "Incluir recomendaciones de Lean Production",
                value=seleccion.get("incluir_lean", False),
                key="incluir_lean_triz",
                help="Complementa las vías TRIZ con ideas para reducir esperas, desperdicio o retrabajo.",
            )
        else:
            st.write(
                "Conversa directamente con el agente. No necesitas elegir vías "
                "ni usar herramientas TRIZ."
            )
        guardar = st.form_submit_button("Continuar")
    if guardar:
        if modo == "Exploración guiada con TRIZ" and not descripcion.strip():
            st.error("Describe el problema antes de guardar.")
            return
        if modo == "Exploración guiada con TRIZ" and not vias:
            st.error("Selecciona al menos una vía de solución.")
            return
        es_general = modo == "Diálogo libre con agente IA (sin TRIZ)"
        st.session_state["seleccion_problema"] = {
            "modo": "general" if es_general else "triz",
            "tipo": tipo if not es_general else "",
            "descripcion": descripcion.strip() if not es_general else "",
            "vias": vias if not es_general else [],
            "incluir_lean": incluir_lean if not es_general else False,
            "accion_mejorar": accion_mejorar.strip() if not es_general else "",
            "parametro_mejorar": parametro_mejorar if not es_general else None,
            "parametro_perjudicado": (
                parametro_perjudicado if not es_general else None
            ),
        }
        st.session_state.pop("analisis_triz", None)
        st.session_state["conversacion_ia"] = []
        cerrar_dialogo()
        st.rerun()


st.header("Innovative")
st.write("El problema es tu oportunidad")
if st.button("Configurar asistencia con IA"):
    st.session_state["dialogo_problema_abierto"] = True

if "seleccion_problema" in st.session_state:
    seleccion = st.session_state["seleccion_problema"]
    if seleccion.get("modo") == "general":
        st.subheader("Diálogo libre con el agente IA")
        st.caption("Esta conversación no usa herramientas ni contexto TRIZ.")
        for mensaje in st.session_state.get("conversacion_ia", []):
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])
        entrada = st.chat_input(
            "Escribe tu mensaje al agente",
            key="mensaje_dialogo_ia",
        )
        if entrada:
            conversacion = st.session_state.setdefault("conversacion_ia", [])
            conversacion.append({"role": "user", "content": entrada})
            agente = None
            try:
                with st.spinner("El agente está respondiendo..."):
                    agente = AgenteTRIZ()
                    respuesta = agente.conversar(conversacion)
            except RuntimeError as exc:
                st.error(f"No se pudo consultar al agente IA: {exc}")
            else:
                if respuesta:
                    conversacion.append(
                        {"role": "assistant", "content": respuesta}
                    )
                else:
                    st.warning("El agente no devolvió una respuesta. Inténtalo de nuevo.")
            finally:
                if agente is not None:
                    agente.cerrar()
    else:
        st.subheader(seleccion["tipo"])
        if seleccion["tipo"] in TIPOS_PROBLEMAS:
            st.caption(TIPOS_PROBLEMAS[seleccion["tipo"]])
        else:
            st.warning("El tipo guardado ya no está disponible. Abre el diálogo para actualizarlo.")
        st.write(seleccion["descripcion"])
        st.markdown("### Vías seleccionadas")
        for via in seleccion["vias"]:
            st.write(VIAS_SOLUCION[via])
            if via == "contradicciones":
                st.caption(AYUDA_CONTRADICCIONES)
            if via == "problema_generico":
                st.markdown("#### 1.1 ¿Qué acción quiero mejorar?")
                if seleccion.get("accion_mejorar"):
                    st.write(seleccion["accion_mejorar"])
                st.markdown(f"[Production Inspiration]({ENLACE_INSPIRACION})")
        parametros = cargar_matriz_contradicciones()[0]
        principios_matriz = []
        if (
            "contradicciones" in seleccion["vias"]
            and seleccion.get("parametro_mejorar") in parametros
            and seleccion.get("parametro_perjudicado") in parametros
        ):
            parametro_mejorar = seleccion["parametro_mejorar"]
            parametro_perjudicado = seleccion["parametro_perjudicado"]
            principios_matriz = obtener_principios_recomendados(
                parametro_mejorar,
                parametro_perjudicado,
            )
            st.markdown("### Resultado de la matriz clásica de contradicciones")
            st.write(
                f"Mejorar: {parametro_mejorar}. "
                f"{parametros[parametro_mejorar]}"
            )
            st.write(
                f"Empeora: {parametro_perjudicado}. "
                f"{parametros[parametro_perjudicado]}"
            )
            if principios_matriz:
                st.caption(
                    "Principios recomendados por la matriz (orientación para "
                    "generar y validar alternativas, no soluciones garantizadas):"
                )
                for numero in principios_matriz:
                    identificador, nombre = PRINCIPIOS_INVENTIVOS[numero - 1]
                    st.markdown(f"**{nombre}**")
                    st.write(DESCRIPCIONES_PRINCIPIOS[identificador])
            else:
                st.warning(
                    "La matriz clásica no recomienda principios para este par. "
                    "Esto no significa que la contradicción carezca de solución."
                )
        elif "contradicciones" in seleccion["vias"]:
            st.warning(
                "Abre la configuración para seleccionar los parámetros que "
                "mejoran y empeoran, y consultar la matriz de contradicciones."
            )
        st.caption(
            "Al solicitar el análisis, el problema, las vías seleccionadas y "
            "la solicitud de recomendaciones Lean (si se seleccionó) se enviarán a OpenRouter."
        )
        if seleccion.get("incluir_lean"):
            st.caption("El análisis incluirá recomendaciones de Lean Production.")
        if st.button("Generar análisis TRIZ", key="generar_analisis_triz"):
            problema = (
                f"Tipo de problema: {seleccion['tipo']}\n"
                f"Descripción: {seleccion['descripcion']}"
            )
            if seleccion.get("accion_mejorar"):
                problema += (
                    "\nAcción que se quiere mejorar: "
                    f"{seleccion['accion_mejorar']}"
                )
            if (
                "contradicciones" in seleccion["vias"]
                and seleccion.get("parametro_mejorar") in parametros
                and seleccion.get("parametro_perjudicado") in parametros
            ):
                problema += (
                    "\nContradicción seleccionada en la matriz TRIZ: mejorar "
                    f"'{parametros[parametro_mejorar]}' mientras empeora "
                    f"'{parametros[parametro_perjudicado]}'."
                )
                if principios_matriz:
                    principios_detallados = []
                    for numero in principios_matriz:
                        identificador, nombre = PRINCIPIOS_INVENTIVOS[numero - 1]
                        principios_detallados.append(
                            f"{nombre}: {DESCRIPCIONES_PRINCIPIOS[identificador]}"
                        )
                    problema += (
                        "\nPrincipios recomendados por la matriz:\n- "
                        + "\n- ".join(principios_detallados)
                        + "\nÚsalos como sugerencias para generar alternativas "
                        "específicas y explicar cómo validarlas; no los presentes "
                        "como soluciones garantizadas."
                    )
                else:
                    problema += (
                        "\nLa matriz clásica no recomienda principios para este "
                        "par. Explora alternativas TRIZ apropiadas sin inventar "
                        "una recomendación de la matriz."
                    )
            identificadores_principios = [
                PRINCIPIOS_INVENTIVOS[numero - 1][0]
                for numero in principios_matriz
            ]
            prompt = construir_prompt_solucion(
                problema,
                enlaces="",
                vias_seleccionadas=seleccion["vias"],
                principios_activos=identificadores_principios,
            )
            if seleccion.get("incluir_lean"):
                prompt += "\n\n" + SOLICITUD_LEAN
            agente = None
            try:
                with st.spinner("Analizando el problema con enfoque TRIZ..."):
                    agente = AgenteTRIZ()
                    respuesta = agente.consultar(prompt)
            except RuntimeError as exc:
                st.error(f"No se pudo generar el análisis TRIZ: {exc}")
            else:
                if respuesta and respuesta.strip():
                    st.session_state["analisis_triz"] = respuesta
                else:
                    st.warning("El agente no devolvió una respuesta. Inténtalo de nuevo.")
            finally:
                if agente is not None:
                    agente.cerrar()

        if st.session_state.get("analisis_triz"):
            st.markdown("### Análisis TRIZ")
            st.markdown(st.session_state["analisis_triz"])
            mostrar_exportacion(st.session_state["analisis_triz"])

st.caption(
    "Production Inspiration se abre en otra pestaña. "
    "Regresa a esta pestaña para continuar en el diálogo."
)
if st.button("Volver al diálogo inicial", key="volver_dialogo_inicial"):
    st.session_state["dialogo_problema_abierto"] = True

if st.session_state.get("dialogo_problema_abierto", False):
    configurar_problema()