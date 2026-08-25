"""
Configuración para el Lienzo Mágico Kinect (Air Canvas)
Define resolución, colores, dimensiones de interfaz y parámetros de detección.
"""
import os

# Configuración de Video / Ventana
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
CAMERA_INDEX = 0  # Índice de cámara por defecto (0 = predeterminada / Kinect)
FPS_TARGET = 30

# Paleta de Colores (Formato BGR para OpenCV)
COLORS = {
    'AMARILLO': (0, 230, 255),    # Amarillo brillante (BGR)
    'AZUL': (255, 130, 0),        # Azul vibrante (BGR)
    'VERDE': (60, 235, 60),       # Verde neón (BGR)
    'BORRADOR': (0, 0, 0),        # Borrador
}

COLOR_OPTIONS = [
    {'id': 'AMARILLO', 'name': 'Amarillo', 'bgr': (0, 230, 255), 'color_fill': (0, 215, 255)},
    {'id': 'AZUL', 'name': 'Azul', 'bgr': (255, 130, 0), 'color_fill': (255, 130, 0)},
    {'id': 'VERDE', 'name': 'Verde', 'bgr': (60, 235, 60), 'color_fill': (60, 235, 60)},
]

# Configuración del Pincel
DEFAULT_COLOR = 'AMARILLO'
DEFAULT_BRUSH_THICKNESS = 7
ERASER_THICKNESS = 45
SMOOTHING_FACTOR = 0.55  # Factor de suavizado para evitar vibraciones en la mano

# Tiempos de detección e interacción
HOVER_DWELL_TIME = 0.40  # Segundos sobre un botón en el aire para activarlo

# Carpeta donde se guardan las capturas
SAVED_DRAWINGS_DIR = 'dibujos_guardados'
if not os.path.exists(SAVED_DRAWINGS_DIR):
    os.makedirs(SAVED_DRAWINGS_DIR, exist_ok=True)
