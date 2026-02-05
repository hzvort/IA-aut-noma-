import asyncio
import cv2
import os
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID, PATH_FOTO_WEBCAM

def acceso_check(user_id):
    if user_id != ADMIN_ID:
        print(f"⚠️ ALERTA: Intento de acceso no autorizado de ID: {user_id}")
        return False
    return True

def _tomar_foto_sync():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False, None
    
    # Leemos varios frames para que la cámara ajuste la luz
    for _ in range(5):
        cap.read()
        
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        cv2.imwrite(PATH_FOTO_WEBCAM, frame)
        return True, PATH_FOTO_WEBCAM
    return False, None

async def comando_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return

    msg = await update.message.reply_text("📸 Enfocando...")

    # AQUÍ ESTÁ LA MAGIA: to_thread
    # Ejecuta la función bloqueante en un hilo separado
    exito, ruta = await asyncio.to_thread(_tomar_foto_sync)

    if exito:
        await update.message.reply_photo(
            photo=open(ruta, 'rb'), 
            caption="👀 Aquí tienes."
        )
        os.remove(ruta) # Limpieza
    else:
        await update.message.reply_text("❌ No pude acceder a la cámara.")

    # Borramos el mensaje de "Enfocando..."
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg.message_id)
    except:
        pass