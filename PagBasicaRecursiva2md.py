import os
import re
import hashlib
import argparse
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urljoin, urlparse

class MarkdownExtractor:
    def __init__(self, base_folder="descargas_md", max_depth=1):
        self.base_folder = base_folder
        self.max_depth = max_depth
        self.visited_urls = set()
        os.makedirs(base_folder, exist_ok=True)

    def fetch_and_save(self, url: str, depth=0, parent_folder=None):
        """Descarga la página, convierte todo el <main> a Markdown y sigue enlaces internos (máx. 1 nivel)."""
        normalized_url = self._normalize_url(url)
        print(f"\n📄 Procesando (nivel {depth}): {normalized_url}\n")

        try:
            resp = requests.get(
                normalized_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126 Safari/537.36"},
                allow_redirects=True,
                timeout=60
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ Error al descargar {normalized_url}: {e}")
            return

        final_url = self._normalize_url(resp.url)
        if final_url in self.visited_urls:
            print(f"🔁 Ya visitada: {final_url}")
            return

        soup = BeautifulSoup(resp.text, "html.parser")

        # Usar todo el <main> (fallback: field-item)
        main_content = soup.find("main") or soup.find("div", class_="field-item")
        if not main_content:
            print("⚠️ No se encontró contenido principal.")
            return

        # Buscar enlaces ANTES de limpiar para no reordenar el DOM
        base_domain = urlparse(final_url).netloc
        links = []
        for a_tag in main_content.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href or href.startswith("#"):
                continue
            full_link = urljoin(final_url, href)
            norm_link = self._normalize_url(full_link)
            if urlparse(norm_link).netloc != base_domain:
                continue
            if norm_link == final_url:
                continue
            links.append(norm_link)

        # Limpiar etiquetas irrelevantes (no tocar div ni table para no deformar tablas)
        for tag in main_content.find_all(["nav", "header", "footer", "aside", "script", "style"]):
            tag.decompose()

        # Convertir a Markdown
        markdown_text = md(str(main_content), heading_style="ATX", strip=["span"])
        markdown_text = "\n".join(line.strip() for line in markdown_text.splitlines() if line.strip())

        # Carpeta base (usa hash corto de la URL final para evitar rutas largas)
        folder = self.base_folder if parent_folder is None else os.path.join(self.base_folder, parent_folder)
        hash_prefix = hashlib.md5(final_url.encode()).hexdigest()[:8]
        folder = os.path.join(folder, hash_prefix)
        os.makedirs(folder, exist_ok=True)

        # Archivo .md = últimos 50 chars del path, saneados
        filename = self._filename_from_url(final_url)
        filepath = os.path.join(folder, filename)

        # Fallback si la ruta total es muy larga
        if len(filepath) > 240:
            short_hash = hashlib.md5(filepath.encode()).hexdigest()[:10]
            filepath = os.path.join(folder, f"{short_hash}.md")

        # Guardar
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"---\nsource: {final_url}\n---\n\n")
            f.write(markdown_text)

        print(f"✅ Guardado en: {filepath}")

        # Marcar visitada DESPUÉS de guardar
        self.visited_urls.add(final_url)

        # Recursión (máx. profundidad)
        if depth < self.max_depth:
            for link in links:
                self.fetch_and_save(link, depth=depth + 1, parent_folder=hash_prefix)

    # ---------- utilidades ----------
    def _normalize_url(self, url: str) -> str:
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}{p.path}".rstrip("/")

    def _filename_from_url(self, url: str) -> str:
        """Nombre de archivo .md a partir de los últimos 50 chars del path (saneados)."""
        path = urlparse(url).path.strip("/") or "index"
        safe = re.sub(r'[<>:"/\\|?*]', "_", path)
        short = safe[-50:] if len(safe) > 50 else safe
        return f"{short}.md"


# ============= MAIN =============
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraer <main> de una URL a Markdown y seguir enlaces 1 nivel.")
    parser.add_argument(
        "url",
        nargs="?",
        default="https://tc.canada.ca/en/corporate-services/acts-regulations/list-regulations/canadian-aviation-regulations-sor-96-433/standards/airworthiness-manual-chapter-533-aircraft-engines-canadian-aviation-regulations-cars",
        help="URL inicial a procesar"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Profundidad máxima de recursión (por defecto 1)"
    )
    parser.add_argument(
        "--out",
        dest="base_folder",
        default="descargas_md",
        help="Carpeta base de salida (por defecto descargas_md)"
    )
    args = parser.parse_args()

    extractor = MarkdownExtractor(base_folder=args.base_folder, max_depth=args.depth)
    extractor.fetch_and_save(args.url)
