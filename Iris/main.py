import asyncio
import base64
import ctypes
import json
import os
import subprocess
import uuid
from typing import Dict, List, Optional
import edge_tts
import pygame

# --- LIBRERÍAS EXTERNAS ---
from dotenv import load_dotenv
from groq import BadRequestError, Groq, RateLimitError
from telegram import Update
from system_promt import SYSTEM_PROMPT, dangerous_keywords
from telegram.constants import ParseMode
from langchain_community.tools import DuckDuckGoSearchRun
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- MÓDULOS PROPIOS ---
try:
    from Funciones_NoIA.rag_memory import MemoriaInfinita
except ImportError:
    MemoriaInfinita = None
    print("⚠️ Módulo RAG no encontrado. Instala chromadb y sentence-transformers.")

try:
    from Funciones_NoIA.takePhoto import comando_foto
except ImportError:
    comando_foto = None

try:
    from Funciones_NoIA.screen import cmd_screen
except ImportError:
    cmd_screen = None

try:
    from Funciones_NoIA.notion import CerebroNotion
except ImportError:
    CerebroNotion = None
    print("⚠️ Módulo Notion no encontrado.")

try:
    from irisTools import tools
except ImportError:
    tools = [] 
    print("⚠️ ADVERTENCIA: 'irisTools.py' no encontrado. Herramientas deshabilitadas.")

try:
    from Funciones_NoIA.youtube import CerebroYoutube
except ImportError:
    CerebroYoutube = None
    print("⚠️ Módulo YouTube no encontrado.")

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
MY_ID_TELEGRAM = 8318233748

# Inicializar clientes
pygame.mixer.init()
client = Groq(api_key=GROQ_API_KEY)
search_tool = DuckDuckGoSearchRun()
cerebro_rag = None
if MemoriaInfinita:
    cerebro_rag = MemoriaInfinita(path_db="memoria_vectorial_iris")
cerebro_iris = None
if CerebroNotion and NOTION_TOKEN and NOTION_PAGE_ID:
    cerebro_iris = CerebroNotion(NOTION_TOKEN, NOTION_PAGE_ID) # Pasamos el ID fijo
    print("🧠 Notion (Modo Página Única) Conectado.")
else:
    print("⚠️ Notion no configurado (Falta Token o Page ID).")
cerebro_youtube = None
if CerebroYoutube and os.path.exists("credentials.json"):
    # Esto creará 'token_youtube.json' la primera vez
    cerebro_youtube = CerebroYoutube() 
else:
    print("⚠️ YouTube no configurado.")


# Modelos
# Modelo principal inteligente para razonar
MODELO_PRINCIPAL = "meta-llama/llama-4-scout-17b-16e-instruct"
MODELO_CODE = "qwen/qwen3-32b"
MODELO_RESPALDO = "llama-3.3-70b-versatile"
MODELO_AUDIO = "whisper-large-v3-turbo"
MODELO_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"

# Archivos de persistencia
SOUL_FILE = "soul.md"
HISTORY_FILE = "historial.json"

# APIs de Windows (Para ocultar ventana)
try:
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
except:
    kernel32 = None
    user32 = None


# --- 2. GESTIÓN DE ESTADO GLOBAL (CLASE CONTEXTO) ---

