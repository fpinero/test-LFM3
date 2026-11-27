# Prueba local de Liquid LFM3 (texto, Q8)

Guía didáctica, paso a paso, para desplegar en local el modelo de texto **Liquid LFM3** (1.7B parámetros) con cuantización de 8 bits (**Q8_0**), usarlo como chatbot básico, medir su eficiencia y, al final, conectarlo a un arnés agéntico para que ejecute tareas con herramientas (tool use).

La primera fase se realiza en un PC Windows corporativo **sin permisos de administrador**. Más adelante se repetirá en un Mac (Apple Silicon), donde se usará otro formato del modelo (MLX).

> Estado: las tres fases (Windows, Linux con 8 GB y Mac) completadas.

## Índice

1. [Qué es LFM3 y qué variante usamos](#qué-es-lfm3-y-qué-variante-usamos)
2. [Entorno de pruebas](#entorno-de-pruebas)
3. [Elección del runtime sin permisos de administrador](#elección-del-runtime-sin-permisos-de-administrador)
4. [Fase 1: Windows sin admin](#fase-1-windows-sin-admin)
   - [Paso 1: instalar Ollama por usuario y descargar LFM3 Q8](#paso-1-instalar-ollama-por-usuario-y-descargar-lfm3-q8)
   - [Paso 2: chatbot básico y medición de eficiencia](#paso-2-chatbot-básico-y-medición-de-eficiencia)
   - [Paso 3: arnés agéntico con tool use](#paso-3-arnés-agéntico-con-tool-use)
5. [Fase 2: Linux con 8 GB de RAM](#fase-2-linux-con-8-gb-de-ram)
6. [Fase 3: Mac (Apple Silicon)](#fase-3-mac-apple-silicon)
7. [Chuleta de Ollama](#chuleta-de-ollama)
8. [Plan B: llama.cpp portable](#plan-b-llamacpp-portable)
9. [Resolución de problemas](#resolución-de-problemas)
10. [Referencias](#referencias)

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

| | Fase 1 | Fase 2 | Fase 3 |
|---|---|---|---|
| Equipo | PC del trabajo, Intel Core Ultra 5 135U (12 núcleos, 14 hilos) con NPU | Portátil, Intel Core i5-5200U (2 núcleos, 4 hilos, AVX2) | MacBook con **Apple M1 Pro** |
| RAM | 31,4 GB visibles (inicialmente se pensaba que eran 16 GB) | **7,7 GiB** (2,8 GiB disponibles en reposo) + 12 GiB de swap | **16 GB** de memoria unificada (CPU y GPU) |
| Sistema | Windows | Ubuntu 24.04.5 LTS | macOS |
| Permisos | **Sin administrador** | root / sudo | Administrador |
| Formato del modelo | GGUF Q8_0 | GGUF Q8_0 (y Q4_K_M para comparar) | GGUF y MLX, 8 y 4 bits |
| Objetivo | Aprender el despliegue | Forzar los límites con poca RAM | Comparar MLX y Pi frente a Hermes |

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

#### 3.4 Hermes Agent

[Hermes Agent](https://hermes-agent.nousresearch.com) de Nous Research es un arnés agéntico mucho más completo que Pi: memoria persistente, *skills* que se van mejorando, navegador, subagentes e integración con mensajería (Telegram, Slack...). Tiene instalador nativo para Windows que, según su documentación, **no requiere permisos de administrador**, y Ollama lo integra con `ollama launch hermes`.

La pregunta que queremos responder: **¿un arnés grande aporta algo con un modelo de 1,7B en CPU, o el coste de su prompt lo hace peor que Pi?**

> **Resultado en el PC del trabajo (26/11/2026): no se pudo instalar.** El bloqueo no vino de la falta de permisos de administrador (Hermes se instala en el perfil de usuario) ni de Hermes o del modelo, sino de dos **reglas ASR (Attack Surface Reduction) de Microsoft Defender** gestionadas por TI:
>
> 1. **"Bloquear ejecutables que no cumplan criterios de prevalencia, antigüedad o lista de confianza".** Hermes crea un entorno virtual de Python cuyo `python.exe` es un binario reciente y poco extendido, y Defender no lo deja arrancar. Sin ese entorno no se pueden instalar las dependencias.
> 2. **"Bloquear herramientas del sistema copiadas o suplantadas".** Hermes descarga un Git portable que incluye utilidades con el mismo nombre que las de Windows (`whoami.exe`, `hostname.exe`, `tar.exe`...), y Defender las bloquea.
>
> **Por qué Pi sí funcionó:** Pi se ejecuta sobre Node.js, un binario muy extendido y firmado que estas reglas no bloquean, y usa el Git for Windows ya instalado en el equipo. Hermes depende de una cadena de herramientas propia (uv, Python 3.14, Git portable y más binarios que descarga después) y casi todo eso cae en esas reglas.
>
> **Lección:** en un equipo corporativo, "no necesita admin" no basta. Conviene preferir herramientas que reutilicen runtimes ya instalados y firmados (Node.js, Git, Ollama) frente a las que traen su propia cadena de binarios. Para Hermes las alternativas serían pedir a TI una exclusión de esas reglas para las carpetas de Hermes, o un entorno de desarrollo aprobado (máquina virtual, Dev Box o WSL).
>
> **Decisión:** la comparación Pi frente a Hermes con LFM3 se hará en la [fase 3 en el Mac](#fase-3-mac-apple-silicon). Los pasos siguientes quedan documentados como referencia.

##### 3.4.1 Qué instala y dónde

| Ruta | Contenido |
|---|---|
| `%LOCALAPPDATA%\hermes\hermes-agent\` | Código fuente de Hermes |
| `%LOCALAPPDATA%\hermes\bin\` | Lanzadores (se añaden al `PATH` de usuario) |
| `%LOCALAPPDATA%\hermes\` | Configuración (`config.yaml`, `.env`), sesiones y logs |

El instalador descarga uv, Python 3.14, Node.js, ripgrep, FFmpeg y, por defecto, Chromium y un controlador de *computer use*. Estos dos últimos no los necesitamos y los omitiremos con `-SkipBrowser -SkipComputerUse`. Igual que Pi, su herramienta de terminal usa **Git Bash**.

##### 3.4.2 Ampliar el contexto a 64K

El *system prompt* de Hermes y la definición de sus herramientas son bastante mayores que los de Pi. Para no quedarnos cortos, subimos el contexto del servidor a 65.536 tokens (con LFM3 el coste en RAM es pequeño):

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_CONTEXT_LENGTH", "65536", "User")
```

Sal de Ollama desde la bandeja, vuelve a abrirlo y abre un PowerShell nuevo.

##### 3.4.3 Instalar Hermes revisando antes el script

En lugar del típico `iex (irm ...)`, que ejecuta directamente lo que descarga, lo bajamos primero a un fichero para poder leerlo (buena práctica con cualquier instalador de Internet, y más en un equipo corporativo):

```powershell
mkdir $env:USERPROFILE\hermes-install -Force
cd $env:USERPROFILE\hermes-install
Invoke-RestMethod https://hermes-agent.nousresearch.com/install.ps1 -OutFile install-hermes.ps1
notepad install-hermes.ps1     # échale un vistazo antes de ejecutarlo
powershell -ExecutionPolicy Bypass -File .\install-hermes.ps1 -SkipBrowser -SkipComputerUse
```

Al terminar, abre un PowerShell nuevo (para recargar el `PATH`) y comprueba:

```powershell
hermes --version
hermes doctor
```

`hermes doctor` revisa la instalación y avisa si falta algo (por ejemplo, Git Bash).

##### 3.4.4 Conectar Hermes con LFM3

Opción A, con Ollama:

```powershell
ollama launch hermes
```

En el selector elige `lfm3:1.7b-q8_0`. Si pregunta por plataformas de mensajería, sáltalo.

Opción B, manual:

```powershell
hermes model
```

Elige *More providers...* > *Custom endpoint (enter URL manually)*, URL `http://127.0.0.1:11434/v1`, clave de API vacía, modelo `lfm3:1.7b-q8_0` y contexto `65536`.

Para entender lo que ha configurado:

```powershell
Get-Content $env:LOCALAPPDATA\hermes\config.yaml
hermes prompt-size      # tamaño del system prompt y de las herramientas
```

Anota lo que muestre `hermes prompt-size`: es la clave para comparar con los ~600 tokens del prompt de Pi.

##### 3.4.5 Mismas tareas que con Pi

Para que la comparación sea justa, usa una carpeta de pruebas nueva y las mismas tareas del apartado 3.3.4:

```powershell
mkdir $env:USERPROFILE\hermes-sandbox -Force
cd $env:USERPROFILE\hermes-sandbox
hermes
```

1. `¿Qué versiones de node y de git hay instaladas en este equipo?`
2. `Crea un fichero notas.md con un título y una lista de 3 ventajas de usar modelos de IA en local.`
3. `Lee notas.md y añade al final una cuarta ventaja relacionada con la privacidad.`
4. La extracción de facturas a `facturas.json` (mismo texto que con Pi).
5. `Valida que facturas.json es un JSON correcto ejecutando un comando y dime cuánto suman los importes.`

Para cada tarea anota el tiempo aproximado hasta la respuesta, si acertó y si se atascó o repitió herramientas. Con `ollama ps` en otra ventana verás la RAM y el contexto.

Plantilla para los resultados:

| Tarea | Pi: tiempo | Pi: resultado | Hermes: tiempo | Hermes: resultado |
|---|---|---|---|---|
| 1. Versiones | | Correcto | | |
| 2. Crear notas.md | | Correcto | | |
| 3. Editar notas.md | | Correcto | | |
| 4. Facturas a JSON | | Perfecto | | |
| 5. Validar y sumar | | | | |

##### 3.4.6 (Opcional) Adelgazar Hermes

Si va lento o se confunde con tantas herramientas, desactiva los conjuntos que no hacen falta (web, memoria, navegador...) y repite una tarea:

```powershell
hermes tools            # activar o desactivar conjuntos de herramientas
hermes prompt-size      # comprobar cuánto ha bajado el prompt
```

Con un modelo pequeño, **menos herramientas suele significar mejores decisiones**: hay menos opciones entre las que equivocarse y menos tokens que procesar en cada turno.

##### 3.4.7 Desinstalar (cuando acabemos)

```powershell
hermes uninstall --dry-run   # muestra qué borraría
hermes uninstall --full      # elimina también configuración y datos
```

La documentación recomienda no borrar `%LOCALAPPDATA%\hermes` a mano.

## Fase 2: Linux con 8 GB de RAM

Objetivo: **llevar LFM3 al límite** en una máquina modesta. En el PC Windows sobraba memoria (31 GB), así que ahora comprobamos cómo se comporta con 8 GB: cuánta memoria queda libre, si la velocidad cae, cuánto contexto podemos permitirnos y si un agente sigue siendo usable.

### Paso L0: inventario de la máquina

Antes de instalar nada, conviene saber con qué contamos. En una terminal:

```bash
cat /etc/os-release | head -4          # distribución y versión
uname -m                               # arquitectura (x86_64 o aarch64)
lscpu | grep -E "Model name|^CPU\(s\)|Thread|Flags" | cut -c1-120
grep -o -w -E "avx2|avx512f|avx_vnni" /proc/cpuinfo | sort -u   # instrucciones vectoriales que acelera llama.cpp
free -h                                # RAM total, usada y swap
df -h ~                                # espacio libre en el home
nproc                                  # núcleos disponibles
command -v curl git python3 node      # herramientas ya instaladas
node -v                                # Pi necesitará Node.js 22.19 o superior
```

Por qué importa cada dato:

- **RAM y swap:** el modelo Q8 ocupa unos 1,9 GB y el sistema y el escritorio pueden comerse 2 o 3 GB más. Si la memoria se agota, Linux tira de swap (lentísimo) o el OOM killer mata el proceso de Ollama.
- **AVX2 / AVX-512 / AVX-VNNI:** llama.cpp (el motor de Ollama) usa estas instrucciones para multiplicar matrices. Sin AVX2 la velocidad cae mucho.
- **Núcleos:** la generación en CPU escala con los núcleos físicos hasta que el cuello de botella pasa a ser el ancho de banda de memoria.
- **Node.js:** `npm 9.2.0` suele venir con Node.js 18 (el de los repositorios de Debian/Ubuntu), insuficiente para Pi. Lo resolveremos al llegar a ese paso.

#### Resultados del paso L0 (26/11/2026)

| Dato | Valor | Lectura |
|---|---|---|
| Sistema | Ubuntu 24.04.5 LTS, x86_64 | Soportado por Ollama sin problemas |
| CPU | Intel Core i5-5200U a 2,2 GHz (Broadwell, 2015), **2 núcleos y 4 hilos** | Frente a los 12 núcleos del PC Windows: esperamos bastante menos velocidad |
| Instrucciones | **AVX2** sí; AVX-512 y AVX-VNNI no | Lo mínimo para que llama.cpp vaya razonablemente bien |
| RAM | 7,7 GiB total, **2,8 GiB disponibles** (4,9 GiB usados con el escritorio y las apps abiertas) | El modelo Q8 (~1,9 GB) cabe, pero muy justo |
| Swap | 12 GiB, prácticamente sin usar | Red de seguridad, pero si el modelo acaba en swap la velocidad se desploma |
| Disco | 309 GB libres | Sin problema |
| Node.js | v18.19.1 (`/usr/bin/node`, paquete de Ubuntu) | Insuficiente para Pi (22.19 o superior); lo actualizaremos en su paso |
| Python | `python3` de Homebrew (`/home/linuxbrew/...`) | Disponible para los scripts de Linux |

Conclusiones antes de instalar:

- **La memoria es el factor crítico.** Con solo 2,8 GiB disponibles, conviene **cerrar el navegador y las aplicaciones pesadas** antes de las pruebas y anotar `free -h` en cada medición. Si `available` baja de unos 500 MB con el modelo cargado, Linux empezará a usar swap.
- **Previsión de velocidad:** en CPU, generar cada token obliga a leer todos los pesos (1,8 GB) de memoria. Con 2 núcleos de 2015 y memoria DDR3 esperamos una velocidad de generación **muy inferior a los 24 tok/s** del PC Windows, quizá en el rango de un solo dígito. El paso L1 lo confirmará.
- Si la Q8 resulta demasiado justa, la alternativa natural es la **Q4_K_M** (`lfm3:1.7b`, 1,1 GB): menos memoria y más velocidad a cambio de algo de precisión. Es justo una de las comparaciones previstas.

### Paso L1: instalar Ollama y el modelo

En este equipo sí tenemos `sudo`, así que usamos el **instalador oficial**, que deja Ollama como un servicio de `systemd` (arranca solo con el sistema y se gestiona con `systemctl`). Es la gran diferencia con Windows, donde Ollama era una app de usuario en la bandeja.

#### L1.1 Instalar Ollama

```bash
curl -fsSL https://ollama.com/install.sh -o /tmp/ollama-install.sh
less /tmp/ollama-install.sh        # opcional: revisarlo antes de ejecutarlo (q para salir)
sh /tmp/ollama-install.sh
```

El script instala el binario en `/usr/local/bin/ollama`, crea el usuario de sistema `ollama` y el servicio `ollama.service`, y lo arranca.

#### L1.2 Verificar el servicio

```bash
ollama --version                          # debe ser 0.40.13 o superior
systemctl status ollama --no-pager        # debe estar "active (running)"
curl -s http://localhost:11434/api/version
```

Los logs del servidor, equivalentes a `%LOCALAPPDATA%\Ollama` en Windows, se ven con:

```bash
journalctl -u ollama -f                   # Ctrl+C para salir
```

Nota: al ser un servicio, Ollama guarda los modelos en `/usr/share/ollama/.ollama/models` (el home del usuario `ollama`), no en tu home. Las variables de entorno como `OLLAMA_MODELS` u `OLLAMA_CONTEXT_LENGTH` **no se ponen en tu `.bashrc`** (el servicio no lo lee), sino en el propio servicio con `sudo systemctl edit ollama`. Es la versión Linux de la lección de `$env:` en Windows. Lo usaremos más adelante.

#### L1.3 Medir la memoria antes de cargar el modelo

Cierra el navegador y las aplicaciones que no necesites, y después:

```bash
free -h
```

Anota la columna `available` de la fila `Mem`: es la RAM de la que dispone realmente el modelo.

#### L1.4 Descargar el modelo Q8 e inspeccionarlo

```bash
ollama pull lfm3:1.7b-q8_0
ollama list
ollama show lfm3:1.7b-q8_0
```

Igual que en Windows: debe aparecer `Q8_0` y la capacidad `tools`.

#### L1.5 Primera conversación con métricas

```bash
ollama run lfm3:1.7b-q8_0 --verbose
```

Usa la misma pregunta que en Windows para poder comparar, por ejemplo: `Hola, soy Fernando, arquitecto cloud. Preséntate en dos frases.` Anota `prompt eval rate` y `eval rate`. Sin salir del chat, en otra terminal:

```bash
ollama ps
free -h
ps -C ollama -o pid,rss,cmd --sort=-rss | head -5      # RSS en KB de los procesos de Ollama
```

Sal con `/bye`.

#### Resultado esperado del paso L1

- [x] Servicio `ollama` activo
- [x] `lfm3:1.7b-q8_0` descargado
- [x] `eval rate` y `prompt eval rate` de la primera respuesta
- [x] RAM disponible antes y después de cargar el modelo

#### Resultados del paso L1 (26/11/2026)

Misma presentación que en Windows, con `ollama run --verbose`:

| Métrica | Linux i5-5200U | Windows Core Ultra 5 135U | Relación |
|---|---|---|---|
| `prompt eval rate` (prefill) | **17,48 tok/s** | 70,38 tok/s | 4 veces más lento |
| `eval rate` (generación) | **4,89 tok/s** | 23,83 tok/s | 5 veces más lento |
| Tokens generados | 161 | 346 | |
| Tiempo total | 34,6 s | 14,9 s | |
| Modelo en memoria (`ollama ps`) | 1,9 GB, 100 % CPU, contexto 4096 | 1,9 GB, 100 % CPU, contexto 4096 | Igual |
| RAM disponible con el modelo cargado (`free -h`) | 2,7 GiB (swap usada: 191 MiB) | | |

Conclusiones:

- **Unos 5 tokens/s es lento pero usable**: más o menos la velocidad a la que se lee en voz alta. Para un chat se puede trabajar; para un agente que encadena varias llamadas se notará más.
- **La diferencia (unas 5 veces) cuadra con el hardware**: 2 núcleos de 2015 con memoria DDR3 frente a 12 núcleos modernos con LPDDR5. La generación en CPU está limitada sobre todo por el ancho de banda de memoria.
- **¿Por qué `free -h` apenas cambió (2,8 → 2,7 GiB disponibles) si el modelo ocupa 1,9 GB?** Porque llama.cpp abre el fichero GGUF con `mmap`: el kernel proyecta el fichero en memoria y sus páginas se contabilizan como **caché de disco** (`buff/cache`), que Linux considera recuperable y por eso incluye en `available`. La memoria se está usando, pero si otra aplicación la necesita, el kernel puede soltar esas páginas y volver a leerlas del disco después, a costa de que el modelo vaya mucho más lento mientras tanto. Con poca RAM, **`available` no basta para saber si el modelo cabe con holgura**.
- **El *runner* no aparecía en `ps -C ollama`**: igual que en Windows, el modelo se ejecuta en un proceso aparte con otro nombre. Para localizarlo:

  ```bash
  ps aux --sort=-rss | head -5
  ```

### Paso L2: chatbot y medición de eficiencia

Los scripts de Windows eran PowerShell. Para Linux hay una versión equivalente en Python, [`scripts/chat.py`](scripts/chat.py), que solo usa la biblioteca estándar (no hay que instalar nada con `pip`). Hace lo mismo que `chat.ps1`, con dos mejoras pensadas para una máquina lenta:

- **Streaming**: el texto aparece a medida que se genera, en lugar de esperar al final. A 5 tok/s, la diferencia en la sensación de uso es enorme.
- **Tiempo hasta el primer token**: mide cuánto tarda en empezar a responder, la métrica que más se nota en un chat.

Además de las métricas de Ollama, lee de `/proc` la RAM disponible y la RSS de los procesos de Ollama, y lo guarda todo en `scripts/metricas-linux.csv`.

#### L2.1 Ejecutar el chat

```bash
cd ~/my_repos/test-LFM3
git pull
python3 scripts/chat.py
```

Opciones: `--no-think` (sin razonamiento), `--num-ctx 16384` y `--system "..."`. Dentro del chat: `/stats`, `/reset`, `/think on|off` y `/bye`.

#### L2.2 Batería de pruebas

Las mismas cuatro del paso 2 en Windows, para comparar directamente:

1. `Hola, soy Fernando, arquitecto cloud. Preséntate en dos frases.`
2. `Extrae en JSON con las claves nombre, empresa, fecha y importe: "Factura de Talleres López S.L. emitida el 3 de marzo de 2026 por 1.250,40 euros a nombre de Ana Ruiz".`
3. `Dame exactamente 3 ventajas de Kubernetes, cada una en menos de 10 palabras, en lista numerada.`
4. `¿Cómo me llamo y a qué me dedico?`

Y una quinta con la lección aprendida, con claves y tipos explícitos:

5. `Extrae en JSON con las claves emisor (empresa), cliente (persona), fecha (AAAA-MM-DD) e importe (número con punto decimal): "Factura de Talleres López S.L. emitida el 3 de marzo de 2026 por 1.250,40 euros a nombre de Ana Ruiz".`

Después, sal con `/bye`, vuelve a entrar con `python3 scripts/chat.py --no-think` y repite la prueba 5 para comparar tiempos.

#### L2.3 Memoria real del modelo

Con el chat abierto, en otra terminal:

```bash
ollama ps
free -h
ps aux --sort=-rss | head -5
```

#### Resultado esperado del paso L2

- [x] Tabla de métricas de las pruebas (prefill, generación y primer token)
- [x] Comparación con y sin razonamiento
- [x] RSS real del proceso que ejecuta el modelo

#### Resultados del paso L2 (26/11/2026)

| Prueba | Modo | Tokens entrada | Prefill (tok/s) | Tokens salida | Generación (tok/s) | Primer token | Total | Resultado |
|---|---|---|---|---|---|---|---|---|
| 1. Presentación | think | 66 | 21,99 | 145 | 5,12 | 8,27 s (5,26 s de carga) | 36,6 s | Correcta |
| 2. JSON con clave ambigua `nombre` | think | 164 | 37,59 | 493 | 4,93 | 4,38 s | 104,5 s | **Correcto** (en Windows falló) |
| 4. Memoria de la conversación | think | 320 | 102,97 | **800** | 4,88 | 3,14 s | **167,0 s** | **Incorrecta**: confundió quién es quién |
| 5. JSON con claves explícitas | think | 428 | 87,78 | 258 | 5,15 | 4,92 s | 55,0 s | Perfecto |
| 5. JSON con claves explícitas | **no think** | 119 | 23,20 | **50** | 5,26 | 5,15 s | **14,6 s** | Perfecto |

Memoria con el modelo cargado:

| Medida | Valor |
|---|---|
| Proceso que ejecuta el modelo | `/usr/local/lib/ollama/llama-server` (usuario `ollama`), **RSS 1,98 GB**, 98 % de CPU |
| RAM disponible (`free -h`) | 2,6 GiB, con 304 MiB de swap en uso |
| Chrome abierto a la vez | ~1,4 GB entre sus procesos |

Conclusiones:

- **La velocidad de generación es constante, unos 5 tok/s**, como en Windows lo era a 24. Lo que cambia el tiempo de respuesta es **cuántos tokens genera**, y ahí manda el razonamiento.
- **El razonamiento domina el tiempo**: en la prueba 5 la misma respuesta perfecta tardó 55 s con razonamiento (258 tokens) y 14,6 s sin él (50 tokens). A 5 tok/s, cada 100 tokens de "pensar" son 20 segundos de espera.
- **Más razonamiento no siempre es mejor**: en la prueba de memoria el modelo generó 800 tokens dándole vueltas a "quién es quién", se enredó y acabó respondiendo sobre sí mismo en vez de sobre el usuario. En Windows la misma pregunta salió bien con 23 tokens. Los modelos pequeños pueden "sobrepensar" una pregunta trivial y llegar a una conclusión peor.
- **La fecha salió correcta en todas las pruebas** (`2026-03-03`). En el razonamiento de la prueba 2 llegó a escribir "formato DD/MM/AAAA", pero la respuesta final usó el formato ISO.
- **Resultados no deterministas**: la prueba 2 (clave ambigua `nombre`) falló en Windows y acertó aquí. Con temperatura 0.1 sigue habiendo variación, sobre todo cuando la instrucción es ambigua. Es otro argumento para dar instrucciones explícitas.
- **Ollama ejecuta el modelo con `llama-server`**, el servidor de llama.cpp, como proceso hijo con parámetros como `-c 4096` (contexto), `-np 1` (una petición a la vez) y `--context-shift` (cuando se llena el contexto descarta lo más antiguo en lugar de fallar). Ese proceso es el que ocupa la memoria de verdad (~2 GB).
- **El modelo cabe en 8 GB, pero sin margen para mucho más**: con Chrome abierto ya se usa algo de swap. Para las pruebas de agentes conviene cerrar el navegador.

#### ¿Razonamiento sí o no? Cómo equilibrarlo

Liquid AI publica LFM3 con el razonamiento activado por defecto y avisa de que desactivarlo "puede ser inconsistente, especialmente en tareas que requieren razonar". Nuestras pruebas matizan esa recomendación:

| Tipo de tarea | Recomendación | Motivo |
|---|---|---|
| Extracción de datos con instrucciones explícitas (claves, tipos, formato) | **Sin razonamiento** | El trabajo ya está especificado; razonar solo añade tiempo (55 s frente a 14,6 s con el mismo resultado) |
| Llamadas a herramientas simples y directas (una herramienta, argumentos obvios) | **Sin razonamiento** | El parser de Ollama valida el formato de la llamada; el modelo solo tiene que elegir |
| Tareas ambiguas, de varios pasos o con decisiones (qué herramientas encadenar, cómo interpretar algo) | **Con razonamiento** | Es donde el razonamiento aporta: planificar antes de actuar |
| Preguntas triviales de conversación | **Sin razonamiento**, o reformular | Riesgo de sobrepensar, como en la prueba de memoria |

En la práctica:

- **Elegir por petición, no por sesión.** El parámetro `think` de la API de Ollama se puede cambiar en cada llamada. Un agente o una aplicación pueden decidir según el tipo de tarea. Para experimentar a mano, `chat.py` admite ahora `/think on` y `/think off` sin perder el historial.
- **En equipos lentos, compensa más precisar la instrucción que dejar pensar al modelo.** La prueba 5 sin razonamiento fue tan buena como con él porque las claves y los tipos estaban claros.
- **Para tareas críticas, validar en lugar de razonar más.** Comprobar el JSON con un esquema (parámetro `format` de Ollama) o un validador es más barato y fiable que muchos tokens de razonamiento.

### Paso L3: mini agente en Linux

Versión en Python del mini agente de Windows: [`scripts/agente_mini.py`](scripts/agente_mini.py). Mismas cuatro herramientas de solo lectura (`obtener_fecha_hora`, `info_sistema`, `listar_ficheros`, `leer_fichero`), con la información del sistema leída de `/proc`. Igual que `chat.py`, usa streaming para que se vea el razonamiento mientras se genera, y admite `/think on|off`.

Antes de empezar, **cierra Chrome** para liberar memoria. Después:

```bash
cd ~/my_repos/test-LFM3
git pull
python3 scripts/agente_mini.py
```

Pruebas (las mismas que en Windows):

1. `¿Qué día de la semana es hoy?`
2. `¿Cuánta RAM disponible tiene este equipo y qué procesador es?`
3. `¿Qué ficheros hay en la carpeta scripts?`
4. `/reset` y después: `Mira qué scripts hay en la carpeta scripts, lee el del chat en Python y explícame en tres frases qué hace.`
5. `¿Hay algún fichero llamado config.yaml en el proyecto?`

Después, aplica lo aprendido sobre el razonamiento: escribe `/think off`, repite las pruebas 1 a 3 (herramientas simples) y compara tiempos. Luego `/reset`, `/think on` y repite la 4 (varios pasos), que es donde el razonamiento debería aportar.

Qué observar: si elige bien las herramientas, si encadena varias cuando hace falta, el tiempo total de cada prueba y, con `ollama ps` y `free -h` en otra terminal, la memoria (el mini agente usa `num_ctx` 8192).

#### Resultados del paso L3 (26/11/2026)

Todas con razonamiento activado:

| Prueba | Herramientas usadas | Pasos | Tokens generados | Tiempo | Resultado |
|---|---|---|---|---|---|
| 1. Día de la semana | `obtener_fecha_hora` | 2 | 138 | 47,9 s | Correcto (jueves) |
| 2. RAM disponible y procesador | `info_sistema` | 2 | 218 | 69,6 s | Correcto (2,7 GB, i5-5200U) |
| 3. Ficheros de `scripts` | `listar_ficheros("scripts")` | 2 | 176 | 39,4 s | Correcto |
| 4. Listar, leer `chat.py` y resumir (tras `/reset`) | `listar_ficheros` + `leer_fichero` | 3 | 863 | **254,2 s** | Correcto y preciso |

Memoria durante las pruebas (con Chrome cerrado):

| Medida | Valor |
|---|---|
| Modelo cargado (`ollama ps`) | 2,0 GB, 100 % CPU, contexto **8192** (frente a 1,9 GB con 4096) |
| RAM disponible (`free -h`) | **4,5 GiB** (frente a 2,6 GiB con Chrome abierto) |

Conclusiones:

- **El tool calling es igual de fiable que en Windows**: herramienta correcta en todos los casos, argumentos bien formados y, en la prueba 4, el encadenamiento completo `listar_ficheros` → identificar `chat.py` entre cinco ficheros → `leer_fichero("scripts/chat.py")` → resumen correcto en tres frases.
- **Razona de forma más directa que en el chat**: con herramientas, cada paso tiene un objetivo concreto ("llamar a X", "responder con el resultado") y el razonamiento es corto (138 a 218 tokens en las preguntas simples). La deriva del paso L2 apareció en una pregunta abierta, sin herramientas que acotasen la tarea.
- **El tiempo por pregunta es alto**: unos 40 a 70 s en las preguntas de una sola herramienta y más de 4 minutos en la de varios pasos. Cada paso del bucle es una llamada completa al modelo (prefill del historial, que crece con cada resultado de herramienta, más el razonamiento a ~5 tok/s). En la prueba 4, leer `chat.py` metió unos 4.000 caracteres en el contexto, que el modelo tuvo que procesar antes de responder.
- **Subir el contexto de 4K a 8K solo añadió ~100 MB**: gracias a que LFM3 tiene solo 6 capas de atención, la caché KV es pequeña. Esto es lo que permite pensar en 32K para Pi incluso con 8 GB.
- **Cerrar Chrome liberó casi 2 GiB**: en una máquina de 8 GB, el navegador compite directamente con el modelo.

Pendiente de esta batería (opcional): repetir las preguntas 1 a 3 con `/think off` para medir cuánto se ahorra en las llamadas simples, y la prueba de `config.yaml`.

### Paso L4: Pi coding agent en Linux

Mismo arnés que en Windows, ahora en una máquina con una cuarta parte de la potencia. Aquí Pi usa el bash nativo de Linux, sin necesidad de Git Bash.

#### L4.1 Actualizar Node.js

Pi necesita **Node.js 22.19 o superior** y el equipo tiene la versión 18.19.1 del paquete de Ubuntu. En lugar de tocar el Node del sistema, aprovechamos que ya está instalado **Homebrew para Linux** (el `python3` viene de ahí) e instalamos un Node moderno en paralelo:

```bash
brew install node
hash -r                 # que bash olvide la ruta antigua de node
which node              # debe apuntar a /home/linuxbrew/.linuxbrew/bin/node
node -v                 # 22.19 o superior
npm -v
```

Como Homebrew está antes que `/usr/bin` en el `PATH`, su `node` tiene prioridad y el paquete de Ubuntu queda intacto. Si `which node` siguiera mostrando `/usr/bin/node`, abre una terminal nueva.

Alternativa sin Homebrew: [nvm](https://github.com/nvm-sh/nvm), que instala versiones de Node en el home del usuario (`nvm install 24`).

#### L4.2 Configurar el servicio de Ollama: contexto y permanencia en memoria

Igual que en Windows hay que subir el contexto, pero en Linux **las variables se configuran en el servicio de systemd**, no en `.bashrc`:

```bash
sudo systemctl edit ollama
```

Se abre un editor con un fichero de *override*. Añade en la zona indicada:

```ini
[Service]
Environment="OLLAMA_CONTEXT_LENGTH=32768"
Environment="OLLAMA_KEEP_ALIVE=30m"
```

Guarda, sal y aplica:

```bash
sudo systemctl restart ollama
systemctl show ollama --property=Environment     # comprobar que las ve
```

- `OLLAMA_CONTEXT_LENGTH=32768`: contexto por defecto para peticiones que no fijan `num_ctx`, como las de Pi a través de la API compatible con OpenAI.
- `OLLAMA_KEEP_ALIVE=30m`: mantiene el modelo cargado 30 minutos sin uso (por defecto son 5). En el paso L3, `ollama ps` mostraba que se iba a descargar en segundos; recargarlo cuesta unos 5 s y, sobre todo, **se pierde la caché del prompt**, que en esta máquina es oro.

El fichero de override queda en `/etc/systemd/system/ollama.service.d/override.conf` y sobrevive a las actualizaciones de Ollama.

#### L4.3 Instalar y lanzar Pi con LFM3

Con Chrome cerrado:

```bash
mkdir -p ~/pi-sandbox && cd ~/pi-sandbox
ollama launch pi --model lfm3:1.7b-q8_0
```

Si `npm install -g` fallase por permisos (el prefijo global apunta a una carpeta del sistema), con el Node de Homebrew no debería ocurrir, porque su prefijo está en `/home/linuxbrew`.

Aplica desde el principio la lección de Windows: edita `~/.pi/agent/models.json` para que Pi conozca el contexto real y reabre Pi:

```json
"models": [{ "id": "lfm3:1.7b-q8_0", "contextWindow": 32768 }]
```

**Aviso de rendimiento:** el primer turno de Pi tendrá que procesar su *system prompt* y la definición de herramientas (unos miles de tokens) a ~20-100 tok/s, así que puede tardar un minuto o más en empezar a responder. A partir del segundo turno la caché del prompt hace el trabajo (en Windows el acierto de caché fue del 96 %).

#### L4.4 Tareas

Las mismas cinco del apartado 3.3.4 de Windows, en `~/pi-sandbox`:

1. `¿Qué versiones de node y de git hay instaladas en este equipo?`
2. `Crea un fichero notas.md con un título y una lista de 3 ventajas de usar modelos de IA en local.`
3. `Lee notas.md y añade al final una cuarta ventaja relacionada con la privacidad.`
4. La extracción de facturas a `facturas.json` (mismo texto que en Windows).
5. `Valida que facturas.json es un JSON correcto ejecutando un comando y dime cuánto suman los importes.`

Anota el tiempo de cada tarea y, en otra terminal, `ollama ps` y `free -h` para ver la memoria con 32K de contexto. La barra de estado de Pi muestra los tokens enviados y recibidos y el porcentaje de acierto de caché.

#### Resultados del paso L4 (26/11/2026)

Pi v1.6.1 con Node.js v26.13.1 (Homebrew) y el servicio de Ollama configurado con `OLLAMA_CONTEXT_LENGTH=32768` y `OLLAMA_KEEP_ALIVE=30m`. **Las cinco tareas se completaron correctamente**, aunque lentas:

| Tarea | Herramientas de Pi | Resultado |
|---|---|---|
| 1. Versiones de node y git | `bash`: `node --version`, `git --version` | Correcto (v26.13.1 y 2.43.0), presentado en tabla |
| 2. Crear `notas.md` | `write` y después `read` para verificar | Correcto |
| 3. Añadir una cuarta ventaja | `read`, `edit` (sustitución del último punto por él mismo más el nuevo) y `read` | Correcto, edición precisa sin reescribir el fichero |
| 4. Facturas a JSON | `write` de `facturas.txt`, `write` de `facturas.json` y `read` | **Perfecto**: emisores, clientes, fechas ISO e importes numéricos |
| 5. Validar y sumar | `bash`: `jq empty` y `jq '[.[].importe] \| add'` | Correcto: 1.772,30 €; detectó y explicó el artefacto de coma flotante (`1772.3000000000002`) |

Datos de la barra de estado de Pi al final: 4,7K tokens enviados, 3,0K generados, **99,4 % de acierto de caché**. Nivel de razonamiento de Pi: `medium`.

Memoria al terminar:

| Medida | Valor |
|---|---|
| Modelo cargado (`ollama ps`) | 2,1 GB, 100 % CPU, contexto **32768**, se mantiene 30 minutos |
| RAM disponible (`free -h`) | 2,4 GiB, con 723 MiB de swap en uso |

Conclusiones:

- **Misma calidad que en Windows con una cuarta parte de la máquina**: LFM3 resolvió todas las tareas agénticas sin un solo error de formato en las llamadas a herramientas. La capacidad del modelo no depende del hardware; solo la velocidad.
- **Comportamiento muy "agéntico"**: verifica su trabajo releyendo los ficheros, usa `edit` en lugar de reescribir, elige `jq` (que estaba instalado) para validar y sumar, y explica el error de redondeo en lugar de mostrarlo sin más.
- **Pasar de 8K a 32K de contexto solo añadió ~100 MB** (2,0 → 2,1 GB). Con LFM3, en 8 GB caben contextos grandes sin problema; lo que no sobra es la velocidad.
- **La lentitud viene del razonamiento**: en los razonamientos visibles se ve al modelo "pensando" en inglés antes de cada acción (por ejemplo, decidiendo cómo convertir `1.250,40`). A unos 5 tok/s, cada párrafo de razonamiento son varios segundos de espera.
- **La caché hace viable el uso**: con un 94-99 % de acierto, solo se procesan los tokens nuevos de cada turno. Sin `OLLAMA_KEEP_ALIVE` el modelo se habría descargado entre tareas y cada una habría empezado de cero.
- **Pendiente:** la barra de Pi seguía mostrando `.../262k`, así que falta añadir `"contextWindow": 32768` en `~/.pi/agent/models.json` (ver el ajuste recomendado del apartado 3.3).

### Paso L5: Q8 frente a Q4_K_M, ¿cuánto se gana?

En CPU, generar cada token obliga a leer todos los pesos de memoria. La Q4_K_M ocupa 1,1 GB frente a 1,8 GB de la Q8_0, así que en teoría debería generar en torno a un 50-60 % más rápido, a cambio de algo de precisión. Es justo lo que hay que medir en una máquina donde la velocidad es el problema.

Para no tener que copiar métricas a mano, hay un banco de pruebas reproducible, [`scripts/bench.py`](scripts/bench.py):

- Lanza las mismas tres preguntas (presentación, JSON con claves explícitas y las 3 ventajas de Kubernetes) a cada modelo, con y sin razonamiento.
- Comprueba automáticamente si el JSON extraído es exactamente el esperado.
- Mide la velocidad, los tokens, el tiempo, la RSS del `llama-server` y la RAM disponible.
- Descarga cada modelo antes de cargar el siguiente, para que no convivan dos en 8 GB.
- Al final imprime una tabla en Markdown lista para pegar en este README.

```bash
cd ~/my_repos/test-LFM3
git pull
ollama pull lfm3:1.7b            # Q4_K_M, 1,1 GB
python3 scripts/bench.py         # compara lfm3:1.7b-q8_0 y lfm3:1.7b
```

Tarda varios minutos (12 respuestas por modelo; las de razonamiento son las lentas). Con `--repeticiones 2` los promedios son más fiables, a costa del doble de tiempo.

Si la Q4 sale bien parada, el remate es repetir alguna tarea de Pi con ella:

```bash
cd ~/pi-sandbox
pi --model ollama/lfm3:1.7b
```

(Antes hay que añadir `{ "id": "lfm3:1.7b", "contextWindow": 32768 }` a la lista de modelos de `~/.pi/agent/models.json`.)

#### Resultados del paso L5 (26/11/2026)

Salida de `python3 scripts/bench.py` (`num_ctx` 4096, 1 repetición):

| Modelo | Razonamiento | Generación media (tok/s) | Tokens medios | Tiempo medio por respuesta (s) | RSS máx. runner (MB) | RAM disponible mín. (MB) | JSON |
|---|---|---|---|---|---|---|---|
| `lfm3:1.7b-q8_0` | no | 5.78 | 45 | 11.4 | 1922 | 2922 | ok |
| `lfm3:1.7b-q8_0` | sí | 5.70 | 482 | 85.1 | 1944 | 2986 | ok |
| `lfm3:1.7b` (Q4_K_M) | no | 9.63 | 38 | 6.3 | 1211 | 3889 | ok |
| `lfm3:1.7b` (Q4_K_M) | sí | 9.28 | 266 | 29.2 | 1228 | 3756 | ok |

Detalle por prueba:

| Prueba | Q8 sin razonar | Q8 razonando | Q4 sin razonar | Q4 razonando |
|---|---|---|---|---|
| Presentación | 60 tok, 12,5 s | 164 tok, 29,3 s | 38 tok, 5,7 s | 140 tok, 15,1 s |
| JSON (claves explícitas) | 49 tok, 13,7 s, ok | 823 tok, 146,4 s, ok | 49 tok, 8,3 s, ok | 464 tok, 51,7 s, ok |
| 3 ventajas de Kubernetes | 27 tok, 8,0 s | 459 tok, 79,7 s | 27 tok, 4,8 s | 193 tok, 20,7 s |
| Carga del modelo | 6,2 s | | 3,8 s | |

Conclusiones:

- **La Q4_K_M genera un 67 % más rápido** (9,6 frente a 5,8 tok/s), muy cerca de lo que predice la teoría: lee 1,1 GB por token en lugar de 1,8 GB. En CPU, **la velocidad de generación es inversamente proporcional al tamaño del modelo en memoria**.
- **Ahorra unos 700 MB de RAM** (RSS de 1,2 GB frente a 1,9 GB) y carga en 3,8 s frente a 6,2 s. En una máquina de 8 GB eso es casi 1 GB más de margen para el sistema y el navegador.
- **Sin pérdida de calidad apreciable en estas pruebas**: el JSON salió exacto en los cuatro casos.
- **Combinando Q4 y sin razonamiento, la respuesta media baja de 85 s a 6 s** respecto a Q8 razonando. Son dos palancas independientes: la cuantización acelera cada token y el modo sin razonamiento reduce cuántos tokens se generan.
- **El número de tokens de razonamiento varía mucho** (823 frente a 464 en el mismo JSON). Con una sola repetición no se puede afirmar que la Q4 razone "menos"; es la variabilidad propia del razonamiento. Para afinar, `--repeticiones 3`.
- **Matiz importante**: estas pruebas son de una sola respuesta. La Q8 se recomendó en la charla por su fiabilidad en tareas agénticas largas, donde los pequeños errores de una cuantización más agresiva se acumulan paso a paso. Falta comprobar la Q4 con Pi.

### Conclusiones de la fase Linux (8 GB)

| | Windows, Core Ultra 5 135U, 31 GB | Linux, i5-5200U, 8 GB, Q8 | Linux, i5-5200U, 8 GB, Q4_K_M |
|---|---|---|---|
| Generación | ~24 tok/s | ~5,8 tok/s | ~9,6 tok/s |
| Memoria del modelo (contexto 4K) | 1,9 GB | 1,9 GB | 1,2 GB |
| Chat sencillo | Instantáneo | Usable, con paciencia | Fluido sin razonamiento |
| Mini agente (una herramienta) | 10-16 s | 40-70 s | No medido |
| Pi (5 tareas) | Rápido, todo correcto | Lento, todo correcto | Facturas con QAD Q4_0: bastante más rápido y correcto |

**¿Es viable LFM3 en un portátil de 2015 con 8 GB?** Sí, con matices:

1. **Cabe con holgura**: incluso con 32K de contexto el modelo Q8 no pasa de 2,1 GB, gracias a sus pocas capas de atención. El factor limitante no es la memoria sino la velocidad de la CPU y de la RAM.
2. **La calidad no depende del hardware**: todas las tareas agénticas salieron igual de bien que en el equipo potente.
3. **Para que sea cómodo hay que usar las dos palancas**: la cuantización Q4 (un 67 % más rápida) y desactivar el razonamiento en las tareas sencillas o bien especificadas.
4. **La configuración del servicio importa**: `OLLAMA_KEEP_ALIVE` para conservar la caché del prompt entre peticiones (con un 94-99 % de acierto en Pi) y cerrar el navegador para no entrar en swap.

**Configuración recomendada para un equipo de 8 GB con CPU modesta:**

| Ajuste | Valor | Por qué |
|---|---|---|
| Modelo | `lfm3:1.7b-qad-q4_0` | ~10 tok/s frente a ~5,8 de la Q8, 1,1 GB en memoria y calidad agéntica validada |
| Razonamiento | Desactivado en tareas bien especificadas; activado en tareas ambiguas o de varios pasos | El razonamiento multiplica el tiempo y es muy variable (de 505 a 1.150 tokens en la misma pregunta) |
| `OLLAMA_KEEP_ALIVE` | `30m` o más | Conserva el modelo y la caché del prompt entre peticiones |
| `OLLAMA_CONTEXT_LENGTH` | `32768` para agentes | Solo cuesta ~100 MB más que 8K gracias a las 6 capas de atención |
| Entorno | Cerrar el navegador | Libera hasta 2 GiB y evita entrar en swap |

### Paso L6: validar la cuantización de 4 bits en tareas agénticas

Liquid AI publica además una variante **QAD Q4_0** (`lfm3:1.7b-qad-q4_0`, 1,0 GB). QAD (*quantization-aware distillation*) significa que el modelo se ha reentrenado para funcionar bien en 4 bits, en lugar de cuantizarse después sin más, así que en principio debería conservar mejor la calidad que la Q4_K_M. Es la candidata natural para esta máquina.

1. Comparar las dos variantes de 4 bits (y de paso repetir para tener promedios):

   ```bash
   ollama pull lfm3:1.7b-qad-q4_0
   python3 scripts/bench.py --models lfm3:1.7b lfm3:1.7b-qad-q4_0 --repeticiones 2
   ```

2. Repetir con Pi las tareas 4 y 5 (facturas y validación con `jq`) usando la mejor de las dos. Antes, añade los modelos de 4 bits a `~/.pi/agent/models.json` con su `contextWindow`:

   ```json
   "models": [
     { "id": "lfm3:1.7b-q8_0", "contextWindow": 32768 },
     { "id": "lfm3:1.7b", "contextWindow": 32768 },
     { "id": "lfm3:1.7b-qad-q4_0", "contextWindow": 32768 }
   ]
   ```

   ```bash
   cd ~/pi-sandbox && rm -f facturas.txt facturas.json
   pi --model ollama/lfm3:1.7b-qad-q4_0
   ```

   Anota el tiempo de cada tarea para compararlo con la Q8.

#### Resultados del paso L6: Q4_K_M frente a QAD Q4_0 (26/11/2026)

Salida de `python3 scripts/bench.py --models lfm3:1.7b lfm3:1.7b-qad-q4_0 --repeticiones 2` (`num_ctx` 4096):

| Modelo | Razonamiento | Generación media (tok/s) | Tokens medios | Tiempo medio por respuesta (s) | RSS máx. runner (MB) | RAM disponible mín. (MB) | JSON |
|---|---|---|---|---|---|---|---|
| `lfm3:1.7b` (Q4_K_M) | no | 9.59 | 38 | 5.2 | 1211 | 3763 | ok, ok |
| `lfm3:1.7b` (Q4_K_M) | sí | 9.07 | 412 | 46.1 | 1254 | 3624 | ok, ok |
| `lfm3:1.7b-qad-q4_0` | no | 10.10 | 52 | 6.6 | 1168 | 3821 | ok, ok |
| `lfm3:1.7b-qad-q4_0` | sí | 9.57 | 422 | 44.4 | 1216 | 3709 | ok, ok |

Conclusiones:

- **Velocidad y memoria prácticamente iguales**: la QAD Q4_0 genera un 5 % más rápido (10,1 frente a 9,6 tok/s) y ocupa unos 50 MB menos. Q4_0 es un formato más simple que Q4_K_M y algo más barato de calcular en CPU.
- **Calidad igual en estas pruebas**: JSON exacto en las 8 respuestas. La ventaja teórica de QAD (el modelo se reentrenó para funcionar en 4 bits) no se aprecia en preguntas sueltas; donde debería notarse es en tareas largas, donde los errores se acumulan.
- **Sin razonamiento la QAD es algo más locuaz** (78 tokens frente a 38 en la presentación), por eso su tiempo medio sale ligeramente mayor pese a generar más rápido.
- **La variabilidad del razonamiento es enorme**: la misma pregunta JSON con el mismo modelo generó 505 tokens una vez y 1.150 la siguiente (55 s frente a 131 s). Es la razón principal para desactivarlo en tareas bien especificadas: además de lento, **es impredecible**.
- **La segunda repetición sin razonamiento es más rápida** (por ejemplo 8,3 s → 5,4 s en el JSON) porque Ollama reutiliza la caché del prompt de sistema.

Elección para la prueba con Pi: **QAD Q4_0**, por ser la variante que Liquid AI ha preparado para 4 bits y salir igual o mejor en todo lo medido.

#### Resultado con Pi y QAD Q4_0 (26/11/2026)

Se borraron los ficheros de la prueba anterior (`rm facturas.*`) y se repitió con `pi --model ollama/lfm3:1.7b-qad-q4_0` la tarea de facturas (crear `facturas.txt`, leerlo y generar `facturas.json` con claves y tipos explícitos):

- **Resultado correcto**, igual que con la Q8.
- **Bastante más rápido** que con la Q8, en la línea del 67-75 % de velocidad extra medido con el banco de pruebas.

Con esto la cuantización de 4 bits queda validada también en una tarea agéntica de varios pasos (escribir, leer, transformar y escribir), que era la duda que quedaba abierta.

### Estado de las pruebas de estrés

| Prueba | Estado |
|---|---|
| Línea base Q8 con `num_ctx` 4096 | Hecha (pasos L1 y L2) |
| Q8 frente a Q4_K_M y QAD Q4_0 | Hecha (pasos L5 y L6) |
| Contexto creciente | Parcial: 4K, 8K y 32K medidos (1,9, 2,0 y 2,1 GB). Quedan 64K y 128K (opcional) |
| Mini agente y Pi | Hecha (pasos L3, L4 y L6) |
| Peticiones en paralelo (`OLLAMA_NUM_PARALLEL`) | Pendiente (opcional) |

## Fase 3: Mac (Apple Silicon)

Objetivo: repetir en el Mac las pruebas de Windows y Linux, comparar el formato **MLX** (propio de Apple Silicon) con el GGUF que hemos usado hasta ahora y, por fin, hacer la **comparación Pi frente a Hermes Agent** que no se pudo hacer en el PC corporativo.

Qué cambia respecto a las fases anteriores:

- **GPU integrada y memoria unificada**: en Apple Silicon la CPU y la GPU comparten la misma RAM. Ollama ejecuta el modelo en la GPU mediante Metal, así que esperamos ver `100% GPU` en `ollama ps` en lugar de `100% CPU`.
- **Formato MLX**: además del GGUF de llama.cpp, LFM3 se publica en formato MLX, el framework de Apple para su hardware. En Ollama son tags distintos del mismo modelo:

| Tag | Formato | Tamaño | Equivale a |
|---|---|---|---|
| `lfm3:1.7b-q8_0` | GGUF, 8 bits | 1,8 GB | El que usamos en Windows y Linux |
| `lfm3:1.7b-mxfp8` | MLX, 8 bits en coma flotante (MXFP8) | 2,1 GB | La versión de 8 bits para Apple Silicon |
| `lfm3:1.7b-nvfp4` | MLX, 4 bits en coma flotante (NVFP4) | 1,7 GB | La versión de 4 bits para Apple Silicon |
| `lfm3:1.7b-qad-q4_0` | GGUF, 4 bits QAD | 1,0 GB | La recomendada en Linux con 8 GB |

- **Administrador**: aquí sí, así que se instala todo de la forma estándar.

### Paso M0: inventario del Mac

```bash
sw_vers                                                    # versión de macOS (Ollama necesita Sonoma 14 o superior)
system_profiler SPHardwareDataType | grep -E "Model Name|Chip|Total Number of Cores|Memory"
sysctl -n machdep.cpu.brand_string                         # chip
sysctl -n hw.memsize | awk '{print $1/1024/1024/1024 " GB"}'   # RAM total
memory_pressure | tail -1                                  # porcentaje de memoria libre
df -h ~ | tail -1                                          # espacio en disco
command -v brew git python3 node jq ollama                 # herramientas ya instaladas
node -v; python3 --version; ollama --version 2>/dev/null   # versiones
```

Por qué importa cada dato:

- **Chip (M1, M2, M3, M4...) y núcleos de GPU**: determinan la velocidad. En Apple Silicon el ancho de banda de memoria es muy superior al de los PC de las fases anteriores, y la generación de tokens depende sobre todo de eso.
- **RAM**: al ser memoria unificada, el modelo y el sistema comparten la misma memoria. Con LFM3 (1 a 2 GB) no debería ser un problema en ningún Mac actual.
- **Node.js**: Pi necesita la versión 22.19 o superior.
- **Ollama**: si ya está instalado, comprobaremos que la versión sea reciente (LFM3 requiere 0.40.12 o superior en macOS).

### Paso M1: instalar Ollama y los modelos

#### M1.1 Instalar Ollama

Si no está instalado, descarga la app desde <https://ollama.com/download/mac>, arrastra `Ollama.app` a Aplicaciones y ábrela. La app instala también el comando `ollama` en el terminal y deja el servidor escuchando en `http://localhost:11434`, con un icono en la barra de menús. Alternativa con Homebrew: `brew install --cask ollama`.

```bash
ollama --version
curl -s http://localhost:11434/api/version
```

Rutas en macOS: modelos en `~/.ollama/models` y logs en `~/.ollama/logs` (`server.log` y `app.log`).

#### M1.2 Descargar los dos modelos de 8 bits

```bash
ollama pull lfm3:1.7b-q8_0       # GGUF, el mismo que en Windows y Linux
ollama pull lfm3:1.7b-mxfp8      # MLX, específico de Apple Silicon
ollama list
ollama show lfm3:1.7b-mxfp8
```

En `ollama show` comprueba el formato y que aparezca la capacidad `tools` en ambos.

#### M1.3 Primera conversación con cada formato

La misma presentación que en las fases anteriores, primero con el GGUF y después con el MLX:

```bash
ollama run lfm3:1.7b-q8_0 --verbose
```

Escribe `Hola, soy Fernando, arquitecto cloud. Preséntate en dos frases.`, anota `prompt eval rate` y `eval rate` y, sin salir, en otra terminal:

```bash
ollama ps
```

Fíjate en la columna `PROCESSOR` (esperamos `100% GPU`). Sal con `/bye` y repite con `ollama run lfm3:1.7b-mxfp8 --verbose`.

#### Resultado esperado del paso M1

- [x] Ollama instalado
- [x] `lfm3:1.7b-q8_0` y `lfm3:1.7b-mxfp8` descargados
- [x] `eval rate` y `prompt eval rate` de cada formato
- [x] `PROCESSOR` en `ollama ps`: 100 % GPU en ambos

#### Resultados del paso M1 (27/11/2026)

Misma presentación que en las fases anteriores, con `ollama run --verbose`:

| Métrica | GGUF `lfm3:1.7b-q8_0` | MLX `lfm3:1.7b-mxfp8` |
|---|---|---|
| `prompt eval rate` (prefill) | 121,73 tok/s | 18,01 tok/s |
| `eval rate` (generación) | **74,68 tok/s** | **61,71 tok/s** |
| Tokens generados (con razonamiento) | 153 | 138 |
| Tiempo total | **2,3 s** | 4,3 s |
| `ollama ps`: tamaño, procesador | 1,9 GB, **100 % GPU** | 2,0 GB, **100 % GPU** |
| `ollama ps`: runner | `llamacpp` | `mlx` |

Comparación con las otras máquinas (GGUF Q8, misma pregunta):

| Equipo | Generación | Tiempo total |
|---|---|---|
| Linux, i5-5200U (CPU) | 4,89 tok/s | 34,6 s |
| Windows, Core Ultra 5 135U (CPU) | 23,83 tok/s | 14,9 s |
| **Mac, Apple Silicon (GPU)** | **74,68 tok/s** | **2,3 s** |

Conclusiones:

- **El Mac es unas 3 veces más rápido que el PC Windows y 15 veces más que el portátil Linux.** La diferencia viene de la GPU integrada y, sobre todo, del ancho de banda de la memoria unificada de Apple Silicon, que es lo que limita la generación de tokens. Con razonamiento incluido, la respuesta completa tarda 2,3 s: la experiencia es fluida incluso dejando pensar al modelo.
- **Ollama usa motores distintos según el formato**: la columna `RUNNER` muestra `llamacpp` para el GGUF y `mlx` para el MLX. Es el mismo modelo, servido por dos motores de inferencia diferentes.
- **Sorpresa: el GGUF fue más rápido que el MLX** (74,7 frente a 61,7 tok/s en generación). Hay que tomarlo con cautela: es una sola medida, el MXFP8 ocupa algo más (2,0 frente a 1,9 GB) y el **prefill tan bajo del MLX (18 tok/s)** apunta a un coste de arranque en la primera petición (compilación de los *kernels* de Metal), no a su velocidad real. El banco de pruebas del paso M2, con repeticiones, lo aclarará.
- **Dos modelos cargados a la vez**: `ollama ps` mostraba los dos modelos en memoria al mismo tiempo. Ollama mantiene varios modelos cargados si caben (`OLLAMA_MAX_LOADED_MODELS`, por defecto 3) y cada uno se descarga al acabar su `keep_alive`. En el portátil de 8 GB esto habría sido un problema; aquí no.

### Paso M2: banco de pruebas con los cuatro formatos

Con `scripts/bench.py` comparamos los cuatro tags de la tabla del principio de esta fase, con y sin razonamiento y con dos repeticiones (la primera petición de cada modelo hace de calentamiento):

```bash
cd ~/my_Repos/test-LFM3
git pull
ollama pull lfm3:1.7b-nvfp4
ollama pull lfm3:1.7b-qad-q4_0
python3 scripts/bench.py --models lfm3:1.7b-q8_0 lfm3:1.7b-mxfp8 lfm3:1.7b-qad-q4_0 lfm3:1.7b-nvfp4 --repeticiones 2
```

En el Mac debería tardar pocos minutos. El script descarga cada modelo antes de cargar el siguiente, para que las medidas no se interfieran. En macOS las columnas de memoria son aproximadas: la memoria que usa la GPU no siempre se refleja en la RSS del proceso, así que la referencia fiable es el tamaño de `ollama ps`.

Preguntas que queremos responder:

1. ¿El MLX es más lento de verdad o era el calentamiento?
2. ¿Cuánto se gana con 4 bits en una GPU, donde el cuello de botella es menor que en CPU?
3. ¿Se mantiene la calidad del JSON en los cuatro formatos?

#### Resultados del paso M2 (27/11/2026)

Equipo: **Apple M1 Pro con 16 GB** de memoria unificada. Salida de `bench.py` con los cuatro formatos y 2 repeticiones (`num_ctx` 4096):

| Modelo | Formato / motor | Razonamiento | Generación media (tok/s) | Tokens medios | Tiempo medio por respuesta (s) | Tamaño en memoria (`ollama ps`) | JSON |
|---|---|---|---|---|---|---|---|
| `lfm3:1.7b-q8_0` | GGUF / llama.cpp | no | 77.29 | 42 | 0.7 | 1,8 GB | ok, ok |
| `lfm3:1.7b-q8_0` | GGUF / llama.cpp | sí | 75.05 | 450 | 6.0 | | ok, ok |
| `lfm3:1.7b-mxfp8` | MLX | no | 61.60 | 44 | 1.1 | 1,9 GB | ok, ok |
| `lfm3:1.7b-mxfp8` | MLX | sí | 64.32 | 499 | 7.8 | | ok, ok |
| `lfm3:1.7b-qad-q4_0` | GGUF / llama.cpp | no | **115.20** | 54 | **0.6** | 1,1 GB | ok, ok |
| `lfm3:1.7b-qad-q4_0` | GGUF / llama.cpp | sí | **113.14** | 669 | 6.0 | | ok, ok |
| `lfm3:1.7b-nvfp4` | MLX | no | 72.71 | 46 | 0.9 | 1,6 GB | ok, ok |
| `lfm3:1.7b-nvfp4` | MLX | sí | 74.99 | 678 | 9.2 | | ok, ok |

La columna de RSS de `bench.py` no es comparable en el Mac: para los modelos MLX marcaba 300-450 MB porque la memoria que reserva la GPU (Metal) no se refleja en la RSS del proceso. La referencia fiable es el tamaño de `ollama ps`.

Conclusiones:

- **No era el calentamiento: en este Mac el GGUF es más rápido que el MLX.** Con repeticiones, la Q8 GGUF genera a 77 tok/s y la MXFP8 a 62-64, un 20 % menos. Lo mismo con 4 bits: QAD Q4_0 (GGUF) a 115 tok/s frente a NVFP4 (MLX) a 73-75.
- **Una explicación probable: el M1 Pro no tiene soporte nativo para los formatos de coma flotante de 8 y 4 bits** (MXFP8 y NVFP4 se diseñaron pensando en GPU recientes). Al no poder calcular directamente con ellos, el chip tiene que convertir los pesos sobre la marcha, mientras que los formatos enteros de llama.cpp (Q8_0, Q4_0) tienen *kernels* de Metal muy optimizados. En chips más nuevos (M3, M4 y siguientes) el resultado podría cambiar.
- **QAD Q4_0 es la más rápida con diferencia: 115 tok/s**, un 50 % más que la Q8. Igual que en CPU, en GPU la generación también está limitada por cuántos bytes hay que leer por token.
- **La calidad del JSON se mantiene en los cuatro formatos** (8 de 8 correctos).
- **A esta velocidad el razonamiento deja de ser un problema**: una respuesta con razonamiento tarda de media 6 s (frente a 85 s en el portátil Linux con Q8). En el Mac se puede dejar activado casi siempre y aprovechar su mejor fiabilidad en tareas complejas.
- **El razonamiento sigue siendo muy variable**: de 175 a 612 tokens en la misma pregunta de Kubernetes con QAD, o de 979 a 1.117 con NVFP4.

**Elección para Pi y Hermes en el Mac**: `lfm3:1.7b-q8_0`. Es la que se recomendó en la charla para tareas agénticas, la misma que usamos en Windows (comparación directa) y a 77 tok/s va sobrada. QAD Q4_0 queda como alternativa si se busca la máxima velocidad.

### Paso M3: Pi en el Mac

En el Mac las pruebas de chat y del mini agente serían una repetición casi instantánea de lo ya visto, así que pasamos directamente a los arneses (si quieres verlos, `python3 scripts/chat.py` y `python3 scripts/agente_mini.py` ya funcionan en macOS).

#### M3.1 Node.js

```bash
node -v      # Pi necesita 22.19 o superior
```

Si no está instalado o es más antiguo: `brew install node`, y después `hash -r` y `node -v`.

#### M3.2 Configurar Ollama: contexto y permanencia en memoria

En macOS la app de Ollama lee las variables de entorno de `launchctl` (es el equivalente a la variable de usuario de Windows o al override de systemd de Linux):

```bash
launchctl setenv OLLAMA_CONTEXT_LENGTH 32768
launchctl setenv OLLAMA_KEEP_ALIVE 30m
```

Después **sal de Ollama desde el icono de la barra de menús** (*Quit Ollama*) y vuelve a abrirlo. Para comprobarlo, tras la primera petición `ollama ps` debe mostrar `CONTEXT 32768` y `UNTIL 29 minutes from now`.

Ojo: `launchctl setenv` **no sobrevive a un reinicio del Mac**. Para hacerlo permanente hay que crear un *LaunchAgent* (un `.plist` en `~/Library/LaunchAgents` que ejecute esos comandos al iniciar sesión); para estas pruebas no hace falta.

#### M3.3 Instalar y lanzar Pi

```bash
mkdir -p ~/pi-sandbox && cd ~/pi-sandbox
ollama launch pi --model lfm3:1.7b-q8_0
```

Y desde el principio, en `~/.pi/agent/models.json`, el contexto real para que la barra de estado de Pi muestre `.../32k`:

```json
"models": [
  { "id": "lfm3:1.7b-q8_0", "contextWindow": 32768 },
  { "id": "lfm3:1.7b-qad-q4_0", "contextWindow": 32768 }
]
```

#### M3.4 Tareas

Las mismas cinco del apartado 3.3.4, en `~/pi-sandbox`:

1. `¿Qué versiones de node y de git hay instaladas en este equipo?`
2. `Crea un fichero notas.md con un título y una lista de 3 ventajas de usar modelos de IA en local.`
3. `Lee notas.md y añade al final una cuarta ventaja relacionada con la privacidad.`
4. La extracción de facturas a `facturas.json` (mismo texto que en Windows).
5. `Valida que facturas.json es un JSON correcto ejecutando un comando y dime cuánto suman los importes.`

Anota el **tiempo aproximado de cada tarea** (con un cronómetro o mirando la hora): será la referencia para comparar con Hermes en el paso M4.

#### M3.5 Resultados (27/11/2026)

`ollama ps` confirma que `launchctl setenv` funcionó: `lfm3:1.7b-q8_0`, 2,0 GB, `100% GPU`, contexto `32768`, runner `llamacpp` y `29 minutes from now`.

| Tarea | Resultado | Observaciones |
|---|---|---|
| 1. Versiones | Correcto | `node --version` y `git --version` (v26.11.1 y 2.56.0), respuesta en una tabla |
| 2. Crear notas.md | Correcto | Escribe el fichero y lo relee para verificarlo |
| 3. Editar notas.md | Correcto, con matiz | Usa `edit` sobre la última línea, pero la "ventaja de privacidad" que añade es *Independencia de proveedores*, relacionada con la privacidad solo de forma indirecta |
| 4. Facturas a JSON | Correcto al cuarto intento | Intenta tres scripts de Python para extraer los datos y los tres fallan (expresión regular mal hecha, `int('mar')`, desempaquetado incorrecto); al final escribe el JSON directamente con los datos que ya había extraído en su razonamiento, y lo hace perfecto |
| 5. Validar y sumar | Correcto | Valida con `python3 -c "import json..."`, obtiene `1772.3000000000002` y explica que es un artefacto de coma flotante: el total es 1.772,30 € |

Impresión de Fernando: *"todo ha ido súper fluido con Pi, todas las tareas se han ejecutado muy rápidas"*. No hizo falta cronometrar: cada tarea tardó unos pocos segundos, frente a minutos en el portátil Linux.

Lo que nos enseña:

- **La velocidad cambia la experiencia**: con 77 tok/s el razonamiento (en inglés, como siempre) y los reintentos pasan casi desapercibidos. En Linux los tres scripts fallidos de la tarea 4 habrían costado varios minutos.
- **El modelo extrae datos mejor que programa un extractor**: el razonamiento ya tenía los cuatro campos bien sacados desde el principio, pero se empeñó en escribir un *parser* y falló tres veces. Con un modelo de 1,7B, para textos cortos conviene pedirle explícitamente que extraiga él mismo los datos ("sin escribir código").
- **Sabe recuperarse**: ante los errores no entró en bucle, cambió de estrategia y terminó bien. También detectó solo el problema de coma flotante de la tarea 5.
- **Ojo con lo que Pi carga al arrancar**: en este Mac Pi ya tenía *skills* (`find-skills`, `hyperframes`...) y la extensión `@ollama/pi-web-search` instaladas de usos anteriores. Todo eso se añade al prompt de cada petición; para comparar de forma justa con Hermes hay que tenerlo en cuenta.

### Paso M4: Hermes Agent en el Mac

Ahora sí, la prueba que no pudimos hacer en el PC del trabajo (ver [3.4](#34-hermes-agent)): **¿aporta algo un arnés grande como Hermes con un modelo de 1,7B, o su prompt lo hace más lento y torpe que Pi?** En el Mac eres administrador y no hay reglas ASR, así que el instalador debería funcionar sin problemas.

#### M4.1 Subir el contexto a 64K

Hermes **exige al menos 64.000 tokens de contexto** y rechaza al arrancar modelos con menos. Subimos el del servidor (con las 6 capas de atención de LFM3 la memoria apenas crece):

```bash
launchctl setenv OLLAMA_CONTEXT_LENGTH 65536
```

Sal de Ollama desde la barra de menús y vuelve a abrirlo. Si quieres volver a Pi más adelante, 64K también le sirve (o deja `contextWindow` en 32768, que sigue siendo coherente porque es menor que el real).

#### M4.2 Instalar Hermes revisando antes el script

La documentación propone `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`, pero igual que en Windows es mejor descargarlo y leerlo antes de ejecutarlo:

```bash
mkdir -p ~/hermes-install && cd ~/hermes-install
curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o install-hermes.sh
less install-hermes.sh          # échale un vistazo; q para salir
bash install-hermes.sh --skip-browser --skip-computer-use
```

`--skip-browser` y `--skip-computer-use` evitan descargar Chromium y el controlador de *computer use*, que no necesitamos. Al terminar:

```bash
source ~/.zshrc
hermes --version
hermes doctor        # revisa la configuración y las dependencias
```

Dónde queda cada cosa:

| Ruta | Contenido |
|---|---|
| `~/.hermes/hermes-agent/` | Código fuente |
| `~/.local/bin/hermes` | Lanzador |
| `~/.hermes/config.yaml` | Configuración (proveedor, modelo, herramientas) |
| `~/.hermes/.env` | Secretos (claves de API; aquí no habrá ninguno) |

#### M4.3 Conectar Hermes con LFM3

```bash
ollama launch hermes
```

En el selector elige `lfm3:1.7b-q8_0` y, si pregunta por mensajería (Telegram, Slack...), sáltalo. Ollama configura Hermes con el endpoint `http://127.0.0.1:11434/v1` y lo arranca; sal con `/exit` o `Ctrl+D` para hacer antes dos comprobaciones:

```bash
cat ~/.hermes/config.yaml
hermes prompt-size      # tamaño del system prompt y de las herramientas
```

**Anota lo que muestre `hermes prompt-size`**: es la cifra clave de la comparación. Si `ollama launch hermes` diera problemas, la alternativa es `hermes model` > *More providers...* > *Custom endpoint*, URL `http://127.0.0.1:11434/v1`, sin clave de API y modelo `lfm3:1.7b-q8_0`.

**Lo que configuró `ollama launch hermes` en el Mac (27/11/2026)**: una configuración ya bastante adelgazada. Deja activos en la CLI solo los conjuntos `file`, `skills`, `terminal` y `vision` (11 herramientas), y desactiva el resto: navegador, web, memoria, subagentes, cron, generación de imágenes, mensajería... También deja la memoria persistente y la compresión del historial desactivadas, `reasoning_effort: medium` y avisos de bucles de herramientas (`tool_loop_guardrails`) activados.

Salida de `hermes prompt-size`:

| Bloque | Tamaño |
|---|---|
| System prompt | 9,1 KB (de ellos 3,4 KB son el índice de 43 *skills* incluidas) |
| Esquemas de herramientas | 14,4 KB (11 herramientas: `file` 5,0 KB, `skills` 4,6 KB, `terminal` 2,6 KB, otras 2,2 KB) |
| **Total por petición** | **~23,5 KB, unos 6.000 tokens** |

Es aproximadamente **diez veces el prompt base de Pi**. En el Mac no debería notarse mucho: el *prefill* en GPU es rápido y Ollama reutiliza la caché del prompt entre turnos. Dos cosas que no aportan nada con LFM3: el índice de *skills* (`p5js`, `songwriting-and-ai-music`, `manim-video`...) y la herramienta `vision`, porque nuestro modelo es solo de texto. Las dejamos en la primera pasada para medir Hermes tal como viene, y las quitamos en el apartado opcional M4.6.

#### M4.4 Mismas tareas que con Pi

```bash
mkdir -p ~/hermes-sandbox && cd ~/hermes-sandbox
hermes
```

Las cinco tareas de siempre (apartado M3.4), copiadas tal cual. Para cada una fíjate en: tiempo aproximado, si acierta, cuántas herramientas usa y si se atasca. En otra terminal, `ollama ps` debe mostrar `CONTEXT 65536`.

#### M4.5 Resultados: Pi frente a Hermes (27/11/2026)

`ollama ps` durante la prueba: `lfm3:1.7b-q8_0`, 2,1 GB (100 MB más que con 32K de contexto), `100% GPU`, contexto `65536`.

Hermes muestra al final de cada tarea su duración y lo que hizo; Pi no, así que para Pi solo tenemos la impresión de "unos segundos".

| Tarea | Pi | Hermes |
|---|---|---|
| 1. Versiones | Correcto. Git 2.56.0 | Correcto en 12,4 s (un comando). Git 2.50.1 (Apple Git) |
| 2. Crear notas.md | Correcto, relee el fichero para verificarlo | Correcto en 6,2 s, sin releerlo (se fía de la confirmación de la herramienta) |
| 3. Editar notas.md | Correcto con `edit`; ventaja poco ligada a la privacidad | Correcto en 10,9 s; reescribe el fichero entero con `write_file`; ventaja *Privacidad total*, bien enfocada |
| 4. Facturas a JSON | Correcto tras 3 scripts de Python fallidos | **Perfecto a la primera en 27,1 s**, extrayendo los datos él mismo, sin código |
| 5. Validar y sumar | Correcto (1.772,30) con `json.load` | Correcto en 13,3 s con `python3 -m json.tool`, más tabla de detalle y aviso de coma flotante |
| **Total** | Unos segundos por tarea | **70 s las cinco tareas** |

Impresión de Fernando: *"Hermes ha funcionado muy rápido, ha tenido que pensar menos que Pi para llegar a las soluciones, se ve un arnés más trabajado"*.

Lo que nos enseña:

- **Un prompt diez veces mayor no ha hecho a Hermes más lento ni más torpe**, al contrario. En una GPU el coste de procesar ~6.000 tokens de prompt es de décimas de segundo, y Ollama reaprovecha la caché entre turnos. En el portátil Linux, a 17 tok/s de *prefill*, ese mismo prompt costaría unos 6 minutos en la primera petición: **el tamaño del arnés importa mucho en CPU y poco en GPU**.
- **Las instrucciones del arnés guían a un modelo pequeño**: los razonamientos de Hermes son de 1 a 10 s y van más al grano. En la tarea 4 extrajo los datos directamente en lugar de programar un *parser*, que es justo lo que a Pi le salió mal. Parte del mérito puede ser también que el prompt de Pi en este Mac arrastra *skills* y extensiones de usos anteriores.
- **Hermes confía en sus herramientas**: no relee lo que escribe porque `write_file` le devuelve los bytes escritos y la ruta. Es más rápido, pero en la tarea 3 reescribió el fichero completo en lugar de añadir una línea; con ficheros grandes eso es más arriesgado (y más lento) que un `patch`.
- **Cada arnés ve un `PATH` distinto**: Pi encontró el Git de Homebrew (2.56.0) y Hermes el de Apple (`/usr/bin/git`, 2.50.1). Hermes ejecuta los comandos en su propio entorno y no carga la configuración de la shell igual que una terminal interactiva. Si un agente tiene que usar una versión concreta de una herramienta, conviene comprobar qué ve.
- **El contexto de 64K apenas cuesta memoria**: 2,1 GB frente a 2,0 GB con 32K, gracias a las 6 capas de atención de LFM3.

### Conclusiones de la fase Mac

- **En Apple Silicon M1 Pro, GGUF gana a MLX**: `q8_0` a 77 tok/s frente a 62 de `mxfp8`, y `qad-q4_0` a 115 tok/s como opción más rápida. La calidad es la misma en los cuatro formatos.
- **Con 75 a 115 tok/s el razonamiento deja de ser un problema**, así que se puede dejar activado y aprovechar su mejor fiabilidad.
- **En el Mac Hermes es mejor opción que Pi** para tareas agénticas con LFM3: más rápido en la práctica, menos razonamiento y mejores decisiones. En un equipo sin GPU (como el portátil Linux) Pi sigue siendo la opción sensata por su prompt mínimo.
- **Configuración recomendada para el Mac**: Ollama con `OLLAMA_CONTEXT_LENGTH=65536` y `OLLAMA_KEEP_ALIVE=30m` (vía `launchctl setenv`), `lfm3:1.7b-q8_0` (o `qad-q4_0` si se busca velocidad) y Hermes configurado con `ollama launch hermes`.

| Equipo | Generación Q8 | Mejor formato | Arnés recomendado |
|---|---|---|---|
| Windows, Core Ultra 5, 31 GB (CPU) | ~24 tok/s | `q8_0` | Pi (Hermes bloqueado por Defender) |
| Linux, i5-5200U, 8 GB (CPU) | ~5,8 tok/s | `qad-q4_0` (10 tok/s) | Pi |
| Mac M1 Pro, 16 GB (GPU) | ~77 tok/s | `q8_0` o `qad-q4_0` (115 tok/s) | Hermes |

#### M4.6 (Opcional) Adelgazar Hermes

Si va lento o se confunde eligiendo herramientas, desactiva los conjuntos que no hacen falta (con LFM3, `skills` y `vision` son los candidatos claros: unos 8 KB menos) y repite la tarea 4:

```bash
hermes tools          # activar o desactivar conjuntos de herramientas
hermes prompt-size    # comprobar cuánto ha bajado el prompt
```

#### M4.7 Desinstalar (cuando acabemos)

```bash
hermes uninstall --dry-run   # muestra qué borraría
hermes uninstall --full      # elimina también configuración y datos
```


## Chuleta de Ollama

Referencia rápida de lo que más se usa en el día a día, recopilado a lo largo de las tres fases. La columna "Visto en" indica dónde lo hemos usado en este proyecto.

### Comandos del terminal

| Comando | Para qué sirve | Visto en |
|---|---|---|
| `ollama pull <modelo>` | Descargar un modelo o actualizarlo | Todas las fases |
| `ollama list` (o `ollama ls`) | Ver los modelos descargados y su tamaño | Todas |
| `ollama show <modelo>` | Ver arquitectura, cuantización, contexto máximo y capacidades (`tools`, `thinking`...) | Paso 1.6 |
| `ollama show --modelfile <modelo>` | Ver el Modelfile: plantilla, parámetros por defecto y sistema | |
| `ollama run <modelo>` | Chat interactivo en el terminal | Paso 1.7 |
| `ollama run <modelo> --verbose` | Igual, mostrando métricas tras cada respuesta (tokens/s de prefill y generación) | Pasos 1.7 y L1 |
| `ollama run <modelo> "pregunta"` | Respuesta única, útil en scripts | |
| `ollama ps` | Modelos cargados en memoria: tamaño, `PROCESSOR` (CPU/GPU), contexto y cuándo se descargarán | Todas |
| `ollama stop <modelo>` | Descargar un modelo de memoria al momento | |
| `ollama rm <modelo>` | Borrar un modelo del disco | |
| `ollama cp <origen> <destino>` | Copiar un modelo con otro nombre (por ejemplo, antes de personalizarlo) | |
| `ollama create <nombre> -f Modelfile` | Crear un modelo propio a partir de un Modelfile | |
| `ollama launch <integración> --model <modelo>` | Instalar, configurar y lanzar una herramienta conectada a Ollama (Pi, Hermes, OpenCode, Claude Code, Codex...) | Pasos 3.3 y L4 |
| `ollama launch <integración> --config` | Solo configurar la integración, sin lanzarla | |
| `ollama serve` | Arrancar el servidor a mano (cuando no se usa la app ni el servicio) | |
| `ollama serve --help` | Lista completa de variables de entorno que admite el servidor | |

### Comandos dentro de `ollama run`

| Comando | Para qué sirve |
|---|---|
| `/?` | Ayuda con todos los comandos disponibles en tu versión |
| `/set parameter num_ctx 16384` | Cambiar un parámetro para esta sesión (vale cualquiera de la tabla de parámetros) |
| `/set system "..."` | Cambiar las instrucciones de sistema |
| `/set think` y `/set nothink` | Activar o desactivar el razonamiento |
| `/show info` | Información del modelo cargado |
| `/save <nombre>` | Guardar la sesión actual (parámetros y sistema) como un modelo nuevo |
| `/clear` | Borrar el historial de la conversación |
| `/bye` | Salir |

Los comandos con `/` pueden variar entre versiones; `/?` muestra los de la tuya.

### Variables de entorno del servidor

| Variable | Por defecto | Para qué sirve | Visto en |
|---|---|---|---|
| `OLLAMA_MODELS` | `~/.ollama/models` (Mac y Windows), `/usr/share/ollama/.ollama/models` (Linux) | Carpeta donde se guardan los modelos | Paso 1.3 |
| `OLLAMA_CONTEXT_LENGTH` | 4096 | Contexto por defecto cuando la petición no fija `num_ctx` (por ejemplo, desde la API compatible con OpenAI) | Pasos 3.3 y L4 |
| `OLLAMA_KEEP_ALIVE` | 5m | Tiempo que el modelo sigue en memoria sin uso. `-1` = siempre, `0` = descargar al terminar | Paso L4 |
| `OLLAMA_HOST` | `127.0.0.1:11434` | Dirección y puerto. `0.0.0.0:11434` lo expone a la red local (con cuidado: no tiene autenticación) | |
| `OLLAMA_NUM_PARALLEL` | 1 | Peticiones simultáneas por modelo. La memoria del contexto se multiplica por este valor | |
| `OLLAMA_MAX_LOADED_MODELS` | 3 (por GPU) | Cuántos modelos distintos pueden estar cargados a la vez | |
| `OLLAMA_MAX_QUEUE` | 512 | Peticiones en cola antes de responder con error 503 | |
| `OLLAMA_FLASH_ATTENTION` | Automático | `1` fuerza Flash Attention, `0` lo desactiva. Reduce memoria con contextos grandes | |
| `OLLAMA_KV_CACHE_TYPE` | `f16` | Cuantiza la caché KV: `q8_0` (mitad de memoria) o `q4_0` (una cuarta parte). Requiere Flash Attention | |
| `OLLAMA_ORIGINS` | Solo local | Orígenes web permitidos (extensiones de navegador, apps web) | |
| `OLLAMA_NO_CLOUD` | Sin definir | `1` desactiva las funciones en la nube de Ollama | |
| `HTTPS_PROXY` | Sin definir | Proxy para descargar modelos detrás de un proxy corporativo | |

**Cómo se definen** (la lección que hemos aprendido en cada sistema):

| Sistema | Cómo | Después |
|---|---|---|
| Windows | `[Environment]::SetEnvironmentVariable("VAR", "valor", "User")` (no `$env:`, que solo dura en esa ventana) | Salir de Ollama desde la bandeja y volver a abrirlo |
| Linux (servicio systemd) | `sudo systemctl edit ollama` y `Environment="VAR=valor"` en `[Service]` (no `.bashrc`) | `sudo systemctl restart ollama` |
| macOS (app) | `launchctl setenv VAR valor` | Salir de Ollama desde la barra de menús y volver a abrirlo |

### Parámetros del modelo

Se pueden fijar en cada petición a la API (`options`), en `ollama run` con `/set parameter` o de forma permanente en un Modelfile con `PARAMETER`.

| Parámetro | Por defecto de Ollama | Recomendado para LFM3 | Para qué sirve |
|---|---|---|---|
| `num_ctx` | 4096 | 4096 para chat, 32768 para agentes | Tamaño de la ventana de contexto en tokens |
| `temperature` | 0.8 | **0.1** (1.0 para matemáticas) | Aleatoriedad. Bajo = respuestas más deterministas |
| `top_k` | 40 | **50** (20 para matemáticas) | Solo elige entre los K tokens más probables |
| `top_p` | 0.9 | 0.95 solo para matemáticas | Solo elige entre los tokens que suman esa probabilidad |
| `repeat_penalty` | 1.0 | **1.1** | Penaliza repetir texto |
| `num_predict` | -1 (sin límite) | | Máximo de tokens a generar. Útil para cortar respuestas largas (pero puede cortar el razonamiento a medias) |
| `seed` | 0 (aleatorio) | Un número fijo para pruebas | Hace las respuestas reproducibles |
| `stop` | | | Textos que detienen la generación |

### Opciones de la API (`/api/chat`)

| Campo | Para qué sirve | Visto en |
|---|---|---|
| `messages` | Historial completo de la conversación (`system`, `user`, `assistant`, `tool`) | `chat.py` |
| `tools` | Lista de herramientas en JSON Schema que el modelo puede pedir | `agente_mini.py` |
| `think` | `true`/`false`: activa o desactiva el razonamiento **en cada petición** | Pasos 2 y L2 |
| `format` | `"json"` o un JSON Schema completo: obliga a que la respuesta cumpla esa estructura | |
| `stream` | `true` devuelve el texto a medida que se genera | `chat.py` |
| `keep_alive` | Igual que `OLLAMA_KEEP_ALIVE`, pero para esta petición (`0` descarga el modelo) | `bench.py` |
| `options` | Parámetros del modelo de la tabla anterior | Todos los scripts |

La API compatible con OpenAI (`/v1/chat/completions`) es la que usan Pi, Hermes y la mayoría de herramientas. Es cómoda, pero **no permite fijar `num_ctx` por petición**: por eso hay que subir `OLLAMA_CONTEXT_LENGTH` en el servidor.

### Modelfile: personalizar un modelo

Un Modelfile permite crear una variante con los parámetros recomendados ya fijados, para no tener que pasarlos en cada petición:

```text
FROM lfm3:1.7b-q8_0
PARAMETER temperature 0.1
PARAMETER top_k 50
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 32768
SYSTEM "Eres un asistente técnico. Responde en español, de forma breve y precisa."
```

```bash
ollama create lfm3-agente -f Modelfile
ollama run lfm3-agente
```


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
| Defender bloquea `python.exe` o `whoami.exe`/`tar.exe` al instalar Hermes | Reglas ASR de prevalencia y de herramientas del sistema suplantadas | Pedir exclusión a TI, usar VM/Dev Box/WSL o probarlo en otro equipo |
| Una variable de Ollama no tiene efecto en Linux | El servicio systemd no lee `.bashrc` ni el entorno de la terminal | `sudo systemctl edit ollama` con `Environment=...` y `sudo systemctl restart ollama` |
| `node -v` sigue mostrando 18 tras `brew install node` | bash recuerda la ruta antigua | `hash -r` o abrir una terminal nueva |
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
- Hermes en Windows nativo: <https://hermes-agent.nousresearch.com/docs/user-guide/windows-native>
- Preguntas frecuentes y variables de entorno de Ollama: <https://docs.ollama.com/faq>
- Comandos de Ollama: <https://docs.ollama.com/cli>
- Ollama en macOS: <https://docs.ollama.com/macos>
- Formato Modelfile: <https://docs.ollama.com/modelfile>
