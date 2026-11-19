from io import BytesIO
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"
PACKAGE_SOURCE = APP.parent / "agente_triz" / "src"
sys.path.insert(0, str(PACKAGE_SOURCE))

import agente_triz
import streamlit as st


class AgenteTRIZSimulado:
    def consultar(self, prompt):
        st.session_state["prompt_triz_prueba"] = prompt
        if st.session_state.get("error_triz_prueba"):
            raise RuntimeError("error simulado")
        return "Alternativa TRIZ para validar."

    def conversar(self, mensajes):
        st.session_state["mensajes_ia_prueba"] = list(mensajes)
        if st.session_state.get("error_triz_prueba"):
            raise RuntimeError("error simulado")
        return "Respuesta general para validar."

    def cerrar(self):
        st.session_state["agente_triz_cerrado"] = True


def abrir_dialogo():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button[0].click().run()
    assert not app.exception
    return app


def abrir_app_con_agente_simulado(error=False):
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["seleccion_problema"] = {
        "modo": "triz",
        "tipo": "Transporte y desplazamientos",
        "descripcion": "Trasladar objetos con menos esfuerzo",
        "vias": ["problema_generico", "contradicciones"],
        "accion_mejorar": "Transportar objetos",
        "parametro_mejorar": 1,
        "parametro_perjudicado": 3,
    }
    app.session_state["error_triz_prueba"] = error
    with patch.object(agente_triz, "AgenteTRIZ", AgenteTRIZSimulado):
        app.run()
        app.button(key="generar_analisis_triz").click().run()
    return app


def test_dialogo_muestra_tipos_y_cuatro_vias():
    app = abrir_dialogo()
    assert len(app.selectbox[0].options) == 8
    assert app.selectbox[0].options == [
        "Hogar y tareas diarias",
        "Tiempo y organización",
        "Transporte y desplazamientos",
        "Accesibilidad e inclusión",
        "Trabajo y estudio",
        "Gastos y ahorro",
        "Mejorar algo pero: Empeorar el sistema en otro punto",
        "Otro problema",
    ]
    assert sum(item.key.startswith("via_") for item in app.checkbox) == 4
    assert not app.checkbox(key="incluir_lean_triz").value
    assert len(app.selectbox[1].options) == 39
    assert len(app.selectbox[2].options) == 39


def test_no_muestra_videos_de_youtube_al_elegir_transporte():
    youtube = "youtube.com"
    app = abrir_dialogo()
    assert not any(youtube in elemento.value.lower() for elemento in app.markdown)
    app.selectbox[0].select("Transporte y desplazamientos").run()
    assert not app.exception
    assert not any(youtube in elemento.value.lower() for elemento in app.markdown)
    app.text_area[0].set_value("Facilitar el transporte de objetos")
    app.checkbox[0].check()
    app.button[-1].click().run()
    assert not app.exception
    assert app.session_state["seleccion_problema"]["tipo"] == "Transporte y desplazamientos"
    assert not any(youtube in elemento.value.lower() for elemento in app.markdown)


def test_dialogo_valida_descripcion_y_vias():
    app = abrir_dialogo()
    app.button[-1].click().run()
    assert app.error[0].value == "Describe el problema antes de guardar."
    app.text_area[0].set_value("Reducir errores de estimación")
    app.button[-1].click().run()
    assert app.error[0].value == "Selecciona al menos una vía de solución."


def test_via_contradicciones_resume_conceptos_y_muestra_guia():
    app = abrir_dialogo()
    ayuda = next(
        elemento.value
        for elemento in app.caption
        if "Técnica:" in elemento.value
    )
    assert "al mejorar una característica, otra empeora" in ayuda
    assert "el mismo elemento necesita propiedades opuestas" in ayuda
    app.text_area[0].set_value("Mejorar la resistencia sin aumentar el peso")
    app.checkbox[2].check()
    app.button[-1].click().run()
    assert not app.exception
    assert any("Técnica:" in elemento.value for elemento in app.caption)


