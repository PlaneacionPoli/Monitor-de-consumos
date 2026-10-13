# Dashboard en GitHub Pages (sitio estático cifrado)

GitHub Pages solo sirve archivos estáticos. Un login hecho solo con JavaScript **no protege** datos que viajen en claro: cualquiera puede leerlos del repositorio. Por eso los datos se publican **cifrados** y el navegador los descifra con el correo y la contraseña de cada usuario autorizado. No hay servidor.

## Cómo funciona

| Pieza | Detalle |
|---|---|
| Datos | `data.enc.json`: AES-256-GCM. En el repositorio no hay valores, facturas, direcciones ni correos en claro |
| Usuarios | Por cada correo autorizado se guarda la clave de datos envuelta con PBKDF2-SHA256 (600.000 iteraciones) derivado de **su** contraseña. El correo se guarda solo como hash |
| Contraseñas | Las genera el script (aleatorias, 20 caracteres). No se eligen a mano: así no pueden adivinarse fuera de línea |
| Gráficos | Apache ECharts 6.1.0 servido desde el propio sitio (`vendor/`); el navegador no carga nada de terceros |
| Política de contenido | `index.html` restringe scripts, estilos y conexiones al mismo origen |

## Publicar

1. Agregue los correos autorizados, uno por línea, en `config/accesos_dashboard.txt` (no se versiona).
2. Genere la validación vigente: `python scripts/pipeline.py` (o al menos hasta `validar_atipicos`).
3. `python scripts/publicar_dashboard.py` crea `site/` y escribe las contraseñas en `data/outputs/control/accesos_dashboard.csv` (no se versiona). **Entregue a cada persona su contraseña por un canal distinto al repositorio.**
4. Suba `site/` a GitHub y active Pages (Settings → Pages) sobre esa carpeta o una rama `gh-pages`.
5. Para actualizar datos: repita 2–3 y suba de nuevo. Las contraseñas existentes se conservan.

Vista local: `python -m http.server 8765 --directory site` y abrir `http://127.0.0.1:8765/`.

## Límites que conviene conocer

- **Quitar un usuario** solo cierra el acceso a los datos publicados *desde la siguiente corrida* (la clave de datos se rota). Quien ya tuvo acceso conserva lo que descargó y las versiones anteriores del repositorio siguen siendo descifrables con su contraseña.
- **No hay límite de intentos**: el blob es público y se puede atacar fuera de línea. La protección depende de que las contraseñas sean las aleatorias que genera el script.
- **El sitio es de solo lectura**. Las decisiones de revisión se siguen registrando en el sistema local (`scripts/cargar_almacen.py`, `src/storage/repositorio.py`).
- **Política de datos**: la Ficha (§7) y la Propuesta (§11) piden no cargar valores de contratos con prestadores en servicios cloud no autorizados. Publicar aquí, aunque cifrado, es una decisión que debe validar TI y Jurídica (actividad F2-14 del plan integral). El archivo cifrado sigue estando en GitHub.
- El cifrado se prueba en `tests/test_publicar_dashboard.py`, incluida la compatibilidad entre Python y el código del navegador.
