<#
.SYNOPSIS
  Mini agente en PowerShell: muestra por dentro cómo funciona el tool calling
  (llamadas a herramientas) con un modelo local servido por Ollama.

.DESCRIPTION
  El "bucle agéntico" es siempre el mismo:
    1. Se envía al modelo la conversación y la lista de herramientas disponibles.
    2. Si el modelo responde con tool_calls, el script ejecuta cada herramienta
       y le devuelve el resultado con un mensaje de rol "tool".
    3. Se repite hasta que el modelo responde con texto normal (sin tool_calls).
  Las herramientas son de solo lectura y no salen de la carpeta base (-Base).
  No requiere admin ni instalar nada.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\agente-mini.ps1
  .\scripts\agente-mini.ps1 -Base C:\Users\yo\test-LFM3 -NoThink
#>
param(
    [string]$Model    = "lfm3:1.7b-q8_0",
    [string]$Base     = (Split-Path $PSScriptRoot -Parent),
    [int]   $NumCtx   = 8192,
    [int]   $MaxPasos = 8,
    [switch]$NoThink,
    [string]$Url      = "http://localhost:11434"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$Base = (Resolve-Path $Base).Path

function New-Client {
    $wc = New-Object System.Net.WebClient
    $wc.Encoding = [Text.Encoding]::UTF8
    $wc.Proxy = $null
    $wc.Headers["Content-Type"] = "application/json"
    return $wc
}

# ---------------------------------------------------------------------------
# 1. Definición de herramientas (JSON Schema, el mismo formato que usa OpenAI)
# ---------------------------------------------------------------------------
$tools = @(
    @{ type = "function"; function = @{
        name = "obtener_fecha_hora"
        description = "Devuelve la fecha, la hora y el día de la semana actuales del equipo."
        parameters = @{ type = "object"; properties = @{} }
    } },
    @{ type = "function"; function = @{
        name = "info_sistema"
        description = "Devuelve el modelo de CPU, el número de núcleos, la RAM total y la RAM libre del equipo."
        parameters = @{ type = "object"; properties = @{} }
    } },
    @{ type = "function"; function = @{
        name = "listar_ficheros"
        description = "Lista los ficheros y carpetas de una ruta relativa a la carpeta del proyecto. Usa '.' para la raíz."
        parameters = @{ type = "object"
            properties = @{ ruta = @{ type = "string"; description = "Ruta relativa, por ejemplo '.' o 'scripts'" } }
            required = @("ruta") }
    } },
    @{ type = "function"; function = @{
        name = "leer_fichero"
        description = "Lee el contenido de texto de un fichero (máximo 4000 caracteres) dada su ruta relativa a la carpeta del proyecto."
        parameters = @{ type = "object"
            properties = @{ ruta = @{ type = "string"; description = "Ruta relativa, por ejemplo 'scripts/chat.ps1'" } }
            required = @("ruta") }
    } }
)

# ---------------------------------------------------------------------------
# 2. Implementación real de cada herramienta (esto lo ejecuta el script, no el modelo)
# ---------------------------------------------------------------------------
function Resolve-Seguro([string]$ruta) {
    if ([string]::IsNullOrWhiteSpace($ruta)) { $ruta = "." }
    $full = [IO.Path]::GetFullPath((Join-Path $Base $ruta))
    if (-not $full.StartsWith($Base, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Ruta fuera de la carpeta del proyecto: $ruta"
    }
    return $full
}

function Invoke-Herramienta([string]$nombre, $argumentos) {
    try {
        switch ($nombre) {
            "obtener_fecha_hora" {
                $c = [Globalization.CultureInfo]::GetCultureInfo("es-ES")
                return (Get-Date).ToString("dddd, d 'de' MMMM 'de' yyyy, HH:mm", $c)
            }
            "info_sistema" {
                $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
                $os  = Get-CimInstance Win32_OperatingSystem
                return (@{
                    cpu            = $cpu.Name.Trim()
                    nucleos        = $cpu.NumberOfCores
                    hilos          = $cpu.NumberOfLogicalProcessors
                    ram_total_gb   = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
                    ram_libre_gb   = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
                } | ConvertTo-Json -Compress)
            }
            "listar_ficheros" {
                $p = Resolve-Seguro $argumentos.ruta
                $items = Get-ChildItem -LiteralPath $p -Force | Where-Object { $_.Name -ne ".git" } |
                    ForEach-Object { if ($_.PSIsContainer) { "[carpeta] $($_.Name)" } else { "$($_.Name) ($($_.Length) bytes)" } }
                if (-not $items) { return "(carpeta vacía)" }
                return ($items -join "`n")
            }
            "leer_fichero" {
                $p = Resolve-Seguro $argumentos.ruta
                $txt = Get-Content -LiteralPath $p -Raw -Encoding UTF8
                if ($txt.Length -gt 4000) { $txt = $txt.Substring(0, 4000) + "`n...(truncado)" }
                return $txt
            }
            default { return "Error: la herramienta '$nombre' no existe." }
        }
    } catch {
        return "Error: $($_.Exception.Message)"
    }
}

# ---------------------------------------------------------------------------
# 3. Bucle agéntico
# ---------------------------------------------------------------------------
$system = "Eres un agente que trabaja en el equipo del usuario. Usa las herramientas disponibles siempre que necesites datos reales (fecha, sistema o ficheros); no inventes esa información. Cuando tengas lo necesario, responde en español de forma breve."
$messages = New-Object System.Collections.ArrayList
[void]$messages.Add(@{ role = "system"; content = $system })

Write-Host "Mini agente | modelo $Model | carpeta base $Base | think $(-not $NoThink)" -ForegroundColor Cyan
Write-Host "Herramientas: $(($tools | ForEach-Object { $_.function.name }) -join ', ')" -ForegroundColor Cyan
Write-Host "Comandos: /reset, /bye`n" -ForegroundColor Cyan

while ($true) {
    $prompt = Read-Host "Tú"
    if ([string]::IsNullOrWhiteSpace($prompt)) { continue }
    $cmd = $prompt.Trim()
    if ($cmd -eq "/bye") { break }
    if ($cmd -eq "/reset") { $messages.RemoveRange(1, $messages.Count - 1); Write-Host "Historial borrado.`n"; continue }

    [void]$messages.Add(@{ role = "user"; content = $prompt })
    $reloj = [Diagnostics.Stopwatch]::StartNew()
    $tokens = 0

    for ($paso = 1; $paso -le $MaxPasos; $paso++) {
        $body = @{
            model    = $Model
            messages = $messages
            tools    = $tools
            stream   = $false
            options  = @{ temperature = 0.1; top_k = 50; repeat_penalty = 1.1; num_ctx = $NumCtx }
        }
        if ($NoThink) { $body.think = $false }
        $json = $body | ConvertTo-Json -Depth 20

        try {
            $resp = (New-Client).UploadString("$Url/api/chat", "POST", $json) | ConvertFrom-Json
        } catch {
            Write-Host "Error llamando a la API: $($_.Exception.Message)" -ForegroundColor Red
            break
        }
        $tokens += [int]$resp.eval_count
        $msg = $resp.message

        if ($msg.thinking) { Write-Host "  [razonamiento] $($msg.thinking)" -ForegroundColor DarkYellow }

        if (-not $msg.tool_calls) {
            # Respuesta final: sin llamadas a herramientas
            Write-Host "`nLFM3: $($msg.content)`n" -ForegroundColor Green
            [void]$messages.Add(@{ role = "assistant"; content = $msg.content })
            break
        }

        # El modelo pide ejecutar herramientas: se guarda su petición en el historial...
        [void]$messages.Add(@{ role = "assistant"; content = "$($msg.content)"; tool_calls = $msg.tool_calls })

        # ...se ejecuta cada una y se devuelve el resultado con rol "tool"
        foreach ($call in $msg.tool_calls) {
            $nombre = $call.function.name
            $args_  = $call.function.arguments
            Write-Host ("  [paso {0}] herramienta: {1}({2})" -f $paso, $nombre, ($args_ | ConvertTo-Json -Compress)) -ForegroundColor Magenta
            $resultado = Invoke-Herramienta $nombre $args_
            $vista = if ($resultado.Length -gt 200) { $resultado.Substring(0, 200) + "..." } else { $resultado }
            Write-Host "           resultado: $vista" -ForegroundColor DarkMagenta
            [void]$messages.Add(@{ role = "tool"; tool_name = $nombre; content = "$resultado" })
        }

        if ($paso -eq $MaxPasos) { Write-Host "Se alcanzó el máximo de $MaxPasos pasos sin respuesta final." -ForegroundColor Red }
    }

    $reloj.Stop()
    Write-Host ("  pasos: {0} | tokens generados: {1} | tiempo total: {2:N1} s`n" -f [math]::Min($paso, $MaxPasos), $tokens, $reloj.Elapsed.TotalSeconds) -ForegroundColor DarkGray
}
