import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

def extract_to_markdown(url, output_file="salida.md"):
    # Obtener la página
    r = requests.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Buscar bloque principal
    main = soup.find("main") or soup.find("div", class_="field-item")
    if not main:
        raise ValueError("No se encontró contenido principal en la página")

    # Eliminar partes no deseadas
    for tag in main.find_all(["nav", "header", "footer", "aside", "script", "style"]):
        tag.decompose()

    # Convertir HTML limpio a Markdown
    markdown_text = md(str(main), heading_style="ATX", strip=["span"])

    # Guardar como archivo .md
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    print(f"✅ Archivo Markdown guardado en: {output_file}")

# Ejemplo de uso
extract_to_markdown(
    "https://tc.canada.ca/en/corporate-services/acts-regulations/list-regulations/canadian-aviation-regulations-sor-96-433/standards/airworthiness-manual-chapter-533-aircraft-engines-canadian-aviation-regulations-cars",
    "chapter_533.md"
)
