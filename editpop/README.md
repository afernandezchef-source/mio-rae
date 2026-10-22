# EditPop — evaluación de Concat

## Estado vigente: r2 verificada y publicada

Descarga y guía: https://github.com/afernandezchef-source/mio-rae/tree/editpop/download-r2

La corrección de Dividir, Pixelate, Dissolve, guardar/reabrir y exportar el mismo
proyecto por los botones de la app a galería a1080p pasó en Android11/API30.
Se corrigieron el bloqueo de inicialización MediaCodec y sus etiquetas de color.
La APK ARM64 se firmó con la misma clave de r1; no requiere desinstalar para
actualizar. No se probó físicamente un Samsung S26. El estado detallado y los
pendientes están en REGRESION-r2.md y SEGUIMIENTO-CONCAT.csv (87 criterios).

Fuente exacta ARM:4efc27da401bc2ba970744890d4b84cbaf2698fd,
run39688535227. x86:9e9606c10cf287a7fc6f8b43bf8299dc6a38d2ba,
run39688535246. Ambos árboles son idénticos. APK SHA256:
0d7c93ac01f2eac274522477e44ae0a50aeeed742c2e707982e1df81d0c44e5f.

Los apartados siguientes conservan el historial de adopción y compilaciones
anteriores; no sustituyen el estado vigente de r2.

## Compilación en un entorno con más capacidad — 21-10-2026

Se publicó una copia completa de la candidata, conservando licencias, en la rama
aislada `editpop/concat-android-build` de `afernandezchef-source/mio-rae`. No se
modificó la rama predeterminada de ese repositorio. Se usó un commit de snapshot
con procedencia explícita porque la copia local de Concat tiene historia shallow;
la rama original local y su historia se conservan.

La primera ejecución de GitHub Actions confirmó **15,6 GiB de RAM y3GiB de swap**;
aprobó la puerta de memoria y falló después por `sdkmanager` ausente. Se corrigió
la preparación con acciones fijadas de Java17 y Android SDK, y se añadió caché de
FFmpeg y dependencias Rust. Se lanzó la segunda ejecución:
https://github.com/afernandezchef-source/mio-rae/actions/runs/39631365886
Fuente exacta: `37cb8b2467f50c044b77bd186032a54faa554b82`.

La tercera ejecución,39631665408, terminó con éxito sobre la fuente
`e57cbccf48b7c68045698739c106f031f0f42972`: compilación ARM64 en14min03s,
picoRSS14.601.456KiB; firma/identidad/ZIPyELF16KiB aprobados. Se descargó la APK y
se firmó con una clave de pruebas persistente fuera del repositorio. Sus12entradas
de contenido ajenas a META-INF son idénticas a las deCI; verificación localPASS.
Entrega `/workspace/editpop-deliveries/EditPop-Concat-Android-arm64-r1.apk`, SHA256
`0dfda72e8d5038af87f4abdc9adf8458f2ae9dcec3f3ec766c5d9a42a89ed0b3`.
Fuente correspondiente `EditPop-Concat-Android-arm64-r1-fuentes.zip` en esa carpeta.
El arranque x86_64/API30 pasó en la ejecución39633057257: 60 s visible, sin
fatal/ANR, captura inspeccionada. Samsung y edición/exportación real siguen pendientes. El fallo de
preparación de la primera ejecución y su memoria se conservan en
`evidence/ci-39630883803.log`. Los bloqueos anteriores de creación de repositorios
no impidieron publicar en este repositorio existente con permiso de escritura.

Primera APK ARM64 basada en Concat obtenida. Candidata de pruebas separada;
no sustituye a EditPop nativo como entrega verificada ni certifica SamsungS26.

Base: https://github.com/jub0t/Concat
Commit fijado: 9f465da4a4f490991696f77890e69a9ba694f18a
Rama local: editpop/evaluate-android
Fecha de revisión: 2026-10-21.

## Cambios propios

