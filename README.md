# EditPop Pruebas r4

[Descargar APK ARM64 para Android](https://github.com/afernandezchef-source/mio-rae/raw/refs/heads/editpop/download-r4/EditPop-Pruebas-r4.apk) · 86,3MiB

Aplicación Android nativa basada en Concat completo, con identidad propia y
filtro nuevo de reducción de grano. Funciona sin cuenta para proyectos locales.
No se afirma que todo el encargo esté terminado ni que exista paridad con CapCut.

## Instalar y probar

Actualiza EditPop Pruebas conservando la instalación anterior y sus proyectos.
Paquete cl.kokumix.editpop.concatcandidate, Android8/API26 o posterior, ARM64.
La app Kotlin anterior tiene otro paquete: sus proyectos no se migran.
El SamsungS26 físico sigue pendiente de prueba.

1. Crea un proyecto e importa un vídeo desde el teléfono.
2. Selecciona el clip y coloca el cabezal dentro de él; pulsa Dividir.
3. Para añadir una transición, usa dos segmentos contiguos en la misma pista.
4. Efectos → Buscar → grano → Reducir grano. Ajusta Intensidad y revisa los detalles.
5. Audio → Tratamientos → Reducir ruido para ruido estacionario del sonido.
6. Editar → Estabilizar (casilla a la izquierda del título) para analizar movimiento.
7. Guarda, reabre y exporta1080p; revisa también el archivo de la galería.

Puedes combinar estas funciones, pero su efecto sobre texturas, recorte y sonido
depende del material. Los originales se conservan. Los resultados publicados
usan medios sintéticos; no equivalen a una prueba de tus vídeos ni del S26.

## Cortes automáticos con revisión

Selecciona un vídeo → Sugerir cortes → Ver → marca las propuestas → Aplicar.
Cerrar o descartar conserva el proyecto. Deshacer revierte el lote completo.
El detector local busca cambios claros de escena; una toma continua puede dar
cero propuestas. No selecciona mejores momentos por significado ni aplica
transiciones automáticamente. [Uso y límites](CORTES-REVISADOS.md).

## Funciones verificadas y pendientes

Android11/API30 x86_64: Dividir, Pixelate, Dissolve, propuestas revisables de
cortes, deshacer/rehacer, guardar/reabrir y exportar1080p pasaron sobre r4.
El filtro de grano pasó desde los controles reales hasta el archivo final:
ruido sintético reducido40–42%, borde conservado, error visor/exportación1,148/255.
El tiempo en GPU de software fue de varios minutos para4s de vídeo; no representa
el rendimiento de tu teléfono. [Pruebas y límites](VERIFICACION.md).
Los resultados anteriores se conservan separados en pruebas/r3 y
[Sonido y estabilización](SONIDO-Y-ESTABILIZACION.md).
[Reducción de grano](REDUCCION-DE-GRANO.md) · [87 requisitos](SEGUIMIENTO-CONCAT.csv).

Falta prueba física en SamsungS26, recorrido ampliado de dos vídeos con imagen,
audio externo y texto, interrupciones, segundo plano y estrés prolongado.
Las funciones IA de upstream siguen pendientes de aislamiento y validación.
No se enviaron vídeos personales ni la clave de firma a GitHub o a los emuladores.

## Fuente y licencias

Se conservan AGPL-3.0-or-later, los avisos de Concat y las licencias de dependencias.
Se incluye la fuente de FFmpeg8.1 utilizada por la compilación móvil LGPL.
[Fuente exacta de la APK](EditPop-Pruebas-r4-fuentes.zip), commit
6e40dffa96a324c6a12618043839b0e6c2c42a05. [Hashes](SHA256SUMS.txt).
[Arquitectura](ARQUITECTURA.md) · [Prueba en SamsungS26](PRUEBA-SAMSUNG-S26.md).
Para compilar: Rust1.93.1, JDK17, NDK27.2.12479018 y herramientas Android fijadas
en .github/workflows/editpop-android.yml. Se necesita un constructor de al menos
16GiB; ese requisito del compilador no mide la memoria de la app en el teléfono.
La clave privada de esta entrega no se distribuye.
