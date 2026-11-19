Esta es una aplicacion WEB, que explora la estadistica de vehiculos en EU
Se presenta un Histograma y grafico de dispersion con la frecuencias de odometros, se observa una posible normalidad en los datos

## Agente TRIZ

El directorio [agente_triz](agente_triz/README.md) contiene un agente de
resolucion de problemas independiente de la aplicacion web de vehiculos.
Incluye su propio [requirements.txt](agente_triz/requirements.txt).

```powershell
cd agente_triz
python -m pip install -r requirements.txt
python launch.py
```

Requiere Python 3.9 o superior, Tkinter y la variable `OPENROUTER_API_KEY`.
Consulta su README para configurar la clave sin guardarla en el codigo.
La matriz clasica de contradicciones TRIZ se encuentra en
`agente_triz/src/agente_triz/data/matriz_contradicciones_triz.json`.
Incluye los 39 parametros en espanol, los 1,482 pares mejorar/perjudicar y
los principios inventivos recomendados para cada par; su fuente y licencia
estan documentadas en el propio JSON.

## Dialogo web de problemas y soluciones

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

El boton "Configurar asistencia con IA" abre un dialogo para elegir entre
exploracion TRIZ y conversacion libre con el agente. En el modo TRIZ permite
elegir el tipo de problema, describirlo y seleccionar una o varias de las
cuatro vias. Al guardar, la seleccion aparece en la pagina principal
y se conserva durante la sesion; se puede volver a abrir para editarla.
Los tipos usan ejemplos cotidianos: hogar y tareas diarias, tiempo y
organizacion, transporte, accesibilidad e inclusion (por ejemplo, el acceso
de personas con discapacidad a un autobus), trabajo y estudio, gastos y
ahorro u otro problema.
La primera via incluye el punto 1.1 "Que accion quiero mejorar?", con un campo
para guardar la accion y un enlace a
[Production Inspiration](http://www.productioninspiration.com/).
El enlace abre otra pestana. Al regresar a la aplicacion, el boton
"Volver al dialogo inicial" reabre el formulario con la seleccion guardada.
Este boton pertenece a la aplicacion, no al sitio externo.
El boton "Generar análisis TRIZ" envía a OpenRouter el tipo y la descripción
del problema, la acción a mejorar (si se indicó) y las vías seleccionadas.
Al elegir contradicciones, se puede seleccionar uno de los 39 parámetros que
se desea mejorar y el que resulta perjudicado. La matriz clásica muestra los
principios inventivos recomendados y sus descripciones, y los incorpora al
prompt del agente. Si la matriz no recomienda principios para un par, lo indica
sin afirmar que la contradicción no tenga solución.
En el formulario, marca **Incluir recomendaciones de Lean Production** para
complementar las vías TRIZ con hipótesis de mejora y un piloto reversible
que se pueda medir antes y después.
La respuesta se muestra en la página y se conserva durante la sesión.
Debajo del análisis, elige PDF, Word o Excel en **Formato de exportación**
y pulsa **Descargar análisis** para guardar el archivo desde el navegador.
La descarga no vuelve a consultar a OpenRouter. Para
usarlo, configura `OPENROUTER_API_KEY`; `OPENROUTER_MODEL` es opcional. La
dependencia `openai` se instala junto con `requirements.txt`.
El formulario también permite elegir "Diálogo libre con agente IA (sin TRIZ)".
En ese modo no se seleccionan vías ni se usa la base de conocimiento TRIZ:
se abre un chat que conserva el historial durante la sesión.
La interfaz web no requiere Tkinter; este solo se carga al usar el dialogo
de escritorio del paquete.

La aplicacion carga el archivo `.env` local de la raiz del repositorio, si
existe, sin reemplazar variables de entorno ya configuradas. Para consultas
al agente se usan `OPENROUTER_API_KEY` y, opcionalmente, `OPENROUTER_MODEL`.
El archivo `.env` esta excluido de Git; no publiques sus valores.
