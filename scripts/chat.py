#!/usr/bin/env python3
"""Chatbot mínimo contra la API local de Ollama, con métricas de eficiencia.

Versión Linux/macOS de chat.ps1. Solo usa la biblioteca estándar de Python.
Diferencia principal: usa streaming, de modo que el texto aparece a medida que
se genera (en una máquina lenta se agradece) y las métricas llegan en el
último fragmento de la respuesta.

Uso:
    python3 scripts/chat.py
    python3 scripts/chat.py --num-ctx 16384 --no-think
Comandos dentro del chat: /reset, /stats, /think on|off, /bye
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.request

DEFAULT_SYSTEM = ("Eres un asistente útil. Responde siempre en español, de forma breve y precisa. "
                  "Si no sabes algo, dilo en lugar de inventarlo.")

GRIS, VERDE, AMARILLO, CIAN, ROJO, FIN = "\033[90m", "\033[92m", "\033[33m", "\033[96m", "\033[91m", "\033[0m"

# localhost: no pasar por ningún proxy aunque haya variables http_proxy definidas
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api_get(url, path):
    with OPENER.open(url + path, timeout=10) as r:
        return json.load(r)


def mem_available_mb():
    """RAM disponible según el kernel (la columna 'available' de free)."""
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    return None


def rss_ollama_mb():
    """Suma la RSS de los procesos cuyo nombre o comando contiene ollama o llama."""
    total = 0
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode(errors="ignore")
            if "ollama" not in cmd and "llama" not in cmd:
                continue
            with open(f"/proc/{pid}/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        total += int(line.split()[1])
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    return total // 1024


def loaded_model(url, model):
    try:
        for m in api_get(url, "/api/ps").get("models", []):
            if m.get("name") == model or m.get("model") == model:
                return m
    except Exception:
        pass
    return None


def show_stats(url, model):
    m = loaded_model(url, model)
    if m:
        print(f"{GRIS}  modelo en memoria: {m['size'] // 2**20} MB (en GPU: {m.get('size_vram', 0) // 2**20} MB), "
              f"contexto {m.get('context_length', '?')}{FIN}")
    if sys.platform.startswith("linux"):
        print(f"{GRIS}  RAM disponible: {mem_available_mb()} MB | RSS procesos ollama/llama: {rss_ollama_mb()} MB{FIN}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default="lfm3:1.7b-q8_0")
    p.add_argument("--system", default=DEFAULT_SYSTEM)
    p.add_argument("--num-ctx", type=int, default=4096)
    p.add_argument("--temperature", type=float, default=0.1)
    p.add_argument("--no-think", action="store_true", help="desactiva el razonamiento previo")
    p.add_argument("--url", default="http://localhost:11434")
    a = p.parse_args()

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metricas-linux.csv")

    try:
        version = api_get(a.url, "/api/version")["version"]
    except Exception as e:
        print(f"{ROJO}No se puede conectar con Ollama en {a.url}: {e}{FIN}")
        print("¿Está activo el servicio? Prueba: systemctl status ollama")
        sys.exit(1)

    print(f"{CIAN}Ollama {version} | modelo {a.model} | num_ctx {a.num_ctx} | "
          f"temperature {a.temperature} | think {not a.no_think}{FIN}")
    print(f"{CIAN}Comandos: /reset (borra historial), /stats (memoria), /think on|off (razonamiento), /bye (salir){FIN}\n")

    messages = [{"role": "system", "content": a.system}]
    turn = 0

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
            messages, turn = messages[:1], 0
            print("Historial borrado.\n")
            continue
        if prompt == "/stats":
            show_stats(a.url, a.model)
            continue
        if prompt in ("/think on", "/think off"):
            # Permite alternar el razonamiento sin perder el historial de la conversación
            a.no_think = prompt.endswith("off")
            print(f"Razonamiento {'desactivado' if a.no_think else 'activado'}.\n")
            continue

        messages.append({"role": "user", "content": prompt})
        body = {
            "model": a.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": a.temperature, "top_k": 50, "repeat_penalty": 1.1, "num_ctx": a.num_ctx},
        }
        if a.no_think:
            body["think"] = False

        req = urllib.request.Request(a.url + "/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        t0 = time.perf_counter()
        first_token = None
        content, final = [], {}
        in_thinking = False
        try:
            with OPENER.open(req, timeout=600) as r:
                # Cada línea de la respuesta es un JSON con un fragmento del mensaje
                for raw in r:
                    chunk = json.loads(raw)
                    msg = chunk.get("message", {})
                    if msg.get("thinking"):
                        if first_token is None:
                            first_token = time.perf_counter()
                        if not in_thinking:
                            print(f"\n{AMARILLO}[razonamiento] ", end="")
                            in_thinking = True
                        print(msg["thinking"], end="", flush=True)
                    if msg.get("content"):
                        if first_token is None:
                            first_token = time.perf_counter()
                        if in_thinking or not content:
                            print(f"{FIN}\n\n{VERDE}LFM3: ", end="")
                            in_thinking = False
                        content.append(msg["content"])
                        print(msg["content"], end="", flush=True)
                    if chunk.get("done"):
                        final = chunk
        except Exception as e:
            print(f"{FIN}\n{ROJO}Error llamando a la API: {e}{FIN}")
            messages.pop()
            continue
        wall = time.perf_counter() - t0
        print(f"{FIN}\n")
        turn += 1
        messages.append({"role": "assistant", "content": "".join(content)})

        # Las duraciones de Ollama vienen en nanosegundos
        ns = 1e9
        p_tok, e_tok = final.get("prompt_eval_count", 0), final.get("eval_count", 0)
        p_s, e_s = final.get("prompt_eval_duration", 0) / ns, final.get("eval_duration", 0) / ns
        prefill = round(p_tok / p_s, 2) if p_s else 0
        decode = round(e_tok / e_s, 2) if e_s else 0
        ttft = (first_token - t0) if first_token else 0
        print(f"{GRIS}  prompt: {p_tok} tok a {prefill} tok/s | respuesta: {e_tok} tok a {decode} tok/s | "
              f"primer token {ttft:.2f} s | carga {final.get('load_duration', 0) / ns:.2f} s | "
              f"total {final.get('total_duration', 0) / ns:.2f} s (reloj {wall:.2f} s){FIN}")
        show_stats(a.url, a.model)
        print()

        m = loaded_model(a.url, a.model)
        new_file = not os.path.exists(csv_path)
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(["fecha", "modelo", "turno", "num_ctx", "think", "prompt_tokens", "prefill_tok_s",
                            "output_tokens", "decode_tok_s", "primer_token_s", "total_s", "modelo_mem_mb",
                            "ram_disponible_mb", "pregunta"])
            w.writerow([dt.datetime.now().isoformat(timespec="seconds"), a.model, turn, a.num_ctx, not a.no_think,
                        p_tok, prefill, e_tok, decode, round(ttft, 2), round(final.get("total_duration", 0) / ns, 3),
                        m["size"] // 2**20 if m else "", mem_available_mb() if sys.platform.startswith("linux") else "",
                        prompt])


if __name__ == "__main__":
    main()
