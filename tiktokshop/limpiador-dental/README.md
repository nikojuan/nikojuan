# TikTok Shop · Limpiador dental

Vídeo: `video-tiktokshop-limpiador-dental.mp4` (1080×1920, 30 fps, 27,0 s, H.264 + AAC), con voz en off, música y efectos.

Parte de un vídeo de referencia de 35 s sobre el mismo producto. Se mantiene la misma estructura de escenas
(sarro → cepillo → producto → vibración → "solo en lo duro" → cabezales → manchas → carrito), pero la animación
está dibujada desde cero (`anim.html`), el guion de la voz es nuevo y el estilo es el de Niko (v1).

## Guion de la voz

"Eso amarillo en la base de tus dientes no es suciedad. Es sarro. Y por más que te cepilles, sigue ahí.
Para eso está este limpiador dental. Vibra y va soltando el sarro poquito a poco. Y tranquilo: solo vibra al
tocar lo duro. Si toca la encía, se detiene. Incluye dos puntas: la fina, para entre los dientes, y la plana,
para la cara del diente. También ayuda con las manchas de café y de té. Lo tienes en el carrito naranja."

| Tiempo | Escena | Voz | En pantalla |
|---|---|---|---|
| 0.0–3.3 | Dientes con sarro | "Eso amarillo… no es suciedad" | Gancho **ESO AMARILLO / NO ES SUCIEDAD**, aro sobre el sarro, tarjeta "No es suciedad" |
| 3.3–3.9 | Primer plano del sarro | "Es *sarro*" | Corte con zoom, etiqueta SARRO |
| 3.9–6.0 | Cepillo que pasa | "Y por más que te cepilles, sigue *ahí*" | Tarjeta "Sigue ahí" |
| 6.0–8.3 | Producto | "Para eso está este *limpiador* dental" | Barrido, el aparato sube, zoom a 112 % |
| 8.3–11.0 | La punta sobre el sarro | "Vibra y va soltando el sarro *poquito* a poco" | Ondas, trocitos que saltan, tarjetas "Vibra" y "Suelta el sarro" |
| 11.0–13.8 | Más cerca | "Y tranquilo: solo vibra al tocar lo duro" | Tarjeta "Sarro → vibra" |
| 13.8–15.7 | La punta baja a la encía | "Si toca la encía, se detiene" | Las ondas paran, tarjeta "Encía → se detiene" |
| 15.7–20.7 | Las dos puntas | "Incluye *dos* puntas: la fina… y la plana…" | Etiquetas FINA / PLANA |
| 20.7–23.5 | Manchas | "También ayuda con las *manchas* de café y de té" | Barrido de limpieza, tarjetas Café y Té, aviso "Los resultados pueden variar" |
| 23.5–27.0 | Cierre | "Lo tienes en el carrito naranja" | Botón naranja "Limpiador dental" |

## Sonido
- **Voz:** sintetizada con Piper (`es_MX-claude-high`) a partir de `guion.txt`. Se cortaron las pausas de más de 0,1 s
  (29,7 s → 25,6 s) y se normalizó a −14 LUFS (`assets/voz.wav`). Si Niko graba su propia voz, basta con sustituir
  ese archivo y volver a sacar `timing.json`.
- **Música:** base lo-fi original (`music.py`), unos 20 dB por debajo de la voz; sube en el cierre.
- **Efectos:** `sfx.py`, un *whoosh* en cada barrido y un *pop* en las tarjetas, nunca a menos de 1 s de otro.
- **Mezcla final:** −14,0 LUFS.

## Pendiente de comprobar
- **Afirmaciones del producto.** "Solo vibra al tocar lo duro / se detiene en la encía", las dos puntas y la ayuda con
  las manchas vienen del vídeo de referencia; confírmalas con la ficha del producto antes de publicar.
- **Nombre en el botón.** Pone "Limpiador dental" sin marca. Se cambia en `anim.html` (`#buy`).

## Volver a generarlo
```bash
# fuentes (OFL) desde npm
mkdir fonts && cd fonts
for p in big-shoulders-display archivo instrument-serif; do npm pack @fontsource/$p; done
for f in *.tgz; do tar xzf $f; mv package ${f%.tgz}; done; cd ..
# voz: piper -> cortar pausas (../juego-cama-lazos/voice_edit.py) -> loudnorm -> assets/voz.wav
# timing.json: las palabras de guion.txt con los tiempos de faster-whisper (word_timestamps=True) sobre assets/voz.wav
node render.js fonts timing.json salida.mp4            # vídeo sin sonido (Playwright + ffmpeg)
node render.js fonts timing.json prueba 3.7 12.6       # solo fotogramas de prueba
python3 sfx.py timing.json sfx.wav
python3 music.py musica.wav 27.0 25.5                  # duración, inicio del cierre
ffmpeg -i salida.mp4 -i assets/voz.wav -i musica.wav -i sfx.wav -filter_complex \
  "[1:a]apad[v];[2:a]volume=-13.4dB[m];[3:a]volume=-8dB[s];[v][m][s]amix=inputs=3:normalize=0:duration=longest,volume=-0.8dB,alimiter=limit=0.89,afade=t=out:st=26.5:d=0.5[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -t 27 final.mp4
```