def test_matriz_muestra_principios_para_parametro_que_mejora_y_empeora():
    app = abrir_dialogo()
    app.selectbox[1].select(1)
    app.selectbox[2].select(3)
    app.text_area[0].set_value("Reducir el peso sin perder alcance")
    app.checkbox[2].check()
    app.button[-1].click().run()

    assert not app.exception
    seleccion = app.session_state["seleccion_problema"]
    assert seleccion["parametro_mejorar"] == 1
    assert seleccion["parametro_perjudicado"] == 3
    salida = "\n".join(elemento.value for elemento in app.markdown)
    assert "Peso de objeto móvil" in salida
    assert "Longitud de objeto móvil" in salida
    for principio in (
        "15 Dinamicidad",
        "8 Contrapeso",
        "29 Construcción neumática o hidráulica",
        "34 Descartar y recuperar",
    ):
        assert principio in salida


def test_matriz_sin_principios_muestra_aviso_no_concluyente():
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["seleccion_problema"] = {
        "modo": "triz",
        "tipo": "Otro problema",
        "descripcion": "Reducir peso estacionario",
        "vias": ["contradicciones"],
        "accion_mejorar": "",
        "parametro_mejorar": 1,
        "parametro_perjudicado": 2,
    }
    app.run()

    assert not app.exception
    assert any(
        "no recomienda principios" in item.value.lower()
        for item in app.warning
    )
    with patch.object(agente_triz, "AgenteTRIZ", AgenteTRIZSimulado):
        app.button(key="generar_analisis_triz").click().run()
    prompt = app.session_state["prompt_triz_prueba"]
    assert "Peso de objeto móvil" in prompt
    assert "Peso de objeto estacionario" in prompt
    assert "La matriz clásica no recomienda principios" in prompt
    assert "15 Dinamicidad" not in prompt


def test_guardar_y_reabrir_conserva_seleccion():
    app = abrir_dialogo()
    app.selectbox[0].select("Gastos y ahorro")
    app.text_area[0].set_value("Reducir costos sin bajar la calidad")
    app.checkbox[2].check()
    app.button[-1].click().run()
    assert not app.exception
    assert app.session_state["seleccion_problema"] == {
        "modo": "triz",
        "tipo": "Gastos y ahorro",
        "descripcion": "Reducir costos sin bajar la calidad",
        "vias": ["contradicciones"],
        "incluir_lean": False,
        "accion_mejorar": "",
        "parametro_mejorar": 1,
        "parametro_perjudicado": 2,
    }
    assert app.subheader[0].value == "Gastos y ahorro"
    seleccion = app.session_state["seleccion_problema"]
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["seleccion_problema"] = seleccion
    app.run()
    app.button[0].click().run()
    assert app.selectbox[0].value == "Gastos y ahorro"
    assert app.checkbox[2].value
    assert app.text_area[0].value == "Reducir costos sin bajar la calidad"


def test_punto_1_1_guarda_accion_y_oculta_videos():
    app = abrir_dialogo()
    assert app.text_input[0].label == "1.1 ¿Qué acción quiero mejorar?"
    assert any(
        "http://www.productioninspiration.com/" in elemento.value
        for elemento in app.markdown
    )
    assert not any("youtube.com" in elemento.value.lower() for elemento in app.markdown)
    app.text_area[0].set_value("La transferencia tarda demasiado")
    app.checkbox[0].check()
    app.text_input[0].set_value("Transportar materiales")
    app.button[-1].click().run()
    assert not app.exception
    seleccion = app.session_state["seleccion_problema"]
    assert seleccion["accion_mejorar"] == "Transportar materiales"
    assert seleccion["vias"] == ["problema_generico"]
    assert any(elemento.value == "Transportar materiales" for elemento in app.markdown)
    restored = AppTest.from_file(str(APP), default_timeout=30)
    restored.session_state["seleccion_problema"] = seleccion
    restored.run()
    assert any(
        "http://www.productioninspiration.com/" in elemento.value
        for elemento in restored.markdown
    )
    assert not any("youtube.com" in elemento.value.lower() for elemento in restored.markdown)
    restored.button[0].click().run()
    assert restored.text_input[0].value == "Transportar materiales"


