@echo off
title Lienzo Magico Kinect Xbox 360 - Air Canvas
cls
echo =====================================================================
echo          LIENZO MAGICO KINECT XBOX 360 - AIR CANVAS PRO
echo =====================================================================
echo.
echo Iniciando el programa de dibujo con el dedo en el aire...
echo.
echo CONTROLES RAPIDOS:
echo   - 1 Dedo (Indice) levantado : Modo DIBUJAR
echo   - 2 Dedos levantados        : Modo SELECCIONAR / PUNTERO
echo   - Tecla 'Q' o ESC           : Salir del programa
echo   - Tecla 'C'                 : Limpiar lienzo
echo   - Tecla 'S'                 : Guardar dibujo
echo   - Tecla 'M'                 : Cambiar modo AR / Pizarra
echo   - Teclas '0', '1', '2'      : Cambiar camara/Kinect
echo.
python air_canvas.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrio un error al iniciar. Verifica que Python este instalado.
    pause
)
