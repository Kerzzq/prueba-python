import os
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
        """
        Descarga la página, extrae SOLO el cuerpo principal, lo convierte a Markdown
        y sigue los enlaces internos (máx. 1 nivel). Evita anclas (#) y duplicados.
        """
        # 1) Normalizamos la URL de entrada (sin #, sin barra final)
        request_url = self._normalize_url(url)
        print(f"\n📄 Procesando (nivel {depth}): {request_url}\n")

        # 2) Descargamos y seguimos redirecciones; AÚN NO marcamos visitado
        try:
            resp = requests.get(request_url, allow_redirects=True, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ Error al descargar {request_url}: {e}")
            return

        # 3) URL final tras redirecciones y normalizada
        final_url = self._normalize_url(resp.url)

        # 4) Si ya la procesamos antes, salimos
        if final_url in self.visited_urls:
            print(f"🔁 Ya visitada (final): {final_url}")
            return

        # 5) Parsear HTML y aislar el contenido principal
        soup = BeautifulSoup(resp.text, "html.parser")
        main = soup.find("main") or soup.find("div", class_="field-item")
        if not main:
            print("⚠️ No se encontró contenido principal.")
            return

        # 6) Limpiar navegación/estilos/guiones
        for tag in main.find_all(["nav", "header", "footer", "aside", "script", "style"]):
            tag.decompose()

        # 7) Extraer enlaces internos VÁLIDOS dentro del main (sin #, mismo dominio)
        base_domain = urlparse(final_url).netloc
        links = []
        for a in main.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#"):
                continue  # ignorar anclas internas

            full = urljoin(final_url, href)
            norm = self._normalize_url(full)

            # mismo dominio y no es la misma página
            if urlparse(norm).netloc != base_domain:
                continue
            if norm == final_url:
                continue

            links.append(norm)

        # 8) Convertimos el main a Markdown y guardamos
        markdown_text = md(str(main), heading_style="ATX", strip=["span"])
        markdown_text = "\n".join(line.strip() for line in markdown_text.splitlines() if line.strip())

        folder = self.base_folder if parent_folder is None else os.path.join(self.base_folder, parent_folder)
        os.makedirs(folder, exist_ok=True)

        filename = self._sanitize_filename(final_url) + ".md"
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"---\nsource: {final_url}\n---\n\n")
            f.write(markdown_text)

        print(f"✅ Guardado en: {filepath}")

        # 9) AHORA SÍ: marcamos la URL final como visitada (después de guardar)
        self.visited_urls.add(final_url)

        # 10) Mostrar enlaces candidatos a visitar
        if links:
            print("\n🔗 Enlaces encontrados (nivel siguiente):")
            for link in links:
                print("   -", link)
        else:
            print("\n(No se encontraron enlaces internos nuevos.)")

        # 11) Recursión limitada a 1 nivel adicional
        if depth < self.max_depth:
            subfolder = os.path.splitext(filename)[0]
            for link in links:
                # Cada hijo repetirá el mismo flujo y comprobará visited al comienzo
                self.fetch_and_save(link, depth=depth + 1, parent_folder=subfolder)

    # ---------------- Utilidades ----------------
    def _normalize_url(self, url: str) -> str:
        """Elimina fragmentos (#) y barras finales; conserva esquema/host/path."""
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}{p.path}".rstrip("/")

    def _sanitize_filename(self, url: str) -> str:
        """Convierte una URL en nombre de archivo seguro."""
        safe = url.replace("https://", "").replace("http://", "")
        safe = safe.split("?")[0].split("#")[0].strip("/").replace("/", "_")
        return safe[:200]


# Ejemplo de uso:
extractor = MarkdownExtractor(base_folder="descargas_md", max_depth=1)
extractor.fetch_and_save(
    "https://tc.canada.ca/en/corporate-services/acts-regulations/list-regulations/canadian-aviation-regulations-sor-96-433/standards/airworthiness-manual-chapter-533-aircraft-engines-canadian-aviation-regulations-cars")
