# EditPop Pruebas r3

[Descargar APK para Android ARM64](https://github.com/afernandezchef-source/mio-rae/raw/refs/heads/editpop/download-r3/EditPop-Pruebas-r3.apk)

Aplicación Android nativa basada en la base completa de Concat, con cambios e
identidad de EditPop. Añade propuestas locales de cortes por cambios de escena,
con revisión antes de aplicarlos. Esta entrega no significa que todo el encargo
esté terminado ni que exista paridad con CapCut.

## Instalar en tu Samsung S26

1. Descarga EditPop-Pruebas-r3.apk (86,3 MiB) y ábrela desde Descargas.
2. Elige actualizar EditPop Pruebas. Conserva la misma firma de r1 y r2.
3. Conserva la instalación anterior: desinstalar elimina sus datos privados.

Paquete: cl.kokumix.editpop.concatcandidate. Android 8/API26 o posterior, ARM64.
La instalación en un Samsung S26 físico sigue pendiente. Los proyectos de la
antigua app Kotlin no se migran a esta base de Concat.

## Revisar cortes automáticos

Selecciona un vídeo → Sugerir cortes → espera el análisis → Ver → marca los cortes
deseados → Aplicar cortes marcados. Cerrar o descartar conserva el proyecto.
Deshacer revierte todo el lote y Rehacer lo repone. Los resultados se guardan
como segmentos editables normales.

Todo el análisis es local. Detecta cambios claros de escena, con muestreo
aproximado; puede proponer cero cortes en tomas continuas. No selecciona los
mejores momentos por su significado, no borra contenido ni añade transiciones
por su cuenta. Puedes ajustar cada corte después por fotogramas. Solo admite
vídeo de al menos2 s con velocidad constante positiva y pista desbloqueada.

Para dividir manualmente, toca un punto interior del clip y pulsa Dividir.
Transiciones necesita clips contiguos en la misma pista. Efectos permite aplicar
el catálogo a la selección. [Detalle y límites del detector](CORTES-REVISADOS.md).

## Verificación y límites

Emulador Android11/API30 x86_64: Dividir, Pixelate, Dissolve, guardar/reabrir y
exportar el mismo proyecto mediante los botones de la app a1080p/30fps H.264/AAC.
El recorrido nuevo de propuestas también pasó: descartar sin cambios, marcar,
mostrar el fotograma propuesto, aplicar, deshacer/rehacer todo el lote, reabrir y
exportar. Se comprobó la imagen y el tono de prueba antes y después del corte.
La APK ARM64 pasó compilación, firma e integridad ZIP/ELF16KiB.169 pruebas del
modelo aprobadas. Estas comprobaciones no sustituyen la prueba física en tu S26.

[Pruebas y procedencia](VERIFICACION.md) · [87 requisitos](SEGUIMIENTO-CONCAT.csv).
La reducción específica de grano sigue pendiente. La reducción de ruido de audio
y la estabilización ya tienen código en Concat, pero requieren comprobación móvil
con material adecuado. También faltan pruebas ampliadas de capas/textos, dos
vídeos con imagen y audio externo, interrupciones y ejecución en segundo plano.
Las funciones IA del upstream todavía deben aislarse para la primera versión.
No se descargaron modelos ni se enviaron vídeos personales a las pruebas remotas.
No se ha comprobado TalkBack en Android: declarar etiquetas Slint no demuestra
que el backend Android exponga controles accesibles al sistema.

## Fuente y licencias

[Fuente exacta de la APK](EditPop-Pruebas-r3-fuentes.zip), commit
9504a2e3080fa5e97534463fa643d30f56f42ce3. Se conservan AGPL-3.0-or-later y los avisos
originales de Concat. Se incluyen THIRD_PARTY_NOTICES.md, las licencias de las
dependencias y ffmpeg-8.1.tar.xz, usado por la compilación móvil LGPL.

Para compilar, descomprime la fuente y sigue editpop/README.md, src/README.md y
.github/workflows/editpop-android.yml. Rust1.93.1, JDK17, NDK27.2.12479018,
SDK/build-tools fijados en el workflow. Constructor con al menos16 GiB: esta
necesidad del compilador no es una medición de memoria de la app en el teléfono.
El workflow crea una firma de pruebas propia; la clave privada de esta entrega
no se distribuye. [Hashes](SHA256SUMS.txt).
