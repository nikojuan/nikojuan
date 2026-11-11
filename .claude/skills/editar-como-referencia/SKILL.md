---
name: editar-como-referencia
description: Edita un vídeo de Niko copiando el ritmo, los cortes, los subtítulos y los colores de un vídeo de referencia. Úsala siempre que Niko dé un vídeo para editar junto con un vídeo de referencia ("como este", "igual que la referencia", "mismo estilo").
---

# Editar igual que el vídeo de referencia

Cuando Niko da un vídeo + un vídeo de referencia, el resultado debe tener **el mismo ritmo, los mismos cortes,
los mismos subtítulos y los mismos colores** que la referencia.

## Prioridad frente al estilo de casa (niko-edit-style)
- Para **ritmo, cortes/pausas, subtítulos y colores, manda la referencia**. Esto pasa por encima de la paleta,
  las fuentes y las reglas de corte del estilo de casa.
- Lo demás del estilo de casa sigue igual: formato 9:16, zona segura (sin texto en el 20 % de abajo ni en el
  16 % de la derecha), voz a −14 LUFS, revisar nombres de marca, último subtítulo dentro del vídeo.
- Copiar el **estilo** sí; **no** copiar logos, mascotas, marcas de agua ni gráficos propios del creador
  de la referencia.

## Pasos
1. Analiza la referencia:
   `python3 referencia/analizar_referencia.py REFERENCIA.mp4 trabajo/ref/`
   Saca `perfil.json`, `hoja.jpg` (12 fotogramas) y `subs_*.jpg` (recortes de la franja de subtítulos).
2. **Mira `hoja.jpg` y `subs_*.jpg`** (con Read) y corrige a mano en `perfil.json` → `subtitulos`:
   - `fuente`: la más parecida de `referencia/fuentes/` (archivo-800, montserrat-800/900, anton-400,
     big-shoulders-display-900, instrument-serif-400-italic...). Si falta, baja otra OFL con
     `npm pack @fontsource/<nombre>` y copia el `.woff` a `referencia/fuentes/<nombre>-<peso>.woff`.
   - `tamano` (px sobre 1920 de alto), `mayusculas`, `palabras_por_subtitulo`,
     `palabra_activa`:
       - `caja` = caja de color detrás de la palabra que se dice,
       - `color` = la palabra que se dice cambia de color,
       - `lineas` = caja (`color_caja`) detrás de cada línea, las líneas aparecen una a una, una palabra
         clave por grupo en `color_resalte` (de `palabras_clave` o la más larga); usa `ancho_linea`,
       - `ninguna`,
     `color_texto`, `color_resalte`, `color_texto_en_caja`, `contorno`, `sombra`.
   - Si la referencia tiene gráficos fijos encima (paneles, logos), vuelve a analizar con
     `--excluir x0,y0,x1,y1` (fracciones) para que no cuenten en el color.
   - Comprueba también que `ritmo.cortes` tiene sentido (los cortes detectados de verdad).
3. Transcribe la voz del vídeo nuevo (faster-whisper, `word_timestamps=True`) a
   `[{"w","s","e"}, ...]`. Si HuggingFace está bloqueado, el modelo Whisper small (CTranslate2 int8)
   está en npm en 4 partes: `npm pack @skillninja/shortmovie-telop-model-p0` … `-p3` (solo datos, sin
   scripts). Une `model.bin.part0..3` en `model.bin`, comprueba que el sha256 coincide con `model.sha256`
   (ca732cb1…ce73) y pasa la carpeta a `WhisperModel(...)`. Pasa el audio como array numpy (16 kHz mono):
   la versión de PyAV instalada falla al abrir el archivo directamente. Corrige marcas y términos
   (p. ej. "polyester" → "poliéster"). Si nada funciona, pide la transcripción a Niko.
4. Fotogramas de prueba primero y revísalos:
   `python3 referencia/aplicar_referencia.py trabajo/ref/perfil.json VIDEO.mp4 salida.mp4 --palabras p.json --prueba 1 4 8`
5. Render completo (mismo comando sin `--prueba`). Ajusta `--ancla-y` si el zoom corta la cara y
   `--intensidad-color` (0–1, por defecto 0.7) si el color queda forzado: cuanto más distinta es la luz
   del vídeo frente a la referencia, más baja.

Perfiles ya hechos (reutilizables): `referencia/perfiles/<nombre>/perfil.json`. El vídeo de referencia
no se sube al repositorio (es contenido de otro creador); se trabaja en `trabajo/`, que está en .gitignore.
6. Verifica: analiza `salida.mp4` con `analizar_referencia.py` y compara con la referencia
   (`plano_medio`, `cortes`, `hueco_max_tipico`, `saturacion_media`, `brillo_medio`, `temperatura_r_menos_b`).
7. Informa: duración vieja → nueva, cortes de plano de la referencia vs. los del vídeo, diferencias de
   color, y lo que no se pudo copiar (fuente exacta, animaciones de texto especiales, transiciones raras,
   B-roll que la referencia tiene y el vídeo no).

## Límites
- Si el vídeo de Niko es una sola toma, los "cortes" se hacen con cambios de encuadre (punch-in al 112 %
  alternado) en los mismos tiempos que la referencia, ajustados al inicio de palabra más cercano.
- Las animaciones especiales de la referencia (rebotes de texto, emojis, efectos de transición) no se
  detectan solas: descríbelas y pregunta antes de improvisar.
- Si Niko lo edita en CapCut en vez de con estos scripts, pásale el perfil en claro: duración de plano,
  tiempos de corte, fuente/tamaño/colores de subtítulo y los valores de color.