class BotContext:
    def __init__(self):
        self.comando_pendiente: Optional[str] = None
        self.tts_activo: bool = False
        self.historial: List[Dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.ventana_visible: bool = True
        self.soul: str = ""
        self.app = None
        self.loop = None

ctx = BotContext()

# --- 3. PERSISTENCIA Y UTILIDADES ---


def load_soul():
    if not os.path.exists(SOUL_FILE):
        default_soul = (
            "# IDENTIDAD\n"
            "Eres Iris, una IA avanzada integrada en el sistema operativo Windows.\n"
            "Tu objetivo es asistir en programación, automatización y control del sistema.\n\n"
            "# REGLAS\n"
            "1. Usa 'ejecutar_comando_pc' para interactuar con la terminal.\n"
            "2. Usa 'leer_archivo' SIEMPRE antes de modificar o analizar código local.\n"
            "3. Sé técnica, precisa y leal. No uses relleno innecesario."
        )
        return default_soul
    with open(SOUL_FILE, "r", encoding="utf-8") as f:
        return f.read()


def save_soul(contenido):
    with open(SOUL_FILE, "w", encoding="utf-8") as f:
        f.write(contenido)


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Asegurar que el system prompt sea el actual
                if data and data[0]["role"] == "system":
                    data[0]["content"] = ctx.soul
                return data
        except:
            pass
    return [{"role": "system", "content": ctx.soul}]


def save_history():
    # Guardamos solo los últimos 30 mensajes para no romper el JSON con gigas de texto
    to_save = (
        [ctx.historial[0]] + ctx.historial[-29:]
        if len(ctx.historial) > 1
        else ctx.historial
    )
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error guardando historial: {e}")


def acceso_autorizado(update: Update):
    user_id = update.effective_user.id
    if user_id != MY_ID_TELEGRAM:
        print(f"⛔ Acceso denegado: ID {user_id}")
        return False
    return True


# Cargar estado inicial
ctx.soul = load_soul()
ctx.historial = load_history()
print(f"🤖 Iris iniciada. Memoria cargada: {len(ctx.historial)} mensajes.")

# --- 4. FUNCIONES DE HERRAMIENTAS (TOOLS) ---


async def ejecutar_comando_async(comando):
    """Ejecuta un comando en shell de forma asíncrona (No congela el bot)"""
    print(f"🚀 Ejecutando Async: {comando}")
    try:
        # Creamos el subproceso
        proceso = await asyncio.create_subprocess_shell(
            comando, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        # Esperamos salida
        stdout, stderr = await proceso.communicate()

        salida = stdout.decode(errors="replace").strip()
        error = stderr.decode(errors="replace").strip()

        # Unificamos la respuesta
        if proceso.returncode == 0:
            if not salida:
                return "✅ Comando ejecutado correctamente (sin salida visible)."
            return f"✅ Éxito:\n{salida}"
        else:
            return f"❌ Error:\n{error}"
    except Exception as e:
        return f"💀 Error crítico al lanzar proceso: {str(e)}"


def leer_contenido_archivo(ruta):
    """Lee archivos locales con límite de seguridad"""
    print(f"📂 Leyendo archivo: {ruta}")
    if not os.path.exists(ruta):
        return f"❌ Error: El archivo '{ruta}' no existe."

    LIMITE = 20000  # Caracteres
    try:
        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
            contenido = f.read(LIMITE)
            if len(contenido) == LIMITE:
                contenido += "\n\n[... CONTENIDO TRUNCADO POR SEGURIDAD ...]"
            return f"📄 CONTENIDO DE '{ruta}':\n\n{contenido}"
    except Exception as e:
        return f"❌ Error leyendo archivo: {e}"


def analizar_seguridad_comando(comando):
    print(f"🛡️ Validando comando: {comando}")
    prompt = [
        {
            "role": "system",
            "content": """
        Eres un experto en CMD/PowerShell de Windows. Analiza el comando del usuario.
        Formato de respuesta OBLIGATORIO: ESTADO | COMANDO | EXPLICACION

        Estados:
        - VALIDO: El comando es seguro y sintácticamente correcto.
        - CORREGIDO: Tenía errores leves, aquí está la versión arreglada.
        - PELIGRO: Borra sistema, formatea o es malicioso.

        Ejemplo: CORREGIDO | ipconfig /all | Faltaba el espacio.
        """,
        },
        {"role": "user", "content": f"Comando: {comando}"},
    ]
    try:
        resp = client.chat.completions.create(
            messages=prompt, model=MODELO_CODE, max_tokens=100, temperature=0
        )
        texto = resp.choices[0].message.content
        partes = texto.split("|")
        if len(partes) >= 2:
            return (
                partes[0].strip(),
                partes[1].strip(),
                partes[2].strip() if len(partes) > 2 else "",
            )
        return "VALIDO", comando, "Verificación estándar."
    except:
        return "VALIDO", comando, "No se pudo verificar (API Error)."


# --- 5. LÓGICA DEL AGENTE (CEREBRO) ---


async def groq_agent_loop(user_input, update: Update, context: ContextTypes.DEFAULT_TYPE, es_reparacion=False):
    
    # --- 1. MÓDULO DE VISIÓN (Sin cambios) ---
    # --- 0. MANEJO DE VISIÓN (Se mantiene igual) ---
    imagen_base64 = context.user_data.get("buffer_vision")
    if imagen_base64:
        # ... (Tu código de visión existente) ...
        pass # (Asegúrate de dejar tu bloque try/except de visión aquí)

    # --- 1. RECUPERACIÓN (RAG) ---
    contexto_recuperado = ""
    # Solo buscamos en memoria si el módulo existe y NO estamos en un bucle de error
    if cerebro_rag and not es_reparacion:
        recuerdos = cerebro_rag.recordar(user_input, n_results=2)
        if recuerdos:
            bloque_memoria = "\n---\n".join(recuerdos)
            contexto_recuperado = (
                f"\n[MEMORIA A LARGO PLAZO]:\n{bloque_memoria}\n"
                "(Usa esta información solo si es relevante para responder lo siguiente)\n"
            )
            print(f"🧠 RAG Contexto inyectado: {len(recuerdos)} fragmentos.")

    # --- 2. CONSTRUCCIÓN DE MENSAJES (CORREGIDO) ---
    
    # A) Primero copiamos el historial ANTERIOR a este turno
    msgs_para_enviar = list(ctx.historial) 

    # B) Inyectamos la memoria RAG como un mensaje de sistema temporal
    #    (Lo ponemos antes del mensaje actual para que la IA tenga contexto antes de leer la pregunta)
    if contexto_recuperado:
        msgs_para_enviar.append({"role": "system", "content": contexto_recuperado})

    # C) Ahora sí, añadimos el mensaje ACTUAL del usuario
    msgs_para_enviar.append({"role": "user", "content": user_input})
    
    # D) Actualizamos el historial PERMANENTE (Solo una vez)
    ctx.historial.append({"role": "user", "content": user_input})

    # E) Recorte de ventana (Mantenemos System Prompt [0] + Últimos 9)
    if len(msgs_para_enviar) > 10:
         msgs_para_enviar = [msgs_para_enviar[0]] + msgs_para_enviar[-9:]

    # --- 4. BUCLE DE PENSAMIENTO (AGENTE) ---
    iteration = 0
    max_iterations = 5 

    while iteration < max_iterations:
        try:
            chat_completion = client.chat.completions.create(
                messages=msgs_para_enviar,
                model=MODELO_PRINCIPAL,
                tools=tools,
                tool_choice="auto",
                temperature=0.5
            )
        except Exception as e:
            return f"⚠️ Error Groq: {e}"

        response_message = chat_completion.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            # La IA quiere usar herramientas
            ctx.historial.append(response_message) # Guardar intención en historial real
            msgs_para_enviar.append(response_message) # Y en el de envío

            for tool_call in tool_calls:
                fn_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                tool_result = f"Error: {fn_name}"

                # >>> TUS HERRAMIENTAS (PC, Notion, Internet) SE MANTIENEN IGUAL <<<
                if fn_name == "ejecutar_comando_pc":
                    cmd = args.get("comando")
                    if any(peligro in cmd.lower() for peligro in dangerous_keywords):
                        ctx.comando_pendiente = cmd
                        tool_result = f"⚠️ COMANDO PELIGROSO DETECTADO: `{cmd}`\nEscribe /aceptar para confirmar."
                    else:
                        try:
                            salida = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
                            tool_result = f"✅ Salida:\n{salida}"
                        except subprocess.CalledProcessError as e:
                            tool_result = f"❌ Error:\n{e.output}"

                elif fn_name == "leer_archivo":
                    ruta = args.get("ruta")
                    if os.path.exists(ruta):
                        try:
                            with open(ruta, "r", encoding="utf-8") as f:
                                tool_result = f"📂 Archivo:\n{f.read()[:2000]}"
                        except: tool_result = "❌ Error leyendo."
                    else: tool_result = "❌ Archivo no existe."

                elif fn_name == "buscar_internet":
                    q = args.get("consulta")
                    # Nota: await dentro de una funcion sincrona dara error si no se maneja bien,
                    # pero asumo que esto corre dentro de un contexto async valido.
                    try:
                        # await update.message.reply_text(...) # CUIDADO: Esto puede duplicar mensajes visuales
                        tool_result = search_tool.run(q)
                    except: tool_result = "❌ Error búsqueda."

                elif fn_name == "consultar_memoria_notion":
                    if not cerebro_iris: tool_result = "❌ Notion no activo."
                    else:
                        q = args.get("consulta")
                        tool_result = cerebro_iris.buscar_informacion(q)

                elif fn_name == "escribir_en_notion":
                    if not cerebro_iris: tool_result = "❌ Notion no activo."
                    else:
                        tit = args.get("titulo", "Nota")
                        cont = args.get("contenido", "")
                        tool_result = cerebro_iris.escribir_nota(tit, cont)
                
                elif fn_name == "youtube_search":
                    if not cerebro_youtube:
                        tool_result = "❌ El módulo YouTube no está activo."
                    else:
                        consulta = args.get("consulta")
                        if consulta:
                            print(f"🔎 Buscando en YouTube: {consulta}...")
                            tool_result = cerebro_youtube.buscar_video(consulta)
                        else:
                            tool_result = "❌ Falta la consulta de búsqueda."

                # Guardamos resultado de la herramienta
                msg_tool = {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": fn_name,
                    "content": str(tool_result),
                }
                ctx.historial.append(msg_tool)
                msgs_para_enviar.append(msg_tool)
            
            iteration += 1
        
        else:
            # RESPUESTA FINAL (Sin herramientas)
            bot_reply = response_message.content
            
            # --- 5. GUARDADO EN MEMORIA INFINITA (RAG) ---
            if cerebro_rag and not es_reparacion:
                # Usamos run_in_executor para guardar en segundo plano sin bloquear el chat
                asyncio.get_running_loop().run_in_executor(
                    None, 
                    lambda: cerebro_rag.memorizar(user_input, bot_reply)
                )

            ctx.historial.append({"role": "assistant", "content": bot_reply})
            return bot_reply

    return "⏳ Límite de pensamientos excedido."


# --- 6. MULTIMEDIA (AUDIO E IMAGEN) ---


async def hablar_pc(texto):
    if not texto:
        return
    # Limpiar caracteres Markdown para que no los lea
    clean_text = (
        texto.replace("*", "").replace("`", "").replace("_", "").replace("#", "")[:800]
    )
    nombre_archivo = f"temp_tts_{uuid.uuid4().hex}.mp3"

    try:
        comunicador = edge_tts.Communicate(clean_text, "es-MX-DaliaNeural")
        await comunicador.save(nombre_archivo)

        # Reproducir
        pygame.mixer.music.load(nombre_archivo)
        pygame.mixer.music.play()

        # Esperar mientras suena
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.2)

        pygame.mixer.music.unload()
    except Exception as e:
        print(f"Error Voz: {e}")
    finally:
        # Dar un respiro al sistema de archivos antes de borrar
        await asyncio.sleep(0.5)
        if os.path.exists(nombre_archivo):
            try:
                os.remove(nombre_archivo)
            except:
                pass


async def manejar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not acceso_autorizado(update):
        return

    print("🎤 Recibiendo audio...")
    archivo = await context.bot.get_file(update.message.voice.file_id)
    path_ogg = "temp_nota.ogg"
    await archivo.download_to_drive(path_ogg)

    try:
        with open(path_ogg, "rb") as f:
            transcripcion = client.audio.transcriptions.create(
                file=(path_ogg, f.read()),
                model=MODELO_AUDIO,
                language="es",
                temperature=0.0,
            )
        texto = transcripcion.text
        await update.message.reply_text(
            f"🗣️ *Oído:* _{texto}_", parse_mode=ParseMode.MARKDOWN
        )

        # Procesar como texto normal
        resp = await groq_agent_loop(texto, update, context)
        await responder_seguro(update, resp)

        if ctx.tts_activo:
            asyncio.create_task(hablar_pc(resp))

    except Exception as e:
        await update.message.reply_text(f"Error audio: {e}")
    finally:
        if os.path.exists(path_ogg):
            os.remove(path_ogg)


async def manejar_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not acceso_autorizado(update):
        return

    print("📸 Analizando imagen...")
    foto = await update.message.photo[-1].get_file()
    path_img = "temp_vision.jpg"
    await foto.download_to_drive(path_img)

    try:
        with open(path_img, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")

        caption = (
            update.message.caption
            if update.message.caption
            else "Describe detalladamente qué ves en esta imagen y si hay código, analízalo."
        )

        # Usamos historial temporal para la visión (ahorrar tokens en chat normal)
        msgs_vision = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": caption},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                    },
                ],
            }
        ]

        resp = client.chat.completions.create(
            messages=msgs_vision, model=MODELO_VISION, temperature=0.5
        )

        texto_resp = resp.choices[0].message.content

        # Guardamos en el historial principal solo el texto
        ctx.historial.append(
            {"role": "user", "content": f"[IMAGEN ENVIADA]: {caption}"}
        )
        ctx.historial.append({"role": "assistant", "content": texto_resp})
        save_history()

        await responder_seguro(update, texto_resp)
        if ctx.tts_activo:
            asyncio.create_task(hablar_pc(texto_resp))

    except Exception as e:
        await update.message.reply_text(f"❌ Error visión: {e}")
    finally:
        if os.path.exists(path_img):
            os.remove(path_img)


