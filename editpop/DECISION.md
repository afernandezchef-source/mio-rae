# Base profesional: decisión y pruebas de adopción

Revisión de código del20-10-2026. La elección provisional es una variante de Concat como motor único, conservando la app Kotlin hasta aprobar la sustitución. No equivale a una APK lista ni a paridad con CapCut.

## Comparación basada en evidencia

| Área | EditPop Kotlin/Media3 | Concat Rust/Slint | Decisión |
|---|---|---|---|
| Herramientas | Montaje, varias capas, SRT, color, congelación, velocidad; alcance verificado documentado | Código de animación, máscaras, transiciones, audio y127 paquetes; ejecución móvil pendiente propia | Evaluar Concat para evitar reimplementar herramientas |
| Persistencia | AtomicFile, revisiones, recuperación y relink | projects.rs guarda temporal con sync_all/rename y ordena revisiones; document reader normaliza/desecha entradas inválidas | No copiar automáticamente; comprobar corrupción, conservación y recuperación con casos iguales |
| Android/archivos | SAF, almacenamiento privado, MediaStore y servicio de exportación | Puente JNI/SAF/MediaStore; no se encontraron startForeground/WakeLock en la capa Android revisada | Adaptar protección del trabajo largo; exportar con pantalla bloqueada es criterio obligatorio |
| Exportación | Pruebas de contenido720/1080 y cancelación en emulador;0.19 aún pendiente | Android selecciona h264/hevc/av1_mediacodec; no garantiza capacidad por ofrecer el nombre | Comprobar H264/AAC1080 en teléfono; ocultar/no prometer formatos no compatibles |
| Automatización | Pendiente API pública | concat-api/CLI/MCP con comandos del proyecto | Base útil para Kokumix; ningún servidor activado |
| Proyectos existentes | Esquema8, microsegundos, apariencia propia | concat.jsonv1 con campos y reglas distintas, segundosf64 en documento/racionales al renderizar | Importador explícito y reporte de diferencias antes de migrar |

No se mezclan dos renderizadores en una APK ni se traducen shaders WGSL a Media3 automáticamente. Se pueden reutilizar experiencia, contratos, recursos propios y fixtures para comparar ambos motores. Trasladar el servicio Android necesita un puente de ciclo de vida y notificaciones; no basta copiar una clase Kotlin.

## Cambio funcional ya aplicado al candidato

`ConcatFiles.publish` comprueba los bytes copiados y exige que MediaStore confirme exactamente una fila publicada antes de borrar el temporal original. Un rechazo o copia incompleta elimina el registro pendiente y conserva el original. Las carpetas de publicación son Movies/EditPop y Download/EditPop. Validación Java con SDK36 aprobada; ejecución Android de rechazo/cancelación/poco espacio pendiente. No acredita durabilidad de todos los proveedores ni cierre del proceso.

`FFMPEG_JOBS` permite acotar compilación a2procesos en este entorno sin cambiar el motor. La preparación de ARM64 está en marcha con el toolchain upstream1.93.1, NDK27.2 y FFmpeg8.1. Las bibliotecas sherpa son dependencias de compilación del upstream; no se descargaron modelos IA ni se enviaron vídeos.

## Puertas para sustituir la app actual

1. APK ARM64 compilada, firmada y con avisos/fuentes; luego instalación y arranque. Pruebas x86_64 requieren otra compilación.
2. Dos vídeos+imagen+audio → recorte/división/reordenación → imagen/texto/transición → guardar/cerrar/reabrir → MP4H264/AAC1080. Inspección de imagen, señal de audio, PTS y duración.
3. Cancelar, falta de espacio, recursos ausentes, muerte del proceso, pantalla bloqueada y retorno del segundo plano sin perder proyecto ni publicar parciales.
4. Importación de proyectos EditPop con copia original intacta; rechazar o informar cada propiedad incompatible. No suprimir capas silenciosamente.
5. Idioma español, identidad propia, IA apartada de la primera entrega y permisos solicitados cuando proceden.
6. Medición en Android ARM64 real: apertura, búsqueda, memoria y exportación. El estado actual no acredita rendimiento de teléfono.

La distribución de la variante conserva AGPL-3.0-or-later y sus atribuciones, con fuente correspondiente. La rama Kotlin no se ha relicenciado ni se le añadió código de Concat.

## Resultados adicionales de esta revisión

- `concat-project`:162 pruebas originales aprobadas en Linux/Rust1.93.1, incluidas operaciones y documentos. Registro `evidence/project-tests.log`.
- Importación Android usa ahora `ImportFileTarget`: reserva exclusiva del nombre, copia por bloques64KiB, sync/cierre antes de dar éxito, limpieza de su archivo al fallar y fallback a almacenamiento interno si el externo no está disponible. Siete escenarios host aprobados, incluida concurrencia de12importaciones con el mismo nombre; registro `evidence/import-files-test.log`.
- La clase Java del puente y el nuevo helper compilan con SDK36/JDK17. Esto no equivale a ejecutar SAF/MediaStore en Android. La limpieza tras muerte del proceso y el aviso detallado de cada importación fallida siguen pendientes.
- cargo-apk0.10.0, CMake, libclang18 y Ninja preparados sin privilegios de sistema; el intento inicial apt falló por permisos y no es requisito para repetir la build si se usan herramientas locales equivalentes.

