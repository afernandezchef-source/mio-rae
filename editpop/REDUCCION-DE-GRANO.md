# Reducir grano — candidato r4

La r3 publicada mantiene sus funciones verificadas y sirve de respaldo. Este
filtro nuevo no está en esa APK: se verifica en el candidato r4 antes de entregar.

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
Pendiente de resultado Android antes de publicar la APK r4.
