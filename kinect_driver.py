"""
=============================================================================
           DRIVER NATIVO KINECT XBOX 360 / KINECT FOR WINDOWS (V1.8)
=============================================================================
Controlador directo de alta velocidad para capturar la cámara del Kinect v1
utilizando la biblioteca oficial Kinect10.dll de Microsoft.
=============================================================================
"""

import ctypes
from ctypes import wintypes
import numpy as np
import cv2
import time

# Constantes del SDK de Kinect v1.8 (NuiApi.h)
NUI_INITIALIZE_FLAG_USES_COLOR = 0x00000002
NUI_IMAGE_TYPE_COLOR = 1
NUI_IMAGE_RESOLUTION_640x480 = 2
NUI_IMAGE_STREAM_FRAME_LIMIT_MAXIMUM = 2

class NUI_IMAGE_VIEW_AREA(ctypes.Structure):
    _fields_ = [
        ("eDigitalZoom", ctypes.c_int),
        ("lCenterX", ctypes.c_long),
        ("lCenterY", ctypes.c_long)
    ]

class NUI_LOCKED_RECT(ctypes.Structure):
    _fields_ = [
        ("Pitch", ctypes.c_int),
        ("size", ctypes.c_int),
        ("pBits", ctypes.c_void_p)
    ]

class INuiFrameTexture(ctypes.Structure):
    pass

class INuiFrameTextureVtbl(ctypes.Structure):
    _fields_ = [
        ("QueryInterface", ctypes.c_void_p),
        ("AddRef", ctypes.c_void_p),
        ("Release", ctypes.c_void_p),
        ("BufferLen", ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p)),
        ("Pitch", ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p)),
        ("LockRect", ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(NUI_LOCKED_RECT), ctypes.c_void_p, ctypes.c_ulong)),
        ("UnlockRect", ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint))
    ]

INuiFrameTexture._fields_ = [("lpVtbl", ctypes.POINTER(INuiFrameTextureVtbl))]

class NUI_IMAGE_FRAME(ctypes.Structure):
    _fields_ = [
        ("liTimeStamp", ctypes.c_longlong),
        ("dwFrameNumber", ctypes.c_ulong),
        ("eImageType", ctypes.c_int),
        ("eResolution", ctypes.c_int),
        ("pFrameTexture", ctypes.POINTER(INuiFrameTexture)),
        ("dwFrameFlags", ctypes.c_ulong),
        ("ViewArea", NUI_IMAGE_VIEW_AREA)
    ]

# Funciones de Windows Kernel32
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
CreateEvent = kernel32.CreateEventW
CreateEvent.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
CreateEvent.restype = wintypes.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL


class KinectSensorCamera:
    """Clase compatible con cv2.VideoCapture para captura directa desde Kinect Xbox 360."""
    def __init__(self):
        self.is_connected = False
        self.kinect = None
        self.h_stream = wintypes.HANDLE()
        self.h_event = None
        self._init_kinect()

    def _init_kinect(self):
        try:
            self.kinect = ctypes.WinDLL("Kinect10.dll")

            # Configurar firmas de funciones
            self.kinect.NuiInitialize.argtypes = [ctypes.c_ulong]
            self.kinect.NuiInitialize.restype = ctypes.c_long

            self.kinect.NuiShutdown.argtypes = []
            self.kinect.NuiShutdown.restype = None

            self.kinect.NuiImageStreamOpen.argtypes = [
                ctypes.c_int, ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                wintypes.HANDLE, ctypes.POINTER(wintypes.HANDLE)
            ]
            self.kinect.NuiImageStreamOpen.restype = ctypes.c_long

            self.kinect.NuiImageStreamGetNextFrame.argtypes = [
                wintypes.HANDLE, ctypes.c_ulong, ctypes.POINTER(ctypes.POINTER(NUI_IMAGE_FRAME))
            ]
            self.kinect.NuiImageStreamGetNextFrame.restype = ctypes.c_long

            self.kinect.NuiImageStreamReleaseFrame.argtypes = [
                wintypes.HANDLE, ctypes.POINTER(NUI_IMAGE_FRAME)
            ]
            self.kinect.NuiImageStreamReleaseFrame.restype = ctypes.c_long

            # Inicializar sensor
            hr = self.kinect.NuiInitialize(NUI_INITIALIZE_FLAG_USES_COLOR)
            if hr != 0:
                print(f"[KINECT-DRIVER] Error en NuiInitialize: {hex(hr & 0xFFFFFFFF)}")
                self.is_connected = False
                return

            self.h_event = CreateEvent(None, True, False, None)
            hr = self.kinect.NuiImageStreamOpen(
                NUI_IMAGE_TYPE_COLOR,
                NUI_IMAGE_RESOLUTION_640x480,
                0,
                NUI_IMAGE_STREAM_FRAME_LIMIT_MAXIMUM,
                self.h_event,
                ctypes.byref(self.h_stream)
            )

            if hr != 0:
                print(f"[KINECT-DRIVER] Error en NuiImageStreamOpen: {hex(hr & 0xFFFFFFFF)}")
                self.kinect.NuiShutdown()
                self.is_connected = False
                return

            self.is_connected = True
            print("[KINECT-DRIVER] !Sensor Kinect Xbox 360 conectado y listo para transmitir!")
        except Exception as e:
            print(f"[KINECT-DRIVER] Excepcion al conectar con Kinect10.dll: {e}")
            self.is_connected = False

    def isOpened(self):
        return self.is_connected

    def read(self):
        """Captura el siguiente fotograma BGR del Kinect (640x480)."""
        if not self.is_connected or not self.kinect:
            return False, None

        p_frame = ctypes.POINTER(NUI_IMAGE_FRAME)()
        hr = self.kinect.NuiImageStreamGetNextFrame(self.h_stream, 200, ctypes.byref(p_frame))
        if hr == 0:
            frame_struct = p_frame.contents
            tex = frame_struct.pFrameTexture.contents
            locked_rect = NUI_LOCKED_RECT()
            hr_lock = tex.lpVtbl.contents.LockRect(frame_struct.pFrameTexture, 0, ctypes.byref(locked_rect), None, 0)
            if hr_lock == 0:
                # Datos de color vienen en formato BGRA 32-bit (640x480x4)
                buffer = ctypes.cast(locked_rect.pBits, ctypes.POINTER(ctypes.c_ubyte * (640 * 480 * 4))).contents
                arr = np.frombuffer(buffer, dtype=np.uint8).reshape((480, 640, 4))
                # Convertir a BGR estándar de OpenCV
                bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
                tex.lpVtbl.contents.UnlockRect(frame_struct.pFrameTexture, 0)
                self.kinect.NuiImageStreamReleaseFrame(self.h_stream, p_frame)
                return True, bgr

            self.kinect.NuiImageStreamReleaseFrame(self.h_stream, p_frame)

        return False, None

    def release(self):
        """Libera el sensor y recursos de Windows."""
        if self.is_connected and self.kinect:
            try:
                self.kinect.NuiShutdown()
                if self.h_event:
                    CloseHandle(self.h_event)
            except Exception:
                pass
            self.is_connected = False
            print("[KINECT-DRIVER] Sensor Kinect liberado correctamente.")
