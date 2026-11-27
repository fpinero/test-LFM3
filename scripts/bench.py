#!/usr/bin/env python3
"""Banco de pruebas reproducible: compara modelos (por ejemplo, cuantizaciones Q8 y Q4)
con las mismas preguntas, con y sin razonamiento, y genera una tabla en Markdown.

Solo usa la biblioteca estándar. Cada modelo se descarga de memoria antes de pasar
al siguiente (keep_alive=0), para que en una máquina con poca RAM no convivan dos.

Uso:
    python3 scripts/bench.py
    python3 scripts/bench.py --models lfm3:1.7b-q8_0 lfm3:1.7b --repeticiones 2
"""
import argparse
import datetime as dt
import json
import os
import statistics
import sys
import time
import urllib.request

from sysinfo import mem_available_mb, rss_mb

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
SYSTEM = "Eres un asistente útil. Responde siempre en español, de forma breve y precisa."
PRUEBAS = [
    ("presentacion", "Hola, soy Fernando, arquitecto cloud. Preséntate en dos frases."),
    ("json", 'Extrae en JSON con las claves emisor (empresa), cliente (persona), fecha (AAAA-MM-DD) e importe '
             '(número con punto decimal): "Factura de Talleres López S.L. emitida el 3 de marzo de 2026 por '
             '1.250,40 euros a nombre de Ana Ruiz".'),
    ("kubernetes", "Dame exactamente 3 ventajas de Kubernetes, cada una en menos de 10 palabras, en lista numerada."),
]
JSON_ESPERADO = {"emisor": "Talleres López S.L.", "cliente": "Ana Ruiz", "fecha": "2026-03-03", "importe": 1250.40}


def post(url, path, body, timeout=900):
    req = urllib.request.Request(url + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=timeout) as r:
        return json.load(r)


def rss_runner_mb():
    """RSS del proceso que ejecuta el modelo (llama-server o runner de Ollama).
    En Mac la memoria que usa la GPU (Metal) puede no reflejarse entera en la RSS."""
    return rss_mb(["llama-server", "ollama runner"])


def comprobar_json(texto):
    """Devuelve 'ok' si el JSON extraído coincide con el esperado, o qué falla."""
    t = texto.strip()
    if "```" in t:
        t = t.split("```")[1]
        t = t[4:] if t.startswith("json") else t
    try:
        d = json.loads(t[t.index("{"):t.rindex("}") + 1])
    except Exception:
        return "JSON no válido"
    fallos = [k for k, v in JSON_ESPERADO.items() if d.get(k) != v]
    return "ok" if not fallos else "difiere: " + ", ".join(fallos)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=["lfm3:1.7b-q8_0", "lfm3:1.7b"])
    ap.add_argument("--repeticiones", type=int, default=1)
    ap.add_argument("--num-ctx", type=int, default=4096)
    ap.add_argument("--url", default="http://localhost:11434")
    a = ap.parse_args()

    filas = []
    for model in a.models:
        print(f"\n=== {model} ===", flush=True)
        t0 = time.perf_counter()
        # Carga del modelo (petición vacía) para medir el tiempo de carga aparte
        post(a.url, "/api/generate", {"model": model, "prompt": "", "keep_alive": "10m",
                                      "options": {"num_ctx": a.num_ctx}})
        carga = time.perf_counter() - t0
        ps = None
        try:
            with OPENER.open(a.url + "/api/ps", timeout=10) as r:
                ps = next((m for m in json.load(r)["models"] if m["name"] == model), None)
        except Exception:
            pass
        mem_modelo = ps["size"] // 2**20 if ps else None
        print(f"cargado en {carga:.1f} s | tamaño en memoria {mem_modelo} MB | RSS runner {rss_runner_mb()} MB | "
              f"RAM disponible {mem_available_mb()} MB", flush=True)

        for think in (False, True):
            for nombre, prompt in PRUEBAS:
                for rep in range(a.repeticiones):
                    body = {"model": model, "stream": False, "think": think,
                            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                            "options": {"temperature": 0.1, "top_k": 50, "repeat_penalty": 1.1, "num_ctx": a.num_ctx}}
                    r = post(a.url, "/api/chat", body)
                    ns = 1e9
                    pe, ed = r.get("prompt_eval_duration", 0) / ns, r.get("eval_duration", 0) / ns
                    fila = {
                        "modelo": model, "think": think, "prueba": nombre,
                        "prefill": round(r.get("prompt_eval_count", 0) / pe, 1) if pe else 0,
                        "tokens": r.get("eval_count", 0),
                        "decode": round(r.get("eval_count", 0) / ed, 2) if ed else 0,
                        "total": round(r.get("total_duration", 0) / ns, 1),
                        "rss": rss_runner_mb(), "disp": mem_available_mb(),
                        "calidad": comprobar_json(r["message"]["content"]) if nombre == "json" else "",
                    }
                    filas.append(fila)
                    print(f"  think={think!s:5} {nombre:12} {fila['tokens']:4} tok a {fila['decode']:5} tok/s | "
                          f"total {fila['total']:6} s {fila['calidad']}", flush=True)

        # Descargar el modelo antes de pasar al siguiente
        post(a.url, "/api/generate", {"model": model, "prompt": "", "keep_alive": 0})
        time.sleep(2)

    # Resumen en Markdown
    print("\n### Resultados del banco de pruebas\n")
    print("| Modelo | Razonamiento | Generación media (tok/s) | Tokens medios | Tiempo medio por respuesta (s) | "
          "RSS máx. runner (MB) | RAM disponible mín. (MB) | JSON |")
    print("|---|---|---|---|---|---|---|---|")
    for model in a.models:
        for think in (False, True):
            g = [f for f in filas if f["modelo"] == model and f["think"] == think]
            if not g:
                continue
            json_ok = [f["calidad"] for f in g if f["prueba"] == "json"]
            rss = [f["rss"] for f in g if f["rss"]]
            disp = [f["disp"] for f in g if f["disp"]]
            print(f"| `{model}` | {'sí' if think else 'no'} | {statistics.mean(f['decode'] for f in g):.2f} | "
                  f"{statistics.mean(f['tokens'] for f in g):.0f} | {statistics.mean(f['total'] for f in g):.1f} | "
                  f"{max(rss) if rss else '-'} | {min(disp) if disp else '-'} | {', '.join(json_ok)} |")
    print(f"\nFecha: {dt.datetime.now():%Y-%m-%d %H:%M} | num_ctx {a.num_ctx} | repeticiones {a.repeticiones}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
