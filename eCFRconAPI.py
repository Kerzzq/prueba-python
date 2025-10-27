import argparse
import re
import requests
from pathlib import Path
from urllib.parse import urlencode
from tqdm import tqdm
import keyboard
import threading

stop_after = False  # se pone True cuando el usuario pulsa 'q'

def build_ecfr_api_url(title: int, chapter=None, subchapter=None, part=None) -> str:
    base = f"https://www.ecfr.gov/api/versioner/v1/versions/title-{title}.json"
    params = {k: v for k, v in {"chapter": chapter, "subchapter": subchapter, "part": part}.items() if v}
    return base + ("?" + urlencode(params) if params else "")

def fetch_ecfr_json(api_url: str):
    print(f"API: {api_url}")
    resp = requests.get(api_url, headers={"accept": "application/json"}, timeout=60)
    resp.raise_for_status()
    return resp.json()

def fetch_full_text(date: str, title: str, part: str, section: str) -> str:
    url = f"https://www.ecfr.gov/api/versioner/v1/full/{date}/title-{title}.xml"
    params = {"part": part}
    if section:
        params["section"] = f"{part}.{section}"
    resp = requests.get(url, params=params, headers={"Accept": "application/xml"}, timeout=60)
    resp.raise_for_status()
    return resp.text.strip()

def append_xml(identifier: str, xml_text: str):
    xml_text = re.sub(r'<\?xml[^>]*\?>', '', xml_text).strip()
    with open(SALIDA_XML, "a", encoding="utf-8") as f:
        f.write(f'<section id="{identifier}">\n')
        f.write(xml_text)
        f.write('\n</section>\n')

def main():
    global stop_after
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", type=int, required=True)
    parser.add_argument("--chapter", default=None)
    parser.add_argument("--subchapter", default=None)
    parser.add_argument("--part", default=None)
    parser.add_argument("--max", type=int, default=None, help="Parar tras N secciones")
    args = parser.parse_args()

    url = build_ecfr_api_url(args.title, args.chapter, args.subchapter, args.part)
    data = fetch_ecfr_json(url)
    entries = data.get("content_versions", [])
    if not entries:
        print("No hay entradas")
        return

    print(f"Secciones totales: {len(entries)}")
    if args.max:
        entries = entries[:args.max]
        print(f"Limitado a las primeras {len(entries)} secciones")
    print("Pulsa 'q' para terminar tras la descarga actual\n")

    global SALIDA_XML
    SALIDA_XML = "salida_completa.xml"
    if Path(SALIDA_XML).exists():
        Path(SALIDA_XML).unlink()
    Path(SALIDA_XML).write_text('<?xml version="1.0" encoding="UTF-8"?>\n<document>\n', encoding="utf-8")

    # detector de tecla 'q' (sin bloquear)
    def check_quit():
        global stop_after
        keyboard.wait('q')
        stop_after = True
    threading.Thread(target=check_quit, daemon=True).start()

    try:
        for idx, entry in enumerate(tqdm(entries, desc="Descargando")):
            if stop_after:
                tqdm.write("[-] Interrumpido por usuario (tras esta petición)")
                break
            identifier = entry.get("identifier")
            date = entry.get("date")
            title = entry.get("title")
            part, section = (identifier.split(".", 1) if "." in identifier else (identifier, None))
            try:
                xml_text = fetch_full_text(date, title, part, section)
                append_xml(identifier, xml_text)
                tqdm.write(f"[+] Añadido {identifier}")
            except Exception as e:
                tqdm.write(f"[*-*] Error {identifier}: {e}")
    finally:
        with open(SALIDA_XML, "a", encoding="utf-8") as f:
            f.write("</document>\n")
        print(f"\nXML guardado en: {SALIDA_XML}")

if __name__ == "__main__":
    main()