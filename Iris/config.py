import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("❌ ERROR: No se encontró TELEGRAM_TOKEN en el archivo .env")

ADMIN_ID = 8318233748  

PATH_FOTO_WEBCAM = "captura_webcam.jpg"
PATH_HISTORIAL = "historial.json"