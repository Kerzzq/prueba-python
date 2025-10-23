import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class ContentExtractor:
    def __init__(self, base_folder="descargas", max_depth=1):
        """
        base_folder: carpeta raíz para guardar los textos
        max_depth: profundidad máxima de exploración recursiva
        """
        self.base_folder = base_folder
        self.max_depth = max_depth
        self.visited_urls = set()  # almacenar URLs ya visitadas
        os.makedirs(base_folder, exist_ok=True)

    def fetch_and_save(self, url: str, depth=0, parent_folder=None):
        """
        Descarga una URL, guarda su contenido principal y,
        si depth < max_depth, explora los enlaces del cuerpo principal.
        """
        normalized_url = self._normalize_url(url)

        print(f"\n📄 Procesando (nivel {depth}): {normalized_url}\n")

        # Descargar y seguir redirecciones
        try:
            response = requests.get(normalized_url, allow_redirects=True, timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Error al descargar {normalized_url}: {e}")
            return

        # URL final tras redirecciones
        final_url = self._normalize_url(response.url)

        # Evitar procesar la misma URL varias veces
        if final_url in self.visited_urls:
            print(f"🔁 Ya visitada: {final_url}")
            return
        self.visited_urls.add(final_url)

        soup = BeautifulSoup(response.text, "html.parser")

        # Buscar contenido principal
        main_content = soup.find("main") or soup.find("div", class_="field-item")
        if not main_content:
            print("⚠️ No se encontró contenido principal.")
            return

        # Eliminar partes irrelevantes
        for tag in main_content.find_all(["nav", "header", "footer", "aside", "script", "style"]):
            tag.decompose()

        # Buscar enlaces relevantes dentro del cuerpo principal
        links = []
        base_domain = urlparse(final_url).netloc

        for a_tag in main_content.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href or href.startswith("#"):
                continue  # Ignorar anclas internas

            full_link = urljoin(final_url, href)
            normalized_link = self._normalize_url(full_link)
            link_domain = urlparse(normalized_link).netloc

            # Ignorar dominios distintos
            if link_domain != base_domain:
                continue

            # Ignorar enlaces repetidos o con mismo path
            if normalized_link in self.visited_urls or normalized_link == final_url:
                continue

            links.append(normalized_link)

        # Extraer texto limpio
        important_text = main_content.get_text(separator="\n", strip=True)

        # Determinar carpeta destino (subcarpeta si viene de otro nivel)
        folder = self.base_folder if parent_folder is None else os.path.join(self.base_folder, parent_folder)
        os.makedirs(folder, exist_ok=True)

        # Guardar texto
        filename = self._sanitize_filename(final_url) + ".txt"
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(important_text)

        print(f"✅ Guardado en: {filepath}")

        # Mostrar enlaces encontrados
        if links:
            print("\n🔗 Enlaces detectados (nivel siguiente):")
            for link in links:
                print("   -", link)
        else:
            print("\n(No se encontraron enlaces nuevos para seguir.)")

        # Llamada recursiva si no hemos alcanzado el límite
        if depth < self.max_depth:
            subfolder_name = os.path.splitext(filename)[0]
            for link in links:
                self.fetch_and_save(link, depth=depth + 1, parent_folder=subfolder_name)

    def _normalize_url(self, url: str) -> str:
        """
        Normaliza una URL eliminando fragmentos (#), barras finales y parámetros innecesarios.
        """
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        return normalized

    def _sanitize_filename(self, url: str) -> str:
        """
        Convierte una URL en un nombre de archivo seguro.
        """
        safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_")
        safe_name = safe_name.split("?")[0].split("#")[0]
        return safe_name[:200]  # limitar tamaño por seguridad


# Ejemplo de uso:
if __name__ == "__main__":
    extractor = ContentExtractor(base_folder="descargas", max_depth=1)
    extractor.fetch_and_save(
        "https://tc.canada.ca/en/corporate-services/acts-regulations/list-regulations/canadian-aviation-regulations-sor-96-433/standards/airworthiness-manual-chapter-533-aircraft-engines-canadian-aviation-regulations-cars"
    )
