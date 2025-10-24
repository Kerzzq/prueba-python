import os
import re
import hashlib
import argparse
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

class MarkdownExtractor:
    def __init__(self, base_folder="descargas_md", max_depth=1):
        self.base_folder = base_folder
        self.max_depth = max_depth
        self.visited_urls = set()
        os.makedirs(base_folder, exist_ok=True)

    def fetch_and_save(self, url: str, depth=0, parent_folder=None, use_render=False):
        """Descarga la página, convierte el bloque principal a Markdown y sigue enlaces internos (máx. 1 nivel).
        Si use_render=True, renderiza JS con Playwright.
        """
        normalized_url = self._normalize_url(url)
        print(f"\n📄 Procesando (nivel {depth}): {normalized_url}\n")

        html = None
        if use_render:
            # 🔹 Renderizado con JS habilitado (Playwright)
            print("🧠 Renderizando con JavaScript (Playwright)...")
            try:
                html = self._get_rendered_html(normalized_url)
                # --- DEBUG: guardar HTML renderizado para inspección ---
                debug_path = os.path.join(self.base_folder, "debug_rendered.html")
                with open(debug_path, "w", encoding="utf-8") as dbg:
                    dbg.write(html)
                print(f"🧩 Archivo debug guardado en: {debug_path}")

            except Exception as e:
                print(f"❌ Error al renderizar {normalized_url}: {e}")
                return
        else:
            # 🔹 Descarga normal con requests
            try:
                resp = requests.get(
                    normalized_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126 Safari/537.36"
                    },
                    allow_redirects=True,
                    timeout=60
                )
                resp.raise_for_status()
                html = resp.text
            except Exception as e:
                print(f"❌ Error al descargar {normalized_url}: {e}")
                return

        soup = BeautifulSoup(html, "html.parser")

        # --- Buscar bloque principal ---
        main_content = (
            soup.find("main")
            or soup.find("div", class_="field-item")
            or soup.find("div", class_="content-block")
            or soup.find("div", id="content")         # 💡 eCFR y otras webs SPA
            or soup.find("div", id="main-content")
            or soup.find("section", id=re.compile(r"^part-", re.I))  # ej. <section id="part-21">
)


        if not main_content:
            print("⚠️ No se encontró contenido principal (<main>, .field-item o .content-block).")
            return

        # --- Limpiar etiquetas irrelevantes ---
        for tag in main_content.find_all(["nav", "header", "footer", "aside", "script", "style"]):
            tag.decompose()

        # --- Convertir HTML a Markdown ---
        markdown_text = md(str(main_content), heading_style="ATX", strip=["span"])

        # --- Guardar resultado ---
        folder = self.base_folder if parent_folder is None else os.path.join(self.base_folder, parent_folder)
        hash_prefix = hashlib.md5(normalized_url.encode()).hexdigest()[:8]
        folder = os.path.join(folder, hash_prefix)
        os.makedirs(folder, exist_ok=True)

        filename = self._filename_from_url(normalized_url)
        filepath = os.path.join(folder, filename)
        if len(filepath) > 240:
            short_hash = hashlib.md5(filepath.encode()).hexdigest()[:10]
            filepath = os.path.join(folder, f"{short_hash}.md")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"---\nsource: {normalized_url}\nrendered: {use_render}\n---\n\n")
            f.write(markdown_text)

        print(f"✅ Guardado en: {filepath}")

        self.visited_urls.add(normalized_url)

        # --- Recursión (máx. profundidad) ---
        if depth < self.max_depth:
            base_domain = urlparse(normalized_url).netloc
            links = []
            for a_tag in main_content.find_all("a", href=True):
                href = a_tag["href"].strip()
                if not href or href.startswith("#"):
                    continue
                full_link = urljoin(normalized_url, href)
                norm_link = self._normalize_url(full_link)
                if urlparse(norm_link).netloc != base_domain or norm_link in self.visited_urls:
                    continue
                links.append(norm_link)
            for link in links:
                self.fetch_and_save(link, depth=depth + 1, parent_folder=hash_prefix, use_render=use_render)

    # ---------- utilidades ----------

    def _get_rendered_html(self, url: str) -> str:
        """Obtiene HTML renderizado con Playwright (sin interfaz gráfica)."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            html = page.content()
            browser.close()
        return html

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
    parser.add_argument(
        "--render",
        action="store_true",
        help="Renderizar la página con JavaScript (usa Playwright)"
    )
    args = parser.parse_args()

    extractor = MarkdownExtractor(base_folder=args.base_folder, max_depth=args.depth)
    extractor.fetch_and_save(args.url, use_render=args.render)
