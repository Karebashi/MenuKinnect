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

> **🎯 Detección Automática:** El programa detecta y selecciona automáticamente la cámara del sensor Kinect como fuente principal de video al iniciar. Si conectas el Kinect después de haber abierto la aplicación, solo presiona la tecla `K` para conectarte a él de inmediato.

---

## ✋ 3. ¿Cómo Usar el Pincel en el Aire? (Gestos y Controles)

El sistema utiliza visión por computadora avanzada (MediaPipe) para rastrear los 21 puntos de tu mano con ultra precisión:

### 1. ☝️ Modo Dibujo (1 Dedo Arriba)
- **Gesto:** Levanta únicamente tu **dedo índice** (como apuntando).
- **Acción:** Traza líneas suaves en el aire con el color activo (Amarillo, Azul o Verde).

### 2. ✊ Detener Dibujo (Puño Cerrado)
- **Gesto:** Cierra la mano formando un **puño** (todos los dedos doblados).
- **Acción:** **Pausa y detiene el dibujo**. Puedes mover la mano libremente por el espacio sin pintar nada.

### 3. 🖐️ Reanudar Dibujo (Mano Abierta)
- **Gesto:** Abre la palma de la **mano completa** (todos los dedos extendidos).
- **Acción:** **Reanuda el modo de dibujo** para que puedas volver a pintar al levantar el dedo índice.

### 4. ✌️ Modo Selección de Botones (2 Dedos Arriba o Tocar en el Aire)
- **Gesto:** Levanta el **dedo índice y el dedo medio** (signo ✌️) o apunta a la barra superior.
- **Acción:** Muestra un puntero/retícula flotante. Mantén el puntero sobre cualquier botón durante **0.4 segundos** para activarlo.

---

## 🎨 4. Botones Flotantes en el Aire

| Botón | Función |
| :--- | :--- |
| 🟡 **AMARILLO** | Cambia el color del pincel a **Amarillo Brillante**. |
| 🔵 **AZUL** | Cambia el color del pincel a **Azul Eléctrico**. |
| 🟢 **VERDE** | Cambia el color del pincel a **Verde Neón**. |
| 🧹 **LIMPIAR** | Borra todo el lienzo al instante. |

---

## ⌨️ 5. Atajos de Teclado Auxiliares

- `Q` o `ESC` : Salir de la aplicación.
- `C` : Limpiar todo el lienzo.
- `K` : Re-escanear y conectar al sensor Kinect.
- `0`, `1`, `2`, `3` : Cambiar índice de cámara manualmente.

---

## 🚀 6. ¿Cómo Ejecutar el Programa?

Haz doble clic en el archivo [`run_kinect_canvas.bat`](file:///c:/Users/Usuario/Downloads/MenuKinnect/run_kinect_canvas.bat) o ejecuta desde la terminal:

```powershell
python air_canvas.py
```
