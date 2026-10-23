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
