# TikTok Shop · Limpiador dental

Vídeo: `video-tiktokshop-limpiador-dental.mp4` (1080×1920, 30 fps, 25,0 s, H.264 + AAC), con voz en off, música y efectos.

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
| 0.0–2.9 | Dientes con sarro | "Eso amarillo… no es suciedad" | Gancho **ESO AMARILLO / NO ES SUCIEDAD**, aro sobre el sarro, tarjeta "No es suciedad" |
| 2.9–3.5 | Primer plano del sarro | "Es *sarro*" | Corte con zoom, etiqueta SARRO |
| 3.5–5.4 | Cepillo que pasa | "Y por más que te cepilles, sigue *ahí*" | Tarjeta "Sigue ahí" |
| 5.4–7.3 | Producto | "Para eso está este *limpiador* dental" | Barrido, el aparato sube, zoom a 112 % |
| 7.3–9.7 | La punta sobre el sarro | "Vibra y va soltando el sarro *poquito* a poco" | Ondas, trocitos que saltan, tarjetas "Vibra" y "Suelta el sarro" |
| 9.7–12.1 | Más cerca | "Y tranquilo: solo vibra al tocar lo duro" | Tarjeta "Sarro → vibra" |
| 12.1–14.0 | La punta baja a la encía | "Si toca la encía, se detiene" | Las ondas paran, tarjeta "Encía → se detiene" |
| 14.0–18.7 | Las dos puntas | "Incluye *dos* puntas: la fina… y la plana…" | Etiquetas FINA / PLANA |
| 18.7–21.3 | Manchas | "También ayuda con las *manchas* de café y de té" | Barrido de limpieza, tarjetas Café y Té, aviso "Los resultados pueden variar" |
| 21.3–25.0 | Cierre | "Lo tienes en el carrito naranja" | Botón naranja "Limpiador dental" |

## Sonido
- **Voz:** sintetizada con Piper (`es_ES-sharvard-medium`, locutor 0: voz masculina de España), frase a frase a partir
  de `guion.txt`, quedándose con la toma que mejor se entiende; "carrito" se escribe "carrrito" para que marque la erre.
  Pausas recortadas y normalizada a −14 LUFS (`assets/voz.wav`, 23,2 s). El audio de muestra que mandó Niko (otra voz
  leyendo otro anuncio) solo sirvió de referencia de tono y ritmo: no se clonó. Para usar una grabación propia basta con
  sustituir ese archivo y volver a sacar `timing.json`.
- **Música:** base lo-fi original (`music.py`), unos 20 dB por debajo de la voz; sube en el cierre.
- **Efectos:** `sfx.py`, un *whoosh* en cada barrido y un *pop* en las tarjetas, nunca a menos de 1 s de otro.
- **Mezcla final:** unos −14 LUFS.

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
python3 music.py musica.wav 25.0 23.2                  # duración, inicio del cierre
ffmpeg -i salida.mp4 -i assets/voz.wav -i musica.wav -i sfx.wav -filter_complex \
  "[1:a]apad[v];[2:a]volume=-13.4dB[m];[3:a]volume=-8dB[s];[v][m][s]amix=inputs=3:normalize=0:duration=longest,volume=0.7dB,alimiter=limit=0.89,afade=t=out:st=24.5:d=0.5[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -t 25 final.mp4
```
