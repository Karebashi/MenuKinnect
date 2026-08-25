import subprocess
import json
import os
import cv2

def run_diagnostics():
    print("=" * 60)
    print("        DIAGNOSTICO DE KINECT XBOX 360 Y CAMARAS")
    print("=" * 60)

    # 1. Probar PyGrabber (DirectShow Video Devices)
    print("\n1. Dispositivos DirectShow detectados por OpenCV/PyGrabber:")
    try:
        from pygrabber.dshow_graph import FilterGraph
        graph = FilterGraph()
        devices = graph.get_input_devices()
        if devices:
            for idx, dev in enumerate(devices):
                print(f"   [Cam {idx}] {dev}")
        else:
            print("   [!] No se encontraron dispositivos DirectShow.")
    except Exception as e:
        print(f"   [!] Error al consultar DirectShow: {e}")

    # 2. Probar cv2.VideoCapture indices 0..5
    print("\n2. Prueba de apertura con OpenCV (cv2.VideoCapture):")
    for i in range(5):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            print(f"   [Indice {i}] DISPONIBLE - ret={ret}, resolucion={frame.shape if ret else 'N/A'}")
            cap.release()
        else:
            print(f"   [Indice {i}] No disponible")

    # 3. Consultar Dispositivos USB y PnP de Windows
    print("\n3. Escaneando dispositivos USB/PnP de Windows:")
    ps_script = "Get-PnpDevice | Select-Object Status, Class, FriendlyName, InstanceId | ConvertTo-Json"
    with open("temp_pnp.ps1", "w", encoding="utf-8") as f:
        f.write(ps_script)

    res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "temp_pnp.ps1"], capture_output=True, text=True)
    if os.path.exists("temp_pnp.ps1"):
        os.remove("temp_pnp.ps1")

    if res.stdout:
        try:
            data = json.loads(res.stdout)
            found = False
            for d in data:
                name = str(d.get("FriendlyName") or "")
                iid = str(d.get("InstanceId") or "")
                cls = str(d.get("Class") or "")
                status = str(d.get("Status") or "")
                # Microsoft Kinect Xbox 360 VID=045E, PID=02AE (Camera), 02AD (Audio), 02B0 (Motor)
                is_kinect_id = any(pid in iid.upper() for pid in ["045E", "02AE", "02AD", "02B0", "02C2", "02BF"])
                is_kinect_name = any(k in name.lower() for k in ["kinect", "xbox", "nui", "primesense"])
                if is_kinect_id or is_kinect_name:
                    found = True
                    print(f"   -> [ENCONTRADO] Status: {status} | Clase: {cls} | Nombre: {name} | HardwareID: {iid}")

            if not found:
                print("   [!] NO se detecto ningun dispositivo Kinect en el bus USB de Windows.")
                print("   Posibles razones:")
                print("   - El cable de corriente de 12V del Kinect no esta enchufado a la pared.")
                print("   - El cable USB no esta conectado a un puerto USB directo.")
                print("   - Faltan los drivers del 'Kinect for Windows SDK 1.8'.")
        except Exception as e:
            print(f"   [!] Error parseando datos PnP: {e}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    run_diagnostics()
