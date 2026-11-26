#!/usr/bin/env python3
"""Mini agente: muestra por dentro cómo funciona el tool calling con Ollama.

Versión Linux/macOS de agente-mini.ps1. Solo usa la biblioteca estándar.

El bucle agéntico:
  1. Se envía al modelo la conversación y la lista de herramientas.
  2. Si responde con tool_calls, el script ejecuta cada herramienta y le
     devuelve el resultado con un mensaje de rol "tool".
  3. Se repite hasta que el modelo responde con texto normal.
Las herramientas son de solo lectura y no salen de la carpeta base (--base).

Uso:
    python3 scripts/agente_mini.py
    python3 scripts/agente_mini.py --no-think
Comandos: /reset, /think on|off, /bye
"""
import argparse
import datetime as dt
import json
import os
import platform
import sys
import time
import urllib.request

GRIS, VERDE, AMARILLO, CIAN, MAGENTA, ROJO, FIN = ("\033[90m", "\033[92m", "\033[33m", "\033[96m",
                                                   "\033[95m", "\033[91m", "\033[0m")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]

# ---------------------------------------------------------------------------
# 1. Definición de herramientas (JSON Schema, el mismo formato que usa OpenAI)
# ---------------------------------------------------------------------------
TOOLS = [
    {"type": "function", "function": {
        "name": "obtener_fecha_hora",
        "description": "Devuelve la fecha, la hora y el día de la semana actuales del equipo.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "info_sistema",
        "description": "Devuelve el modelo de CPU, el número de hilos, la RAM total y la RAM disponible del equipo.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "listar_ficheros",
        "description": "Lista los ficheros y carpetas de una ruta relativa a la carpeta del proyecto. Usa '.' para la raíz.",
        "parameters": {"type": "object",
                       "properties": {"ruta": {"type": "string", "description": "Ruta relativa, por ejemplo '.' o 'scripts'"}},
                       "required": ["ruta"]}}},
    {"type": "function", "function": {
        "name": "leer_fichero",
        "description": "Lee el contenido de texto de un fichero (máximo 4000 caracteres) dada su ruta relativa a la carpeta del proyecto.",
        "parameters": {"type": "object",
                       "properties": {"ruta": {"type": "string", "description": "Ruta relativa, por ejemplo 'scripts/chat.py'"}},
                       "required": ["ruta"]}}},
]


# ---------------------------------------------------------------------------
# 2. Implementación real de cada herramienta (la ejecuta el script, no el modelo)
# ---------------------------------------------------------------------------
def ruta_segura(base, ruta):
    full = os.path.realpath(os.path.join(base, ruta or "."))
    if full != base and not full.startswith(base + os.sep):
        raise ValueError(f"Ruta fuera de la carpeta del proyecto: {ruta}")
    return full


def info_sistema():
    cpu, mem = platform.processor() or "desconocida", {}
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()
                    break
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                mem[k] = int(v.split()[0])
    except FileNotFoundError:
        pass
    return json.dumps({
        "cpu": cpu,
        "hilos": os.cpu_count(),
        "ram_total_gb": round(mem.get("MemTotal", 0) / 2**20, 1),
        "ram_disponible_gb": round(mem.get("MemAvailable", 0) / 2**20, 1),
    }, ensure_ascii=False)