## 21-10-2026: preparación de APK

FFmpeg8.1 ARM64 terminó correctamente; bibliotecas estáticas instaladas, registro `evidence/ffmpeg-arm64-build.log`. `concat-effects`:72 pruebas originales aprobadas en host, registro `evidence/effects-tests.log`; validan catálogo y composición/validación de shaders según las pruebas, no rendimiento ni salida GPU del teléfono. Sumadas a64 de core y162 de project son298 pruebas upstream host, más7 escenarios propios de archivos.

Primera APK de evaluación en compilación con `cargo apk build --profile quick -p concat-android --target aarch64-linux-android`. Se usa el perfil quick del upstream para evaluación, no se atribuyen mediciones de una build release. El arranque ahora fija español y acento coral cuando no hay preferencias explícitas; cambiar idioma/color sigue siendo posible y las elecciones guardadas se respetan. Comprobación de formato Rust aprobada. No afirmar instalación/exportación de esta variante hasta tener evidencia Android.

### Dependencias Android y fallos de compilación resueltos

El primer intento falló en bindgen por no encontrar stddef.h. mobile-env.sh indica ahora el resource-dir del compilador del NDK, además de su sysroot. El segundo intento avanzó y falló por HTTP403 del CDN de ort-sys. Android ARM64 usa ahora el mismo ONNX Runtime de sherpa que upstream ya usa en x86_64: libonnxruntime.so1.27.1, con símbolos exportados OrtGetApiBase y OrtSessionOptionsAppendExecutionProvider_Nnapi (VERS_1.27.1); concat-vision solicita API27. Se evita incluir dos runtimes distintos. Esto comprueba identidad y símbolos de enlace, no ejecución de inferencia en teléfono. Los intentos y sus registros se conservan en /workspace/android-toolchain/concat-apk-arm64*.log. Compilación incremental reanudada; ninguna APK declarada aprobada aún.

### Límite de memoria del compilador

El intento con ONNX compartido compiló las dependencias, pero rustc del crate concat fue terminado por SIGKILL. El contador cgroup oom_kill pasó de0 a1 al alcanzar8GiB: fallo de recursos de compilación, no diagnóstico Rust ni medida de memoria de la app. Se desactiva incremental solo para profile.quick.package.concat en src/.cargo/config.toml y se reintenta con CARGO_BUILD_JOBS=1, conservando dependencias compiladas. Registro: /workspace/android-toolchain/concat-apk-arm64-noincremental.log. El ajuste no se declara suficiente hasta terminar el intento.

### Resultado del reintento y entrega de fuentes

El segundo intento también terminó por SIGKILL; oom_kill pasó a2. No se generó APK. La desactivación de incremental no fue suficiente con8GiB. Ambos registros se copiaron a editpop/evidence/. El ajuste queda documentado como intento fallido, no como solución validada.

Se preparó .github/workflows/editpop-android.yml para ejecución manual en un runner con al menos16GB como hipótesis inicial, no capacidad medida. Incluye firma efímera de pruebas para el perfil quick (cargo-apk exige CARGO_APK_QUICK_KEYSTORE/PASSWORD), verificación estructural y fuentes del commit. YAML y bloques bash pasan revisión sintáctica; workflow no ejecutado. Las tres bibliotecas precompiladas ARM64 sí tienen segmentos ELF16KiB; evidencia y hashes archivados. Biblioteca principal/APK/instalación/exportación siguen pendientes.

### Nuevo intento móvil

Un tercer intento quick con16 unidades de código, sin incremental y firma de pruebas se detuvo manualmente después de más de12min en el límite8GiB, sin producir APK. Para Android, build.rs genera ahora una entrada Slint a partir de app.slint sin el título ni el workspace de escritorio, que en teléfono nunca se instancian. El archivo generado conserva los tipos compartidos y callbacks. La salida de Slint pasó de73,868,969 a63,171,445 bytes (~14,5% menos). Aun así, el cuarto intento terminó SIGKILL/OOM del crate concat. Tres advertencias del código no eran errores; el fallo fue el límite de memoria. Log: evidence/concat-apk-arm64-phone-ui.log. Se requiere una máquina de compilación con más memoria; ninguna APK nueva es declarada.

### Interfaz como crate independiente

La generación Slint pasó a `concat-ui`, una dependencia local de `concat`, para separar los 63 MB de Rust generado del código del editor. El perfil `quick` compila esa interfaz sin incremental y con una sola unidad de código. Las dos pruebas de APK de esta estructura terminaron por SIGKILL/OOM del crate `concat-ui`, una con 16 unidades y otra con una. No se encontró error de compilación previo al agotamiento de memoria. Los registros están en `evidence/concat-apk-arm64-split-ui*.log`.

Con las rutas explícitas del compilador C del NDK, `cargo check --profile quick -p concat-android --target aarch64-linux-android` finalizó correctamente. Este resultado valida tipos y uso de los crates en ARM64, pero no hace el enlace final ni genera ejecutable o APK. El registro está en `evidence/concat-check-arm64-split-ui-ndk.log`. El workflow de CI ahora mide el límite de memoria efectivo del runner antes de compilar; no se ha ejecutado. La candidata Kotlin 0.19 es la única APK instalable producida en este entorno y no certifica la variante Concat.
