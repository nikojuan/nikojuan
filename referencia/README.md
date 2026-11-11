# Editar un vídeo igual que una referencia

Copia de un vídeo de referencia **el ritmo, los cortes, los subtítulos y los colores**, y los aplica a un vídeo nuevo.

```bash
# 1. Analizar la referencia → perfil.json + hoja.jpg + subs_*.jpg
python3 referencia/analizar_referencia.py referencia.mp4 trabajo/ref/
# 2. Revisar a ojo la sección "subtitulos" de perfil.json (fuente, tamaño, mayúsculas, palabras por subtítulo)
# 3. Fotogramas de prueba
python3 referencia/aplicar_referencia.py trabajo/ref/perfil.json mi_video.mp4 salida.mp4 --palabras palabras.json --prueba 1 4 8
# 4. Vídeo completo (salida.mp4 + salida.mp4.json con el informe y los tiempos de las palabras)
python3 referencia/aplicar_referencia.py trabajo/ref/perfil.json mi_video.mp4 salida.mp4 --palabras palabras.json
```

| Qué se copia | Cómo se mide en la referencia | Cómo se aplica |
|---|---|---|
| **Ritmo / cortes** | Detección de cortes por diferencia de fotogramas → duración de cada plano | Mismas duraciones de plano, en el mismo orden, ajustadas al inicio de palabra más cercano. Con una sola toma: cambios de encuadre (punch-in 112 %) |
| **Pausas** | `silencedetect`: huecos que deja la voz | Se cortan los silencios más largos que el hueco típico de la referencia |
| **Colores** | Curva de cada canal R/G/B (percentiles) + saturación media | Igualación de curvas por canal + ajuste de saturación |
| **Subtítulos** | Posición vertical y colores medidos; fuente, tamaño y palabras por subtítulo revisados en `subs_*.jpg` | Mismo estilo, palabra activa con caja o color |

Requisitos: `ffmpeg`, Python con `numpy` y `Pillow`. Para transcribir solo: `faster-whisper` (si no, pasar `--palabras`).
Fuentes OFL de `@fontsource` en `fuentes/`.

**Probado** con el vídeo de la ropa de cama como referencia y una toma en bruto de 29,7 s (con pausas y un tono azulado):
salió de 21,5 s, con cambios de plano a 2,5 / 5,4 / 8,3 / 9,8 / 13,3 / 16,1 / 18,8 s (referencia: 2,4 / 5,2 / 8,2 / 9,8 / 13,3 / 16,2 / 18,8 s),
saturación 0,124 (ref. 0,123) y brillo 142 (ref. 138).

