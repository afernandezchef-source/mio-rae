# Corrección del recorrido móvil — r2 en verificación

La prueba del usuario en Samsung S26 detectó que Dividir no producía respuesta y
que no podía usar transiciones/efectos. r1 sólo había pasado compilación y arranque;
esos resultados no cubrían edición. Esta corrección mantiene Concat como motor.

| Problema identificado en código | Cambio | Verificación actual |
| --- | --- | --- |
| Tocar un clip en teléfono sólo seleccionaba, dejaba el cabezal en cero; dividir en un extremo era un no-op silencioso. | El tap posiciona el cabezal; una división inválida explica que debe situarse dentro; se selecciona el ID de la cola realmente creada. | Modelo y pulsaciones reales Android API30 aprobados; dos segmentos y mapeo de origen correctos. |
| Una transición aplicada al primer segmento exigía seleccionar su vecino de entrada. | En teléfono cualquiera de los dos lados de una unión válida resuelve al clip de entrada; no se inventan uniones sobre huecos ni entre pistas. | Casos del modelo aprobados; Dissolve aplicado mediante pulsaciones y conservado al reabrir. |
| Las cuatro pistas de escritorio de 80 px podían dejar el vídeo seleccionado debajo del visor de pistas de teléfono. | La geometría de la pista seleccionada se publica y el teléfono la desplaza a la vista al cambiar de selección/geometría. | Compilación ARM/x86 aprobada; clip visible al reabrir, incluidas pistas vacías compactas. |
| Transiciones y efectos del clip estaban al final de una barra extensa. | Se colocan junto a Dividir. Nombres accesibles en controles de teléfono. | Acceso a ambos paneles y aplicación mediante pulsaciones Android comprobados. |
| El estante inicial de efectos mostraba sólo el primer grupo. | Las bibliotecas de teléfono arrancan mostrando todos los grupos. Al aplicar a un clip fuera del cabezal se busca su interior y se confirma la operación. | Pixelate aplicado mediante pulsaciones, visible en el monitor y conservado al reabrir. Comparación de exportación pendiente. |

165 pruebas concat-project aprobadas, sin fallos. Incluyen división, transición,
efecto, deshacer/rehacer y serialización/reapertura, además de las regresiones
originales. Registro: evidence/r2-project-tests.log. No equivalen a prueba de UI.

Fuentes compiladas y firmadas, aún sin publicar actualización:
- ARM64: 71437d54c0e9a943fa20eeb703d46a32cbfe54e0, run39678071346.
- x86_64: f32fc27e375b513dd6f459887710fc8cfe1564b6, run39678071674.
Ambos commits tienen el mismo árbol fuente. Las pruebas posteriores sólo
modifican el script y workflow, no la aplicación compilada.

**Bloqueo inicial, corregido en la compilación siguiente:** los runs39680426318 y39680600905 completaron división,
efecto, transición, guardado y reapertura, pero la exportación de cuatro segundos
a1080p no terminó en300segundos en SwiftShader. No se declara exportación
verificada ni se atribuye el problema al rendimiento del Samsung. El run39682305653
confirmó frame0/120 y la espera dentro de MediaCodec::dequeueInputBuffer,
llamado desde avcodec_send_frame. El renderizador sí terminó el primer frame.
Evidencia: evidence/r2-export-stalled-native-stack.txt y status.json.

Se cambió la inicialización H.264/HEVC MediaCodec para mantener SPS/PPS/VPS en
el primer paquete, que el muxer MP4 de FFmpeg sabe leer. Evita el procedimiento
GLOBAL_HEADER del wrapper (frame ficticio, EOS y flush del codificador). Android
no define flush para codificadores; la espera capturada estaba dentro del NDK,
por lo que la paciencia de10s del bucle Rust no podía interrumpirla. El check
ARM64 pasa. La corrección requiere nueva compilación y prueba Android; aún no
se declara resuelta ni se ha probado HEVC. El diálogo de
exportación y las tareas en segundo plano tampoco están certificados.

El protocolo editpop/tools/android-edit-check.py usa un emulador de pruebas con
adb root y un vídeo sintético. La API de automatización existente se habilita
sólo en los ajustes privados del emulador para crear el proyecto inicial; los
cortes, efectos y transiciones se hacen mediante pulsaciones Android. Se revisa
el documento guardado, se reabre y se exporta ese documento por el motor/API.
Esta última parte no certifica el diálogo de exportación, sus permisos o su
comportamiento en segundo plano. La comparación de fotogramas con controles
sin efecto/sin transición comprueba que el motor no ignore las propiedades.
No hay entradas de prueba ni ajustes de automatización activados en la APK.
Los vídeos del usuario y su clave privada de firma no se envían a CI.

## Exportación resuelta y nueva revisión de color

Run39683762902 (x86b0883fcc, app equivalente a ARM53b12356) aprobó el recorrido
completo de edición y exportación por API:120frames,1920x1080,H264/AAC,4s.
Pixelate y Dissolve se distinguen de sus controles sin efecto/sin transición.
La decodificación estricta local pasó; tono440Hz presente en1sy3s sin silencio.
Run39687957650 aprobó además los botones reales Exportar y la publicación
MediaStore de un proyecto1080p en Movies/EditPop, is_pending=0. No prueba Samsung.

La inspección posterior encontró VUI con primarias/transferencia/matriz0
(reservado/GBR), aunque el codificador recibía BT709. El emulador ignora los
color aspects. Error medio visor/export alrededor de8.7/255, por lo que se
reforzó la prueba. Un diagnóstico local de cambio de etiquetas, SIN recodificar,
redujo el error a2.93/255 (Pixelate) y2.73/255 (Dissolve). Ese archivo modificado
es sólo diagnóstico; no se presenta como salida de una nueva APK.

Corrección nueva pendiente de ejecutar: PacketTags usa los filtros existentes
h264_metadata/hevc_metadata de FFmpeg sobre los paquetes de MediaCodec, y repone
las etiquetas del contenedor. Respeta las primarias, transferencia y rango del
encoder, incluido HDR declarado; no desarrolla un códec ni recodifica. Check
ARM64 aprobado16.12s. H264/BT709 se verificará con una nueva APK; HEVC/HDR no se
declaran comprobados en dispositivo.

La prueba nueva usa proyecto1080p, exige BT709 en todos los campos y rangoTV,
reduce el umbral de error medio a4/255 y exige mayor parecido al resultado
editado que al control. También exporta el mismo documento editado desde los
botones de la app a galería. No hay validación física de SamsungS26.
