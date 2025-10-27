from bs4 import BeautifulSoup
import re
from pathlib import Path
from markdownify import markdownify as md
import xml.etree.ElementTree as ET

ENTRADA = "salida_completa.xml"
SALIDA  = "salida_completa.md"

def indentar_html_listas(html: str) -> str:
    """
    Convierte (a) / (1) / (i) en listas anidadas <ul><li>...</li></ul>
    Devuelve HTML listo para markdownify.
    """
    soup = BeautifulSoup(html, "html.parser")

    # regex: (a), (1), (i), (A), (I)
    regex = re.compile(r'^\(([a-z0-9A-Z]+)\)\s*(.*)')

    # pila de <ul> activos por nivel (1=letras, 2=números, 3=romanos)
    stack = []

    for p in soup.find_all("p"):
        txt = p.get_text(strip=True)
        m = regex.match(txt)
        if not m:
            # cerramos todas las listas abiertas
            while stack:
                stack.pop()
            continue

        label, resto = m.groups()
        nivel = len(label)          # 1 carácter → nivel 1
        li_txt = f"({label}) {resto}"

        # cerramos listas más profundas que el actual
        while len(stack) > nivel:
            stack.pop()

        # si necesitamos un nivel nuevo, lo creamos
        while len(stack) < nivel:
            ul = soup.new_tag("ul")
            if stack:
                stack[-1].append(ul)
            else:
                p.insert_before(ul)
            stack.append(ul)

        # creamos <li> y lo añadimos al <ul> activo
        li = soup.new_tag("li")
        li.string = li_txt
        stack[-1].append(li)

        # eliminamos el <p> original
        p.decompose()

    return str(soup)

def main():
    xml = Path(ENTRADA).read_text(encoding="utf-8")

    # 1) parsea y extrae cada <section>
    root = ET.fromstring(xml)
    md_parts = ["# eCFR completo\n"]

    for sec in root.findall("section"):
        ident = sec.get("id", "id?")
        # 2) todo el contenido de la sección → string HTML
        html = ET.tostring(sec, encoding="unicode")
        html = indentar_html_listas(html)
        # 3) HTML → MD
        md_text = md(html, heading_style="atx", strip=["a"])
        md_parts.append(f"\n## Sección {ident}\n")
        md_parts.append(md_text)

    Path(SALIDA).write_text("\n".join(md_parts), encoding="utf-8")
    print(f"✅ Markdown guardado en {SALIDA}")

if __name__ == "__main__":
    main()