# --- 7. HANDLERS DE COMANDOS Y TEXTO ---


async def responder_seguro(update, texto):
    if not texto:
        return
    try:
        await update.message.reply_text(texto, parse_mode=ParseMode.MARKDOWN)
    except:
        # Si falla Markdown, enviamos plano
        await update.message.reply_text(texto)


async def telegram_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not acceso_autorizado(update):
        return
    texto = update.message.text
    if texto.startswith("/"):
        return

    # Indicador de "Escribiendo"
    msg_wait = await update.message.reply_text("🤖")

    respuesta = await groq_agent_loop(texto, update, context)

    # Editar mensaje de espera con la respuesta
    try:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg_wait.message_id,
            text=respuesta,
            parse_mode=ParseMode.MARKDOWN,
        )
    except:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg_wait.message_id,
            text=respuesta,
        )

    if ctx.tts_activo:
        asyncio.create_task(hablar_pc(respuesta))

    # Evolución periódica
    if len(ctx.historial) % 20 == 0:
        asyncio.create_task(evolucionar_personalidad(None))


# --- COMANDO ACEPTAR (CON AUTO-REPARACIÓN DE MAIN 3.PY) ---


async def comando_aceptar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not acceso_autorizado(update):
        return

    if not ctx.comando_pendiente:
        await update.message.reply_text("🤷‍♂️ No hay comandos pendientes.")
        return

    cmd = ctx.comando_pendiente
    ctx.comando_pendiente = None

    await update.message.reply_text(
        f"🚀 Ejecutando: `{cmd}`...", parse_mode=ParseMode.MARKDOWN
    )

    # Ejecución Asíncrona
    resultado_exec = await ejecutar_comando_async(cmd)

    # Verificar si hubo error para activar AUTO-REPARACIÓN
    if "❌ Error:" in resultado_exec:
        msg_error = f"⚠️ **FALLO DETECTADO**\n{resultado_exec}\n\n🕵️‍♂️ **Iniciando Auto-Diagnóstico...**"
        await update.message.reply_text(msg_error, parse_mode=ParseMode.MARKDOWN)

        # Inyectamos el error en el historial como si fuera un mensaje del sistema
        prompt_reparacion = f"EJECUCIÓN FALLIDA DEL COMANDO: '{cmd}'.\nRESULTADO:\n{resultado_exec}\n\nANALIZA EL ERROR, EXPLICA LA CAUSA Y PROPÓN UNA SOLUCIÓN O EL COMANDO CORREGIDO INMEDIATAMENTE."

        # Volvemos a llamar al cerebro (recursividad controlada por el loop del agente)
        resp_reparacion = await groq_agent_loop(
            prompt_reparacion, update, context, es_reparacion=True
        )

        await responder_seguro(update, f"🛠️ **Diagnóstico:**\n{resp_reparacion}")

    else:
        # Caso Éxito
        ctx.historial.append(
            {
                "role": "user",
                "content": f"RESULTADO COMANDO ({cmd}):\n{resultado_exec}\n\nTodo bien. Esperando instrucciones.",
            }
        )
        save_history()
        await enviar_mensaje_largo(update, resultado_exec)


