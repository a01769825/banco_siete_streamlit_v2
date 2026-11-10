# Registro de prompts — Bloque 1 — equipo 2

Herramienta: Claude (Anthropic). Los prompts se muestran en español (los mensajes originales estaban en francés y se tradujeron); entre corchetes, lo que el equipo debe completar. Etapas del SDLC: planeación, diseño, diseño técnico, implementación, pruebas, revisión, documentación, incidentes, datos y analítica.

## 1. Planeación

- **Etapa:** planeación
- **Prompt (literal):** «Mira lo que tengo que hacer. Entonces, dime qué aspectos ya están completados.» (traducido al español; el original se escribió en francés)
- **Qué devolvió:** Una lectura del plan de trabajo (semanas 13 a 16, roles R1 a R7, hipótesis H1 a H4) con lo ya cubierto y lo pendiente para el tablero.
- **Qué cambiamos:** Nada se tomó tal cual: los códigos R y H se interpretaron primero como documentos y resultaron ser roles e hipótesis; se corrigió con el documento del plan.
- **Qué decidimos nosotros y no el modelo:** Qué pantallas entran en este bloque y quién se encarga de Streamlit (rol R4).
- **Qué verificó el equipo:** Se contrastó la interpretación contra el documento original del plan de trabajo. [EQUIPO: confirmar.]

## 2. Datos y analítica

- **Etapa:** datos y analítica
- **Prompt (literal):** «¿Estás seguro? Dime también, de forma exhaustiva, cuáles son las diferencias entre las dos bases de datos...» (el resto del mensaje está en el historial) (traducido al español; el original se escribió en francés)
- **Qué devolvió:** Una comparación columna por columna entre `hmeq_preparado_1` y `PREPPED_2`, con diferencias en `JOB_Other`, `CLAGE` y los faltantes.
- **Qué cambiamos:** La primera respuesta decía que eran la misma base; tras la comparación completa se corrigió y se eligió `hmeq_preparado_1`, con `REASON_FALTANTE` agregado.
- **Qué decidimos nosotros y no el modelo:** Qué base es la versión oficial («la más reciente es hmeq_preparado»); mantener «Sin dato» como categoría y no imputar; mínimo de 30 solicitudes por grupo.
- **Qué verificó el equipo:** Cifras de control contra el CSV: 5,960 filas, 1,189 incumplimientos (19.95 %), 1,267 sin dato de deuda sobre ingreso, 2 filas con `BAD` mal escrito que explican 5,958 en el informe. [EQUIPO: confirmar cuál cifra queda en el informe.]

## 3. Diseño

- **Etapa:** diseño
- **Prompt (literal):** «Hay que cambiar el nombre de las variables para alguien que no conoce su significado ... Agregar una razón (ratio) para los datos. Hay que crear una identidad visual para el dashboard. Todos los KPI deben existir en relación con un benchmark (un semáforo o algo así). Las cifras tienen que explicarse solas. Se pueden dividir las pantallas del analista en varias. Los filtros no deben ser tan visibles. La pantalla de los gerentes debe simplificarse, más concisa. Todo debe ser autoexplicativo xD. Hay que poder observar las relaciones entre todas las cifras de un vistazo. Mostrar los casos en una tabla en lugar de hacer scroll.» (recorte de esta copia; texto completo en el historial) (traducido al español; el original se escribió en francés)
- **Qué devolvió:** Una versión 2 con nombres claros, razones «1 de cada N» y «× la cartera», semáforo con referencia en cada indicador, el analista dividido en cuatro pantallas, filtros en un botón, gerente simplificado y tablas completas.
- **Qué cambiamos:** El semáforo pasó de cuatro etiquetas con emoji a texto; «Sin alerta» se volvió verde; la tabla de perfiles pasó a todo el ancho porque en dos columnas se cortaban las últimas columnas; se redujeron las columnas de la tabla del gerente.
- **Qué decidimos nosotros y no el modelo:** Que «filtros poco visibles» significa discretos y no ocultos; qué referencia usa cada indicador; qué metas se muestran en el modelo (AUC ≥ 0.85, recall ≥ 0.70).
- **Qué verificó el equipo:** Pruebas automáticas por rol y capturas de cada pantalla; el texto de cada observación contra el Cierre de Condiciones. [EQUIPO: revisar las pantallas en la URL desplegada.]

## 4. Diseño (identidad visual)

