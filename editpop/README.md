# EditPop — evaluación de Concat

Candidato Android separado, no APK entregada ni sustitución de EditPop nativo.

Base: https://github.com/jub0t/Concat
Commit fijado: 9f465da4a4f490991696f77890e69a9ba694f18a
Rama local: editpop/evaluate-android
Fecha de revisión: 2026-10-21.

## Cambios propios

- Paquete Android `cl.kokumix.editpop.concatcandidate`, para evaluar sin sobrescribir la app anterior ni sus proyectos.
- Nombre `EditPop Pruebas`, APK `EditPop-Concat-Candidate`.
- Icono original de EditPop para Android y ventana; identificación de la base Concat en inicio.
- Se conservan copyright, AGPL, avisos y procedencia. No es una distribución oficial de Concat.

También se mejoró la seguridad de importación y publicación, y se fijaron español y acento coral como preferencias iniciales. Estos cambios no migran proyectos; la compilación Android se encuentra bloqueada por memoria en este entorno. Las funciones de IA del upstream siguen presentes en el código; desactivarlas/aislarlas para la primera entrega solicitada forma parte de la adaptación pendiente. No se descargaron modelos ni se enviaron medios a servidores.

## Comprobación ejecutada

Rust 1.93.1, Linux x86_64: 64 pruebas originales de concat-core aprobadas, 0 fallos. El crate no tiene dependencias externas; se compiló directamente con rustc, sin resolver el workspace completo:

```sh
rustc +1.93.1 --edition 2024 --test src/crates/concat-core/src/lib.rs -o /tmp/editpop-concat-core-tests
/tmp/editpop-concat-core-tests
```

Además:162 pruebas de concat-project,72 de concat-effects y7 escenarios de importación Java aprobados; registros en evidence/. Registro core: `evidence/core-tests.log`. Esto comprueba lógica de tiempo, retiming, animación y modelo; no acredita reproducción, GPU, exportación ni teléfono.

## Compilación Android pendiente

Seguir `src/README.md`, `.github/workflows/mobile.yml` y el toolchain fijado en `src/rust-toolchain.toml`. Se requieren SDK Android, NDK, JDK, Rust1.93.1, cargo-apk, CMake, libclang y las dependencias nativas. El entorno actual dispone de SDK/NDK/JDK, Rust1.93.1 con targetARM64, cargo-apk0.10.0, CMake, libclang18 y Ninja. Las bibliotecas sherpa están preparadas y FFmpeg8.1 móvil ARM64 terminó de compilar. La APK aún no está aprobada; consultar DECISION.md y los registros antes de atribuir resultados.

Desde la raíz, con esas herramientas preparadas:

```sh
rustup target add aarch64-linux-android --toolchain 1.93.1
cargo +1.93.1 install cargo-apk --locked
src/scripts/ffmpeg-mobile.sh aarch64-linux-android
src/scripts/sherpa-mobile.sh aarch64-linux-android
cd src
eval "$(scripts/mobile-env.sh aarch64-linux-android)"
# El perfil quick requiere una clave de pruebas explícita.
# Crear una vez y conservarla fuera del repositorio para futuras actualizaciones.
keytool -genkeypair -keystore /ruta/privada/editpop-test.jks -storepass android -keypass android -alias editpop -keyalg RSA -keysize 2048 -validity 365 -dname 'CN=EditPop Test'
export CARGO_APK_QUICK_KEYSTORE=/ruta/privada/editpop-test.jks
export CARGO_APK_QUICK_KEYSTORE_PASSWORD=android
CARGO_BUILD_JOBS=1 cargo +1.93.1 apk build --profile quick -p concat-android --target aarch64-linux-android
```

El comando final genera una build de pruebas. La entrega requiere comprobar firma, bibliotecas/16KiB, instalación y el recorrido de edición/exportación. Una prueba nativa x86_64 exige build separada de todas las dependencias; no se debe afirmar que el APK ARM64 corre en el emulador AOSP existente.

## Licencia y próximos criterios