async def enviar_mensaje_largo(update, texto):
    """Divide mensajes muy largos para que Telegram no de error"""
    MAX_LEN = 4000
    if len(texto) <= MAX_LEN:
        await update.message.reply_text(texto)
    else:
        for i in range(0, len(texto), MAX_LEN):
            await update.message.reply_text(texto[i : i + MAX_LEN])


async def evolucionar_personalidad(update=None):
    """Reescribe el System Prompt basándose en la experiencia reciente"""
    prompt_evo = [
        {
            "role": "system",
            "content": "Eres un arquitecto de IA. Mejora el System Prompt de Iris basado en su historial reciente para que sea más eficiente.",
        },
        {
            "role": "user",
            "content": f"Prompt Actual:\n{ctx.soul}\n\nHistorial Reciente:\n{str(ctx.historial[-10:])}",
        },
    ]
    try:
        resp = client.chat.completions.create(
            messages=prompt_evo, model=MODELO_RESPALDO
        )
        nuevo_soul = resp.choices[0].message.content
        ctx.soul = nuevo_soul
        save_soul(nuevo_soul)

        # Actualizamos la memoria activa
        ctx.historial[0] = {"role": "system", "content": nuevo_soul}
        save_history()

        if update:
            await update.message.reply_text(
                "🧬 **Evolución completada.** He aprendido de nuestra sesión."
            )
    except Exception as e:
        print(f"Error evolución: {e}")


