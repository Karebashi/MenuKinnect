@echo off
title Lienzo Magico Kinect Xbox 360 - Air Canvas
cls
echo =====================================================================
echo          LIENZO MAGICO KINECT XBOX 360 - AIR CANVAS PRO
echo =====================================================================
echo.
echo Iniciando el programa de dibujo con el dedo en el aire...
echo.
echo BOTONES EN EL AIRE:
echo   [ ROJO ]  [ AZUL ]  [ VERDE ]  [ INICIAR ]  [ DETENER ]  [ LIMPIAR ]
echo.
echo CONTROLES GESTUALES:
echo   - 1 Dedo (Indice) arriba : DIBUJAR (cuando esta iniciado)
echo   - 2 Dedos arriba         : MODO SELECCION / tocar botones
echo   - Puno cerrado (Fist)    : DETENER dibujo
echo   - Mano abierta           : INICIAR dibujo
echo.
echo ATAJOS DE TECLADO:
echo   - Tecla 'I'              : Invertir / Alternar modo espejo
echo   - Tecla 'C'              : Limpiar lienzo
echo   - Tecla 'K'              : Reconectar a sensor Kinect
echo   - Tecla 'Q' o ESC        : Salir
echo   - Teclas '0', '1', '2'   : Cambiar camara manualmente
echo.
python air_canvas.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrio un error al iniciar. Verifica que Python este instalado.
    pause
)
