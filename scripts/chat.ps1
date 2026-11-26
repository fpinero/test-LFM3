<#
.SYNOPSIS
  Chatbot mínimo contra la API local de Ollama, con métricas de eficiencia.

.DESCRIPTION
  Mantiene el historial de la conversación, envía cada turno a /api/chat,
  muestra tokens/s de prefill y de generación, la memoria del modelo cargado
  (/api/ps) y guarda las métricas en metricas.csv junto al script.
  Compatible con Windows PowerShell 5.1 y PowerShell 7. No requiere admin.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\chat.ps1
  .\scripts\chat.ps1 -NumCtx 16384 -NoThink
#>
param(
    [string]$Model  = "lfm3:1.7b-q8_0",
    [string]$System = "Eres un asistente útil. Responde siempre en español, de forma breve y precisa. Si no sabes algo, dilo en lugar de inventarlo.",
    [int]   $NumCtx = 4096,
    [double]$Temperature = 0.1,
    [switch]$NoThink,
    [string]$Url = "http://localhost:11434"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$csv = Join-Path $PSScriptRoot "metricas.csv"

function New-Client {
    $wc = New-Object System.Net.WebClient
    $wc.Encoding = [Text.Encoding]::UTF8   # cuerpo y respuesta en UTF-8 (tildes, eñes)
    $wc.Proxy = $null                      # localhost: evitar el proxy corporativo
    $wc.Headers["Content-Type"] = "application/json"
    return $wc
}

function Get-LoadedModel {
    try {
        $ps = (New-Client).DownloadString("$Url/api/ps") | ConvertFrom-Json
        return $ps.models | Where-Object { $_.name -eq $Model -or $_.model -eq $Model } | Select-Object -First 1
    } catch { return $null }
}

function Show-Stats {
    $m = Get-LoadedModel
    if ($m) {
        $sizeMB = [math]::Round($m.size / 1MB)
        $vramMB = [math]::Round($m.size_vram / 1MB)
        Write-Host ("  modelo en memoria: {0} MB (de ellos en GPU: {1} MB), contexto {2}" -f $sizeMB, $vramMB, $m.context_length) -ForegroundColor DarkGray
    }
    $procs = Get-Process -Name "ollama*" -ErrorAction SilentlyContinue
    if ($procs) {
        $ram = [math]::Round((($procs | Measure-Object WorkingSet64 -Sum).Sum) / 1MB)
        Write-Host ("  RAM procesos ollama*: {0} MB" -f $ram) -ForegroundColor DarkGray
    }
}

function Reset-History {
    $h = New-Object System.Collections.ArrayList
    [void]$h.Add(@{ role = "system"; content = $System })
    return ,$h
}

# Comprobar que el servidor responde
try {
    $ver = ((New-Client).DownloadString("$Url/api/version") | ConvertFrom-Json).version
} catch {
    Write-Host "No se puede conectar con Ollama en $Url. ¿Está abierto el icono de la bandeja?" -ForegroundColor Red
    exit 1
}

Write-Host "Ollama $ver | modelo $Model | num_ctx $NumCtx | temperature $Temperature | think $(-not $NoThink)" -ForegroundColor Cyan
Write-Host "Comandos: /reset (borra historial), /stats (memoria), /bye (salir)`n" -ForegroundColor Cyan

$messages = Reset-History
$turn = 0

while ($true) {
    $prompt = Read-Host "Tú"
    if ([string]::IsNullOrWhiteSpace($prompt)) { continue }
    # Nota: se usa if y no switch, porque "continue" dentro de un switch no salta el bucle while
    $cmd = $prompt.Trim()
    if ($cmd -eq "/bye")   { Write-Host "Hasta luego."; break }
    if ($cmd -eq "/reset") { $messages = Reset-History; $turn = 0; Write-Host "Historial borrado.`n"; continue }
    if ($cmd -eq "/stats") { Show-Stats; continue }

    [void]$messages.Add(@{ role = "user"; content = $prompt })

    $body = @{
        model    = $Model
        messages = $messages
        stream   = $false
        options  = @{
            temperature    = $Temperature
            top_k          = 50
            repeat_penalty = 1.1
            num_ctx        = $NumCtx
        }
    }
    if ($NoThink) { $body.think = $false }
    $json = $body | ConvertTo-Json -Depth 10

    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        $resp = (New-Client).UploadString("$Url/api/chat", "POST", $json) | ConvertFrom-Json
    } catch {
        Write-Host "Error llamando a la API: $($_.Exception.Message)" -ForegroundColor Red
        $messages.RemoveAt($messages.Count - 1)
        continue
    }
    $sw.Stop()
    $turn++

    if ($resp.message.thinking) {
        Write-Host "`n[razonamiento]" -ForegroundColor DarkYellow
        Write-Host $resp.message.thinking -ForegroundColor DarkYellow
    }
    Write-Host "`nLFM3: $($resp.message.content)`n" -ForegroundColor Green
    [void]$messages.Add(@{ role = "assistant"; content = $resp.message.content })

    # Métricas: las duraciones de Ollama vienen en nanosegundos
    $promptTok = [int]$resp.prompt_eval_count
    $evalTok   = [int]$resp.eval_count
    $promptS   = $resp.prompt_eval_duration / 1e9
    $evalS     = $resp.eval_duration / 1e9
    $loadS     = $resp.load_duration / 1e9
    $totalS    = $resp.total_duration / 1e9
    $prefill   = if ($promptS -gt 0) { [math]::Round($promptTok / $promptS, 2) } else { 0 }
    $decode    = if ($evalS   -gt 0) { [math]::Round($evalTok / $evalS, 2) }     else { 0 }

    Write-Host ("  prompt: {0} tok a {1} tok/s | respuesta: {2} tok a {3} tok/s | carga {4:N2} s | total {5:N2} s (reloj {6:N2} s)" -f `
        $promptTok, $prefill, $evalTok, $decode, $loadS, $totalS, $sw.Elapsed.TotalSeconds) -ForegroundColor DarkGray
    Show-Stats
    Write-Host ""

    $m = Get-LoadedModel
    [pscustomobject]@{
        fecha          = (Get-Date).ToString("s")
        modelo         = $Model
        turno          = $turn
        num_ctx        = $NumCtx
        think          = -not $NoThink
        prompt_tokens  = $promptTok
        prefill_tok_s  = $prefill
        output_tokens  = $evalTok
        decode_tok_s   = $decode
        load_s         = [math]::Round($loadS, 3)
        total_s        = [math]::Round($totalS, 3)
        modelo_mem_mb  = if ($m) { [math]::Round($m.size / 1MB) } else { $null }
        pregunta       = $prompt
    } | Export-Csv -Path $csv -Append -NoTypeInformation -Encoding UTF8
}