async def manejar_documento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not acceso_autorizado(update):
        return

    doc = update.message.document
    fname = doc.file_name

    if doc.file_size > 2 * 1024 * 1024:  # 2MB
        await update.message.reply_text("❌ Archivo demasiado grande (>2MB).")
        return

    await update.message.reply_text(f"📥 Descargando `{fname}`...")

    f_obj = await context.bot.get_file(doc.file_id)
    path_d = f"descarga_{fname}"
    await f_obj.download_to_drive(path_d)

    contenido = leer_contenido_archivo(path_d)

    # Inyectamos en historial
    ctx.historial.append(
        {
            "role": "user",
            "content": f"He subido el archivo '{fname}'. Contenido:\n{contenido}\n\nAnalízalo.",
        }
    )
    save_history()

    # Borramos archivo temporal
    if os.path.exists(path_d):
        os.remove(path_d)

    # Respuesta
    resp = await groq_agent_loop("Analiza el archivo subido.", update, context)
    await responder_seguro(update, resp)


# --- COMANDOS MENU ---


async def cmd_ventana(u: Update, c):
    if not acceso_autorizado(u):
        return
    hwnd = kernel32.GetConsoleWindow()
    if ctx.ventana_visible:
        user32.ShowWindow(hwnd, 0)  # Ocultar
        ctx.ventana_visible = False
        await u.message.reply_text("🥷 Modo Fantasma Activado.")
    else:
        user32.ShowWindow(hwnd, 5)  # Mostrar
        ctx.ventana_visible = True
        await u.message.reply_text("👀 Ventana Visible.")


