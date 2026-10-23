# Reducir grano — r4 verificada en emulador

La r3 publicada mantiene sus funciones verificadas y sirve de respaldo. Este
filtro nuevo se entrega en r4 después de verificarlo en emulador Android.

## Implementación

Paquete propio editpop.grain-reduction, en el catálogo normal de Efectos, nombre
Reducir grano. Filtro bilateral espacial5×5: combina cercanía de los píxeles con
semejanza de color para suavizar grano conservando bordes. Intensidad0–100%,
defecto60%. Cero es identidad; conserva el alfa y evita tomar RGB oculto de
vecinos transparentes. No recorta los valores de color a1 ni necesita fotogramas
anteriores, modelos, cuentas, red o nuevos permisos.

Se ejecuta mediante el compositor WGSL existente de Concat, en el espacio de
visualización, compartido por visor y exportación. No añade códecs ni dependencias.
Usa25muestras por píxel y las texturas reutilizadas del motor. Su coste y fluidez
en SamsungS26 deben medirse; no se promete tiempo real. Se calcula al tamaño de
la imagen preparada para el render: un visor de calidad reducida es orientativo
y puede diferir del archivo final. La prueba de correspondencia usa el visor
completo al mismo tamaño que la exportación.

Es reducción espacial de grano, no eliminación total de ruido, estabilización,
reconstrucción de detalle perdido ni corrección de compresión. Puede suavizar
texturas finas; hay que revisar el resultado y bajar la intensidad si hace falta.

## Pruebas realizadas y pendientes

72pruebas de catálogo pasan, incluidas compilación WGSL y validación de paquetes.
Prueba real de GPU local mediante Vulkan/Lavapipe (adaptador de software delSDK):
ruido sintético RGB, borde nítido y alfa parcial. Ruido RMS relativo0,5332 con
fuerza por defecto; borde conservado; intensidad0 idéntica dentro de precisión
half-float; sondas de color plano, transparencia y luces altas pasan. El test
exige un adaptador y no acepta saltarse la GPU como un éxito.

No es una medida de rendimiento en GPU física. Prueba Android preparada:
importación de vídeo H.264 con grano estacionario conocido y borde vertical,
aplicar desde catálogo con pulsaciones, guardar/reabrir, exportar1080p a galería,
comparar ruido y borde con otra exportación del mismo proyecto sin efecto,
y comparar el fotograma del visor completo con el archivo final.
Prueba Android PASS: run39875576216, commit de pruebas
da1a463606134561e8b733c82cfc8c3052586045. Reutiliza sin recompilar la APK x86 de
run39872742984, fuented04c32dd3647ded08ccb35679306d1fcd0fe8734, cuyo árbol es
idéntico al ARM6e40dffa96a324c6a12618043839b0e6c2c42a05.

| Comprobación Android11/API30 x86_64 | Resultado |
|---|---:|
| Ruido relativo a exportación de control, zona izquierda |0,5795|
| Ruido relativo, zona derecha |0,5973|
| Contraste del borde, original100 niveles |99,58|
| Error medio visor completo/exportación, escala0–255 |1,148|
| Error medio visor/control sin filtro |2,256|

La desviación del grano se redujo aproximadamente40–42% en este caso sintético.
Aplicación desde catálogo, guardado/reapertura exacta y publicación1080p30
H.264/AAC en galería, BT.709/rangoTV,4s: PASS. El vídeo completo se decodificó sin
error. No es una medida de calidad de vídeos reales ni de un SamsungS26.

El primer intento llegó69% a180s, con ETA81s, y venció el límite del arnés.
Se conservó esa evidencia y se amplió solo esta prueba a420s por el coste
observado de SwiftShader. La repetición pasó sin modificar ni recompilar la APK.
El recorrido de exportación/OCR/validación tardó271,24s; el campo
publication_seconds_including_polling de PASS-ui-export incluye también la
transferencia y validación posteriores. Ninguno mide exclusivamente el codificador
ni predice velocidad en GPU física. El rendimiento del SamsungS26 sigue pendiente.
