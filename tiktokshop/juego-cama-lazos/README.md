# TikTok Shop · Juego de ropa de cama con lazos en relieve

Vídeo: `video-tiktokshop-juego-cama-lazos.mp4` (1080×1920, 30 fps, 21,9 s, H.264 + AAC), con voz en off, música y efectos.

## Análisis del producto

**Lo que se ve en las fotos:** funda nórdica + fundas de almohada con un bordado tipo *tufted* (chenilla) en relieve.
Hay dos colores: beige/arena y blanco. Ambiente "hotel minimalista": ratán, plantas y luz natural.

**Puntos de venta, de más a menos fuerte en vídeo:**
1. **Textura en relieve.** Es lo que para el scroll. El zoom de la foto 1/10 es el plano más fuerte.
2. **Calidad de hotel / estética.** Encaja con la tendencia *clean girl* / *coquette* de los lazos.
3. **Práctico:** lavable a máquina, transpirable, suave, para todo el año.
4. **8 tamaños + 2 colores.** Quita la objeción de "¿hay para mi cama?".
5. **Idea de regalo:** estrenar casa, cumpleaños, Navidad (el vídeo sale en noviembre, en plena temporada).

**Riesgos que hay que vigilar (devoluciones y reseñas):**
- **"Mariposas" vs. lazos.** El título dice *estampado de mariposas*, pero el dibujo son **lazos/moños**.
  El vídeo dice "lazos" para no prometer algo que no es. Recomiendo añadir "lazos" al título:
  *"Juego de funda nórdica con lazos en relieve (estilo coquette)…"*. Se puede dejar "mariposa" en las palabras clave.
- **Relleno no incluido.** La propia ficha lo avisa ("Edredón no incluido / Sin relleno de almohada").
  El vídeo lo dice claramente en 16–19 s para evitar devoluciones.
- **¿Sábanas?** El título dice "sábanas", pero las fotos solo muestran la funda y las fundas de almohada.
  Confirma con el proveedor si incluye sábana bajera/encimera. El vídeo dice "Funda + fundas" para no prometer de más.
- **Color.** La ficha avisa de que el color varía con la luz. No se ha tocado el color de las fotos.
- **Material.** Es fibra de poliéster: no decir "algodón".

## Guion (sincronizado con la voz)

Los cortes, los subtítulos, las tarjetas y los zooms caen en la palabra que se está diciendo (ver `timing.json`).

| Tiempo | Plano | Voz / texto | Movimiento |
|---|---|---|---|
| 0.0–2.3 | Cama blanca | Gancho **TU CAMA / NIVEL HOTEL** · "Mira este juego" | Gancho que entra de golpe a los 0.1 s, empuje lento |
| 2.3–5.3 | Beige + círculo de detalle | "Los lazos van / en *relieve* / se sienten al tocarlos" | Barrido · *pop* del círculo · zoom a 112 % en "relieve" |
| 5.3–8.3 | Beige con cojines | Tarjetas 1 Suave · 2 Transpirable · 3 Para todo el año | Cada tarjeta entra con su palabra · empuje lento |
| 8.3–9.7 | Funda | ✓ Lavable a máquina · "Va directo / a la lavadora" | Zoom a 112 % en "lavadora" |
| 9.7–13.2 | Beige ambiente | Tarjetas 8 tamaños · Blanco o beige · "Calidad de *hotel* / en ocho tamaños / blanco o beige" | Empuje lento |
| 13.2–16.2 | Beige, lateral | Tarjetas Funda + fundas · ! Relleno no incluido · "Ojo: es la funda / el relleno / no viene incluido" | Zoom a 112 % en "no" |
| 16.2–18.8 | Cama blanca, otro encuadre | "El regalo *perfecto* / para estrenar casa" | Empuje lento |
| 18.8–21.9 | Fondo Ink + miniatura | **TOCA EL CARRITO** (entra con "Toca") · "y elige tu tamaño" | *Pop* · la música sube al acabar la voz |

## Texto para publicar

**Descripción:**
> Tu cama nivel hotel 🤍 Funda nórdica con lazos en relieve, súper suave y lavable a máquina. Blanco o beige, 8 tamaños. Ojo: relleno no incluido. El regalo perfecto 🎁

**Hashtags:** #tiktokshop #ropadecama #decoracionhogar #dormitorio #fundanordica #coquette #lazos #regalosnavidad #hogar #roomdecor

**Guion de la voz:**
"¿Tu cama nivel hotel? Mira este juego. Los lazos van en relieve, se sienten al tocarlos. Suave, transpirable y para todo el año. Va directo a la lavadora. Calidad de hotel en ocho tamaños, blanco o beige. Ojo, es la funda, el relleno no viene incluido. El regalo perfecto para estrenar casa. Toca el carrito y elige tu tamaño."

## Sonido
- **Voz:** la grabación que mandó Niko (`assets/voz_original.wav`). Se cortó el "Cero segundos" del principio (la app leyó la marca de tiempo del guion) y todas las pausas de más de 0.1 s (`voice_edit.py`): pasa de 29.7 s a 21.0 s. Lleva una reducción de ruido suave y está normalizada a −14 LUFS.
- **Música:** base lo-fi **original** de `music.py`, libre de derechos, a unos −20 dB por debajo de la voz. Sube +3 dB cuando termina la voz, en el cierre.
- **Efectos:** un *whoosh* en cada barrido y un *pop* en el gancho y en la primera tarjeta, nunca a menos de 1 s de otro efecto.
- **Mezcla final:** −14.7 LUFS, con un limitador en los picos.

## Volver a generarlo
```bash
# fuentes (OFL) desde npm
mkdir fonts && cd fonts
for p in big-shoulders-display archivo instrument-serif; do npm pack @fontsource/$p; done
for f in *.tgz; do tar xzf $f; mv package ${f%.tgz}; done; cd ..
# voz: cortar el "cero segundos" (antes de 3.5 s) y las pausas; luego re-transcribir
# el audio cortado (faster-whisper, word_timestamps=True) para obtener timing.json
python3 voice_edit.py assets/voz_original.wav assets/voz_original_words.json voz.wav tmp_timing.json --start 3.5
ffmpeg -i voz.wav -af "afftdn=nf=-30,loudnorm=I=-14:TP=-2:LRA=7" -ar 48000 voz_n.wav
python3 render.py assets fonts timing.json salida.mp4          # vídeo + efectos (salida.mp4.sfx.wav)
python3 render.py assets fonts timing.json salida.mp4 1.5 8.5  # solo fotogramas de prueba
python3 music.py musica.wav 21.88 20.88                         # duración, inicio del cierre
ffmpeg -i salida.mp4 -i voz_n.wav -i musica.wav -i salida.mp4.sfx.wav -filter_complex \
  "[1:a]apad[v];[2:a]volume=-13.4dB[m];[3:a]volume=-8dB[s];[v][m][s]amix=inputs=3:normalize=0:duration=longest,alimiter=limit=0.89[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -t 21.88 final.mp4
```
`assets/` guarda los recortes de las capturas, sin la interfaz de la app ni los textos de la ficha (el aviso, los iconos, la lavadora y las muestras de color).