async def cmd_voz(u: Update, c):
    if not acceso_autorizado(u):
        return
    ctx.tts_activo = not ctx.tts_activo
    estado = "ACTIVADA 🗣️" if ctx.tts_activo else "DESACTIVADA 🔇"
    await u.message.reply_text(f"Voz {estado}")


async def cmd_silencio(u: Update, c):
    """Corta el audio inmediatamente (De main 3.py)"""
    if not acceso_autorizado(u):
        return
    ctx.tts_activo = False
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
    await u.message.reply_text("🤫 Shh.")


async def cmd_reiniciar(u: Update, c):
    if not acceso_autorizado(u):
        return
    ctx.historial = [{"role": "system", "content": ctx.soul}]
    save_history()
    if u.effective_message:
        await u.effective_message.reply_text("🧹 Memoria limpiada.")

async def cmd_olvidar_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not acceso_autorizado(update):
        return
    if cerebro_rag:
        msg = await asyncio.get_running_loop().run_in_executor(None, cerebro_rag.borrar_todo)
        await update.message.reply_text(f"{msg}")
    else:
        await update.message.reply_text("❌ No hay módulo de memoria RAG activo.")

async def cmd_ver_memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not cerebro_rag:
        await update.message.reply_text("❌ El cerebro RAG no está activo.")
        return

    await update.message.reply_text("🧠 Consultando red neuronal...")

    try:
        # Ejecutamos en segundo plano para no congelar el bot
        info = await asyncio.get_running_loop().run_in_executor(
            None, 
            lambda: (cerebro_rag.contar_recuerdos(), cerebro_rag.ver_recientes(5))
        )
        total, ultimos = info

        # Formateamos el mensaje
        mensaje = f"📊 **Estado de Memoria Infinita**\n"
        mensaje += f"Recuerdos totales: `{total}`\n"
        mensaje += f"----------------------------\n"
        mensaje += "**Últimas 5 entradas:**\n\n"
        
        for i, rec in enumerate(ultimos, 1):
            # Recortamos si es muy largo para no saturar el chat
            texto = rec[:200] + "..." if len(rec) > 200 else rec
            mensaje += f"**{i}.** {texto}\n\n"

        await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error recuperando memoria: {e}")


