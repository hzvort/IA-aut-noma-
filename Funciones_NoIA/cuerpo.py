import tkinter as tk
from PIL import Image, ImageTk, ImageSequence
import threading
import random
import os
import queue

# --- CONFIGURACIÓN DE COLORES ---
BG_COLOR = "#4e4e4e"      # Gris oscuro
TEXT_COLOR = "#dbdbdb"    # Verde Hacker
ACCENT_COLOR = "#FFBD66"  # Gris borde
FONT_MAIN = ("Consolas", 10)
FONT_BUTTON = ("Arial", 10, "bold")

class VirtualPet:
    def __init__(self, gif_path="image_0.png", scale=0.3, callback_func=None):
        self.gif_path = gif_path
        self.scale = scale
        self.callback_func = callback_func
        self.root = None
        self.is_running = False
        self.thread = None
        self.label = None
        self.frames = []
        
        self.msg_queue = queue.Queue()
        self.screen_width = 0
        self.screen_height = 0
        self.current_action = "idle"
        self.target_x = 0
        self.target_y = 0
        self.bubble = None
        self.input_win = None

    def _run_gui(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.config(bg='black')
        self.root.wm_attributes('-transparentcolor', 'black')
        self.root.wm_attributes("-topmost", True)
        
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        # Posición inicial
        start_x = self.screen_width - 250
        start_y = self.screen_height - 250
        self.root.geometry(f"+{start_x}+{start_y}")

        # --- CARGAR IMAGEN (Soporte GIF y PNG) ---
        try:
            pil_image = Image.open(self.gif_path)
            self.frames = []
            is_animated = getattr(pil_image, "is_animated", False)
            
            if is_animated:
                for frame in ImageSequence.Iterator(pil_image):
                    if self.scale != 1.0:
                        w, h = frame.size
                        frame = frame.resize((int(w*self.scale), int(h*self.scale)), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(frame)
                    self.frames.append(photo)
            else:
                if self.scale != 1.0:
                    w, h = pil_image.size
                    pil_image = pil_image.resize((int(w*self.scale), int(h*self.scale)), Image.LANCZOS)
                self.frames.append(ImageTk.PhotoImage(pil_image))
        except Exception as e:
            print(f"Error imagen: {e}")
            self.root.destroy()
            return

        self.label = tk.Label(self.root, bg='black')
        self.label.pack()

        if len(self.frames) > 1:
            self.animate(0)
        else:
            self.label.configure(image=self.frames[0])
            
        self.decide_behavior()
        self.check_messages()
        
        # --- NUEVOS EVENTOS ---
        self.label.bind("<Button-1>", self.start_move)
        self.label.bind("<B1-Motion>", self.do_move)
        
        # Click Derecho AHORA abre un MENÚ, no el chat directo
        self.label.bind("<Button-3>", self.show_context_menu)

        self.root.mainloop()

    # --- MENÚ CONTEXTUAL (CLICK DERECHO) ---
    def show_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0, bg=BG_COLOR, fg=TEXT_COLOR)
        menu.add_command(label="💬 Hablar con Iris", command=lambda: self.open_input_dialog(event))
        menu.add_separator()
        menu.add_command(label="🔇 Cerrar Mensajes", command=self.close_all_popups)
        menu.add_command(label="💨 Ocultar Mascota", command=self.hide)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def close_all_popups(self):
        if self.bubble: 
            try: self.bubble.destroy() 
            except: pass
        if self.input_win:
            try: self.input_win.destroy()
            except: pass

    # --- INPUT (CHAT) ---
    def open_input_dialog(self, event):
        if hasattr(self, 'input_win') and self.input_win and self.input_win.winfo_exists():
            self.input_win.lift()
            self.entry.focus_set()
            return

        self.current_action = "input"
        
        self.input_win = tk.Toplevel(self.root)
        self.input_win.overrideredirect(True)
        self.input_win.attributes("-topmost", True)
        self.input_win.config(bg=TEXT_COLOR) # Borde verde

        main_frame = tk.Frame(self.input_win, bg=BG_COLOR)
        main_frame.pack(padx=1, pady=1, fill=tk.BOTH, expand=True)

        # Botón Cerrar (X) ROJO para que se vea bien
        close_btn = tk.Button(main_frame, text=" X ", bg="#ff4444", fg="white",
                              font=("Arial", 9, "bold"), bd=0, 
                              command=self.input_win.destroy, cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=2, pady=2)

        self.entry = tk.Entry(main_frame, width=25, bg=BG_COLOR, fg=TEXT_COLOR, 
                              insertbackground=TEXT_COLOR, font=FONT_MAIN, bd=0)
        self.entry.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        self.entry.focus_set()

        self.entry.bind("<Return>", self.send_message)
        self.entry.bind("<Escape>", lambda e: self.input_win.destroy())
        
        # SI HACES CLICK AFUERA, SE CIERRA (Auto-Close)
        self.input_win.bind("<FocusOut>", lambda e: self.input_win.destroy())

        # Posición
        self.input_win.geometry(f"+{event.x_root}+{event.y_root - 50}")

    def send_message(self, event=None):
        text = self.entry.get()
        if text and self.callback_func:
            self.callback_func(text)
        self.input_win.destroy()
        self.current_action = "idle"
        self.decide_behavior()

    # --- BURBUJAS DE TEXTO (IA) ---
    def speak(self, text):
        self.msg_queue.put(text)

    def check_messages(self):
        if not self.root: return
        try:
            msg = self.msg_queue.get_nowait()
            self.show_bubble(msg)
        except queue.Empty:
            pass
        self.root.after(500, self.check_messages)

    def show_bubble(self, text):
        if self.bubble:
            try: self.bubble.destroy()
            except: pass

        self.bubble = tk.Toplevel(self.root)
        self.bubble.overrideredirect(True)
        self.bubble.attributes("-topmost", True)
        self.bubble.config(bg=TEXT_COLOR) 

        main_frame = tk.Frame(self.bubble, bg=BG_COLOR)
        main_frame.pack(padx=1, pady=1)

        # Barra superior pequeña para cerrar
        top = tk.Frame(main_frame, bg=BG_COLOR)
        top.pack(fill=tk.X)
        tk.Button(top, text="×", bg=BG_COLOR, fg="#666", bd=0, font=("Arial", 12),
                  command=self.bubble.destroy, cursor="hand2").pack(side=tk.RIGHT)

        lbl = tk.Label(main_frame, text=text, bg=BG_COLOR, fg=TEXT_COLOR, 
                       font=FONT_MAIN, wraplength=200, justify="left")
        lbl.pack(padx=8, pady=(0, 8))

        x = self.root.winfo_x()
        y = self.root.winfo_y() - self.bubble.winfo_reqheight() - 10
        if y < 0: y = self.root.winfo_y() + 100
        self.bubble.geometry(f"+{x}+{y}")

    # --- MOVIMIENTOS ---
    def animate(self, frame_idx):
        if not self.root: return
        try:
            frame = self.frames[frame_idx]
            self.label.configure(image=frame)
            frame_idx = (frame_idx + 1) % len(self.frames)
            self.root.after(100, self.animate, frame_idx)
        except: pass

    def decide_behavior(self):
        if not self.root or self.current_action == "input": return
        decision = random.choice(["walk", "idle", "idle", "idle"])
        if decision == "walk":
            self.target_x = random.randint(50, self.screen_width - 200)
            self.target_y = random.randint(50, self.screen_height - 200)
            self.current_action = "walking"
            self.walk_step()
        else:
            self.current_action = "idle"
            self.root.after(random.randint(3000, 7000), self.decide_behavior)

    def walk_step(self):
        if not self.root or self.current_action != "walking": return
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        dx = self.target_x - current_x
        dy = self.target_y - current_y
        if abs(dx) < 5 and abs(dy) < 5:
            self.decide_behavior()
            return
        move_x = 3 if dx > 0 else -3
        move_y = 3 if dy > 0 else -3
        if abs(dx) < 5: move_x = 0
        if abs(dy) < 5: move_y = 0
        self.root.geometry(f"+{current_x + move_x}+{current_y + move_y}")
        self.root.after(30, self.walk_step)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y
        self.current_action = "dragging"

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        self.root.geometry(f"+{self.root.winfo_x() + deltax}+{self.root.winfo_y() + deltay}")
        if self.current_action == "dragging":
            self.root.after(1000, self.decide_behavior)
            self.current_action = "idle"

    # EXTERNO
    def show(self):
        if self.is_running: return "Ya estoy aquí."
        if not os.path.exists(self.gif_path): return f"Falta imagen: {self.gif_path}"
        self.is_running = True
        self.thread = threading.Thread(target=self._run_gui)
        self.thread.daemon = True
        self.thread.start()
        return "Activada."

    def hide(self):
        if self.root and self.is_running:
            try:
                self.root.quit()
                self.root.update()
            except: pass
            self.is_running = False
            self.root = None
            return "Adiós."
        return "Off."