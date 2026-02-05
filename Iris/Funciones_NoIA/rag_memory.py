import chromadb
import uuid
import os
from chromadb.utils import embedding_functions
from datetime import datetime

class MemoriaInfinita:
    def __init__(self, path_db="iris_brain_db"):
        self.client = chromadb.PersistentClient(path=path_db)
        
        # Usamos un modelo ligero y rápido para crear los vectores localmente
        # 'all-MiniLM-L6-v2' es estándar, rápido y eficiente para CPU
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Creamos (o cargamos) la colección de memorias
        self.collection = self.client.get_or_create_collection(
            name="iris_memoria_chat",
            embedding_function=self.ef
        )
        print(f"🧠 Memoria Infinita (ChromaDB) cargada. Entradas: {self.collection.count()}")

    def borrar_todo(self):
        try:
            self.client.delete_collection(name="iris_memoria_chat")
            # Recreamos la colección vacía inmediatamente
            self.collection = self.client.get_or_create_collection(
                name="iris_memoria_chat",
                embedding_function=self.ef
            )
            return "🧹 Memoria a largo plazo formateada completamente."
        except Exception as e:
            return f"⚠️ Error borrando memoria: {e}"

    def recordar(self, query, n_results=3):

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            # Aplanamos la lista de resultados
            if results and results['documents']:
                return results['documents'][0]
            return []
        except Exception as e:
            print(f"⚠️ Error recuperando memoria: {e}")
            return []

    def memorizar(self, usuario, respuesta_ia):
        try:
            texto_a_guardar = f"Usuario: {usuario}\nIris: {respuesta_ia}"
            
            # CORRECCIÓN: Usar fecha real
            fecha_ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.collection.add(
                documents=[texto_a_guardar],
                metadatas=[{"role": "conversation", "timestamp": fecha_ahora}], # <--- AQUÍ
                ids=[str(uuid.uuid4())]
            )
        except Exception as e:
            print(f"⚠️ Error guardando memoria: {e}")

    def ver_recientes(self, n=5):
        """Devuelve los últimos n recuerdos guardados (crudos)"""
        try:
            # .get() recupera documentos sin necesidad de query vectorial
            # include=['documents', 'metadatas']
            datos = self.collection.get(limit=n)
            
            if not datos or not datos['documents']:
                return ["📭 La memoria está vacía."]
            
            return datos['documents']
        except Exception as e:
            return [f"⚠️ Error leyendo memoria: {e}"]
    
    def contar_recuerdos(self):
        return self.collection.count()