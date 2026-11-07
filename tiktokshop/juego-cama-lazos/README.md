# TikTok Shop · Juego de ropa de cama con lazos en relieve

Vídeo: `video-tiktokshop-juego-cama-lazos.mp4` (1080×1920, 30 fps, 26 s, H.264 + AAC).

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

## Guion (lo que aparece en pantalla)

| Tiempo | Plano | Texto | Movimiento |
|---|---|---|---|
| 0.0–3.2 | Cama blanca | Gancho **TU CAMA / NIVEL HOTEL** · "Mira este juego / de ropa de cama" | Gancho que entra de golpe a los 0.1 s (110→100 %), empuje lento |
| 3.2–6.4 | Cama beige + círculo de detalle | "Lazos en *relieve* / que se sienten" | Barrido rápido · el círculo aparece con *pop* · zoom a 112 % |
| 6.4–9.8 | Beige con cojines | Tarjetas 1 Suave · 2 Transpirable · 3 Para todo el año · "Suave y fresca / todo el año" | Tarjetas escalonadas 120 ms |
| 9.8–12.8 | Funda (sin la lavadora) | Tarjeta ✓ Lavable a máquina · "Directo a la lavadora / sin miedo" | Zoom a 112 % |
| 12.8–16.0 | Beige ambiente | Tarjetas 8 tamaños · Blanco o beige · "Calidad de *hotel* / en 8 tamaños" | Empuje lento |
| 16.0–19.4 | Beige, lateral | Tarjetas Funda + fundas · ! Relleno no incluido · "Ojo: es la funda / relleno no incluido" | Zoom a 112 % |
| 19.4–22.6 | Cama blanca, otro encuadre | "El regalo *perfecto* / para estrenar casa" | Empuje lento |
| 22.6–26.0 | Fondo Ink + miniatura | **TOCA EL CARRITO** · "Elige tu tamaño" | *Pop* de la tarjeta final |

## Texto para publicar

**Descripción:**
> Tu cama nivel hotel 🤍 Funda nórdica con lazos en relieve, súper suave y lavable a máquina. Blanco o beige, 8 tamaños. Ojo: relleno no incluido. El regalo perfecto 🎁

**Hashtags:** #tiktokshop #ropadecama #decoracionhogar #dormitorio #fundanordica #coquette #lazos #regalosnavidad #hogar #roomdecor

**Guion de voz opcional** (si quieres grabarte encima, ~24 s):
"¿Tu cama nivel hotel? Mira este juego. Los lazos van en relieve, se sienten al tocarlos. Es suave, transpirable y sirve para todo el año. Va directo a la lavadora. Hay ocho tamaños, en blanco o beige. Ojo: es la funda, el relleno no viene incluido. Y es el regalo perfecto. Toca el carrito y elige tu tamaño."

## Sonido
- **Música:** una base lo-fi / pop minimalista **original**, compuesta por código con `music.py` (piano eléctrico, bajo, batería y campanita; Fa–Mi–Re–Do a 75 BPM). Es libre de derechos porque no usa ninguna canción existente. En el cierre (22.6 s) sube unos +3 dB y termina con un fundido.
- **Efectos:** un *whoosh* en cada barrido y un *pop* en el gancho y en cada grupo de tarjetas, nunca más de uno por segundo.
- **Mezcla final** normalizada a unos −14 LUFS, con picos por debajo de −1.5 dBTP.
- **Sin voz.** Si grabas el guion de voz, baja la música hasta que quede unos −20 dB por debajo de la voz. También puedes cambiarla por un sonido en tendencia de TikTok desde la app.

## Volver a generarlo
```bash
# fuentes (OFL) desde npm
mkdir fonts && cd fonts
for p in big-shoulders-display archivo instrument-serif; do npm pack @fontsource/$p; done
for f in *.tgz; do tar xzf $f; mv package ${f%.tgz}; done; cd ..
python3 render.py assets fonts salida.mp4            # vídeo + efectos (salida.mp4.sfx.wav)
python3 music.py musica.wav 26                       # música original
ffmpeg -i salida.mp4 -i musica.wav -i salida.mp4.sfx.wav -filter_complex \
  "[1:a]volume=-6dB[m];[2:a]volume=-2dB[s];[m][s]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k final.mp4
python3 render.py assets fonts salida.mp4 1.5 8.5    # solo fotogramas de prueba
```
`assets/` guarda los recortes de las capturas, sin la interfaz de la app ni los textos de la ficha (el aviso, los iconos, la lavadora y las muestras de color).
