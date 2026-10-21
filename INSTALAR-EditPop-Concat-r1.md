# EditPop sobre Concat — primera candidata ARM64

APK: **EditPop-Concat-Android-arm64-r1.apk**,90.346.615bytes (aprox.86,2MiB).
Nombre en Android: **EditPop Pruebas**.

Esta APK sí está construida a partir de Concat y su motor. Compiló en un runner
con15,6GiB RAM y3GiB swap; el compilador alcanzó aproximadamente13,9GiB RSS. La
compilación ARM64 duró14min03s. Ese tiempo y memoria son del compilador, no una
medida del consumo ni de la velocidad de edición en el celular.

## Instalar en el Samsung S26

1. Descargar la APK al teléfono y abrirla desde Descargas.
2. Si Android lo pide, habilitar la instalación desde la app que abre ese archivo.
3. Abrir **EditPop Pruebas** y crear un proyecto de prueba.
4. Importar los vídeos mediante el selector de Android y comprobar visor,
   recorte/división, audio, transición, guardado/reapertura y exportación.

El paquete es `cl.kokumix.editpop.concatcandidate`, distinto del EditPop nativo
anterior. Ambas apps mantienen proyectos separados. No hay migración automática
de los proyectos Kotlin; los originales se mantienen en su aplicación.

## Comprobado y pendiente

Comprobado: compilación completa ARM64, hashes del artefacto de GitHub, firmaAPKv2
yv3, identidad, ABI, alineaciónZIP16KiB y segmentosELF16KiB de las cuatro
bibliotecas. La APK final usa una clave de pruebas persistente guardada fuera
del repositorio. Sus12entradas de contenido ajenas a META-INF son idénticas a
las del artefacto compilado en CI; sólo cambió la firma.

La comprobación de arranque sobre otra build nativa x86_64/Android 11 pasó:
60 segundos con la actividad visible, sin errores fatales ni ANR registrados.
Se inspeccionó la captura de la pantalla inicial en español. Evidencias en
EditPop-Concat-Android11-evidencias.zip. Esta prueba no cubre edición ni exportación. No se ha ejecutado la APK ARM64 en tu SamsungS26, ni se
completó el recorrido de edición/exportación con los dos vídeos en esta base.
Estas comprobaciones no acreditan una aplicación terminada ni perfecta.

La fuente Concat ya contiene cortes manuales, transiciones, un efecto de ruido
de audio y estabilización, entre otras herramientas; todavía hay que verificar
su funcionamiento en esta adaptación Android. Los cortes automáticos revisables
añadidos antes en Kotlin no se han portado a esta base. La reducción específica
de grano de imagen y la revisión/desactivación de las funcionesIA del upstream
para el alcance inicial siguen pendientes. No se descargaron modelos ni se
enviaron los vídeos del usuario al runner.

## Fuente y trazabilidad

- Fuente correspondiente: **EditPop-Concat-Android-arm64-r1-fuentes.zip**.
- Licencia: AGPL-3.0-or-later, con atribuciones y dependencias de la base Concat.
- Upstream: https://github.com/jub0t/Concat
- Commit exacto compilado: `e57cbccf48b7c68045698739c106f031f0f42972`.
- Ejecución exitosa: https://github.com/afernandezchef-source/mio-rae/actions/runs/39631665408
- Checksums locales: **EditPop-Concat-r1-SHA256SUMS.txt**.

APK final SHA-256:
`0dfda72e8d5038af87f4abdc9adf8458f2ae9dcec3f3ec766c5d9a42a89ed0b3`.
Certificado de pruebas SHA-256:
`367e653b8cdf0206aeaa6cbf70783a74e084baef418cb3e366f54395bd0b8b2a`.

La clave privada no está incluida en el APK, el ZIP de fuentes ni los artefactos
de entrega. Futuras candidatas deben firmarse con esa misma clave local para
permitir actualización; la firma temporal original de CI es diferente.

En r1 la bienvenida todavía dice «Concat»; el nombre instalado es EditPop Pruebas.
La corrección del texto está preparada en las fuentes de la siguiente candidata,
pero no cambia esta APK ni su ZIP de fuentes correspondientes.
