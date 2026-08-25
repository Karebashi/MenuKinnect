"""
=============================================================================
             LIENZO MÁGICO KINECT XBOX 360 / AIR CANVAS PRO
=============================================================================
Aplicación interactiva de dibujo en el aire para Kinect Xbox 360 y Webcams.
- Dibuja con el dedo índice (☝️).
- Selector de color en el aire: Amarillo, Azul y Verde.
- Botones en el aire: INICIAR, DETENER y LIMPIAR.
- Inicia detenido por defecto.
- Controles gestuales: Puño cerrado (✊) DETIENE el dibujo, Mano abierta (🖐️) INICIA.
=============================================================================
"""

import cv2
import numpy as np
import mediapipe as mp
import time
import os
import threading
import sys

# Importar configuraciones y driver nativo de Kinect
import config
import kinect_driver

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

try:
    from pygrabber.dshow_graph import FilterGraph
    HAS_PYGRABBER = True
except ImportError:
    HAS_PYGRABBER = False


def list_camera_devices():
    """Enumera todos los nombres de dispositivos de captura de video conectados en Windows."""
    if HAS_PYGRABBER:
        try:
            graph = FilterGraph()
            return graph.get_input_devices()
        except Exception:
            pass
    return []


def play_feedback_sound(sound_type="click"):
    """Emite un sonido de confirmación en un hilo separado para no trabar el video."""
    if not HAS_SOUND:
        return
    def _beep():
        try:
            if sound_type == "click":
                winsound.Beep(1200, 70)
            elif sound_type == "clear":
                winsound.Beep(800, 100)
                winsound.Beep(600, 100)
            elif sound_type == "pause":
                winsound.Beep(700, 100)
            elif sound_type == "resume":
                winsound.Beep(1100, 80)
                winsound.Beep(1400, 100)
        except Exception:
            pass
    threading.Thread(target=_beep, daemon=True).start()


class AirButton:
    """Representa un botón interactivo flotante en el aire con animación dwell."""
    def __init__(self, btn_id, text, rect, bg_color=(45, 45, 45), text_color=(255, 255, 255), border_color=(100, 100, 100)):
        self.btn_id = btn_id
        self.text = text
        self.rect = rect  # (x1, y1, x2, y2)
        self.bg_color = bg_color
        self.text_color = text_color
        self.border_color = border_color
        self.hover_start_time = None
        self.dwell_progress = 0.0
        self.pulse_effect = 0

    def contains(self, x, y):
        x1, y1, x2, y2 = self.rect
        return x1 <= x <= x2 and y1 <= y <= y2

    def update(self, is_hovering, current_time, dwell_time):
        """Actualiza el progreso de activación por permanencia (Dwell time)."""
        triggered = False
        if is_hovering:
            if self.hover_start_time is None:
                self.hover_start_time = current_time
            elapsed = current_time - self.hover_start_time
            self.dwell_progress = min(1.0, elapsed / dwell_time)
            if self.dwell_progress >= 1.0:
                triggered = True
                self.hover_start_time = current_time  # Reiniciar para evitar disparos repetidos
                self.pulse_effect = 10
        else:
            self.hover_start_time = None
            self.dwell_progress = 0.0

        if self.pulse_effect > 0:
            self.pulse_effect -= 1

        return triggered

    def draw(self, img, is_selected=False):
        x1, y1, x2, y2 = self.rect
        w = x2 - x1
        h = y2 - y1

        # Color base o destacado si está seleccionado
        fill_color = self.bg_color
        stroke_color = self.border_color
        if is_selected:
            stroke_color = (0, 255, 255)

        if self.pulse_effect > 0:
            fill_color = (min(255, fill_color[0] + 50), min(255, fill_color[1] + 50), min(255, fill_color[2] + 50))

        # Dibujar fondo del botón con efecto translúcido
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), fill_color, -1)
        cv2.addWeighted(overlay, 0.78, img, 0.22, 0, img)

        # Borde exterior
        cv2.rectangle(img, (x1, y1), (x2, y2), stroke_color, 2 if not is_selected else 4, cv2.LINE_AA)

        # Barra de progreso Dwell
        if self.dwell_progress > 0:
            bar_w = int(w * self.dwell_progress)
            cv2.rectangle(img, (x1, y2 - 6), (x1 + bar_w, y2), (0, 255, 255), -1)

        # Texto centrado
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 0.62
        font_thickness = 2
        text_size = cv2.getTextSize(self.text, font, font_scale, font_thickness)[0]
        text_x = x1 + (w - text_size[0]) // 2
        text_y = y1 + (h + text_size[1]) // 2

        # Sombra de texto
        cv2.putText(img, self.text, (text_x + 1, text_y + 1), font, font_scale, (0, 0, 0), font_thickness + 1, cv2.LINE_AA)
        cv2.putText(img, self.text, (text_x, text_y), font, font_scale, self.text_color, font_thickness, cv2.LINE_AA)


