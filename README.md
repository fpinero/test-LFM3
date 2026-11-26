# Prueba local de Liquid LFM3 (texto, Q8)

Guía didáctica, paso a paso, para desplegar en local el modelo de texto **Liquid LFM3** (1.7B parámetros) con cuantización de 8 bits (**Q8_0**), usarlo como chatbot básico, medir su eficiencia y, al final, conectarlo a un arnés agéntico para que ejecute tareas con herramientas (tool use).

La primera fase se realiza en un PC Windows corporativo **sin permisos de administrador**. Más adelante se repetirá en un Mac (Apple Silicon), donde se usará otro formato del modelo (MLX).

> Estado: fase 1, paso 1 (instalación del runtime y del modelo). Cada paso se valida en la máquina real antes de documentar el siguiente.

## Índice

1. [Qué es LFM3 y qué variante usamos](#qué-es-lfm3-y-qué-variante-usamos)
2. [Entorno de pruebas](#entorno-de-pruebas)
3. [Elección del runtime sin permisos de administrador](#elección-del-runtime-sin-permisos-de-administrador)
4. [Fase 1: Windows sin admin](#fase-1-windows-sin-admin)
   - [Paso 1: instalar Ollama por usuario y descargar LFM3 Q8](#paso-1-instalar-ollama-por-usuario-y-descargar-lfm3-q8)
   - [Paso 2: chatbot básico y medición de eficiencia](#paso-2-chatbot-básico-y-medición-de-eficiencia) (pendiente)
   - [Paso 3: arnés agéntico con tool use](#paso-3-arnés-agéntico-con-tool-use) (pendiente)
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
| Equipo | PC del trabajo, Intel Core i5 con NPU | Mac (Apple Silicon) |
| RAM | 16 GB | Por definir |
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

Después cierra Ollama desde el icono de la bandeja y vuelve a abrirlo (y abre un PowerShell nuevo) para que lea la variable.

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

- [ ] `ollama --version` ≥ 0.40.13
- [ ] `ollama list` muestra `lfm3:1.7b-q8_0`
- [ ] `ollama show` indica `Q8_0` y la capacidad `tools`
- [ ] El modelo responde en español
- [ ] Anotado el `eval rate` de la primera respuesta: ____ tokens/s

### Paso 2: chatbot básico y medición de eficiencia

Pendiente de validar el paso 1. Previsto: medir tokens/s y RAM (`ollama ps` y Administrador de tareas), probar el contexto y montar un chat sencillo contra la API local.

### Paso 3: arnés agéntico con tool use

Pendiente. Previsto: conectar un arnés agéntico (Hermes Agent, Pi coding agent u otro compatible con la API de Ollama) al modelo local y encargarle una tarea que requiera usar herramientas.

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
| Logs del servidor | | `%LOCALAPPDATA%\Ollama` |

## Referencias

- Modelo GGUF en Hugging Face: <https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF>
- Ollama para Windows: <https://docs.ollama.com/windows>
- LFM3 en Ollama, tags y tool calling: <https://www.betterclaw.io/blog/lfm3-ollama-tool-calling-agent-setup>
- Resumen de LFM3 en Ollama: <https://jdneer.com/blog/liquid-ai-lfm3-local-agent-model-ollama>
