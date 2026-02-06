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

    def borrar_todo_menos_origen(self, conservar=3):
        try:
            # 1. Obtenemos IDs y metadatos
            datos = self.collection.get()
            ids = datos['ids']
            metadatas = datos['metadatas']

            if not ids or len(ids) <= conservar:
                return f"ℹ️ Memoria intacta. Solo hay {len(ids)} recuerdos (mínimo {conservar})."

            lista_recuerdos = []
            
            # 2. Asignamos fechas falsas a los antiguos
            for i, doc_id in enumerate(ids):
                # Verificamos si existe el diccionario de metadata
                meta = metadatas[i] if metadatas[i] else {}
                
                # TRUCO: Si no hay timestamp, ponemos año 0000. 
                # Esto asegura que los viejos sin fecha queden PRIMEROS en la lista.
                timestamp = meta.get('timestamp', '0000-00-00 00:00:00') 
                
                lista_recuerdos.append((doc_id, timestamp))

            # 3. Ordenamos: "0000..." irá antes que "2026..."
            lista_ordenada = sorted(lista_recuerdos, key=lambda x: x[1])

            # 4. Debug (Opcional: imprime esto para ver qué está pasando)
            # print(f"Ordenados: {[x[1] for x in lista_ordenada]}")

            # 5. Cortamos: Saltamos los primeros 'conservar' (los viejos/0000) y borramos el resto
            a_borrar = lista_ordenada[conservar:]
            ids_a_eliminar = [item[0] for item in a_borrar]

            if ids_a_eliminar:
                self.collection.delete(ids=ids_a_eliminar)
                return f"🧹 Se borraron {len(ids_a_eliminar)} recuerdos recientes. Se conservaron los {conservar} primeros (incluyendo los antiguos sin fecha)."
            
            return "✅ Nada que borrar."

        except Exception as e:
            return f"⚠️ Error crítico al borrar: {e}"

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