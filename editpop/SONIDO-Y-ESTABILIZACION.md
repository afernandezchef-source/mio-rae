# Sonido y estabilización — validación sobre r3

## Ruido de audio: comprobado en Android

La función existente de Concat se activa en la barra del clip: Audio →
Tratamientos → Reducir ruido. Desplaza el panel si hace falta. La fuerza por
omisión es50%; procesa localmente mediante FFmpeg afftdn, sin modelos ni servicios.
Escucha el resultado y ajusta la fuerza según el material. Los originales se
conservan y el filtro queda editable.

Run39870369883, commit de pruebas2eac7db4beae61df0de7454ea6d88c8690f9292f,
PASS. Se reutilizó la APK x86 e8ea0fa de r3; no hubo recompilación ni cambios en
src/crates respecto a la fuente ARM publicada9504a2e.

En Android11/API30 x86_64 se pulsó el interruptor real, se comprobó el filtro en
el proyecto guardado y se reabrió sin cambios. La exportación por UI publicó
MP4H.264/AAC1080p30 en galería, con colorBT.709 y duración4s. Se comparó con otra
exportación del mismo proyecto realizada en Android quitando solo ese filtro.
Ambas pistas AAC son estéreo48kHz, alrededor de192kbit/s.

| Ventana | Reducción de ruido residual | Cambio del tono440Hz |
|---|---:|---:|
|1–2s|9,55dB|+0,015dB|
|2,5–3,5s|8,66dB|+0,039dB|

La señal contiene ruido blanco estacionario y un tono conocido. El residuo se
mide retirando la componente440Hz y el nivel continuo de cada ventana. No es una
medición de calidad de voz, viento, reverberación ni música real. No se probó
físicamente un SamsungS26. No significa que pueda eliminar cualquier ruido.

Artefacto12466535826. Evidencia local en
/workspace/editpop-deliveries/r3-audio-cleanup/android-edit-check.
La reducción específica de grano de imagen es otra función y sigue pendiente.

## Estabilización: comprobada en Android

Editar → Estabilizar (casilla a la izquierda del título). La app mide el movimiento
localmente y conserva el análisis en la caché del proyecto. El zoom puede recortar
los bordes; los controles de suavidad y zoom máximo permanecen editables.

Run39871074587, fuente de pruebasa0d70ddcf4ea2ce392793be9c48f6a8130202b35, PASS.
Se reutilizó la misma APK x86 r3. Se pulsó la casilla real, se midieron120fotogramas
(119con seguimiento), se guardó/reabrió y se exportó por UI a1080p. Un control
separado quitó solo la estabilización del mismo proyecto y se exportó en Android.

La vibración RMS de una marca, medida a320×180 entre0,5y3,5s, pasó de6,960a0,404px:
ratio0,0581, reducción94,2%. La textura y los desplazamientos son sintéticos; esto
no prueba paneos, giros, zooms, obturación móvil, metraje real ni SamsungS26físico.
Artefacto12466073663, evidencia local en
/workspace/editpop-deliveries/r3-stabilization-verified/android-edit-check.
