import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class ContentExtractor:
    def __init__(self, base_folder="descargas"):
        """
        base_folder: carpeta donde se guardarán los textos extraídos
        """
        self.base_folder = base_folder
        os.makedirs(base_folder, exist_ok=True)

    def fetch_and_save(self, url: str):
        """
        Descarga la página, extrae el contenido principal,
        imprime los enlaces relevantes y guarda el texto limpio.
        """
        print(f"\n📄 Procesando: {url}\n")

        # Descargar la página
        response = requests.get(url)
        response.raise_for_status()

        # Parsear HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Buscar el contenido principal
        main_content = soup.find("main")
        if not main_content:
            main_content = soup.find("div", class_="field-item")

        if not main_content:
            print("⚠️ No se encontró contenido principal.")
            return

        # Eliminar partes irrelevantes
        for tag in main_content.find_all(["nav", "header", "footer", "aside", "script", "style"]):
            tag.decompose()

        # Extraer texto limpio
        important_text = main_content.get_text(separator="\n", strip=True)

        # Guardar el texto en archivo
        filename = self._sanitize_filename(url) + ".txt"
        filepath = os.path.join(self.base_folder, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(important_text)

        print(f"✅ Contenido guardado en: {filepath}")

        # Buscar enlaces dentro del cuerpo principal
        links = []
        for a_tag in main_content.find_all("a", href=True):
            href = a_tag["href"]
            full_link = urljoin(url, href)
            links.append(full_link)

        # Mostrar enlaces encontrados
        if links:
            print("\n🔗 Enlaces encontrados dentro del cuerpo principal:")
            for link in links:
                print("   -", link)
        else:
            print("\n(No se encontraron enlaces internos relevantes.)")

    def _sanitize_filename(self, url: str) -> str:
        """
        Convierte una URL en un nombre de archivo seguro.
        """
        safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_")
        safe_name = safe_name.split("?")[0]
        return safe_name[:100]  # limitar tamaño por seguridad


# Ejemplo de uso:
if __name__ == "__main__":
    extractor = ContentExtractor()
    extractor.fetch_and_save("https://tc.canada.ca/en/corporate-services/acts-regulations/list-regulations/canadian-aviation-regulations-sor-96-433/standards/airworthiness-manual-chapter-533-aircraft-engines-canadian-aviation-regulations-cars")
