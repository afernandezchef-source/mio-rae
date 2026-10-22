# Cortes de escena con revisión — candidato r3

Se amplía la base completa de Concat. Esta función es código propio; no usa el
motor, los servicios ni recursos privados de CapCut. Se conserva r2 publicada
como versión anterior comprobada. Un candidato no se considera verificado por
tener código o compilar.

## Recorrido

Seleccionar un vídeo → Sugerir cortes → esperar el progreso → Ver cada propuesta
en el visor → marcar los cortes deseados → Aplicar cortes marcados. Ningún corte
se marca automáticamente. Descartar/cerrar cancela el análisis y deja intacta la
edición. Aplicar utiliza `Command::Batch` y deshacer restaura toda la operación.
Los cortes se guardan como segmentos normales del proyecto; no se crea un formato
de proyecto nuevo ni se modifican los originales. No se elimina material ni se
añaden transiciones automáticamente.

## Análisis y límites

- Local, sin modelos, pagos, red ni permisos adicionales.
- Solo el vídeo seleccionado, desbloqueado, de al menos 2 s y con velocidad
  constante positiva. Se respetan su entrada de origen y su velocidad. Las curvas
  de velocidad se rechazan explícitamente.
- Lectura mediante el decodificador existente de Concat, con sus timestamps de
  origen; se solicitan imágenes pequeñas con cobertura de 64×36, conservando la proporción (sin bandas negras). La lista conserva histogramas
  RGB de 24 valores, no fotogramas. Caché propia de 1 MiB y un lector. Esto no
  establece un límite total de memoria: el códec también necesita sus buffers.
- Como máximo 1.200 muestras; intervalo mínimo 250 ms, mayor para clips largos.
  Una propuesta es aproximada y se puede ajustar después por fotogramas. No es
  comprensión semántica, reconocimiento de voz ni detección de silencios.
- Distancia RGB normalizada, umbral 0,35 y estabilidad anterior/posterior 0,25.
  Rechaza destellos de una sola muestra, pero no garantiza detectar todas las
  escenas ni distinguir un cambio de luz de un corte.
- Máximo 12 propuestas, separadas al menos 1 s entre sí y de los extremos.
  Se ajustan a la cuadrícula de fotogramas del proyecto, incluidas tasas racionales.
- Se analiza el archivo fuente, antes de efectos y superposiciones.
- El trabajo ocurre fuera del hilo de interfaz. Cancelación entre lecturas; una
  lectura en curso debe finalizar. Un token y la revisión del documento evitan
  resultados de trabajos antiguos. Editar, abrir/cerrar proyecto o cerrar el panel
  descarta el análisis pendiente. Los errores no alteran la edición.

## Verificación

Las pruebas del modelo cubren cambio sostenido frente a destello, extremos,
tiempos inválidos, cuadrícula NTSC, cortes descendentes sin duplicados y aplicación
con entrada recortada/velocidad 2×, preservación de propiedades, serialización y
deshacer/rehacer de todo el lote. Resultado local inicial: 169 pruebas aprobadas.

`EDITPOP_TEST_SCENARIO=scene-cuts` en `android-edit-check.py` prepara un vídeo
sintético rojo/azul de 4 s con destello breve y tono de 440 Hz. La API solo crea el
proyecto inicial; la propuesta, descarte, selección, vista previa, aplicación y
deshacer/rehacer se realizan con controles Android reales. Después se reabre y
exporta a 1080p, verificando publicación, duración, pistas y decodificación.
Esta prueba está preparada, pendiente de ejecución para el candidato. No hay
acceso físico al Samsung S26.

La limpieza de audio, la estabilización y la reducción de grano mantienen sus
propios pendientes; esta función no demuestra que estén verificadas en Android.
