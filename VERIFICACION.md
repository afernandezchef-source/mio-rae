# Verificación de EditPop Pruebas r4

## Procedencia

ARM64: fuente6e40dffa96a324c6a12618043839b0e6c2c42a05,
[run39872743117](https://github.com/afernandezchef-source/mio-rae/actions/runs/39872743117)
PASS, artefacto12468091164. x86_64: fuented04c32dd3647ded08ccb35679306d1fcd0fe8734,
[run39872742984](https://github.com/afernandezchef-source/mio-rae/actions/runs/39872742984).
Ambos árboles son3452ec2c2a417908b0b86b42653417c0ca048207.

La primera ejecución x86 pasó edición y escenas. La exportación del nuevo filtro
avanzaba al69% a180s, ETA81s, al vencer el límite del arnés. Se conservó FAIL.png.
Se repitió únicamente esa prueba con420s en SwiftShader: [run39875576216](https://github.com/afernandezchef-source/mio-rae/actions/runs/39875576216)
PASS, commit de pruebasda1a463606134561e8b733c82cfc8c3052586045,
artefacto12467899632. No cambia src/crates ni se recompila la APK. SHA256 x86
5dd0457a919c85c8c17c7d8d9c60259cc9f0f6acd47d286ed1a55270d3655bb3 idéntico
al artefacto original. El ZIP fuente conserva el arnés original; la versión usada
en la repetición se adjunta en pruebas/r4/android-edit-check.py.

## Resultado nuevo

Se aplicó Reducir grano desde Efectos y se comprobó el documento, la reapertura
y la exportación por los botones reales de la app a MediaStore Movies/EditPop.
MP4H.264/AAC1080p30, BT.709/rangoTV,4s, decodificación estricta sin errores.
Control: mismo proyecto Android quitando solo videoEffects, exportado por el motor.

| Medida | Resultado |
|---|---:|
| Desviación ruido izquierda, control→filtrado |4,246→2,460|
| Desviación ruido derecha |4,273→2,552|
| Ruido relativo izquierda/derecha |0,5795/0,5973|
| Contraste borde de100 niveles |99,58|
| Error medio visor completo/exportación, escala0–255 |1,148|
| Error medio visor/control sin filtro |2,256|

Medios sintéticos de grano estacionario. El recorrido UI/OCR/exportación/validación
fue271,24s en GPU de software. El campo publication_seconds_including_polling
incluye también transferencia y validación posteriores; no mide solo el codificador.
No es una medición de GPU física, reproducción fluida ni rendimiento SamsungS26.

## Cobertura de esta versión

pruebas/r4/edicion: Dividir por pulsación, Pixelate, Dissolve, guardar/cerrar/reabrir,
exportación del mismo proyecto por motor y UI1080p, comparación de contenido.
pruebas/r4/escenas: detección, descarte, Ver, selección, aplicación atómica,
deshacer/rehacer, reapertura, imagen y tono440Hz antes/después del corte.
pruebas/r4/grano: controles, persistencia, exportación y métricas anteriores.

72 pruebas de concat-effects: catálogo, controles y compilaciónWGSL. GPU local
Vulkan/Lavapipe: ruido RMS relativo0,5332; bordes, alfa, intensidad0, colores planos
y luces altas. El test exige adaptador y no acepta saltarse la GPU como éxito.
Cargo check AndroidARM64 aprobado. Las169 pruebas anteriores del modelo temporal
y propuestas corresponden al código conservado de r3.

pruebas/r3 conserva por separado los resultados históricos de ruido de audio
(8,66–9,55dB de reducción residual con tono conservado) y estabilización
(6,960→0,404px RMS sobre marca sintética). Su código se conserva, pero no se
presentan como una repetición de esas pruebas sobre r4. Ver SONIDO-Y-ESTABILIZACION.md.

## Firma, formatos y entornos

APK ARM64 firmadaV2/V3 con certificadoSHA256
367e653b8cdf0206aeaa6cbf70783a74e084baef418cb3e366f54395bd0b8b2a,
igual a r1/r2/r3. VerificaciónZIP/4ELF16KiB PASS. Sus12entradas ajenas a
META-INF son idénticas al artefactoCI. El binario incorpora el shader nuevo.
La clave privada no se distribuye. APK SHA256
e6e4f82b59fc1fcbf6f621ba9fd446c40aaee1112284b53cdffa14b873d095ce.
Fuente ZIP SHA25607ce96f42a5e116014624ace95b6f44678842b3521ea3c89b2e069d17fff3cef.

- Android11/API30, emulador perfilPixel6 x86_64,4CPU/4GiB, gráficosSwiftShader:
  entrada sintética H.264/AAC vertical/horizontal y salidaMP4H.264/AAC1080p30.
- Linux host, Rust1.93.1, GPU softwareLavapipe: catálogo y pruebas GPU.
- AndroidARM64: compilación/firma/estructura; no ejecución física comprobada.
- SamsungS26: prueba física pendiente; no se afirma compatibilidad ya ensayada.

La compilación ARM duró7m56s y alcanzóRSS14.945.060KiB en el constructor remoto.
Es memoria del compilador; no de la app en el celular. Herramientas y comandos
reproducibles están en el ZIP fuente, editpop/README.md y el workflow Android.

## Limitaciones y siguiente etapa

Faltan prueba física S26, vídeos reales completos, dos vídeos con imagen/texto/
audio externo, cancelación, poco almacenamiento, medios inaccesibles, interrupciones,
segundo plano y estrés prolongado. No hay reanudación de exportación interrumpida
verificada. La IA del upstream debe aislarse y validarse. No están aprobados los
87requisitos ni se afirma paridad con CapCut. La siguiente etapa es el recorrido
ampliado y la validación del teléfono usando PRUEBA-SAMSUNG-S26.md.

Las pruebas remotas usan solo medios sintéticos. No se publicaron vídeos
personales ni la clave de firma. El filtro propio y las modificaciones conservan
AGPL-3.0-or-later, fuente correspondiente y avisos de Concat.