def ejecutar(base, nombre, args):
    try:
        if nombre == "obtener_fecha_hora":
            n = dt.datetime.now()
            return f"{DIAS[n.weekday()]}, {n.day} de {MESES[n.month - 1]} de {n.year}, {n:%H:%M}"
        if nombre == "info_sistema":
            return info_sistema()
        if nombre == "listar_ficheros":
            p = ruta_segura(base, args.get("ruta", "."))
            items = []
            for e in sorted(os.scandir(p), key=lambda e: e.name):
                if e.name == ".git":
                    continue
                items.append(f"[carpeta] {e.name}" if e.is_dir() else f"{e.name} ({e.stat().st_size} bytes)")
            return "\n".join(items) or "(carpeta vacía)"
        if nombre == "leer_fichero":
            p = ruta_segura(base, args.get("ruta", ""))
            with open(p, encoding="utf-8", errors="replace") as f:
                txt = f.read()
            return txt[:4000] + ("\n...(truncado)" if len(txt) > 4000 else "")
        return f"Error: la herramienta '{nombre}' no existe."
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# 3. Una llamada al modelo, en streaming para ver el progreso en máquinas lentas
# ---------------------------------------------------------------------------
def llamar(url, body):
    req = urllib.request.Request(url + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    content, tool_calls, final, en_razonamiento = [], [], {}, False
    with OPENER.open(req, timeout=900) as r:
        for raw in r:
            chunk = json.loads(raw)
            msg = chunk.get("message", {})
            if msg.get("thinking"):
                if not en_razonamiento:
                    print(f"  {AMARILLO}[razonamiento] ", end="")
                    en_razonamiento = True
                print(msg["thinking"], end="", flush=True)
            if msg.get("content"):
                content.append(msg["content"])
            if msg.get("tool_calls"):
                tool_calls.extend(msg["tool_calls"])
            if chunk.get("done"):
                final = chunk
    if en_razonamiento:
        print(FIN)
    return "".join(content), tool_calls, final


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="lfm3:1.7b-q8_0")
    ap.add_argument("--base", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--max-pasos", type=int, default=8)
    ap.add_argument("--no-think", action="store_true")
    ap.add_argument("--url", default="http://localhost:11434")
    a = ap.parse_args()
    base = os.path.realpath(a.base)

    system = ("Eres un agente que trabaja en el equipo del usuario. Usa las herramientas disponibles siempre que "
              "necesites datos reales (fecha, sistema o ficheros); no inventes esa información. Cuando tengas lo "
              "necesario, responde en español de forma breve.")
    messages = [{"role": "system", "content": system}]

    print(f"{CIAN}Mini agente | modelo {a.model} | carpeta base {base} | think {not a.no_think}{FIN}")
    print(f"{CIAN}Herramientas: {', '.join(t['function']['name'] for t in TOOLS)}{FIN}")
    print(f"{CIAN}Comandos: /reset, /think on|off, /bye{FIN}\n")

    while True:
        try:
            prompt = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not prompt:
            continue
        if prompt == "/bye":
            break
        if prompt == "/reset":
            messages = messages[:1]
            print("Historial borrado.\n")
            continue
        if prompt in ("/think on", "/think off"):
            a.no_think = prompt.endswith("off")
            print(f"Razonamiento {'desactivado' if a.no_think else 'activado'}.\n")
            continue

        messages.append({"role": "user", "content": prompt})
        t0, tokens, paso = time.perf_counter(), 0, 0

        for paso in range(1, a.max_pasos + 1):
            body = {"model": a.model, "messages": messages, "tools": TOOLS, "stream": True,
                    "options": {"temperature": 0.1, "top_k": 50, "repeat_penalty": 1.1, "num_ctx": a.num_ctx}}
            if a.no_think:
                body["think"] = False
            try:
                content, tool_calls, final = llamar(a.url, body)
            except Exception as e:
                print(f"{ROJO}Error llamando a la API: {e}{FIN}")
                break
            tokens += final.get("eval_count", 0)

            if not tool_calls:
                # Respuesta final: sin llamadas a herramientas
                print(f"\n{VERDE}LFM3: {content}{FIN}\n")
                messages.append({"role": "assistant", "content": content})
                break

            # El modelo pide herramientas: se guarda su petición en el historial...
            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
            # ...se ejecuta cada una y se devuelve el resultado con rol "tool"
            for call in tool_calls:
                nombre = call["function"]["name"]
                args = call["function"].get("arguments") or {}
                if isinstance(args, str):
                    args = json.loads(args or "{}")
                print(f"  {MAGENTA}[paso {paso}] herramienta: {nombre}({json.dumps(args, ensure_ascii=False)}){FIN}")
                resultado = ejecutar(base, nombre, args)
                vista = resultado if len(resultado) <= 200 else resultado[:200] + "..."
                print(f"  {MAGENTA}          resultado: {vista}{FIN}")
                messages.append({"role": "tool", "tool_name": nombre, "content": resultado})
        else:
            print(f"{ROJO}Se alcanzó el máximo de {a.max_pasos} pasos sin respuesta final.{FIN}")

        print(f"{GRIS}  pasos: {paso} | tokens generados: {tokens} | tiempo total: "
              f"{time.perf_counter() - t0:.1f} s{FIN}\n")


if __name__ == "__main__":
    main()