- **Etapa:** diseño
- **Prompt (literal):** «¿Puedes usar los colores de esta imagen para la identidad visual (y la tipografía también, si es posible) y eliminar los emojis si hay? El profe me dijo que los banqueros eran gente seria y todo eso.» (con una imagen de referencia de una marca bancaria) (traducido al español; el original se escribió en francés)
- **Qué devolvió:** Paleta de azul profundo y blanco, títulos y cifras en serif (Source Serif 4), texto en Inter, y sin emojis.
- **Qué cambiamos:** Los iconos de fuentes del sistema se rompieron con la primera regla de tipografía y se corrigió el selector; el título del encabezado desapareció por un color mal aplicado y se corrigió con una clase propia.
- **Qué decidimos nosotros y no el modelo:** Usar solo la paleta y el estilo como inspiración, sin nombre, logo ni elementos de la marca de la imagen; mantener los colores rojo, ámbar y verde solo como código funcional del semáforo.
- **Qué verificó el equipo:** Capturas de pantalla de cada rol. Las fuentes de Google se cargan solo con internet. [EQUIPO: confirmar cómo se ven en la URL desplegada.]

## 5. Revisión

- **Etapa:** revisión
- **Prompt (literal):** «Explícame los elementos de la pantalla, no entiendo nada jaja:» (con una captura del tablero de la versión 1) (traducido al español; el original se escribió en francés)
- **Qué devolvió:** Una explicación de cada elemento de la pantalla del analista y qué es un perfil prioritario.
- **Qué cambiamos:** Que la persona que construyó el tablero no entendiera las pantallas fue la señal para rehacer nombres, subtítulos y leyendas (punto 3).
- **Qué decidimos nosotros y no el modelo:** Que cada figura tenía que explicarse sola para alguien que no conoce las variables.
- **Qué verificó el equipo:** [EQUIPO: probar el tablero con alguien que no conozca el proyecto.]

## 6. Implementación (despliegue)

- **Etapa:** implementación
- **Prompt (literal):** «Quiero desplegarlo con ayuda de VS Studio.» (traducido al español; el original se escribió en francés)
- **Qué devolvió:** Los pasos para subir el repositorio a GitHub desde VS Code (Source Control, Commit, Sync) y desplegar en Streamlit Cloud.
- **Qué cambiamos:** Se adaptaron los pasos a las pantallas reales de VS Code y de Streamlit Cloud que se enviaron como capturas.
- **Qué decidimos nosotros y no el modelo:** Repositorio público; no usar credenciales ajenas; avisar que el repositorio público muestra los datos y la contraseña de demostración.
- **Qué verificó el equipo:** Que la app en línea abre en una ventana privada y muestra 5,960 solicitudes. [EQUIPO: confirmar tras el último Commit y Sync.]

## 7. Incidentes

- **Etapa:** incidentes
- **Prompt (literal):** [PEGAR el mensaje con la captura de la app desplegada que mostraba 5,953 solicitudes en lugar de 5,960.]
- **Qué devolvió:** El diagnóstico: el control de valor de la propiedad redondeaba el máximo (855,909 pasaba a 853,000) y excluía las solicitudes de mayor valor.
- **Qué cambiamos:** Los límites se redondean al paso del control y, si no se toca, no se filtra ninguna solicitud; en local la cifra volvió a 5,960.
- **Qué decidimos nosotros y no el modelo:** Que la cifra sin filtros debe ser siempre la de toda la cartera.
- **Qué verificó el equipo:** La prueba automática da 5,960 sin filtros. [EQUIPO: confirmar en la URL desplegada.]

## 8. Documentación

- **Etapa:** documentación
- **Prompt (literal):** «Hola. Debo presentarle a mi prof un prompt que replique todo (incluye los documentos a utilizar) lo que hemos hecho hasta ahora con streamlit. Entendido(? En español...»
- **Qué devolvió:** Un documento «Prompt maestro» con el propósito, los archivos a adjuntar, el prompt, las cifras de control, las decisiones y las limitaciones.
- **Qué cambiamos:** Ese documento describe la versión 1; se reescribió el contrato de esta entrega (`contrato-prompt.md`) para la versión 2.
- **Qué decidimos nosotros y no el modelo:** Qué archivos se adjuntan y qué se declara como decisión del equipo.
- **Qué verificó el equipo:** Que las cifras de control del documento coinciden con las del CSV. [EQUIPO: confirmar.]