def test_boton_volver_abre_dialogo_y_conserva_datos():
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["seleccion_problema"] = {
        "tipo": "Otro problema",
        "descripcion": "Mejorar el transporte",
        "vias": ["problema_generico"],
        "accion_mejorar": "Transportar",
    }
    app.run()
    app.button(key="volver_dialogo_inicial").click().run()
    assert not app.exception
    assert app.session_state["dialogo_problema_abierto"]
    assert app.text_area[0].value == "Mejorar el transporte"
    assert app.text_input[0].value == "Transportar"
    assert app.checkbox[0].value


def test_generar_analisis_envia_problema_y_vias_y_muestra_respuesta():
    app = abrir_app_con_agente_simulado()
    assert not app.exception
    prompt = app.session_state["prompt_triz_prueba"]
    assert "Tipo de problema: Transporte y desplazamientos" in prompt
    assert "Trasladar objetos con menos esfuerzo" in prompt
    assert "Transportar objetos" in prompt
    assert "Elevar el problema específico" in prompt
    assert "contradicción técnica o física" in prompt
    assert "Contradicción seleccionada en la matriz TRIZ" in prompt
    assert "Peso de objeto móvil" in prompt
    assert "Longitud de objeto móvil" in prompt
    assert "15 Dinamicidad" in prompt
    assert "34 Descartar y recuperar" in prompt
    assert "Haga que las características de un objeto" in prompt
    assert "recomendaciones de Lean Production" not in prompt
    assert app.session_state["analisis_triz"] == "Alternativa TRIZ para validar."
    assert app.session_state["agente_triz_cerrado"]
    assert any("Alternativa TRIZ para validar." in item.value for item in app.markdown)


def test_error_del_agente_se_muestra_y_se_cierra():
    app = abrir_app_con_agente_simulado(error=True)
    assert not app.exception
    assert any("error simulado" in item.value for item in app.error)
    assert app.session_state["agente_triz_cerrado"]
    assert "analisis_triz" not in app.session_state
    assert not app.get("download_button")


def test_lean_se_guarda_y_complementa_las_vias_triz():
    app = abrir_dialogo()
    app.text_area[0].set_value("Reducir las esperas en un proceso")
    app.checkbox(key="via_problema_generico").check()
    app.checkbox(key="incluir_lean_triz").check()
    app.button[-1].click().run()
    assert not app.exception
    seleccion = app.session_state["seleccion_problema"]
    assert seleccion["incluir_lean"]
    assert not app.get("download_button")

    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["seleccion_problema"] = seleccion
    app.run()
    with patch.object(agente_triz, "AgenteTRIZ", AgenteTRIZSimulado):
        app.button(key="generar_analisis_triz").click().run()
    assert not app.exception
    prompt = app.session_state["prompt_triz_prueba"]
    assert "Elevar el problema específico" in prompt
    assert "recomendaciones de Lean Production" in prompt
    assert "piloto reversible con medición antes y después" in prompt


@pytest.mark.parametrize(
    ("extension", "nombre", "mime", "archivo_interno"),
    [
        (".pdf", "PDF", "application/pdf", None),
        (".docx", "Word", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "word/document.xml"),
        (".xlsx", "Excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xl/worksheets/sheet1.xml"),
    ],
)
def test_descarga_resultado_web(extension, nombre, mime, archivo_interno):
    app = abrir_app_con_agente_simulado()
    selector = app.selectbox(key="formato_exportacion_triz")
    assert selector.options == ["PDF", "Word", "Excel"]
    with patch.object(st, "download_button", wraps=st.download_button) as descargar:
        selector.select(extension).run()
    assert not app.exception
    descargar.assert_called_once()
    kwargs = descargar.call_args.kwargs
    assert descargar.call_args.args == (f"Descargar análisis en {nombre}",)
    assert kwargs["file_name"] == f"Analisis_TRIZ{extension}"
    assert kwargs["mime"] == mime
    assert kwargs["on_click"] == "ignore"
    if archivo_interno is None:
        assert kwargs["data"].startswith(b"%PDF-")
    else:
        with ZipFile(BytesIO(kwargs["data"])) as documento:
            assert b"Alternativa TRIZ para validar." in documento.read(archivo_interno)


