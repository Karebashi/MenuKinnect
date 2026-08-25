import ctypes
from ctypes import wintypes
import numpy as np
import cv2
import time

# Constantes del SDK de Kinect v1.8
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

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
CreateEvent = kernel32.CreateEventW
CreateEvent.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
CreateEvent.restype = wintypes.HANDLE

def test_kinect():
    print("Cargando Kinect10.dll...")
    kinect = ctypes.WinDLL("Kinect10.dll")

    kinect.NuiInitialize.argtypes = [ctypes.c_ulong]
    kinect.NuiInitialize.restype = ctypes.c_long

    kinect.NuiShutdown.argtypes = []
    kinect.NuiShutdown.restype = None

    kinect.NuiImageStreamOpen.argtypes = [
        ctypes.c_int,           # eImageType
        ctypes.c_int,           # eResolution
        ctypes.c_ulong,         # dwImageFrameFlags
        ctypes.c_ulong,         # dwFrameLimit
        wintypes.HANDLE,        # hNextFrameEvent
        ctypes.POINTER(wintypes.HANDLE) # phStreamHandle
    ]
    kinect.NuiImageStreamOpen.restype = ctypes.c_long

    kinect.NuiImageStreamGetNextFrame.argtypes = [
        wintypes.HANDLE,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.POINTER(NUI_IMAGE_FRAME))
    ]
    kinect.NuiImageStreamGetNextFrame.restype = ctypes.c_long

    kinect.NuiImageStreamReleaseFrame.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(NUI_IMAGE_FRAME)
    ]
    kinect.NuiImageStreamReleaseFrame.restype = ctypes.c_long

    print("Inicializando NuiInitialize...")
    hr = kinect.NuiInitialize(NUI_INITIALIZE_FLAG_USES_COLOR)
    if hr != 0:
        print(f"NuiInitialize error: {hex(hr & 0xFFFFFFFF)}")
        return

    h_event = CreateEvent(None, True, False, None)
    h_stream = wintypes.HANDLE()

    print("Abriendo NuiImageStreamOpen...")
    hr = kinect.NuiImageStreamOpen(
        NUI_IMAGE_TYPE_COLOR,
        NUI_IMAGE_RESOLUTION_640x480,
        0,
        NUI_IMAGE_STREAM_FRAME_LIMIT_MAXIMUM,
        h_event,
        ctypes.byref(h_stream)
    )

    if hr != 0:
        print(f"NuiImageStreamOpen error: {hex(hr & 0xFFFFFFFF)}")
        kinect.NuiShutdown()
        return

    print("Flujo de color de Kinect abierto con exito! Stream Handle:", h_stream.value)

    print("Leyendo 10 fotogramas del sensor Kinect...")
    for i in range(10):
        p_frame = ctypes.POINTER(NUI_IMAGE_FRAME)()
        hr = kinect.NuiImageStreamGetNextFrame(h_stream, 1000, ctypes.byref(p_frame))
        if hr == 0:
            frame_struct = p_frame.contents
            tex = frame_struct.pFrameTexture.contents
            locked_rect = NUI_LOCKED_RECT()
            hr_lock = tex.lpVtbl.contents.LockRect(frame_struct.pFrameTexture, 0, ctypes.byref(locked_rect), None, 0)
            if hr_lock == 0:
                buffer = ctypes.cast(locked_rect.pBits, ctypes.POINTER(ctypes.c_ubyte * (640 * 480 * 4))).contents
                arr = np.frombuffer(buffer, dtype=np.uint8).reshape((480, 640, 4))
                bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
                print(f"   [Frame {i+1}] CAPTURADO OK! Res: {bgr.shape}, Brillo promedio: {np.mean(bgr):.1f}")
                tex.lpVtbl.contents.UnlockRect(frame_struct.pFrameTexture, 0)
            kinect.NuiImageStreamReleaseFrame(h_stream, p_frame)
        else:
            print(f"   [Frame {i+1}] Esperando... (hr={hex(hr & 0xFFFFFFFF)})")
        time.sleep(0.05)

    print("Cerrando sensor Kinect...")
    kinect.NuiShutdown()
    print("Todo funciono a la perfeccion!")

if __name__ == "__main__":
    test_kinect()
