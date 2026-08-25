"""
=============================================================================
             LIENZO MÁGICO KINECT XBOX 360 / AIR CANVAS PRO
=============================================================================
Aplicación interactiva de dibujo en el aire para Kinect Xbox 360 y Webcams.
Permite dibujar con el dedo índice, seleccionar colores (Amarillo, Azul, Verde),
limpiar el lienzo, iniciar/detener el pincel y guardar las obras creadas.
=============================================================================
"""

import cv2
import numpy as np
import mediapipe as mp
import time
import os
import threading
import sys
from datetime import datetime

# Importar configuraciones
import config

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False


def play_feedback_sound(sound_type="click"):
    """Emite un sonido de confirmación en un hilo separado para no trabar el video."""
    if not HAS_SOUND:
        return
    def _beep():
        try:
            if sound_type == "click":
                winsound.Beep(1200, 70)
            elif sound_type == "clear":
                winsound.Beep(800, 120)
                winsound.Beep(600, 120)
            elif sound_type == "toggle":
                winsound.Beep(1500, 90)
            elif sound_type == "save":
                winsound.Beep(900, 80)
                winsound.Beep(1300, 120)
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
        self.is_active = False
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
                self.hover_start_time = current_time  # Reiniciar para evitar disparos repetidos inmediatos
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

        # Dibujar fondo del botón con esquinas redondeadas
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), fill_color, -1)
        cv2.addWeighted(overlay, 0.75, img, 0.25, 0, img)

        # Borde exterior
        cv2.rectangle(img, (x1, y1), (x2, y2), stroke_color, 2 if not is_selected else 4, cv2.LINE_AA)

        # Barra / Círculo de progreso Dwell
        if self.dwell_progress > 0:
            bar_w = int(w * self.dwell_progress)
            cv2.rectangle(img, (x1, y2 - 6), (x1 + bar_w, y2), (0, 255, 255), -1)

        # Texto centrado
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 0.58
        font_thickness = 1
        text_size = cv2.getTextSize(self.text, font, font_scale, font_thickness)[0]
        text_x = x1 + (w - text_size[0]) // 2
        text_y = y1 + (h + text_size[1]) // 2

        # Sombra de texto
        cv2.putText(img, self.text, (text_x + 1, text_y + 1), font, font_scale, (0, 0, 0), font_thickness + 1, cv2.LINE_AA)
        cv2.putText(img, self.text, (text_x, text_y), font, font_scale, self.text_color, font_thickness, cv2.LINE_AA)


