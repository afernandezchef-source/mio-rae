# Verificación de EditPop Pruebas r3

## Procedencia

- ARM64: fuente9504a2e3080fa5e97534463fa643d30f56f42ce3,
  [run39770421752](https://github.com/afernandezchef-source/mio-rae/actions/runs/39770421752), compilación PASS.
- x86_64: fuentee8ea0fa889735cf3df5c165fd06d82f20614dd89,
  [run39770421244](https://github.com/afernandezchef-source/mio-rae/actions/runs/39770421244).
  Ambos árboles fuente son idénticos. La APK x86 se conservó sin recompilar.
- Regresión final [run39773291471](https://github.com/afernandezchef-source/mio-rae/actions/runs/39773291471), PASS,
  commit de pruebas4339518ba3425fe88a6f4cc01496c194cc0baa0a. Ningún archivo en
  src/crates cambia respecto a la fuente compilada.

El primer run x86 pasó el recorrido de Dividir/efecto/transición/exportación,
pero su prueba nueva se detuvo al intentar localizar Deshacer mediante un árbol
de accesibilidad que NativeActivity no expone. Se corrigió el arnés para pulsar
el icono visible y comprobar el documento. Un intento posterior perdió la conexión
al reiniciar adbd; la repetición final reconecta y verifica el shell del emulador.
La app entregada es la misma: estos ajustes solo afectan al banco de pruebas.
El script final se incluye en pruebas/android-edit-check.py; el ZIP fuente
conserva exactamente el estado del commit compilado, incluido su arnés anterior.

## Resultados

169 pruebas del modelo: cambios sostenidos/destellos, límites, separación,
cuadrícula NTSC, entrada recortada y velocidad2x, aplicación atómica, persistencia
y deshacer/rehacer. Cargo check del objetivo Android ARM64 PASS.

Android11/API30, emulador Pixel6 x86_64, GLES SwiftShader:

- Dividir por pulsación real, Pixelate y Dissolve, guardar/cerrar/reabrir.
- Mismo documento exportado por motor y por botones de la app,1080p30 H.264/AAC,
  BT.709 y rango TV,4s/120fotogramas; publicación final en MediaStore Movies/EditPop.
- Comparación de imagen con controles: error medio efecto2,926/255 y transición
  2,729/255; exportación más cercana al efecto real que al control sin aplicar.
- Propuesta en vídeo vertical sintético rojo/azul con destello: un corte a2s.
  Descartar conserva documento; Ver muestra azul; aplicar crea segmentos0–2 y2–4.
  Deshacer/rehacer y reapertura conservan exactamente el estado esperado.
- Exportación final del proyecto de escenas por UI a galería: decodificación
  estricta, centroRGB[253,0,1]a1s y[1,0,253]a3s; tono440Hz de amplitud0,1252/0,1247,
  audio presente a ambos lados. Ver JSON, PNG y MP4 sintético adjuntos.

La APK ARM64 se firmó con la misma clave de r1/r2, certificadoSHA256
367e653b8cdf0206aeaa6cbf70783a74e084baef418cb3e366f54395bd0b8b2a.
FirmaV2/V3, alineaciónZIP y4bibliotecas ELF16KiB PASS. Las12entradas ajenas a la
firma son idénticas al artefacto de CI. La llave privada no se distribuye.

## Límites y siguiente etapa

No se probó físicamente el Samsung S26. No se afirma paridad con CapCut ni que
estén terminados los87requisitos. Cancelación durante decodificación, segundo
plano, interrupciones y estrés prolongado requieren pruebas específicas.
La revisión muestra un fotograma de cada propuesta, no una reproducción de su
entorno. Las tomas continuas pueden producir cero propuestas. Las transiciones
se añaden manualmente. La selección se reconoce por el color del botón.

Siguiente etapa: verificar reducción de ruido de audio y estabilización en
Android, implementar reducción de grano con comparación antes/después y comprobar
un proyecto con dos vídeos, imagen, audio externo y texto. Después validar en
el teléfono físico. No se enviaron vídeos personales a GitHub ni al emulador remoto.

## Ampliación verificada sobre la misma APK r3

Audio: [run39870369883](https://github.com/afernandezchef-source/mio-rae/actions/runs/39870369883)
PASS. Interruptor real Reducir ruido, guardar/reabrir y exportación UI1080p.
Comparado con el mismo proyecto Android sin filtro: residuo de ruido blanco
baja9,55/8,66dB, tono440Hz cambia+0,015/+0,039dB.

Estabilización: [run39871074587](https://github.com/afernandezchef-source/mio-rae/actions/runs/39871074587)
PASS. Casilla real, análisis120frames/119seguidos, guardar/reabrir y UI1080p.
Vibración sintética de una marca a320×180:6,960→0,404px RMS, ratio0,0581.
Véanse pruebas/audio y pruebas/estabilizacion con controles y exportaciones.
No prueba voz/metraje real, paneos/giros ni teléfono físico.

No cambió la app: APK/hash/firma/fuente se conservan. El script adjunto se
actualiza para reproducir estas comprobaciones. El filtro nuevo de grano
se prepara en un candidato posterior.