class AirCanvasApp:
    def __init__(self, camera_index=None):
        self.width = config.WINDOW_WIDTH
        self.height = config.WINDOW_HEIGHT
        self.camera_index = camera_index
        self.camera_name = "Detectando..."
        self.flip_camera = config.FLIP_CAMERA  # Control de inversión de cámara (False = Normal, True = Espejo)

        # Inicialización de captura de video (Prioridad a Kinect Xbox 360)
        self.cap = self._init_camera(self.camera_index)

        # Inicialización de MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.65,
            min_tracking_confidence=0.65
        )
        self.mp_draw = mp.solutions.drawing_utils

        # Capa de dibujo (Lienzo persistente)
        self.canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Variables de estado del pincel
        self.current_color_key = config.DEFAULT_COLOR
        self.current_color_bgr = config.COLORS[self.current_color_key]
        self.brush_size = config.BRUSH_THICKNESS
        
        # Inicia DETENIDO por defecto
        self.drawing_enabled = False

        # Puntos de seguimiento con suavizado
        self.prev_x, self.prev_y = 0, 0
        self.smooth_x, self.smooth_y = 0, 0
        self.has_prev_point = False

        # Notificación inicial
        self.notification_text = "Pincel DETENIDO [Toca INICIAR o abre la mano]"
        self.notification_time = time.time() + 4.0

        # Crear los 6 botones superiores (Amarillo, Azul, Verde, Iniciar, Detener, Limpiar)
        self.buttons = self._create_buttons()

    def _init_camera(self, target):
        """Inicializa primero el sensor Kinect Xbox 360 nativo y si no está disponible recurre a WebCam."""
        # 1. Intentar conectar al sensor Kinect Xbox 360 nativo
        if target is None or target == 'auto' or target == 'kinect':
            print("[INFO] Intentando conectar con el sensor Kinect Xbox 360 nativo...")
            k_cam = kinect_driver.KinectSensorCamera()
            if k_cam.isOpened():
                self.camera_index = "Kinect"
                self.camera_name = "Sensor Kinect Xbox 360"
                print("[KINECT OK] Sensor Kinect Xbox 360 inicializado y transmitiendo en vivo.")
                return k_cam
            else:
                print("[INFO] No se pudo inicializar Kinect nativo. Recurriendo a cámara web...")
                target = 0

        # 2. Conectar a cámara web estándar por índice numérico
        idx = int(target) if str(target).isdigit() else 0
        self.camera_index = idx
        devices = list_camera_devices()
        if 0 <= idx < len(devices):
            self.camera_name = devices[idx]
        else:
            self.camera_name = f"Camara #{idx}"

        if sys.platform.startswith('win'):
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(idx)

        if not cap.isOpened():
            cap = cv2.VideoCapture(idx)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, config.FPS_TARGET)
        return cap

    def change_camera(self, new_index):
        """Cambia a otro índice de cámara web."""
        if hasattr(self.cap, 'release'):
            self.cap.release()
        self.cap = self._init_camera(new_index)
        if self.cap.isOpened():
            self.show_notification(f"Camara activa: {self.camera_name}")
            play_feedback_sound("click")
        else:
            self.show_notification(f"Error al abrir camara {new_index}")

    def connect_kinect(self):
        """Re-conecta al sensor Kinect Xbox 360 nativo."""
        self.show_notification("Conectando al Kinect...")
        if hasattr(self.cap, 'release'):
            self.cap.release()
        self.cap = self._init_camera('kinect')
        if self.cap.isOpened():
            self.show_notification("Sensor Kinect Xbox 360 Conectado")
            play_feedback_sound("resume")
        else:
            self.show_notification("Kinect no responde. Verifica conexion")

    def _create_buttons(self):
        """Construye los 6 botones superiores: Amarillo, Azul, Verde, Iniciar, Detener, Limpiar."""
        buttons = []
        btn_height = 58
        btn_y1 = 15
        btn_y2 = btn_y1 + btn_height

        # 6 botones distribuidos en 1280px
        # 1. Amarillo
        buttons.append(AirButton("COLOR_AMARILLO", "AMARILLO", (20, btn_y1, 215, btn_y2),
                                 bg_color=(0, 160, 210), text_color=(255, 255, 255), border_color=(0, 230, 255)))
        # 2. Azul
        buttons.append(AirButton("COLOR_AZUL", "AZUL", (225, btn_y1, 420, btn_y2),
                                 bg_color=(190, 85, 0), text_color=(255, 255, 255), border_color=(255, 130, 0)))
        # 3. Verde
        buttons.append(AirButton("COLOR_VERDE", "VERDE", (430, btn_y1, 625, btn_y2),
                                 bg_color=(25, 140, 25), text_color=(255, 255, 255), border_color=(60, 235, 60)))
        # 4. Iniciar
        buttons.append(AirButton("START_DRAW", "INICIAR", (640, btn_y1, 835, btn_y2),
                                 bg_color=(20, 140, 60), text_color=(255, 255, 255), border_color=(50, 240, 100)))
        # 5. Detener
        buttons.append(AirButton("STOP_DRAW", "DETENER", (845, btn_y1, 1040, btn_y2),
                                 bg_color=(30, 30, 160), text_color=(255, 255, 255), border_color=(60, 80, 255)))
        # 6. Limpiar
        buttons.append(AirButton("CLEAR", "LIMPIAR", (1050, btn_y1, 1260, btn_y2),
                                 bg_color=(110, 30, 120), text_color=(255, 255, 255), border_color=(200, 70, 220)))

        return buttons

    def show_notification(self, text, duration=2.2):
        self.notification_text = text
        self.notification_time = time.time() + duration

    def clear_canvas(self):
        """Limpia todo el dibujo."""
        self.canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.show_notification("Lienzo Limpiado")
        play_feedback_sound("clear")

    def handle_button_trigger(self, btn_id):
        """Ejecuta la acción cuando se presiona un botón en el aire."""
        if btn_id == "COLOR_AMARILLO":
            self.current_color_key = "AMARILLO"
            self.current_color_bgr = config.COLORS["AMARILLO"]
            self.show_notification("Color: AMARILLO")
            play_feedback_sound("click")

        elif btn_id == "COLOR_AZUL":
            self.current_color_key = "AZUL"
            self.current_color_bgr = config.COLORS["AZUL"]
            self.show_notification("Color: AZUL")
            play_feedback_sound("click")

        elif btn_id == "COLOR_VERDE":
            self.current_color_key = "VERDE"
            self.current_color_bgr = config.COLORS["VERDE"]
            self.show_notification("Color: VERDE")
            play_feedback_sound("click")

        elif btn_id == "START_DRAW":
            self.drawing_enabled = True
            self.show_notification("Pincel: INICIADO (Activo)")
            play_feedback_sound("resume")

        elif btn_id == "STOP_DRAW":
            self.drawing_enabled = False
            self.show_notification("Pincel: DETENIDO (Pausado)")
            play_feedback_sound("pause")

        elif btn_id == "CLEAR":
            self.clear_canvas()

    def process_hand_gestures(self, landmarks):
        """
        Analiza los gestos de la mano:
        - Puño cerrado (✊): Detener dibujo.
        - Mano abierta (🖐️): Reanudar dibujo.
        - 1 Dedo (Índice ☝️): Dibujar.
        - 2 Dedos (✌️) o zona superior: Seleccionar botones.
        """
        tip_ids = [8, 12, 16, 20]
        fingers_up = []

        # 4 dedos (Índice, Medio, Anular, Meñique)
        for i in range(4):
            tip_idx = tip_ids[i]
            pip_idx = tip_idx - 2
            if landmarks[tip_idx].y < landmarks[pip_idx].y:
                fingers_up.append(1)
            else:
                fingers_up.append(0)

        index, middle, ring, pinky = fingers_up

        # Posición de la punta del dedo índice en píxeles
        ix = int(landmarks[8].x * self.width)
        iy = int(landmarks[8].y * self.height)

        # 1. Detección de Puño Cerrado (Todos los 4 dedos doblados)
        is_fist = (index == 0 and middle == 0 and ring == 0 and pinky == 0)

        # 2. Detección de Mano Abierta (Todos los 4 dedos extendidos)
        is_open_hand = (index == 1 and middle == 1 and ring == 1 and pinky == 1)

        # 3. Control de Estado Iniciar / Detener por gesto
        if is_fist and self.drawing_enabled:
            self.drawing_enabled = False
            self.show_notification("Pincel DETENIDO [Puno cerrado]")
            play_feedback_sound("pause")
        elif is_open_hand and not self.drawing_enabled:
            self.drawing_enabled = True
            self.show_notification("Pincel INICIADO [Mano abierta]")
            play_feedback_sound("resume")

        # 4. Modo Selección / Menú: 2 dedos (Índice y Medio) o dedo en zona superior
        is_selection_mode = (index == 1 and middle == 1 and ring == 0 and pinky == 0)

        # 5. Modo Dibujo: 1 solo dedo arriba (Índice)
        is_drawing_mode = (index == 1 and middle == 0 and ring == 0 and pinky == 0)

        return (ix, iy), is_drawing_mode, is_selection_mode

    def draw_hud(self, img, cursor_pos, is_drawing_mode, is_selection_mode):
        """Dibuja la barra de interfaz superior, botones, estado y notificaciones."""
        curr_time = time.time()

        # Fondo de barra superior
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, 85), (15, 15, 20), -1)
        cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)
        cv2.line(img, (0, 85), (self.width, 85), (60, 60, 80), 2, cv2.LINE_AA)

        cx, cy = cursor_pos if cursor_pos else (-1, -1)

        # Procesar y dibujar los 6 botones
        for btn in self.buttons:
            is_hovering = btn.contains(cx, cy) and (is_selection_mode or cy < 90)
            triggered = btn.update(is_hovering, curr_time, config.HOVER_DWELL_TIME)

            if triggered:
                self.handle_button_trigger(btn.btn_id)

            # Destacar botón seleccionado
            is_selected = False
            if btn.btn_id == f"COLOR_{self.current_color_key}":
                is_selected = True
            elif btn.btn_id == "START_DRAW" and self.drawing_enabled:
                is_selected = True
            elif btn.btn_id == "STOP_DRAW" and not self.drawing_enabled:
                is_selected = True

            btn.draw(img, is_selected=is_selected)

        # Barra de estado inferior izquierda
        hud_box_y = self.height - 70
        overlay_bottom = img.copy()
        cv2.rectangle(overlay_bottom, (15, hud_box_y), (540, self.height - 15), (20, 20, 25), -1)
        cv2.addWeighted(overlay_bottom, 0.75, img, 0.25, 0, img)
        cv2.rectangle(img, (15, hud_box_y), (540, self.height - 15), (70, 70, 90), 1, cv2.LINE_AA)

        # Muestra del color actual activo
        cv2.circle(img, (40, hud_box_y + 27), 16, self.current_color_bgr, -1)
        cv2.circle(img, (40, hud_box_y + 27), 17, (255, 255, 255), 2, cv2.LINE_AA)

        # Estado del pincel
        if not self.drawing_enabled:
            status_text = "DETENIDO (Toca INICIAR o abre mano)"
            status_color = (0, 70, 255)  # Rojo / Naranja
        elif is_drawing_mode:
            status_text = f"DIBUJANDO ({self.current_color_key})"
            status_color = (0, 255, 0)   # Verde
        else:
            status_text = "INICIADO (Levanta 1 dedo para dibujar)"
            status_color = (255, 200, 0) # Cyan

        cv2.putText(img, f"PINCEL: {status_text}", (70, hud_box_y + 25),
                    cv2.FONT_HERSHEY_DUPLEX, 0.50, status_color, 1, cv2.LINE_AA)

        hint = "1 Dedo: Dibujar | Botones: INICIAR / DETENER / LIMPIAR | 'I': Espejo"
        cv2.putText(img, hint, (70, hud_box_y + 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1, cv2.LINE_AA)

        # Indicador de Cámara Activa en la esquina inferior derecha
        cam_box_w = 340
        cam_box_x = self.width - cam_box_w - 15
        overlay_cam = img.copy()
        cv2.rectangle(overlay_cam, (cam_box_x, hud_box_y), (self.width - 15, self.height - 15), (20, 20, 25), -1)
        cv2.addWeighted(overlay_cam, 0.75, img, 0.25, 0, img)
        cv2.rectangle(img, (cam_box_x, hud_box_y), (self.width - 15, self.height - 15), (70, 70, 90), 1, cv2.LINE_AA)

        is_kinect = "kinect" in self.camera_name.lower()
        cam_tag = " [Kinect OK]" if is_kinect else ""
        cam_color = (60, 235, 60) if is_kinect else (0, 220, 255)
        mirror_tag = " (Espejo)" if self.flip_camera else " (Normal)"

        cv2.putText(img, f"Cam: {self.camera_name[:18]}{cam_tag}", (cam_box_x + 12, hud_box_y + 25),
                    cv2.FONT_HERSHEY_DUPLEX, 0.43, cam_color, 1, cv2.LINE_AA)
        cv2.putText(img, f"Modo:{mirror_tag} | 'I': Invertir | 'K': Kinect", (cam_box_x + 12, hud_box_y + 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1, cv2.LINE_AA)

        # Notificación flotante central
        if curr_time < self.notification_time:
            notif_w = 520
            notif_x = (self.width - notif_w) // 2
            notif_y = 105
            overlay_notif = img.copy()
            cv2.rectangle(overlay_notif, (notif_x, notif_y), (notif_x + notif_w, notif_y + 45), (10, 10, 15), -1)
            cv2.addWeighted(overlay_notif, 0.85, img, 0.15, 0, img)
            cv2.rectangle(img, (notif_x, notif_y), (notif_x + notif_w, notif_y + 45), (0, 230, 255), 2, cv2.LINE_AA)
            cv2.putText(img, self.notification_text, (notif_x + 15, notif_y + 28),
                        cv2.FONT_HERSHEY_DUPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

    def draw_cursor(self, img, pos, is_drawing_mode, is_selection_mode):
        """Dibuja el cursor neón en la punta del dedo."""
        if pos is None:
            return
        x, y = pos

        if is_drawing_mode and self.drawing_enabled and y > 85:
            # Cursor de dibujo activo
            radius = max(6, self.brush_size)
            cv2.circle(img, (x, y), radius, self.current_color_bgr, -1, cv2.LINE_AA)
            cv2.circle(img, (x, y), radius + 2, (255, 255, 255), 2, cv2.LINE_AA)
        elif not self.drawing_enabled and y > 85:
            # Cursor cuando está DETENIDO (Círculo rojo suave con retícula)
            cv2.circle(img, (x, y), 10, (0, 70, 255), 2, cv2.LINE_AA)
            cv2.circle(img, (x, y), 2, (0, 70, 255), -1, cv2.LINE_AA)
        elif is_selection_mode or y <= 85:
            # Cursor de selección (Retícula cyan)
            cv2.circle(img, (x, y), 12, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.circle(img, (x, y), 3, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.line(img, (x - 18, y), (x + 18, y), (0, 255, 255), 1, cv2.LINE_AA)
            cv2.line(img, (x, y - 18), (x, y + 18), (0, 255, 255), 1, cv2.LINE_AA)

    def run(self):
        """Bucle principal de la aplicación."""
        print("="*60)
        print("Iniciando Lienzo Magico Kinect / Air Canvas...")
        print("Botones Disponibles: AMARILLO | AZUL | VERDE | INICIAR | DETENER | LIMPIAR")
        print("Atajos de Teclado:")
        print("  - 'I'             : Invertir / Alternar modo espejo")
        print("  - 'C'             : Limpiar lienzo")
        print("  - 'K'             : Re-conectar a Kinect")
        print("  - 'Q' o ESC       : Salir")
        print("="*60)

        window_name = "Lienzo Magico Kinect - Air Canvas"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.width, self.height)

        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success:
                time.sleep(0.03)
                continue

            # Redimensionar
            frame = cv2.resize(frame, (self.width, self.height))

            # Inversión de imagen (si flip_camera está habilitado)
            if self.flip_camera:
                frame = cv2.flip(frame, 1)

            # Procesamiento de mano con MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)

            cursor_pos = None
            is_drawing_mode = False
            is_selection_mode = False

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(
                        frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                        self.mp_draw.DrawingSpec(color=(80, 80, 80), thickness=1, circle_radius=2),
                        self.mp_draw.DrawingSpec(color=(120, 240, 120), thickness=1)
                    )

                    (ix, iy), is_drawing_mode, is_selection_mode = self.process_hand_gestures(hand_landmarks.landmark)
                    cursor_pos = (ix, iy)

                    # Suavizado de coordenadas (EMA)
                    if not self.has_prev_point:
                        self.smooth_x, self.smooth_y = ix, iy
                        self.prev_x, self.prev_y = ix, iy
                        self.has_prev_point = True
                    else:
                        alpha = config.SMOOTHING_FACTOR
                        self.smooth_x = int(alpha * ix + (1 - alpha) * self.smooth_x)
                        self.smooth_y = int(alpha * iy + (1 - alpha) * self.smooth_y)

                    # Lógica de dibujo con 1 dedo
                    if is_drawing_mode and self.drawing_enabled and iy > 85:
                        draw_color = self.current_color_bgr
                        thickness = self.brush_size

                        cv2.line(self.canvas, (self.prev_x, self.prev_y), (self.smooth_x, self.smooth_y),
                                 draw_color, thickness, cv2.LINE_AA)
                        cv2.circle(self.canvas, (self.smooth_x, self.smooth_y), thickness // 2,
                                   draw_color, -1, cv2.LINE_AA)

                        self.prev_x, self.prev_y = self.smooth_x, self.smooth_y
                    else:
                        self.prev_x, self.prev_y = self.smooth_x, self.smooth_y
            else:
                self.has_prev_point = False

            # Fusión de dibujo sobre la imagen de la cámara (Realidad Aumentada)
            canvas_gray = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(canvas_gray, 10, 255, cv2.THRESH_BINARY)
            mask_inv = cv2.bitwise_not(mask)

            frame_bg = cv2.bitwise_and(frame, frame, mask=mask_inv)
            canvas_fg = cv2.bitwise_and(self.canvas, self.canvas, mask=mask)
            final_frame = cv2.add(frame_bg, canvas_fg)

            # Dibujar interfaz HUD y botones
            self.draw_hud(final_frame, cursor_pos, is_drawing_mode, is_selection_mode)

            # Dibujar cursor en la punta del dedo
            self.draw_cursor(final_frame, cursor_pos, is_drawing_mode, is_selection_mode)

            # Mostrar ventana
            cv2.imshow(window_name, final_frame)

            # Manejo de teclas auxiliares
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord('q') or key == ord('Q'):
                break
            elif key == ord('c') or key == ord('C'):
                self.clear_canvas()
            elif key == ord('i') or key == ord('I'):
                self.flip_camera = not self.flip_camera
                modo = "ESPEJO" if self.flip_camera else "NORMAL (Sin invertir)"
                self.show_notification(f"Camara: {modo}")
                play_feedback_sound("click")
            elif key == ord('k') or key == ord('K'):
                self.connect_kinect()
            elif key in [ord('0'), ord('1'), ord('2'), ord('3'), ord('4')]:
                cam_id = key - ord('0')
                self.change_camera(cam_id)

        # Liberar recursos
        self.cap.release()
        cv2.destroyAllWindows()
        print("Aplicacion finalizada correctamente.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Lienzo Magico Kinect Xbox 360")
    parser.add_argument("--camera", type=str, default=str(config.CAMERA_INDEX),
                        help="Indice de la camara (ej: 0, 1 o 'auto' para Kinect)")
    args = parser.parse_args()

    cam_arg = args.camera
    if cam_arg.isdigit():
        cam_arg = int(cam_arg)

    app = AirCanvasApp(camera_index=cam_arg)
    app.run()