class AirCanvasApp:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.width = config.WINDOW_WIDTH
        self.height = config.WINDOW_HEIGHT

        # Inicialización de captura de video
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
        self.brush_size = config.DEFAULT_BRUSH_THICKNESS
        self.is_eraser = False
        self.drawing_enabled = True  # Iniciar / Detener
        self.view_mode = "AR"        # "AR" (Realidad Aumentada) o "CANVAS" (Pizarra)

        # Puntos de seguimiento con suavizado
        self.prev_x, self.prev_y = 0, 0
        self.smooth_x, self.smooth_y = 0, 0
        self.has_prev_point = False

        # Notificaciones en pantalla
        self.notification_text = "¡Bienvenido al Lienzo Mágico Kinect!"
        self.notification_time = time.time() + 3.0

        # Crear interfaz de botones flotantes
        self.buttons = self._create_buttons()

    def _init_camera(self, index):
        """Inicializa la cámara seleccionada optimizada con DirectShow si está en Windows."""
        if sys.platform.startswith('win'):
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(index)

        if not cap.isOpened():
            cap = cv2.VideoCapture(index)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, config.FPS_TARGET)
        return cap

    def change_camera(self, new_index):
        """Cambia a otro índice de cámara en caliente (ej: cambiar entre webcam y Kinect)."""
        self.cap.release()
        self.camera_index = new_index
        self.cap = self._init_camera(self.camera_index)
        if self.cap.isOpened():
            self.show_notification(f"Cámara cambiada a índice: {new_index}")
        else:
            self.show_notification(f"Error: Cámara {new_index} no disponible")

    def _create_buttons(self):
        """Construye la botonera superior flotante."""
        buttons = []
        btn_height = 55
        btn_y1 = 15
        btn_y2 = btn_y1 + btn_height
        spacing = 10

        # Botones de color
        # 1. Amarillo
        buttons.append(AirButton("COLOR_AMARILLO", "AMARILLO", (20, btn_y1, 160, btn_y2),
                                 bg_color=(0, 160, 200), text_color=(255, 255, 255), border_color=(0, 230, 255)))
        # 2. Azul
        buttons.append(AirButton("COLOR_AZUL", "AZUL", (170, btn_y1, 290, btn_y2),
                                 bg_color=(180, 80, 0), text_color=(255, 255, 255), border_color=(255, 130, 0)))
        # 3. Verde
        buttons.append(AirButton("COLOR_VERDE", "VERDE", (300, btn_y1, 420, btn_y2),
                                 bg_color=(30, 140, 30), text_color=(255, 255, 255), border_color=(60, 235, 60)))
        # 4. Iniciar / Detener Dibujo
        buttons.append(AirButton("TOGGLE_DRAW", "PAUSAR / DIBUJAR", (440, btn_y1, 640, btn_y2),
                                 bg_color=(70, 30, 110), text_color=(255, 255, 255), border_color=(180, 70, 255)))
        # 5. Grosor de Pincel
        buttons.append(AirButton("BRUSH_SIZE", f"GROSOR: {self.brush_size}px", (650, btn_y1, 800, btn_y2),
                                 bg_color=(50, 50, 50), text_color=(230, 230, 230), border_color=(140, 140, 140)))
        # 6. Borrador
        buttons.append(AirButton("ERASER", "BORRADOR", (810, btn_y1, 950, btn_y2),
                                 bg_color=(40, 40, 60), text_color=(220, 220, 220), border_color=(120, 120, 180)))
        # 7. Limpiar
        buttons.append(AirButton("CLEAR", "LIMPIAR", (960, btn_y1, 1090, btn_y2),
                                 bg_color=(30, 30, 150), text_color=(255, 255, 255), border_color=(50, 50, 255)))
        # 8. Guardar
        buttons.append(AirButton("SAVE", "GUARDAR", (1100, btn_y1, 1250, btn_y2),
                                 bg_color=(20, 120, 80), text_color=(255, 255, 255), border_color=(40, 220, 140)))

        return buttons

    def show_notification(self, text, duration=2.5):
        self.notification_text = text
        self.notification_time = time.time() + duration

    def clear_canvas(self):
        """Limpia todo el dibujo."""
        self.canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.show_notification("¡Lienzo limpiado!")
        play_feedback_sound("clear")

    def save_drawing(self, frame_blend):
        """Guarda la obra de arte en la carpeta de capturas."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(config.SAVED_DRAWINGS_DIR, f"kinect_dibujo_{timestamp}.png")
        
        # Si estamos en modo AR o lienzo, guardar la imagen compuesta de alta calidad
        cv2.imwrite(filename, frame_blend)
        self.show_notification(f"Guardado: {os.path.basename(filename)}", duration=3.5)
        play_feedback_sound("save")

    def handle_button_trigger(self, btn_id):
        """Ejecuta la acción cuando se presiona un botón en el aire."""
        if btn_id == "COLOR_AMARILLO":
            self.current_color_key = "AMARILLO"
            self.current_color_bgr = config.COLORS["AMARILLO"]
            self.is_eraser = False
            self.show_notification("Color seleccionado: AMARILLO")
            play_feedback_sound("click")

        elif btn_id == "COLOR_AZUL":
            self.current_color_key = "AZUL"
            self.current_color_bgr = config.COLORS["AZUL"]
            self.is_eraser = False
            self.show_notification("Color seleccionado: AZUL")
            play_feedback_sound("click")

        elif btn_id == "COLOR_VERDE":
            self.current_color_key = "VERDE"
            self.current_color_bgr = config.COLORS["VERDE"]
            self.is_eraser = False
            self.show_notification("Color seleccionado: VERDE")
            play_feedback_sound("click")

        elif btn_id == "TOGGLE_DRAW":
            self.drawing_enabled = not self.drawing_enabled
            estado = "DIBUJANDO (Activo)" if self.drawing_enabled else "PAUSADO (Detenido)"
            self.show_notification(f"Pincel: {estado}")
            play_feedback_sound("toggle")

        elif btn_id == "BRUSH_SIZE":
            sizes = [4, 8, 14, 22]
            current_idx = sizes.index(self.brush_size) if self.brush_size in sizes else 1
            next_idx = (current_idx + 1) % len(sizes)
            self.brush_size = sizes[next_idx]
            # Actualizar texto del botón
            for b in self.buttons:
                if b.btn_id == "BRUSH_SIZE":
                    b.text = f"GROSOR: {self.brush_size}px"
            self.show_notification(f"Grosor del pincel: {self.brush_size}px")
            play_feedback_sound("click")

        elif btn_id == "ERASER":
            self.is_eraser = not self.is_eraser
            if self.is_eraser:
                self.show_notification("Modo: BORRADOR ACTIVADO")
            else:
                self.show_notification(f"Modo: PINCEL ({self.current_color_key})")
            play_feedback_sound("click")

        elif btn_id == "CLEAR":
            self.clear_canvas()

        elif btn_id == "SAVE":
            # Guardado diferido con el frame actual
            self.save_requested = True

    def process_hand_gestures(self, landmarks):
        """
        Analiza los dedos levantados.
        Retorna:
        - index_tip (x, y)
        - is_drawing_mode (bool: 1 dedo levantado)
        - is_selection_mode (bool: 2 dedos levantados)
        - all_folded (bool: puño)
        """
        # Índices de MediaPipe para puntas y articulaciones
        # Dedo Índice: punta 8, articulación 6
        # Dedo Medio: punta 12, articulación 10
        # Dedo Anular: punta 16, articulación 14
        # Dedo Meñique: punta 20, articulación 18
        # Pulgar: punta 4, articulación 2

        tip_ids = [8, 12, 16, 20]
        fingers_up = []

        # Pulgar (comparación horizontal en espejo)
        if landmarks[4].x < landmarks[3].x:
            fingers_up.append(1)
        else:
            fingers_up.append(0)

        # 4 dedos restantes (comparación vertical y)
        for i in range(4):
            tip_idx = tip_ids[i]
            pip_idx = tip_idx - 2
            if landmarks[tip_idx].y < landmarks[pip_idx].y:
                fingers_up.append(1)
            else:
                fingers_up.append(0)

        # Dedos: [Pulgar, Índice, Medio, Anular, Meñique]
        thumb, index, middle, ring, pinky = fingers_up

        # Posición de la punta del dedo índice en píxeles
        ix = int(landmarks[8].x * self.width)
        iy = int(landmarks[8].y * self.height)

        # Modo Selección / Menú: 2 dedos (Índice y Medio arriba) o dedo en zona superior
        is_selection_mode = (index == 1 and middle == 1 and ring == 0 and pinky == 0)

        # Modo Dibujo: 1 dedo (Solo Índice arriba)
        is_drawing_mode = (index == 1 and middle == 0 and ring == 0 and pinky == 0)

        return (ix, iy), is_drawing_mode, is_selection_mode, fingers_up

    def draw_hud(self, img, cursor_pos, is_drawing_mode, is_selection_mode):
        """Dibuja la barra de interfaz superior, botones, estado y notificaciones."""
        curr_time = time.time()

        # Dibujar fondo de barra superior tipo Cyber/Glass
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, 80), (15, 15, 20), -1)
        cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)
        cv2.line(img, (0, 80), (self.width, 80), (60, 60, 80), 2, cv2.LINE_AA)

        cx, cy = cursor_pos if cursor_pos else (-1, -1)

        # Procesar y dibujar cada botón
        for btn in self.buttons:
            is_hovering = btn.contains(cx, cy) and (is_selection_mode or cy < 85)
            triggered = btn.update(is_hovering, curr_time, config.HOVER_DWELL_TIME)

            if triggered:
                self.handle_button_trigger(btn.btn_id)

            # Determinar si el botón está actualmente activo/seleccionado
            is_selected = False
            if btn.btn_id == f"COLOR_{self.current_color_key}" and not self.is_eraser:
                is_selected = True
            elif btn.btn_id == "ERASER" and self.is_eraser:
                is_selected = True

            btn.draw(img, is_selected=is_selected)

        # Indicador de Modo en la esquina inferior izquierda
        hud_box_y = self.height - 70
        overlay_bottom = img.copy()
        cv2.rectangle(overlay_bottom, (15, hud_box_y), (480, self.height - 15), (20, 20, 25), -1)
        cv2.addWeighted(overlay_bottom, 0.75, img, 0.25, 0, img)
        cv2.rectangle(img, (15, hud_box_y), (480, self.height - 15), (70, 70, 90), 1, cv2.LINE_AA)

        # Color actual activo
        current_bgr = (40, 40, 40) if self.is_eraser else self.current_color_bgr
        cv2.circle(img, (40, hud_box_y + 27), 16, current_bgr, -1)
        cv2.circle(img, (40, hud_box_y + 27), 17, (255, 255, 255), 2, cv2.LINE_AA)

        # Estado del pincel
        status_text = "DIBUJANDO" if (self.drawing_enabled and is_drawing_mode) else ("PAUSADO" if not self.drawing_enabled else "SELECCION")
        status_color = (0, 255, 0) if (self.drawing_enabled and is_drawing_mode) else ((0, 165, 255) if not self.drawing_enabled else (255, 200, 0))

        cv2.putText(img, f"PINCEL: {status_text}", (70, hud_box_y + 25),
                    cv2.FONT_HERSHEY_DUPLEX, 0.55, status_color, 1, cv2.LINE_AA)
        
        hint = "1 Dedo: Dibujar | 2 Dedos: Seleccionar | 'C': Limpiar | 'S': Guardar"
        cv2.putText(img, hint, (70, hud_box_y + 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 180, 180), 1, cv2.LINE_AA)

        # Notificación flotante con desvanecimiento
        if curr_time < self.notification_time:
            notif_w = 400
            notif_x = (self.width - notif_w) // 2
            notif_y = 100
            overlay_notif = img.copy()
            cv2.rectangle(overlay_notif, (notif_x, notif_y), (notif_x + notif_w, notif_y + 45), (10, 10, 15), -1)
            cv2.addWeighted(overlay_notif, 0.85, img, 0.15, 0, img)
            cv2.rectangle(img, (notif_x, notif_y), (notif_x + notif_w, notif_y + 45), (0, 230, 255), 2, cv2.LINE_AA)
            cv2.putText(img, self.notification_text, (notif_x + 15, notif_y + 28),
                        cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    def draw_cursor(self, img, pos, is_drawing_mode, is_selection_mode):
        """Dibuja el cursor neón en la punta del dedo."""
        if pos is None:
            return
        x, y = pos
        color = (255, 255, 255) if self.is_eraser else self.current_color_bgr

        if is_drawing_mode and self.drawing_enabled and y > 85:
            # Cursor de dibujo (círculo con el grosor del pincel)
            radius = max(6, self.brush_size if not self.is_eraser else config.ERASER_THICKNESS // 2)
            cv2.circle(img, (x, y), radius, color, -1, cv2.LINE_AA)
            cv2.circle(img, (x, y), radius + 2, (255, 255, 255), 2, cv2.LINE_AA)
        elif is_selection_mode or y <= 85:
            # Cursor de selección (Retícula / Puntero flotante)
            cv2.circle(img, (x, y), 12, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.circle(img, (x, y), 3, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.line(img, (x - 18, y), (x + 18, y), (0, 255, 255), 1, cv2.LINE_AA)
            cv2.line(img, (x, y - 18), (x, y + 18), (0, 255, 255), 1, cv2.LINE_AA)

    def run(self):
        """Bucle principal de la aplicación."""
        print("="*60)
        print("Iniciando Lienzo Mágico Kinect / Air Canvas...")
        print("Atajos de teclado:")
        print("  - 'Q' o ESC : Salir")
        print("  - 'C'       : Limpiar lienzo")
        print("  - 'S'       : Guardar dibujo")
        print("  - 'M'       : Alternar modo de vista (AR / Pizarra)")
        print("  - 'D' / ESPACIO : Iniciar / Detener dibujo")
        print("  - '0'..'4'  : Cambiar índice de cámara/Kinect")
        print("="*60)

        window_name = "Lienzo Magico Kinect - Air Canvas Pro"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.width, self.height)

        self.save_requested = False

        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success:
                # Si falla un fotograma, esperar e intentar nuevamente
                time.sleep(0.03)
                continue

            # Redimensionar y voltear horizontalmente para efecto espejo
            frame = cv2.resize(frame, (self.width, self.height))
            frame = cv2.flip(frame, 1)

            # Convertir a RGB para MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)

            cursor_pos = None
            is_drawing_mode = False
            is_selection_mode = False

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Opcional: dibujar conexiones de la mano con estilo translúcido
                    self.mp_draw.draw_landmarks(
                        frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                        self.mp_draw.DrawingSpec(color=(80, 80, 80), thickness=1, circle_radius=2),
                        self.mp_draw.DrawingSpec(color=(120, 240, 120), thickness=1)
                    )

                    (ix, iy), is_drawing_mode, is_selection_mode, fingers = self.process_hand_gestures(hand_landmarks.landmark)
                    cursor_pos = (ix, iy)

                    # Suavizado de coordenadas con filtro exponencial (EMA)
                    if not self.has_prev_point:
                        self.smooth_x, self.smooth_y = ix, iy
                        self.prev_x, self.prev_y = ix, iy
                        self.has_prev_point = True
                    else:
                        alpha = config.SMOOTHING_FACTOR
                        self.smooth_x = int(alpha * ix + (1 - alpha) * self.smooth_x)
                        self.smooth_y = int(alpha * iy + (1 - alpha) * self.smooth_y)

                    # Lógica de dibujo
                    # Solo dibuja si: 1 dedo arriba, dibujo activado, y no está sobre la barra superior
                    if is_drawing_mode and self.drawing_enabled and iy > 85:
                        draw_color = (0, 0, 0) if self.is_eraser else self.current_color_bgr
                        thickness = config.ERASER_THICKNESS if self.is_eraser else self.brush_size

                        # Trazar línea suave y continua
                        cv2.line(self.canvas, (self.prev_x, self.prev_y), (self.smooth_x, self.smooth_y),
                                 draw_color, thickness, cv2.LINE_AA)
                        # Dibujar círculo en el extremo para bordes redondeados
                        cv2.circle(self.canvas, (self.smooth_x, self.smooth_y), thickness // 2,
                                   draw_color, -1, cv2.LINE_AA)

                        self.prev_x, self.prev_y = self.smooth_x, self.smooth_y
                    else:
                        # Si no está dibujando, reiniciar punto previo para no conectar trazos inconexos
                        self.prev_x, self.prev_y = self.smooth_x, self.smooth_y
            else:
                self.has_prev_point = False

            # Composición de imagen final según el modo de vista
            if self.view_mode == "AR":
                # Modo Realidad Aumentada: fusionar lienzo sobre la cámara
                # Crear máscara de dibujo
                canvas_gray = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
                _, mask = cv2.threshold(canvas_gray, 10, 255, cv2.THRESH_BINARY)
                mask_inv = cv2.bitwise_not(mask)

                # Fondo de cámara sin dibujo
                frame_bg = cv2.bitwise_and(frame, frame, mask=mask_inv)
                # Dibujo coloreado
                canvas_fg = cv2.bitwise_and(self.canvas, self.canvas, mask=mask)
                # Combinación
                final_frame = cv2.add(frame_bg, canvas_fg)
            else:
                # Modo Pizarra: Pizarra digital con Picture-in-Picture en la esquina
                final_frame = np.full((self.height, self.width, 3), 20, dtype=np.uint8)  # Fondo oscuro elegante
                canvas_gray = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
                _, mask = cv2.threshold(canvas_gray, 10, 255, cv2.THRESH_BINARY)
                mask_inv = cv2.bitwise_not(mask)
                final_frame = cv2.bitwise_and(final_frame, final_frame, mask=mask_inv)
                final_frame = cv2.add(final_frame, self.canvas)

                # Miniatura PiP de la cámara en la esquina inferior derecha
                pip_w, pip_h = 240, 135
                pip_x, pip_y = self.width - pip_w - 20, self.height - pip_h - 20
                small_cam = cv2.resize(frame, (pip_w, pip_h))
                cv2.rectangle(final_frame, (pip_x - 2, pip_y - 2), (pip_x + pip_w + 2, pip_y + pip_h + 2), (0, 230, 255), 2)
                final_frame[pip_y:pip_y + pip_h, pip_x:pip_x + pip_w] = small_cam

            # Dibujar interfaz HUD y botones
            self.draw_hud(final_frame, cursor_pos, is_drawing_mode, is_selection_mode)

            # Dibujar cursor en la punta del dedo
            self.draw_cursor(final_frame, cursor_pos, is_drawing_mode, is_selection_mode)

            # Si se solicitó guardar, capturar el cuadro final
            if self.save_requested:
                self.save_drawing(final_frame)
                self.save_requested = False

            # Mostrar ventana
            cv2.imshow(window_name, final_frame)

            # Manejo de teclas
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord('q') or key == ord('Q'):
                break
            elif key == ord('c') or key == ord('C'):
                self.clear_canvas()
            elif key == ord('s') or key == ord('S'):
                self.save_drawing(final_frame)
            elif key == ord('m') or key == ord('M'):
                self.view_mode = "CANVAS" if self.view_mode == "AR" else "AR"
                self.show_notification(f"Modo de vista: {self.view_mode}")
            elif key == ord('d') or key == ord('D') or key == 32:  # 32 = Barra espaciadora
                self.drawing_enabled = not self.drawing_enabled
                estado = "DIBUJANDO" if self.drawing_enabled else "PAUSADO"
                self.show_notification(f"Pincel: {estado}")
                play_feedback_sound("toggle")
            elif key in [ord('0'), ord('1'), ord('2'), ord('3'), ord('4')]:
                cam_id = key - ord('0')
                self.change_camera(cam_id)

        # Liberar recursos
        self.cap.release()
        cv2.destroyAllWindows()
        print("Aplicación finalizada correctamente.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Lienzo Mágico Kinect Xbox 360 / Air Canvas")
    parser.add_argument("--camera", type=int, default=config.CAMERA_INDEX, help="Índice de la cámara (ej: 0, 1)")
    args = parser.parse_args()

    app = AirCanvasApp(camera_index=args.camera)
    app.run()
