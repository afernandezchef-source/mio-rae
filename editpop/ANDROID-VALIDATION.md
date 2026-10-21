# Validación de la candidata Android

Estado: pendiente de ejecución. Las pruebas host no sustituyen este protocolo.

## Identificar la instalación

Antes de probar, conservar APK, SHA256, certificado, commit y cambios locales. Ejecutar tools/verify-apk.sh. Con un teléfono de pruebas conectado y autorizado:

```sh
adb shell getprop ro.product.model
adb shell getprop ro.build.version.sdk
adb shell getprop ro.product.cpu.abilist
adb shell getconf PAGE_SIZE
adb install -r /ruta/EditPop-Concat-Candidate.apk
adb shell monkey -p cl.kokumix.editpop.concatcandidate -c android.intent.category.LAUNCHER 1
adb logcat -d -s concat AndroidRuntime > arranque.log
```

La build actual es ARM64. No instalarla como si fuera compatible con un emulador x86_64 sin traducción. No desinstalar la app Kotlin ni borrar sus proyectos.

## Recorrido obligatorio

Usar recursos propios o fixtures con señales verificables: dos vídeos con contadores visibles y tonos diferenciados, una imagen y una pista de audio. Registrar duración, resolución, fps, orientación y SHA256 de cada original.

1. Crear proyecto sin cuenta, sin conexión y con interfaz en español.
2. Importar los cuatro recursos mediante el selector del sistema. Confirmar que nombres repetidos conservan ambas copias y que la interfaz responde durante la copia.
3. Reordenar y recortar los vídeos; dividir en un tiempo anotado y mover el segmento. Registrar posiciones finales para comprobar el comportamiento de los huecos.
4. Añadir imagen superpuesta y texto; ajustar volumen y una transición implementada. Comparar los límites de las capas en reproducción y búsqueda pausada.
5. Guardar, cerrar desde recientes y reabrir. Comprobar textos, capas, efectos, posiciones, volúmenes y duración.
6. Exportar H264/AAC a1080p30. Registrar ajustes, tiempo real, progreso y ubicación publicada. Reproducir desde la galería y otra app.
7. Inspeccionar el archivo con ffprobe y análisis de fotogramas/audio: dimensiones, PTS monótonos, duración, cortes, capas, texto, transición y sincronía de las señales. Conservar archivo y resultados; no declarar éxito solo porque existe un MP4.

## Recuperación y límites

- Cancelar exportación: no publicar un MP4 incompleto; poder editar y exportar otra vez.
- Poco almacenamiento: error accionable y proyecto/originales intactos. Usar almacenamiento limitado de pruebas, sin llenar un teléfono personal.
- Recurso ausente: identificar el recurso y ofrecer recuperación; no sustituirlo silenciosamente.
- Pantalla bloqueada y segundo plano durante exportación: comprobar continuidad o interrupción explicada. No existe aún un servicio foreground adaptado; esta prueba es una puerta pendiente, no una capacidad garantizada.
- Cierre del proceso y reapertura: medir qué estado se recupera. Una exportación interrumpida no se considera reanudable sin implementación y prueba.
- Vídeo vertical, horizontal, rotado, distintas tasas y VFR: comparar orientación, duración y sincronía final con los originales.
- Android8/9: la publicación actual depende de MediaStore de Android10; resolver guardado/compartir alternativo o limitar el soporte anunciado antes de entregar.

Registrar cada caso como aprobado/fallido/no ejecutado, con dispositivo/API, build, pasos, resultado esperado, resultado real y archivos de evidencia. No atribuir a Concat los resultados de la app Kotlin anterior.
