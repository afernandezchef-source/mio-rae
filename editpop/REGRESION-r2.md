# Corrección del recorrido móvil — r2 en verificación

La prueba del usuario en Samsung S26 detectó que Dividir no producía respuesta y
que no podía usar transiciones/efectos. r1 sólo había pasado compilación y arranque;
esos resultados no cubrían edición. Esta corrección mantiene Concat como motor.

| Problema identificado en código | Cambio | Verificación actual |
| --- | --- | --- |
| Tocar un clip en teléfono sólo seleccionaba, dejaba el cabezal en cero; dividir en un extremo era un no-op silencioso. | El tap posiciona el cabezal; una división inválida explica que debe situarse dentro; se selecciona el ID de la cola realmente creada. | Pruebas del modelo aprobadas; pulsaciones Android pendientes. |
| Una transición aplicada al primer segmento exigía seleccionar su vecino de entrada. | En teléfono cualquiera de los dos lados de una unión válida resuelve al clip de entrada; no se inventan uniones sobre huecos ni entre pistas. | Casos de adyacencia, hueco, audio y pistas distintas aprobados. |
| Las cuatro pistas de escritorio de 80 px podían dejar el vídeo seleccionado debajo del visor de pistas de teléfono. | La geometría de la pista seleccionada se publica y el teléfono la desplaza a la vista al cambiar de selección/geometría. | Compilación y prueba Android pendientes. |
| Transiciones y efectos del clip estaban al final de una barra extensa. | Se colocan junto a Dividir. Nombres accesibles en controles de teléfono. | Prueba Android pendiente. |
| El estante inicial de efectos mostraba sólo el primer grupo. | Las bibliotecas de teléfono arrancan mostrando todos los grupos. Al aplicar a un clip fuera del cabezal se busca su interior y se confirma la operación. | Prueba de aplicación y renderizado Android pendiente. |

165 pruebas concat-project aprobadas, sin fallos. Incluyen división, transición,
efecto, deshacer/rehacer y serialización/reapertura, además de las regresiones
originales. Registro: evidence/r2-project-tests.log. No equivalen a prueba de UI.

Fuentes en compilación externa:
- ARM64: 0cc3aea805bccb612aa1581cc123775f314860c2, run 39644578870.
- x86_64: 48480fcb4ed245d95f62edb1a47fd8c23bf43fb6, run 39644578816.
Ambos commits tienen el mismo árbol fuente. El archivo de pruebas puede mejorar
en un commit separado sin cambiar la app compilada: se registra siempre el run,
commit y SHA-256 del APK que se ejecutó. No distribuir una corrección como
verificada antes de terminar los pasos que constan pendientes.

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