- Paquete Android `cl.kokumix.editpop.concatcandidate`, para evaluar sin sobrescribir la app anterior ni sus proyectos.
- Nombre `EditPop Pruebas`, APK `EditPop-Concat-Candidate`.
- Icono original de EditPop para Android y ventana; identificación de la base Concat en inicio.
- Se conservan copyright, AGPL, avisos y procedencia. No es una distribución oficial de Concat.

También se mejoró la seguridad de importación y publicación, y se fijaron español y acento coral como preferencias iniciales. Estos cambios no migran proyectos. El límite local de8GiB se resolvió para esta compilación usando GitHub Actions con15,6GiB RAM y3GiB swap. Las funciones de IA del upstream siguen presentes en el código; desactivarlas/aislarlas para la primera entrega solicitada forma parte de la adaptación pendiente. No se descargaron modelos ni se enviaron medios a servidores.

## Comprobación ejecutada

Rust 1.93.1, Linux x86_64: 64 pruebas originales de concat-core aprobadas, 0 fallos. El crate no tiene dependencias externas; se compiló directamente con rustc, sin resolver el workspace completo:

```sh
rustc +1.93.1 --edition 2024 --test src/crates/concat-core/src/lib.rs -o /tmp/editpop-concat-core-tests
/tmp/editpop-concat-core-tests
```

Además:162 pruebas de concat-project,72 de concat-effects y7 escenarios de importación Java aprobados; registros en evidence/. Registro core: `evidence/core-tests.log`. Esto comprueba lógica de tiempo, retiming, animación y modelo; no acredita reproducción, GPU, exportación ni teléfono.

## Compilación Android reproducible

Seguir `src/README.md`, `.github/workflows/mobile.yml` y el toolchain fijado en `src/rust-toolchain.toml`. Se requieren SDK Android, NDK, JDK, Rust1.93.1, cargo-apk, CMake, libclang y las dependencias nativas. El entorno actual dispone de SDK/NDK/JDK, Rust1.93.1 con targetARM64, cargo-apk0.10.0, CMake, libclang18 y Ninja. Las bibliotecas sherpa están preparadas y FFmpeg8.1 móvil ARM64 terminó de compilar. La APK ARM64 pasó la comprobación estructural y la build x86_64 pasó arranque; el recorrido audiovisual aún no está aprobado.

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

Comprueba firma, alineación ZIP, identidad separada, minSdk26/targetSdk35, biblioteca principal ARM64 y segmentos ELF de16KiB. Es una comprobación estructural: no demuestra instalación, reproducción, mezcla ni exportación. El script también imprime SHA256 y certificado para identificar exactamente el artefacto probado. Se ejecutó sobre la APK ARM64 en CI y sobre la entrega final firmada localmente; ambas pasaron.

El script mobile-env.sh reutiliza ONNX Runtime1.27.1 incluido en sherpa para ambos ABI Android. Evita la descarga alternativa de ort-sys cuyo CDN respondió403 en este entorno. En una máquina con libclang sin cabeceras incorporadas, también indica explícitamente el resource-dir del NDK. No hace falta modificar dependencias descargadas de Cargo.

## Historial del bloqueo local y solución externa

El límite local de 8 GiB produjo SIGKILL/OOM al generar código para `concat-ui`,
incluso tras separar la interfaz y usar una unidad de código sin incremental.
`cargo check` sí pasó. Este límite describe el compilador, no la app instalada.

El workflow `.github/workflows/editpop-android.yml` resolvió el bloqueo en el
repositorio existente con 15,6 GiB de RAM y 3 GiB de swap. La creación inicial de
un fork devolvió 403, pero no impidió publicar en una rama aislada del repositorio
propio accesible. La compilación ARM64 y la comprobación estructural terminaron
con éxito. La entrega se volvió a firmar con una clave local de pruebas persistente.

El workflow separado `editpop-smoke.yml` compiló x86_64 y verificó arranque real
con KVM en Android 11. Consulte [CI-ESTADO.md](CI-ESTADO.md) para trazabilidad.
No se ha completado la prueba física Samsung ni el recorrido de exportación.
La bienvenida de r1 dice Concat; la corrección de identidad está preparada en
fuentes para la siguiente candidata y no forma parte de la entrega r1.