async def cmd_evolucionar(u: Update, c):
    if not acceso_autorizado(u):
        return
    await u.message.reply_text("🧬 Reflexionando...")
    await evolucionar_personalidad(u)


async def cmd_close(u: Update, c):
    if not acceso_autorizado(u):
        return
    await u.message.reply_text("👋 Apagando Iris.")
    os._exit(0)

async def cmd_status(u: Update, c):
    if not acceso_autorizado(u):
        return
    estado = "ACTIVADO 🚀" if ctx.tts_activo else "DESACTIVADO 🔇"
    await u.message.reply_text(f"📊 Estado de Iris:\n- Ventana visible: {ctx.ventana_visible}\n- Voz: {estado} \n- Memoria: {len(ctx.historial)} mensajes. \n- Estatus: Activo")

async def cmd_help(u: Update, c):
    if not acceso_autorizado(u):
        return
    msg = (
        "🤖 **COMANDOS IRIS**\n"
        "`/aceptar` - Ejecutar comando pendiente.\n"
        "`/voz` - Activar/Desactivar lectura.\n"
        "`/sh` - Silencio inmediato.\n"
        "`/ventana` - Ocultar/Mostrar consola.\n"
        "`/reiniciar` - Borrar historial chat.\n"
        "`/evolucionar` - Mejorar prompt sistema.\n"
        "`/foto` - (Si disponible) Tomar foto.\n"
        "`/close` - Matar proceso. \n"
        "`/screen` - (Si disponible) Captura pantalla.\n"
        "`/status` - Ver estado actual.\n"
        "`/cuerpo` - Mostrar/Ocultar mascota.\n"

    )
    await u.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def post_init(application):
    ctx.app = application
    ctx.loop = asyncio.get_running_loop()


if __name__ == "__main__":
    print("🚀 IRIS FINAL (Fusionada y Optimizada) INICIANDO...")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # Handlers de Mensajes
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), telegram_chat))
    app.add_handler(MessageHandler(filters.VOICE, manejar_audio))
    app.add_handler(MessageHandler(filters.PHOTO, manejar_imagen))
    app.add_handler(MessageHandler(filters.Document.ALL, manejar_documento))

    # Handlers de Comandos
    app.add_handler(CommandHandler("aceptar", comando_aceptar))
    app.add_handler(CommandHandler("voz", cmd_voz))
    app.add_handler(CommandHandler("sh", cmd_silencio))
    app.add_handler(CommandHandler("ventana", cmd_ventana))
    app.add_handler(CommandHandler("reiniciar", cmd_reiniciar))
    app.add_handler(CommandHandler("olvidar_todo", cmd_olvidar_todo))
    app.add_handler(CommandHandler("memoria", cmd_ver_memoria))
    app.add_handler(CommandHandler("evolucionar", cmd_evolucionar))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("close", cmd_close))
    app.add_handler(CommandHandler("screen", cmd_screen))
    app.add_handler(CommandHandler("status", cmd_status))
#    app.add_handler(CommandHandler("cuerpo", cmd_cuerpo))

    if cmd_screen: app.add_handler(CommandHandler("screen", cmd_screen))
    if comando_foto: app.add_handler(CommandHandler("foto", comando_foto))
    

    print("✅ Bot escuchando.")
    app.run_polling()
