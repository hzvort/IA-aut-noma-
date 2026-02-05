import os
from notion_client import Client

class CerebroNotion:
    def __init__(self, token, id_pagina_principal):
        self.client = Client(auth=token)
        self.root_id = id_pagina_principal # Guardamos el ID fijo

    def buscar_informacion(self, consulta):
        """Busca en todo Notion (Lectura)"""
        try:
            # Buscamos en todo el espacio de trabajo
            response = self.client.search(
                query=consulta,
                page_size=3 # Limitado para ahorrar tokens
            )
            resultados = []
            
            for page in response.get("results", []):
                titulo = "Nota"
                # Intentar sacar título
                if "properties" in page:
                    for key, val in page["properties"].items():
                        if val["type"] == "title" and val["title"]:
                            titulo = val["title"][0]["text"]["content"]
                            break
                
                # Leemos un resumen del contenido (primeros 500 caracteres)
                contenido = self._leer_bloques(page["id"])[:500]
                resultados.append(f"📄 {titulo}: {contenido}...")
            
            return "\n".join(resultados) if resultados else "📭 No encontré nada sobre eso."
        except Exception as e:
            return f"❌ Error leyendo: {e}"

    def escribir_nota(self, titulo, contenido):
        """
        Escribe SIEMPRE en la página principal configurada.
        Crea una sub-página nueva para cada nota.
        """
        if not self.root_id:
            return "❌ Error: No tengo configurado el ID de la página principal."

        try:
            self.client.pages.create(
                parent={"page_id": self.root_id}, # Destino FIJO
                properties={
                    "title": [
                        {"text": {"content": titulo}}
                    ]
                },
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"text": {"content": contenido}}]
                        }
                    }
                ]
            )
            return f"✅ Nota guardada: '{titulo}'"
        except Exception as e:
            return f"❌ Error Notion: {e}"

    def _leer_bloques(self, block_id):
        texto = ""
        try:
            children = self.client.blocks.children.list(block_id=block_id, page_size=10)
            for block in children.get("results", []):
                tipo = block["type"]
                if "rich_text" in block.get(tipo, {}):
                    for t in block[tipo]["rich_text"]:
                        texto += t["text"]["content"] + "\n"
        except: pass
        return texto