Esta rama conserva AGPL-3.0-or-later y los avisos de terceros. Una distribución derivada debe acompañarse del código fuente correspondiente y los avisos aplicables. La marca/icono Concat no se usan como identidad propia.

Antes de adoptar esta base: probar importación SAF, dos vídeos+imagen+audio, recorte/división, texto, transición, guardar/reabrir, 1080p y cancelación; revisar ejecución en segundo plano, descargas y permisos; desactivar IA según el alcance inicial; implementar importador explícito de proyectos EditPop esquema8 con informe de propiedades no trasladables. No abrir esos proyectos directamente como concat.json.

La revisión posterior y las mejoras funcionales propias de importación/publicación se documentan en [DECISION.md](DECISION.md).

## Comprobación estructural de la APK

Con SDK y NDK configurados, ejecutar:

```sh
editpop/tools/verify-apk.sh /ruta/absoluta/EditPop-Concat-Candidate.apk
```

Comprueba firma, alineación ZIP, identidad separada, minSdk26/targetSdk35, biblioteca principal ARM64 y segmentos ELF de16KiB. Es una comprobación estructural: no demuestra instalación, reproducción, mezcla ni exportación. El script también imprime SHA256 y certificado para identificar exactamente el artefacto probado. No se ha ejecutado sobre esta candidata mientras la APK no exista.

El script mobile-env.sh reutiliza ONNX Runtime1.27.1 incluido en sherpa para ambos ABI Android. Evita la descarga alternativa de ort-sys cuyo CDN respondió403 en este entorno. En una máquina con libclang sin cabeceras incorporadas, también indica explícitamente el resource-dir del NDK. No hace falta modificar dependencias descargadas de Cargo.

## Bloqueo actual y compilación alternativa

Los intentos locales de generar la APK terminaron o se detuvieron por el límite de memoria de 8 GiB. La interfaz Android sin el workspace de escritorio genera 63 MB de Rust. Para separar su compilación de la lógica del editor se creó `concat-ui`, con una sola unidad de código y sin incremental en el perfil `quick`. `cargo check --profile quick -p concat-android --target aarch64-linux-android` terminó correctamente con NDK configurado; las dos compilaciones APK de esta estructura terminaron por SIGKILL/OOM mientras Rust generaba código para `concat-ui`. No se generó APK Concat. Esto describe memoria del compilador, no consumo de EditPop instalado.

Se preparó `.github/workflows/editpop-android.yml`, de ejecución manual, con herramientas fijadas, bibliotecas móviles, firma de pruebas, comprobaciones estructurales y entrega conjunta de APK/fuentes/registros. Su sintaxis YAML fue revisada; **no se ejecutó en GitHub ni se publicó nada**. Comprueba la memoria efectiva del runner y exige al menos 14 GiB disponibles como margen inicial; todavía no se ha validado qué memoria basta. La disponibilidad y costes dependen del repositorio/plan GitHub. El flujo conserva licencia y fuentes, y no necesita claves de producción. Su clave de pruebas es temporal: diferentes ejecuciones no garantizan actualización sobre la instalación anterior. No desinstalar una app con proyectos sin guardar una copia.

Antes de usar el workflow, subir todos los cambios de esta candidata a un repositorio propio respetando AGPL. Git archive entrega el commit completo que ejecuta el flujo. Los controles no sustituyen el protocolo Android de ANDROID-VALIDATION.md.

## Acceso de GitHub en esta sesión

La fuente candidata está en la rama local `editpop/evaluate-android`. Se intentó crear un fork de `jub0t/Concat` y un repositorio propio `EditPop-Android`, pero la credencial de esta integración respondió HTTP 403 `Resource not accessible by integration` en ambas operaciones. No se publicó código ni se lanzó Actions. Hace falta un repositorio ya creado y accesible para esa credencial, o una máquina de compilación con más de 8 GiB; el workflow manual queda pendiente de ejecución. La APK Kotlin independiente con ondas está disponible en `/workspace/editpop-native/candidates/` y no acredita la variante Concat.
