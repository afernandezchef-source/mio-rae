# Verificación de EditPop Pruebas r2

Resultado: PASS del recorrido limitado descrito aquí. No se certifica la app
completa ni un Samsung S26 al que no se tuvo acceso.

## Procedencia y entornos

- ARM64 fuente 4efc27da401bc2ba970744890d4b84cbaf2698fd, ejecución 39688535227: compilación
  y controles estructurales aprobados.
- x86_64 fuente 9e9606c10cf287a7fc6f8b43bf8299dc6a38d2ba, ejecución 39688535246: prueba
  completa aprobada. Ambos árboles fuente son idénticos.
- Emulador Android 11/API 30, perfil Pixel 6, OpenGL ES/SwiftShader. No teléfono físico.
- APK firmada con la misma clave persistente de r1;V2/V3, ZIP y4 bibliotecas
  nativas ELF de 16 KiB aprobados. Las12 entradas ZIP ajenas a la firma son idénticas aCI.
- 165 pruebas del modelo aprobadas; sus resultados no sustituyen pruebas del dispositivo.

## Prueba realizada

Vídeo sintético4 s con imagen móvil y tono440 Hz; ningún vídeo privado se subió
al repositorio o aCI. La API local existente sólo prepara el proyecto inicial
y proporciona una exportación de control. Las operaciones se ejecutan por
pulsaciones reales de Android: seleccionar/dividir, Pixelate, Dissolve, guardar,
cerrar y reabrir. Los documentos guardados confirman mapeo temporal, efecto y
transición. También se exporta el mismo documento desde los botones de la app.

Ambos archivos: MP4 H.264/AAC,1920 × 1080,30 fps,120 fotogramas,4 s, rangoTV y
primarias/transferencia/matrizBT.709. Decodificación estricta completa aprobada.
Audio440 Hz presente a 1 s y 3 s en ambas salidas. MediaStore confirma publicación
is_pending=0 en Movies/EditPop/PruebaUI.mp4.

Error medio exportación/visor sobre255: Pixelate2.926 y Dissolve2.729. El archivo
es más parecido al resultado editado que a los controles sin efecto/transición.
H264 tiene pérdidas: no se afirma identidad de píxeles. Evidencia en pruebas/.

## Problemas corregidos

Tap de clip que dejaba el cabezal en cero y división silenciosa; selección del
segmento nuevo; pistas vacías que ocultaban el vídeo; acceso lejano a efectos y
transiciones; selección de la unión desde cualquiera de sus clips; búsqueda del
interior del clip al aplicar efectos. Se evitó el flush de inicialización de
MediaCodec que detenía la exportación y se corrigieron sus etiquetas de color
con filtros de metadatos FFmpeg, sin recodificación adicional.

## Pendientes

Samsung S26 físico; importación real ampliada;720p y formatos/orientaciones/VFR
adicionales; poco espacio y recursos ausentes; cancelación y cierre del proceso;
pantalla bloqueada y segundo plano; deshacer/rehacer por UI; catálogo completo
de efectos; cortes automáticos con revisión; reducción de grano; medición móvil
de limpieza de sonido/estabilización; aislamiento de IA. No se anuncia reanudación
de exportaciones interrumpidas ni paridad con CapCut.

El filtro local de ruido de audio de Concat se probó por separado en host con
ruido sintético: reducción residual 15.23 dB, cambio del tono −0.004 dB. Es diagnóstico
de algoritmo, no evaluación de voz real ni prueba móvil de esa función.
