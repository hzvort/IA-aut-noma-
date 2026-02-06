tools = [
    {
        "type": "function",
        "function": {
            "name": "ejecutar_comando_pc",
            "description": "Ejecuta comandos reales en la terminal de Windows (CMD/PowerShell).",
            "parameters": {
                "type": "object",
                "properties": {
                    "comando": {
                        "type": "string",
                        "description": "El comando exacto a ejecutar, ej: 'mkdir test' o 'ipconfig'."
                    }
                },
                "required": ["comando"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "leer_archivo",
            "description": "Lee el contenido de un archivo de texto o código local para analizarlo. Úsalo cuando te pidan leer, analizar o revisar un archivo específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ruta": {
                        "type": "string",
                        "description": "Ruta relativa o absoluta del archivo (ej: 'main.py', 'logs/error.log')"
                    }
                },
                "required": ["ruta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_internet",
            "description": "Busca información actual en internet usando DuckDuckGo. Úsalo para noticias, documentación reciente o datos que no sabes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": "La búsqueda específica, optimizada para un motor de búsqueda (ej: 'precio bitcoin hoy', 'documentación python 3.12')."
                    }
                },
                "required": ["consulta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_memoria_notion",
            "description": "Busca en la base de datos de Notion. Úsalo cuando te pregunten por recuerdos, notas guardadas, ideas pasadas, proyectos personales o listas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": "Palabras clave para buscar el título de la nota. Ej: 'contraseña', 'idea pato', 'lista compras'."
                    }
                },
                "required": ["consulta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escribir_en_notion",
            "description": "Guarda una nota en la memoria permanente del usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo": {
                        "type": "string",
                        "description": "Título breve."
                    },
                    "contenido": {
                        "type": "string",
                        "description": "El contenido completo."
                    }
                },
                "required": ["titulo", "contenido"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": "Busca videos en YouTube. Útil para encontrar tutoriales, música o información visual.",
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": "El término de búsqueda (ej: 'tutorial python', 'lofi hip hop', 'noticias hoy')."
                    }
                },
                "required": ["consulta"]
            }
        }
    },
]