# 🎨 Guía de Uso y Conexión: Kinect Xbox 360 con Air Canvas

Esta guía te explica cómo conectar tu sensor **Kinect de Xbox 360 (Modelo 1414)** a tu computadora con Windows y cómo utilizar todos los gestos y funciones del pincel en el aire.

---

## 🔌 1. Conexión del Kinect de Xbox 360 a la PC

El Kinect de Xbox 360 original utiliza un conector especial propietario que combina datos USB y alimentación de 12V.

### Requisitos de Hardware:
1. **Sensor Kinect Xbox 360** (Modelo 1414).
2. **Cable Adaptador USB y Fuente de Poder para PC** (cable con clavija naranja que divide en conector USB y cargador de pared de 12V a la corriente).

### Pasos de Conexión:
1. Conecta el cable del Kinect al extremo del adaptador.
2. Enchufa el adaptador a la toma de corriente eléctrica (el LED del adaptador se iluminará en naranja).
3. Conecta el cable USB a un puerto **USB 2.0 o USB 3.0** directo de tu computadora (evita hubs pasivos sin energía).

---

## 💻 2. Instalación de Controladores (Drivers) en Windows

Para que Windows reconozca el flujo de video del Kinect:

### Opción Recomendada (Oficial de Microsoft):
1. Descarga e instala **Kinect for Windows SDK v1.8** desde la página oficial de Microsoft (o busca *KinectSDK-v1.8-Setup.exe*).
2. Reinicia la PC tras la instalación.
3. El sensor encenderá su LED verde y Windows lo detectará como dispositivo de cámara de video.

> **Nota:** La aplicación cuenta con un selector de cámaras integrado. Si tienes una webcam integrada y el Kinect conectado, puedes presionar las teclas `0`, `1` o `2` en el teclado para alternar entre el Kinect y tu webcam en tiempo real.

---

## ✋ 3. ¿Cómo Usar el Pincel en el Aire? (Gestos y Controles)

El sistema utiliza visión por computadora avanzada (MediaPipe) para rastrear los 21 puntos de tu mano con ultra precisión:

### 1. ☝️ Modo Dibujo (1 Dedo Arriba)
- **Gesto:** Levanta únicamente tu **dedo índice** (como apuntando).
- **Acción:** La punta del dedo actuará como un pincel, trazando líneas continuas y suaves con el color seleccionado.

### 2. ✌️ Modo Selección / Menú (2 Dedos Arriba)
- **Gesto:** Levanta el **dedo índice y el dedo medio** (signo de la paz ✌️).
- **Acción:** Aparecerá una retícula/puntero flotante en la pantalla. En este modo puedes moverte libremente y apuntar a los botones superiores **sin pintar sobre la pantalla**.

### 3. 🎯 Botones en el Aire (Air Buttons)
Para presionar cualquier botón superior con la mano:
- Coloca el puntero del dedo sobre el botón durante **0.4 segundos** (verás una animación de carga circular o barra).
- Al completarse, emitirá un sonido y activará la función.

---

## 🎨 4. Funciones de la Interfaz Superior

| Botón | Función |
| :--- | :--- |
| 🟡 **AMARILLO** | Cambia el color del pincel a **Amarillo Brillante**. |
| 🔵 **AZUL** | Cambia el color del pincel a **Azul Eléctrico**. |
| 🟢 **VERDE** | Cambia el color del pincel a **Verde Neón**. |
| ⏯️ **PAUSAR / DIBUJAR** | Activa o detiene el modo de dibujo (permite mover la mano sin pintar). |
| 📏 **GROSOR** | Alterna entre 4 grosores de trazo: Fino (4px), Medio (8px), Grueso (14px) y Extra (22px). |
| 🧽 **BORRADOR** | Convierte la punta del dedo en un borrador. |
| 🧹 **LIMPIAR** | Borra todo el lienzo al instante. |
| 💾 **GUARDAR** | Guarda una captura en alta resolución en la carpeta `dibujos_guardados/`. |

---

## ⌨️ 5. Atajos de Teclado Rápidos

- `Q` o `ESC` : Salir de la aplicación.
- `C` : Limpiar todo el lienzo.
- `S` : Guardar el dibujo en PNG.
- `D` o `ESPACIO` : Alternar entre Iniciar / Detener el dibujo.
- `M` : Alternar modo de visualización (**Realidad Aumentada sobre cámara** o **Pizarra Digital con miniatura de cámara**).
- `0`, `1`, `2`, `3` : Cambiar índice de cámara/Kinect al instante.

---

## 🚀 6. ¿Cómo Ejecutar el Programa?

Puedes iniciarlo de dos formas:
1. Haciendo doble clic en el archivo [`run_kinect_canvas.bat`](file:///c:/Users/Usuario/Downloads/MenuKinnect/run_kinect_canvas.bat).
2. O ejecutando desde la terminal:
   ```powershell
   python air_canvas.py
   ```
   Si tu Kinect está en el índice 1:
   ```powershell
   python air_canvas.py --camera 1
   ```
