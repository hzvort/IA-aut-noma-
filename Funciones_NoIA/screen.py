import os
import io
import base64
from PIL import ImageGrab
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID

def acceso_check(user_id):
    if user_id != ADMIN_ID:
        print(f"⚠️ ALERTA: Intento de acceso no autorizado de ID: {user_id}")
        return False
    return True  # Asegúrate de que este sea tu ID correcto

async def cmd_screen(u: Update, c: ContextTypes.DEFAULT_TYPE):

    await u.message.reply_chat_action(action="upload_photo")
    
    try:
        # 1. Tomar la captura
        screenshot = ImageGrab.grab()
        
        # 2. Procesar para MEMORIA (Base64) - Esto es lo nuevo
        buffered = io.BytesIO()
        screenshot.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # --- AQUÍ GUARDAMOS LA FOTO EN LA MEMORIA DEL BOT ---
        c.user_data["buffer_vision"] = img_str 
        
        # 3. Enviar al chat para que tú también la veas
        buffered.seek(0) # Rebobinar el buffer para leerlo de nuevo
        await u.message.reply_photo(
            photo=buffered, 
            caption="👁️ **Captura en Memoria.**\nPregúntame algo sobre esta imagen."
        )
            
    except Exception as e:
        await u.message.reply_text(f"❌ Error al capturar: {str(e)}")