def test_fallo_de_nueva_consulta_conserva_el_analisis_exportable():
    app = abrir_app_con_agente_simulado()
    app.session_state["error_triz_prueba"] = True
    with patch.object(agente_triz, "AgenteTRIZ", AgenteTRIZSimulado):
        app.button(key="generar_analisis_triz").click().run()
    assert not app.exception
    assert any("error simulado" in item.value for item in app.error)
    assert app.session_state["analisis_triz"] == "Alternativa TRIZ para validar."
    assert len(app.get("download_button")) == 1


def test_dialogo_libre_no_exige_triz_y_conserva_historial():
    app = abrir_dialogo()
    app.radio[0].set_value("Diálogo libre con agente IA (sin TRIZ)").run()
    assert not app.exception
    assert not app.selectbox
    assert not app.checkbox
    assert any("No necesitas elegir vías" in item.value for item in app.markdown)
    app.button[-1].click().run()
    assert not app.exception
    assert app.session_state["seleccion_problema"]["modo"] == "general"
    assert app.session_state["seleccion_problema"]["vias"] == []
    assert len(app.chat_input) == 1
    assert app.chat_input[0].placeholder == "Escribe tu mensaje al agente"


def test_conversacion_general_envia_historial_sin_contexto_triz():
    class CompletionsSimuladas:
        def create(self, **kwargs):
            self.solicitud = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="Respuesta general")
                    )
                ]
            )

    completions = CompletionsSimuladas()
    agente = agente_triz.AgenteTRIZ.__new__(agente_triz.AgenteTRIZ)
    agente.cliente = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    agente.modelo = "modelo-de-prueba"
    historial = [
        {"role": "user", "content": "Ayúdame a organizar la semana."},
        {"role": "assistant", "content": "¿Cuáles son tus prioridades?"},
        {"role": "user", "content": "Trabajo y estudio."},
    ]

    assert agente.conversar(historial) == "Respuesta general"
    mensajes = completions.solicitud["messages"]
    assert mensajes[0] == {
        "role": "system",
        "content": agente_triz.AgenteTRIZ.GENERAL_SYSTEM_PROMPT,
    }
    assert "TRIZ" not in mensajes[0]["content"]
    assert mensajes[1:] == historial


def test_tipo_guardado_eliminado_no_interrumpe_dialogo():
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["seleccion_problema"] = {
        "tipo": "Tipo anterior",
        "descripcion": "Conservar esta descripción",
        "vias": ["problema_generico"],
        "accion_mejorar": "Transportar",
    }
    app.run()
    app.button(key="volver_dialogo_inicial").click().run()
    assert not app.exception
    assert app.warning
    assert app.selectbox[0].value == "Hogar y tareas diarias"
    assert app.text_area[0].value == "Conservar esta descripción"


def test_catalogo_vacio_muestra_error_sin_indexar_lista(tmp_path):
    source = APP.read_text(encoding="utf-8")
    source = source.replace(
        "tipos = list(TIPOS_PROBLEMAS)",
        "tipos = []",
    )
    source_path = tmp_path / "app.py"
    source = source.replace(
        'Path(__file__).resolve().parent / "agente_triz" / "src"',
        f'Path(r"{PACKAGE_SOURCE}")',
    )
    source_path.write_text(source, encoding="utf-8")
    app = AppTest.from_file(str(source_path), default_timeout=30)
    app.session_state["dialogo_problema_abierto"] = True
    app.run()
    assert not app.exception
    assert "No hay tipos de problemas configurados" in app.error[0].value
