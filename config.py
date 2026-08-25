"""
Configuración para el Lienzo Mágico Kinect (Air Canvas)
Define resolución, colores, dimensiones de interfaz y parámetros de detección.
"""
import os

# Configuración de Video / Ventana
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
CAMERA_INDEX = 'auto'  
FPS_TARGET = 30
FLIP_CAMERA = False  # False para cámara sin invertir (normal), True para modo espejo

COLORS = {
    'ROJO': (0, 0, 255),          #(BGR)
    'AZUL': (255, 130, 0),        
    'VERDE': (60, 235, 60),       
    'BORRADOR': (0, 0, 0),        
}

COLOR_OPTIONS = [
    {'id': 'ROJO', 'name': 'Rojo', 'bgr': (0, 0, 255), 'color_fill': (0, 0, 255)},
    {'id': 'AZUL', 'name': 'Azul', 'bgr': (255, 130, 0), 'color_fill': (255, 130, 0)},
    {'id': 'VERDE', 'name': 'Verde', 'bgr': (60, 235, 60), 'color_fill': (60, 235, 60)},
]

# Configuración del Pincel
DEFAULT_COLOR = 'ROJO'
BRUSH_THICKNESS = 8
SMOOTHING_FACTOR = 0.55  # Factor de suavizado para evitar vibraciones en la mano

# Tiempos de detección e interacción
HOVER_DWELL_TIME = 0.40  # Segundos sobre un botón en el aire para activarlo
