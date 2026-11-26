# Prueba local de Liquid LFM3 (texto, Q8)

Guía didáctica, paso a paso, para desplegar en local el modelo de texto **Liquid LFM3** (1.7B parámetros) con cuantización de 8 bits (**Q8_0**), usarlo como chatbot básico, medir su eficiencia y, al final, conectarlo a un arnés agéntico para que ejecute tareas con herramientas (tool use).

La primera fase se realiza en un PC Windows corporativo **sin permisos de administrador**. Más adelante se repetirá en un Mac (Apple Silicon), donde se usará otro formato del modelo (MLX).

> Estado: fase 1 completada (instalación, chatbot, mini agente y Pi). Pendiente: Hermes (opcional) y fase 2 en Mac. Cada paso se valida en la máquina real antes de documentar el siguiente.

## Índice

1. [Qué es LFM3 y qué variante usamos](#qué-es-lfm3-y-qué-variante-usamos)
2. [Entorno de pruebas](#entorno-de-pruebas)
3. [Elección del runtime sin permisos de administrador](#elección-del-runtime-sin-permisos-de-administrador)
4. [Fase 1: Windows sin admin](#fase-1-windows-sin-admin)
   - [Paso 1: instalar Ollama por usuario y descargar LFM3 Q8](#paso-1-instalar-ollama-por-usuario-y-descargar-lfm3-q8)
   - [Paso 2: chatbot básico y medición de eficiencia](#paso-2-chatbot-básico-y-medición-de-eficiencia)
   - [Paso 3: arnés agéntico con tool use](#paso-3-arnés-agéntico-con-tool-use)
5. [Fase 2: Mac (Apple Silicon)](#fase-2-mac-apple-silicon) (pendiente)
6. [Plan B: llama.cpp portable](#plan-b-llamacpp-portable)
7. [Resolución de problemas](#resolución-de-problemas)
8. [Referencias](#referencias)

## Qué es LFM3 y qué variante usamos

LFM3 es una familia de seis modelos abiertos de unos 2.000 millones de parámetros publicada por Liquid AI el 27 de octubre de 2026 (texto, visión, audio, omni y dos de decisión). El de texto:

- 1.730 millones de parámetros en 24 capas, de las que solo 6 son de atención global (el resto son bloques convolucionales cortos, por eso es tan ligero).
- Funciona solo con CPU y sin conexión.
- Admite 16 idiomas, entre ellos el español.
- Contexto de hasta 256K tokens (Ollama usa 4.096 por defecto).
- Pensado para **usar herramientas, extraer datos estructurados y seguir instrucciones**. No está pensado para programar ni para razonamientos largos de muchos pasos.

### Variantes disponibles

| Formato | Dónde | Nombre | Tamaño | Uso |
|---|---|---|---|---|
| GGUF Q8_0 | Ollama | `lfm3:1.7b-q8_0` | 1,8 GB | **El que usamos** en Windows |
| GGUF Q8_0 | Hugging Face | `LiquidAI/LFM3-1.7B-GGUF`, fichero `LFM3-1.7B-Q8_0.gguf` | 1,85 GB | Plan B con llama.cpp |
| GGUF Q4_K_M | Ollama | `lfm3` / `lfm3:1.7b` (por defecto en Windows/Linux) | 1,1 GB | Más pequeño, algo menos preciso |
| MLX 8 bits | Ollama (Mac) | `lfm3:1.7b-mxfp8` | 2,1 GB | Equivalente a 8 bits en Apple Silicon |

Importante: `ollama run lfm3` descarga por defecto la versión **Q4_K_M**, no la Q8. Para la de 8 bits hay que indicar el tag explícito `lfm3:1.7b-q8_0`.

### Por qué Q8

La cuantización reduce la precisión de los pesos para que el modelo ocupe menos y vaya más rápido. Q8_0 (8 bits) pierde muy poca calidad respecto al original en BF16, lo que en un modelo tan pequeño se nota en la fiabilidad del formato de las llamadas a herramientas. Con 1,8 GB cabe sobrado en 16 GB de RAM.

### Parámetros de muestreo recomendados por Liquid AI

- Chat, herramientas y agentes: `temperature 0.1`, `top_k 50`, `repeat_penalty 1.1`.
- Matemáticas y ciencia: `temperature 1.0`, `top_p 0.95`, `top_k 20`.

## Entorno de pruebas

| | Fase 1 | Fase 2 |
|---|---|---|
| Equipo | PC del trabajo, Intel Core Ultra 5 135U (12 núcleos, 14 hilos) con NPU | Mac (Apple Silicon) |
| RAM | 31,4 GB visibles (inicialmente se pensaba que eran 16 GB) | Por definir |
| Sistema | Windows | macOS |
| Permisos | **Sin administrador** | Administrador |
| Formato del modelo | GGUF Q8_0 | MLX 8 bits |

Nota sobre la NPU: ni Ollama ni llama.cpp usan la NPU de Intel; el modelo correrá en la CPU, que es justo para lo que está diseñado LFM3. Aprovechar la NPU requeriría la pila OpenVINO de Intel y una conversión del modelo, algo que queda fuera de esta primera prueba.

## Elección del runtime sin permisos de administrador

| Opción | ¿Necesita admin? | Pros | Contras |
|---|---|---|---|
| **Ollama (instalador por usuario)** | No, se instala en `%LOCALAPPDATA%\Programs\Ollama` | Tag oficial `lfm3`, parser de tool calling ya integrado, API compatible con OpenAI en `localhost:11434` | Si la empresa bloquea ejecutables desconocidos (AppLocker), puede no arrancar |
| llama.cpp (zip portable) | No, se descomprime y se ejecuta | 100 % portable, control total | Hay que configurar a mano plantilla y tool calling (`--jinja`) |
| LM Studio | Normalmente no (instalación por usuario) | Interfaz gráfica cómoda | Más pesado, menos didáctico para entender las piezas |

**Elección: Ollama** como camino principal, porque es lo que recomendaron en la charla (`ollama run lfm3`), su instalador no pide administrador y trae ya integrado el parser de llamadas a herramientas de LFM3, lo que nos simplifica mucho la fase agéntica. llama.cpp queda como [plan B](#plan-b-llamacpp-portable).

Versión mínima: LFM3 requiere **Ollama v0.40.13 o superior** en Windows y Linux. Con versiones anteriores la descarga falla con `model requires ollama version v0.40.13 or newer`.

## Fase 1: Windows sin admin

Todos los comandos se ejecutan en **PowerShell** abierto como usuario normal (no "Ejecutar como administrador").

### Paso 1: instalar Ollama por usuario y descargar LFM3 Q8

#### 1.1 Comprobar si ya hay un Ollama instalado

```powershell
ollama --version
```

- Si responde con una versión igual o superior a `0.40.13`, salta al punto 1.4.
- Si es más antigua, actualízala con el instalador (punto 1.2).
- Si dice que el comando no se reconoce, continúa con el punto 1.2.

#### 1.2 Descargar e instalar Ollama sin administrador

1. Descarga `OllamaSetup.exe` desde <https://ollama.com/download/windows>.
2. Ejecútalo con doble clic. **No** uses "Ejecutar como administrador". El instalador se instala en tu perfil (`%LOCALAPPDATA%\Programs\Ollama`) y añade `ollama` al `PATH` de tu usuario.
3. Al terminar, Ollama queda corriendo en segundo plano (icono en la bandeja del sistema) y escuchando en `http://localhost:11434`.

Si el instalador pidiese elevación o lo bloquease la política de la empresa, avisa y pasamos al [plan B](#plan-b-llamacpp-portable).

#### 1.3 (Opcional) Cambiar la carpeta de los modelos

Por defecto los modelos se guardan en `%USERPROFILE%\.ollama\models`. Si tu perfil tiene poco espacio o se sincroniza con OneDrive, puedes moverlos a otra carpeta con una variable de entorno de usuario (no requiere admin):

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", "D:\ollama\models", "User")
```

Después cierra Ollama desde el icono de la bandeja (clic derecho > *Quit Ollama*), vuelve a abrirlo desde el menú Inicio y abre un PowerShell nuevo para que todo lea la variable. Comprueba que ha quedado guardada con:

```powershell
[Environment]::GetEnvironmentVariable("OLLAMA_MODELS", "User")
```

> **Lección aprendida: `$env:` no es persistente.** En la primera prueba se definió la variable con `$env:OLLAMA_MODELS = "..."`. Eso solo vale para **esa ventana de PowerShell** y sus procesos hijos. La app de Ollama de la bandeja del sistema se arranca desde el Explorador de Windows, no hereda esa variable y por tanto siguió guardando los modelos en la ruta por defecto. Por eso `ollama list` mostraba el modelo (el cliente pregunta al servidor por la API) pero la carpeta nueva estaba vacía.
>
> Solución, sin admin:
>
> 1. Guardar la variable a nivel de usuario con `[Environment]::SetEnvironmentVariable(...)` como arriba (equivale a `setx OLLAMA_MODELS "ruta"`).
> 2. Salir de Ollama desde la bandeja y volver a abrirlo.
> 3. Si el modelo ya estaba descargado, no hace falta bajarlo otra vez: basta mover las carpetas `blobs` y `manifests` de `%USERPROFILE%\.ollama\models` a la nueva ruta **con Ollama cerrado**, y comprobar después con `ollama list`.
>
> En la carpeta verás ficheros con nombres tipo `sha256-...` dentro de `blobs` (los pesos GGUF, la plantilla y los parámetros) y en `manifests` el índice que relaciona el tag `lfm3:1.7b-q8_0` con esos blobs. Ollama almacena así los modelos para no duplicar capas compartidas entre tags.

#### 1.4 Verificar la instalación

Abre un PowerShell **nuevo** (para que recargue el `PATH`) y ejecuta:

```powershell
ollama --version
Invoke-RestMethod http://localhost:11434/api/version
```

El primero muestra la versión del cliente y el segundo confirma que el servidor está escuchando.

#### 1.5 Descargar el modelo LFM3 en 8 bits

```powershell
ollama pull lfm3:1.7b-q8_0
ollama list
```

Descarga unos 1,8 GB. `ollama list` debe mostrar `lfm3:1.7b-q8_0`.

#### 1.6 Inspeccionar el modelo

```powershell
ollama show lfm3:1.7b-q8_0
```

Fíjate en que aparezcan:

- `quantization  Q8_0`
- En `Capabilities`, la capacidad `tools` (imprescindible para la fase agéntica).
- `renderer lfm3` y `parser lfm3` (la plantilla de chat y el parser que convierte las llamadas a herramientas del modelo en el JSON `tool_calls` estándar).

#### 1.7 Primera conversación

```powershell
ollama run lfm3:1.7b-q8_0 --verbose
```

Escribe por ejemplo `Hola, preséntate en dos frases` y pulsa Enter. Con `--verbose`, al final de cada respuesta Ollama imprime estadísticas; la más interesante es `eval rate` (tokens por segundo generados). Sal con `/bye`.

#### Resultado esperado del paso 1

- [x] Ollama instalado sin admin
- [x] `ollama list` muestra `lfm3:1.7b-q8_0` (ID `a329e3b38ec2`, 1,8 GB)
- [x] El modelo responde en español
- [x] Anotado el `eval rate` de la primera respuesta

#### Resultados del paso 1 (Intel Core Ultra 5 135U, 26/11/2026)

Primera interacción con `ollama run --verbose` (una presentación personal):

| Métrica | Valor | Qué significa |
|---|---|---|
| `load duration` | 4,3 ms | El modelo ya estaba cargado en memoria |
| `prompt eval count` | 27 tokens | Tokens de entrada procesados |
| `prompt eval rate` | **70,38 tokens/s** | Velocidad leyendo el prompt (prefill) |
| `eval count` | 346 tokens | Tokens generados en la respuesta |
| `eval rate` | **23,83 tokens/s** | Velocidad generando (decode), la que se nota al leer |
| `total duration` | 14,9 s | Tiempo total de la respuesta |

Unos 24 tokens/s solo con CPU es una velocidad de lectura cómoda (más rápida que lo que una persona lee). Observación cualitativa: la respuesta fue correcta en idioma y tono, pero **inventó detalles** sobre el sector (diseño de interiores, interfaces holográficas...) y fue más larga de lo necesario. Es esperable en un modelo de 1,7B sin instrucciones de sistema y con el muestreo por defecto; en el paso 2 se fijan un *system prompt* y la temperatura recomendada (0.1) para comparar.

### Paso 2: chatbot básico y medición de eficiencia

Objetivo: dejar de usar `ollama run` y hablar con el modelo **a través de su API REST**, que es como lo hará después cualquier arnés agéntico. Para ello usamos un pequeño chatbot en PowerShell, [`scripts/chat.ps1`](scripts/chat.ps1), que no necesita instalar nada (ni Python ni Node).

#### Cómo funciona un chat contra Ollama

Ollama expone en `http://localhost:11434` una API propia (`/api/chat`) y otra compatible con OpenAI (`/v1/chat/completions`). El modelo **no tiene memoria**: en cada petición el cliente le envía toda la conversación como una lista de mensajes con su rol:

```json
{
  "model": "lfm3:1.7b-q8_0",
  "messages": [
    { "role": "system", "content": "Eres un asistente útil..." },
    { "role": "user", "content": "Hola" },
    { "role": "assistant", "content": "¡Hola! ¿En qué te ayudo?" },
    { "role": "user", "content": "Resume esto..." }
  ],
  "options": { "temperature": 0.1, "top_k": 50, "repeat_penalty": 1.1, "num_ctx": 4096 },
  "stream": false
}
```

- `system`: instrucciones fijas que condicionan el comportamiento (tono, idioma, límites).
- `options`: parámetros de muestreo recomendados por Liquid AI y tamaño de la ventana de contexto (`num_ctx`).
- La respuesta incluye el texto y las métricas (`eval_count`, `eval_duration`, etc.), que el script convierte a tokens/s.

El script mantiene ese historial, muestra las métricas tras cada respuesta, consulta `/api/ps` para ver la memoria que ocupa el modelo y lo guarda todo en `scripts/metricas.csv`.

#### 2.1 Traer el script al PC

Con git (si está disponible):

```powershell
git clone https://github.com/fpinero/test-LFM3.git
cd test-LFM3
git checkout claude/project-thread-ni4g59
```

Sin git: descarga el fichero desde GitHub (botón *Download raw file*) a una carpeta, por ejemplo `C:\Users\<usuario>\test-LFM3\scripts\`.

#### 2.2 Ejecutarlo sin admin

Windows puede bloquear scripts `.ps1` descargados. Sin permisos de administrador hay dos opciones:

```powershell
# Opción A: saltar la política solo para esta ejecución
powershell -ExecutionPolicy Bypass -File .\scripts\chat.ps1

# Opción B: permitir scripts locales para tu usuario (una sola vez)
Unblock-File .\scripts\chat.ps1
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\scripts\chat.ps1
```

Si una directiva de grupo de la empresa impide la opción B, la opción A suele funcionar.

Parámetros útiles:

```powershell
.\scripts\chat.ps1 -NumCtx 16384                      # ventana de contexto mayor
.\scripts\chat.ps1 -NoThink                           # desactiva el razonamiento previo
.\scripts\chat.ps1 -System "Responde siempre en una sola frase."
```

Dentro del chat: `/reset` borra el historial, `/stats` muestra la memoria usada y `/bye` sale.

#### 2.3 Batería de pruebas

Ejecuta estas cuatro pruebas y anota las métricas que imprime el script:

1. **Presentación** (comparar con el paso 1): `Hola, soy Fernando, arquitecto cloud. Preséntate en dos frases.`
2. **Extracción estructurada** (su punto fuerte): `Extrae en JSON con las claves nombre, empresa, fecha y importe: "Factura de Talleres López S.L. emitida el 3 de marzo de 2026 por 1.250,40 euros a nombre de Ana Ruiz".`
3. **Seguir instrucciones**: `Dame exactamente 3 ventajas de Kubernetes, cada una en menos de 10 palabras, en lista numerada.`
4. **Memoria de la conversación**: `¿Cómo me llamo y a qué me dedico?` (debe recordarlo de la prueba 1).

Después, repite la prueba 2 con `-NoThink` y compara tiempos y calidad.

#### 2.4 Medir la memoria RAM

Con el chat abierto, en otra ventana de PowerShell:

```powershell
ollama ps
Get-Process ollama* | Select-Object Name, Id, @{n="RAM_MB";e={[math]::Round($_.WorkingSet64/1MB)}}
```

- `ollama ps` muestra el tamaño del modelo cargado, si está en CPU o GPU y cuánto tiempo seguirá en memoria (por defecto 5 minutos sin uso).
- `Get-Process` muestra la RAM real de los procesos de Ollama (el servidor y el *runner* que ejecuta el modelo).
- Prueba también con `-NumCtx 32768` para ver cuánto crece la memoria al ampliar el contexto (la caché KV crece con él).

#### Resultados del paso 2 (Intel Core Ultra 5 135U, 26/11/2026)

Configuración: `scripts/chat.ps1`, `num_ctx` 4096, `temperature` 0.1, razonamiento activado.

| Prueba | Tokens de entrada | Prefill (tok/s) | Tokens de salida | Generación (tok/s) | Tiempo total | Calidad |
|---|---|---|---|---|---|---|
| Instrucciones precisas (3 ventajas de Kubernetes) | 162 | 134,59 | 34 | 24,12 | 2,64 s | Correcta: 3 puntos, menos de 10 palabras cada uno |
| Extracción a JSON (factura) | 258 | 304,49 | 62 | 23,18 | 3,54 s | **Parcial**: JSON válido, pero ver más abajo |
| Memoria de la conversación | 343 | 995,40 | 23 | 24,22 | 1,32 s | Correcta: recordó nombre y profesión |

Memoria:

| Medida | Valor |
|---|---|
| Modelo cargado (`ollama ps` / `/api/ps`) | 1,9 GB (1.835 MB), **100 % CPU**, contexto 4096 |
| Procesos `ollama` + `ollama app` | 42 MB + 95 MB = 137 MB |

Conclusiones:

- **La velocidad de generación es estable, unos 24 tokens/s**, independientemente de la pregunta. Es lo esperable: en CPU la generación está limitada por el ancho de banda de memoria (cada token nuevo lee todos los pesos, unos 1,8 GB).
- **El prefill (leer la entrada) es mucho más rápido y crece en cada turno** (134 → 304 → 995 tok/s). No es que el modelo se acelere: Ollama reutiliza la caché KV de los turnos anteriores y solo procesa los tokens nuevos, pero las métricas dividen el total del prompt entre ese tiempo. Por eso en un chat largo la respuesta empieza casi al instante.
- **La RAM total del sistema dedicada al modelo ronda los 2 GB** con contexto 4096. Los 137 MB de los procesos `ollama*` no incluyen el modelo: en las versiones actuales Ollama lo ejecuta en un proceso *runner* aparte (columna `RUNNER llamacpp`). Para localizarlo: `Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 5 Name, Id, @{n="RAM_MB";e={[math]::Round($_.WorkingSet64/1MB)}}`. El script ya suma también los procesos `llama*`.
- **Sin razonamiento (`-NoThink`) las respuestas son más rápidas y más cortas**, porque el modelo se salta la fase de "pensar" antes de responder. Para tareas sencillas compensa; Liquid AI avisa de que puede ser menos consistente en tareas que requieren razonar.
- **Limitación observada en la extracción:** en `"nombre"` puso el concepto de la factura (`"Factura de Talleres López S.L."`) en lugar de la persona (`"Ana Ruiz"`), e `importe` salió como texto (`"1.250,40 euros"`) en vez de número. La clave `nombre` era ambigua y el modelo eligió mal. Con un modelo de 1,7B conviene **ser explícito**: nombres de clave claros (`cliente`, `emisor`), tipos (`importe` como número con punto decimal) o, mejor aún, pasar un esquema JSON. Ollama admite el parámetro `format` con un JSON Schema para forzar la estructura de salida.

#### Resultado del paso 2

- [x] El script conversa y recuerda el historial
- [x] Tabla de métricas de las pruebas
- [x] RAM con `num_ctx` 4096 (la prueba con 32768 queda pendiente, opcional)
- [x] Comparación con y sin razonamiento (`-NoThink`)

### Paso 3: arnés agéntico con tool use

Objetivo: que el modelo no solo conteste, sino que **actúe**: decida qué herramienta necesita, la pida, reciba el resultado y continúe hasta resolver la tarea. Lo haremos en dos partes:

1. **Mini agente propio en PowerShell** ([`scripts/agente-mini.ps1`](scripts/agente-mini.ps1)), sin instalar nada, para ver por dentro cómo funciona el *tool calling*.
2. **Un arnés agéntico real** (Pi coding agent) conectado al mismo modelo local.

#### 3.1 Qué es el tool calling

El modelo no ejecuta nada por sí mismo. El flujo es este:

1. El cliente envía la conversación **y la lista de herramientas** disponibles, cada una con su nombre, una descripción y sus parámetros en JSON Schema.
2. Si el modelo decide que necesita una herramienta, en lugar de texto devuelve una o varias `tool_calls` con el nombre y los argumentos. LFM3 las genera internamente con un formato XML propio y el *parser* `lfm3` de Ollama las convierte al JSON estándar:

   ```json
   { "role": "assistant", "tool_calls": [ { "function": { "name": "leer_fichero", "arguments": { "ruta": "scripts/chat.ps1" } } } ] }
   ```

3. El **cliente** (nuestro script o el arnés) ejecuta la herramienta de verdad y añade el resultado al historial con el rol `tool`.
4. Se vuelve a llamar al modelo, que ya tiene los datos. Se repite hasta que responde con texto normal.

A ese ciclo se le llama **bucle agéntico**. Un arnés como Pi o Hermes es, en esencia, este bucle más un buen conjunto de herramientas, un *system prompt* trabajado y gestión del contexto.

#### 3.2 Mini agente en PowerShell

El script define cuatro herramientas de **solo lectura**, que nunca salen de la carpeta del proyecto:

| Herramienta | Qué hace |
|---|---|
| `obtener_fecha_hora` | Fecha, hora y día de la semana del equipo |
| `info_sistema` | CPU, núcleos, RAM total y libre |
| `listar_ficheros` | Lista una carpeta del proyecto |
| `leer_fichero` | Lee un fichero del proyecto (hasta 4000 caracteres) |

Ejecútalo desde la raíz del repositorio:

```powershell
git pull
powershell -ExecutionPolicy Bypass -File .\scripts\agente-mini.ps1
```

Por cada paso verás en magenta qué herramienta pide el modelo, con qué argumentos y qué resultado recibe.

Pruebas propuestas, de menos a más pasos:

1. `¿Qué día de la semana es hoy?` (una herramienta)
2. `¿Cuánta RAM libre tiene este equipo y qué procesador es?` (una herramienta, interpretar JSON)
3. `¿Qué ficheros hay en la carpeta scripts?` (una herramienta con argumento)
4. `Mira qué scripts hay en la carpeta scripts, lee el del chat y explícame en tres frases qué hace.` (encadenar `listar_ficheros` y `leer_fichero`)
5. `¿Hay algún fichero llamado config.yaml en el proyecto?` (debe comprobarlo, no inventarlo)

Repite la prueba 4 con `-NoThink` y compara pasos, tokens y tiempo.

Qué observar:

- Si elige la herramienta correcta y con los argumentos bien formados.
- Si encadena varias herramientas cuando hace falta.
- Si se inventa datos en lugar de usar las herramientas (alucinación).

#### Resultados del paso 3.2 (26/11/2026)

| Prueba | Modo | Herramientas usadas | Pasos | Tokens generados | Tiempo | Resultado |
|---|---|---|---|---|---|---|
| Día de la semana | think | `obtener_fecha_hora` | 2 | 131 | 16,3 s | Correcto (jueves) |
| RAM libre y procesador | think | `info_sistema` | 2 | 208 | 12,0 s | Correcto (10,8 GB libres, Core Ultra 5 135U) |
| Ficheros de `scripts` | think | `listar_ficheros("scripts")` | 2 | 177 | 9,6 s | Correcto |
| Listar y leer el chat, resumir en 3 frases | think | `leer_fichero` | 2 | 625 | 52,1 s | Correcto y detallado |
| Igual, sin razonamiento | no think | `listar_ficheros` + `leer_fichero` | 3 | 184 | 30,5 s | Correcto pero más pobre |
| ¿Existe `config.yaml`? | think | `listar_ficheros(".")` | 2 | 741 | 38,6 s | Correcto, **no alucinó** |

Conclusiones:

- **El tool calling funciona de forma fiable**: eligió siempre la herramienta adecuada, con argumentos bien formados (`{"ruta":"scripts/chat.ps1"}`), y no inventó datos que debía consultar.
- **Usa el contexto de forma inteligente**: en la prueba 4 con razonamiento se saltó `listar_ficheros` porque ya tenía el listado de la prueba anterior en el historial. Sin historial (sesión nueva con `-NoThink`) encadenó las dos herramientas, como se esperaba.
- **El razonamiento se escribe en inglés** aunque la respuesta final sale en español. Es habitual en modelos pequeños: el entrenamiento del razonamiento es mayoritariamente en inglés.
- **Razonar cuesta tiempo**: el razonamiento multiplica los tokens generados (625 frente a 184) y, a 24 tok/s, eso son segundos. Sin razonamiento va más rápido pero las respuestas son escuetas, hasta el punto de perder información útil. Para tareas agénticas sencillas `-NoThink` puede bastar; para resumir o analizar compensa razonar.
- **La CPU llega al 100 %** durante la inferencia: es esperable, Ollama usa todos los núcleos para el cálculo. Mientras el modelo genera, el equipo va más lento para otras tareas.
- **Dato corregido del entorno**: la herramienta `info_sistema` reveló que el equipo es un **Intel Core Ultra 5 135U** (12 núcleos, 14 hilos) con **31,4 GB de RAM** visibles, no 16 GB.

#### 3.3 Pi coding agent

[Pi](https://pi.dev) es un arnés agéntico minimalista para terminal: un *system prompt* de unos 600 tokens y cuatro herramientas por defecto (`read`, `write`, `edit` y `bash`). Al ser tan ligero encaja bien con un modelo pequeño en CPU, donde cada token de prompt cuesta tiempo. Ollama lo integra con el comando `ollama launch pi`.

> **Aviso de seguridad:** a diferencia de nuestro mini agente, Pi puede **escribir ficheros y ejecutar comandos** en tu equipo, y por diseño no pide confirmación antes de hacerlo. Trabajaremos siempre en una carpeta de pruebas aislada.

##### 3.3.1 Comprobar requisitos (sin admin)

```powershell
node -v                     # Pi necesita Node.js 22.19 o superior
npm config get prefix       # dónde instala npm los paquetes globales
git --version               # Git for Windows aporta el bash que usa Pi
Get-Command bash -ErrorAction SilentlyContinue | Select-Object Source
```

- `npm config get prefix` debería apuntar a tu perfil (normalmente `C:\Users\<usuario>\AppData\Roaming\npm`). Si es así, `npm install -g` **no necesita admin**. Si apunta a `C:\Program Files\...`, cámbialo para tu usuario con `npm config set prefix "$env:APPDATA\npm"`.
- En Windows nativo Pi ejecuta su herramienta `bash` con **Git Bash**. Si no se encuentra, se puede indicar la ruta con `shellPath` en la configuración de Pi.

##### 3.3.2 Ampliar el contexto de Ollama

Un agente envía en cada petición su *system prompt*, la definición de las herramientas y todo el historial, incluidos los resultados de las herramientas (por ejemplo, un fichero leído entero). Los 4.096 tokens por defecto de Ollama se quedan cortos. Además, Pi habla con Ollama por su API compatible con OpenAI, que **no permite fijar `num_ctx` en cada petición**: hay que subirlo en el servidor.

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_CONTEXT_LENGTH", "32768", "User")
```

Sal de Ollama desde la bandeja (*Quit Ollama*), vuelve a abrirlo y abre un PowerShell nuevo (es la misma lección que con `OLLAMA_MODELS`). Gracias a que LFM3 solo tiene 6 capas de atención, la caché KV crece poco con el contexto y 32K caben de sobra en RAM.

##### 3.3.3 Instalar y lanzar Pi con LFM3

```powershell
mkdir $env:USERPROFILE\pi-sandbox
cd $env:USERPROFILE\pi-sandbox
ollama launch pi --model lfm3:1.7b-q8_0
```

`ollama launch pi` instala Pi con npm si no está (paquete `@earendil-works/pi-coding-agent`), configura Ollama como proveedor y abre una sesión interactiva con el modelo indicado. En otra ventana, comprueba que el contexto ha subido:

```powershell
ollama ps    # la columna CONTEXT debería mostrar 32768
```

Para entender qué ha configurado, mira los ficheros que ha creado:

```powershell
Get-Content $env:USERPROFILE\.pi\agent\models.json
Get-Content $env:USERPROFILE\.pi\agent\settings.json
```

Alternativa manual, si `ollama launch` fallase:

```powershell
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

Y en `%USERPROFILE%\.pi\agent\models.json`:

```json
{
  "providers": {
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "models": [{ "id": "lfm3:1.7b-q8_0" }]
    }
  }
}
```

Después se lanza con `pi --model ollama/lfm3:1.7b-q8_0`.

##### 3.3.4 Tareas agénticas

Dentro de Pi, en la carpeta `pi-sandbox`, de menos a más complejidad:

1. **Ejecutar comandos:** `¿Qué versiones de node y de git hay instaladas en este equipo?`
2. **Crear un fichero:** `Crea un fichero notas.md con un título y una lista de 3 ventajas de usar modelos de IA en local.`
3. **Leer y editar:** `Lee notas.md y añade al final una cuarta ventaja relacionada con la privacidad.`
4. **Extracción estructurada (su punto fuerte), con la lección del paso 2 aplicada:**

   ```text
   Crea un fichero facturas.txt con estas tres líneas:
   Factura de Talleres López S.L. emitida el 3 de marzo de 2026 por 1.250,40 euros a nombre de Ana Ruiz
   Factura de Recambios Norte S.A. emitida el 15 de abril de 2026 por 89,90 euros a nombre de Luis Gómez
   Factura de Neumáticos Sur S.L. emitida el 2 de mayo de 2026 por 432,00 euros a nombre de Marta Pérez
   Después léelo y genera facturas.json con una lista de objetos con las claves emisor (empresa), cliente (persona), fecha (formato AAAA-MM-DD) e importe (número con punto decimal, sin moneda).
   ```

5. **Comprobar su propio trabajo:** `Valida que facturas.json es un JSON correcto ejecutando un comando y dime cuánto suman los importes.`

Qué observar: si las llamadas a herramientas salen bien formadas, si se recupera cuando un comando falla, cuánto tarda cada turno (el prompt de Pi más el historial hacen que el prefill pese más que en el mini agente) y la RAM con `ollama ps`.

Para medir una tarea de forma aislada se puede usar el modo no interactivo de Pi:

```powershell
Measure-Command { pi --model ollama/lfm3:1.7b-q8_0 -p "Crea hola.txt con el texto Hola desde LFM3" | Out-Host }
```

##### Resultados del paso 3.3 (26/11/2026)

Pi se instaló con `ollama launch pi` sin permisos de administrador y completó las tareas propuestas **bien y rápido**, por encima de lo esperado para un modelo de 1,7B.

Resultado de la tarea 4 (extracción de facturas), `facturas.json` generado por el agente:

```json
[
  { "emisor": "Talleres López S.L.", "cliente": "Ana Ruiz",    "fecha": "2026-03-03", "importe": 1250.40 },
  { "emisor": "Recambios Norte S.A.", "cliente": "Luis Gómez",  "fecha": "2026-04-15", "importe": 89.90 },
  { "emisor": "Neumáticos Sur S.L.",  "cliente": "Marta Pérez", "fecha": "2026-05-02", "importe": 432.00 }
]
```

Conclusiones:

- **Extracción perfecta**: clientes y emisores correctos, fechas en ISO e importes numéricos. Es exactamente el caso que falló en el paso 2 con la clave ambigua `nombre`; con claves y tipos explícitos el modelo acierta. **La calidad de la instrucción importa más que el tamaño del modelo** para este tipo de tareas.
- **Comportamiento agéntico correcto**: escribió los dos ficheros y después **los releyó para verificarlos** por iniciativa propia (`read facturas.json`) antes de dar la respuesta.
- **Uso de recursos bajo**: la barra de estado de Pi mostraba 4,4K tokens enviados, 3,1K generados y un 96,4 % de acierto en la caché de prompt (`CH96.4%`). Al reutilizar la caché, Ollama solo procesa lo nuevo de cada turno, y por eso las respuestas son ágiles aunque el historial crezca.
- **El shell de Pi es bash, no PowerShell**: el comando `!ii .` (abrir la carpeta en el Explorador) falló con `ii: command not found`, porque `ii` es un alias de PowerShell. Desde Pi hay que usar sintaxis de bash; para abrir el Explorador vale `explorer.exe .`.

##### Ajuste recomendado: decirle a Pi el contexto real

La barra de estado de Pi indicaba `1.9%/262k`: Pi cree que el modelo dispone de **262K tokens**, el máximo nativo de LFM3, pero el servidor Ollama lo sirve con **32K** (`OLLAMA_CONTEXT_LENGTH`). En sesiones cortas no importa, pero en una larga Pi no compactaría el historial a tiempo y Ollama descartaría por su cuenta el principio de la conversación, sin avisar. Para alinearlos, añade `contextWindow` al modelo en `%USERPROFILE%\.pi\agent\models.json`:

```json
"models": [{ "id": "lfm3:1.7b-q8_0", "contextWindow": 32768 }]
```

Y reabre Pi (o usa `/model` para recargar). El contador debería pasar a `.../32k`.

#### 3.4 Hermes Agent (opcional, más adelante)

Hermes Agent de Nous Research ya tiene instalador nativo para Windows (`install.ps1`) que se instala en `%LOCALAPPDATA%\hermes` y se integra con `ollama launch hermes`. Es mucho más pesado (descarga Python, Node.js, Chromium, FFmpeg...) y su *system prompt* y herramientas son mucho mayores, lo que en CPU significa más tiempo de prefill en cada turno. Lo probaremos después de Pi para comparar.

## Fase 2: Mac (Apple Silicon)

Pendiente. Previsto: instalar Ollama (aquí sí con admin) y usar la variante MLX de 8 bits `lfm3:1.7b-mxfp8`, optimizada para Apple Silicon, repitiendo las mismas mediciones para comparar con el PC Intel.

## Plan B: llama.cpp portable

Solo si Ollama no se puede instalar. Se documentará en detalle si llegamos a necesitarlo. Resumen:

1. Descargar de <https://github.com/ggml-org/llama.cpp/releases> el zip para Windows x64 CPU (versión b11960 o posterior, que es la mínima que soporta LFM3).
2. Descomprimirlo en una carpeta de tu usuario.
3. Descargar `LFM3-1.7B-Q8_0.gguf` desde <https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF>.
4. Arrancar el servidor con plantilla Jinja (necesaria para tool calling):

```powershell
.\llama-server.exe -m .\LFM3-1.7B-Q8_0.gguf --jinja --temp 0.1 --top-k 50 --repeat-penalty 1.1 --port 8080
```

## Resolución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `model requires ollama version v0.40.13 or newer` | Ollama antiguo | Reinstalar con el último `OllamaSetup.exe` |
| `ollama` no se reconoce como comando | PowerShell abierto antes de instalar | Abrir un PowerShell nuevo |
| `ollama run lfm3` descarga 1,1 GB | Tag por defecto es Q4_K_M | Usar `lfm3:1.7b-q8_0` |
| Error `tools param requires --jinja flag` | Modelo importado desde `hf.co/...` sin parser | Usar el tag oficial `lfm3:...` de Ollama |
| Un `.ps1` no se ejecuta por la política de ejecución | Scripts descargados bloqueados | `powershell -ExecutionPolicy Bypass -File .\scripts\<script>.ps1` |
| `ii: command not found` dentro de Pi | Pi ejecuta comandos con Git Bash, no con PowerShell | Usar sintaxis bash, por ejemplo `explorer.exe .` |
| Pi muestra `.../262k` de contexto | Pi lee el máximo nativo del modelo, no el de Ollama | Añadir `contextWindow: 32768` en `models.json` |
| Logs del servidor | | `%LOCALAPPDATA%\Ollama` |

## Referencias

- Modelo GGUF en Hugging Face: <https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF>
- Ollama para Windows: <https://docs.ollama.com/windows>
- LFM3 en Ollama, tags y tool calling: <https://www.betterclaw.io/blog/lfm3-ollama-tool-calling-agent-setup>
- Resumen de LFM3 en Ollama: <https://jdneer.com/blog/liquid-ai-lfm3-local-agent-model-ollama>
- API de Ollama (chat y tool calling): <https://docs.ollama.com/api>
- Pi con Ollama: <https://docs.ollama.com/integrations/pi>
- Hermes con Ollama: <https://docs.ollama.com/integrations/hermes>
- Instalación de Hermes Agent: <https://hermes-agent.nousresearch.com/docs/getting-started/installation>
