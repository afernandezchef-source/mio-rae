# EditPop Pruebas r2

[Descargar APK para Android ARM64](https://github.com/afernandezchef-source/mio-rae/raw/refs/heads/editpop/download-r2/EditPop-Pruebas-r2.apk)

Actualización para corregir Dividir, acceso a efectos/transiciones y exportación
móvil. Aplicación nativa basada en Concat, con identidad y cambios de EditPop.
Esta candidata no representa todas las funciones terminadas del encargo.

## Instalar en tu Samsung S26

1. Descarga EditPop-Pruebas-r2.apk (86,2 MiB) y ábrela desde Descargas.
2. Elige actualizar EditPop Pruebas. Se conserva la misma firma de r1.
3. No desinstales la app anterior: desinstalar elimina sus datos privados.

El paquete es cl.kokumix.editpop.concatcandidate. Los proyectos de la antigua
base Kotlin siguen separados; esta actualización no los migra.

Para dividir, toca un punto interior del clip en la línea de tiempo y pulsa
Dividir. El nuevo segmento queda seleccionado. Transiciones y Efectos aparecen
junto a Dividir. Las transiciones requieren clips contiguos en la misma pista.
Si el cabezal está en un extremo, la app explica cómo situarlo dentro del clip.

## Qué se comprobó

Emulador Android 11/API 30 x86_64: pulsaciones reales para dividir, aplicar Pixelate
y Dissolve, guardar, cerrar y reabrir. El mismo documento editado se exportó por
el motor y por los botones Exportar de la app a MP4 H.264/AAC a 1080p y 30 fps. Se confirmó
publicación completa en Movies/EditPop,120 fotogramas,4 s, audio presente y etiquetas
BT.709 correctas. Se compararon imágenes con controles sin efecto/sin transición.
La APK ARM64 pasó compilación, firma e integridad ZIP/ELF de 16 KiB. No hubo acceso
físico al Samsung S26. No se afirma equivalencia de rendimiento con CapCut.

[Ver pruebas y pendientes](VERIFICACION.md) · [Seguimiento de 87 criterios](SEGUIMIENTO-CONCAT.csv)

## Pendientes importantes

Cortes automáticos con revisión, reducción específica de grano, evaluación móvil
de reducción de ruido de audio y estabilización, trabajo en segundo plano,
pruebas de interrupciones y el recorrido ampliado con dos vídeos, imagen, audio
y texto. Las funciones IA del upstream aún deben aislarse para la primera versión
solicitada. No se descargaron modelos ni se subieron vídeos privados a estas pruebas.

## Fuente y licencias

[Fuente exacta de la APK](EditPop-Pruebas-r2-fuentes.zip), commit
4efc27da401bc2ba970744890d4b84cbaf2698fd. Build ARM:
https://github.com/afernandezchef-source/mio-rae/actions/runs/39688535227

Prueba x86 del mismo árbol fuente:
https://github.com/afernandezchef-source/mio-rae/actions/runs/39688535246

Se conservan AGPL-3.0-or-later y los avisos de Concat. THIRD_PARTY_NOTICES.md y
DEPENDENCIAS-LICENCIAS.csv identifican dependencias; las licencias de fuentes
tipográficas están en el ZIP fuente. Se incluye el archivo fuente original
ffmpeg-8.1.tar.xz usado por el script de compilación móvil LGPL.

Para compilar, descomprime la fuente y sigue editpop/README.md, src/README.md y
.github/workflows/editpop-android.yml. El workflow fija Rust 1.93.1, JDK 17,
NDK 27.2.12479018 y SDK/build-tools. Requiere un constructor con al menos16 GiB;
el límite del compilador no describe la memoria de la app en el teléfono.
El workflow genera su propia firma de pruebas. La clave privada de la entrega
no se distribuye. [Hashes de los archivos](SHA256SUMS.txt).
