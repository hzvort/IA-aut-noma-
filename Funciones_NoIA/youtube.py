import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Permiso para ver y gestionar tu cuenta de YouTube (necesario para búsquedas completas)
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

class CerebroYoutube:
    def __init__(self, creds_path="credentials.json"):
        self.creds = None
        self.service = None
        self.creds_path = creds_path
        self._autenticar()

    def _autenticar(self):
        """Maneja la autenticación OAuth2 (reutiliza token si existe y es válido para estos scopes)"""
        # Nota: Si ya tienes un token.json de Gmail, es posible que necesites borrarlo 
        # para que te pida permisos de nuevo para YouTube, o manejar tokens separados.
        # Para simplificar, aquí usaremos 'token_youtube.json'.
        
        token_file = "token_youtube.json"

        if os.path.exists(token_file):
            self.creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except:
                    self.creds = None # Forzar re-login si falla el refresh
            
            if not self.creds:
                if not os.path.exists(self.creds_path):
                    print(f"❌ Error: No encontré {self.creds_path} para YouTube")
                    return
                flow = InstalledAppFlow.from_client_secrets_file(self.creds_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Guardar el token específico de YouTube
            with open(token_file, "w") as token:
                token.write(self.creds.to_json())

        try:
            self.service = build("youtube", "v3", credentials=self.creds)
            print("📺 Cerebro YouTube Conectado.")
        except HttpError as err:
            print(f"❌ Error conectando a YouTube: {err}")

    def buscar_video(self, consulta, max_results=3):
        """Busca videos en YouTube y devuelve los enlaces"""
        if not self.service: return "❌ YouTube no conectado."

        try:
            # Llamada a la API de búsqueda
            request = self.service.search().list(
                part="snippet",
                maxResults=max_results,
                q=consulta,
                type="video" # Solo videos, no canales ni playlists
            )
            response = request.execute()

            resultados = []
            if not response.get("items"):
                return f"No encontré videos para: {consulta}"

            for item in response["items"]:
                titulo = item["snippet"]["title"]
                video_id = item["id"]["videoId"]
                canal = item["snippet"]["channelTitle"]
                url = f"https://www.youtube.com/watch?v={video_id}"
                resultados.append(f"🎥 {titulo} ({canal}) - {url}")

            return "\n".join(resultados)

        except Exception as e:
            return f"❌ Error buscando en YouTube: {e}"