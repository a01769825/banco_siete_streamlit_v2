# Investigación: el curso *AI-Native SDLC Playbook* frente a cómo trabajamos — Equipo 2

Curso: [AI-Native SDLC Playbook](https://academy.claude.com/courses/ai-native-sdlc-playbook/introduction) (Anthropic Academy, 14 lecciones). Propone reorganizar el ciclo de vida del software en seis etapas que no son lineales (Plan, Design, Build, Test, Deploy, Maintain). La idea central es que, como la IA ya escribe el código rápido, el cuello de botella se mueve a planear, revisar y desplegar. Por eso cada etapa debe terminar con un archivo versionado que lea la siguiente (`intent.md`, `spec.md`, `plan.md`, `CLAUDE.md`…).

## 1. ¿En qué etapas cayeron nuestros prompts?

Clasificamos los prompts del bloque 1 (registrados en `prompts/contrato-prompts.md`) y los de esta semana, que salen de las conversaciones con Claude de dos integrantes del equipo.

| Etapa | Bloque 1 | Esta semana | Qué tipo de prompts fueron (esta semana) |
|---|---|---|---|
| Plan | 1 | 8 | Repartir la entrega entre los integrantes, decidir qué parte tomaba cada quien y entender qué pedía cada tarea. |
| Design | 3 | 0 | — |
| Build | 0 | 4 | Generar el contrato de datos, la validación y los textos de la entrega, y pedir ajustes sobre ellos. |
| Test | 1 | 2 | Confirmar con capturas de pantalla que el workflow y los archivos quedaron bien en GitHub. |
| Deploy | 1 | 11 | Qué archivos subir, a qué carpeta y cómo hacerlo desde GitHub, y si convenía reemplazar `app.py`. |
| Maintain | 2 | 0 | — |

Lo que vemos con evidencia, sin suponer:

- **Esta semana no hubo ningún prompt de Design.** Las 4 decisiones del contrato de datos (qué columnas publicar, qué significa cada vacío, la herramienta del pipeline y cómo marcar dato, calculado y simulado) las propuso la IA, y el equipo solo las confirmó. El profe pidió justo que esas decisiones fueran del equipo. Las revisamos, pero no las discutimos antes de pedirlas.
- **Casi la mitad de los prompts de esta semana (11 de 25) son de Deploy, pero no en el sentido del curso.** Para el curso, Deploy es revisión de PRs y *gates* de aprobación. Para nosotros fueron dudas operativas sobre cómo subir archivos desde la interfaz web de GitHub. La causa fue que nadie trabajaba con el repositorio clonado, la IA tenía permiso solo de lectura y los archivos generados quedaron en la conversación de una sola persona, por lo que hubo que regenerarlos.
- **Test casi no existe como prompt.** Probamos mandando capturas, no pidiendo pruebas. Lo que sí funcionó fue la prueba que la IA corrió sola: rompió el CSV a propósito («abc» en `LOAN`) y comprobó que la app y el pipeline fallaban.
- **Maintain solo aparece en el bloque 1**: la documentación del prompt maestro y el incidente en el que la app desplegada mostraba 5,953 solicitudes en vez de 5,960. Lo arreglamos, pero no dejamos ninguna prueba para que no vuelva a pasar.

## 2. ¿Qué práctica concreta podemos adoptar esta semana?

**Un `CLAUDE.md` en la raíz del repo (lección 5), conectado con el *feedback loop* (lección 8).** El curso dice que se haga con `/init`, que se recorte a lo que necesitaría alguien nuevo el primer día, que no pase de una página y que, cuando la IA cometa el mismo error dos veces, se agregue la corrección.

Nos sirve porque los errores que más nos costaron no estaban en el código, sino en el significado de los datos, y ese conocimiento solo estaba en nuestras cabezas o en chats viejos:

- En el CSV, el faltante de `DELINQ`, `DEROG` y `NINQ` viene como **0** y solo `_FALTANTE = 1` dice que no hay dato. Todos los `JOB_*` en 0 significa «Gerencia», no falta de dato.
- La IA confundió las dos bases (`hmeq_preparado_1` y `PREPPED_2`) y al principio dijo que eran iguales.
- Las cifras de control son 5,960 solicitudes, 19.95 % de incumplimiento y 9 perfiles prioritarios. Si sale otra cifra, algo está mal.

El `CLAUDE.md` también tendría los dos comandos para verificar, con su salida sana, que es lo que pide la lección 8: `streamlit run app.py` y `python validar_datos.py`, que imprime «✓ … 26 columnas cumplen el contrato» y termina con error si algo falla. Así, la próxima vez que alguien abra un chat nuevo, la IA arranca sabiendo esto, en lugar de que una persona tenga que pegar el contexto otra vez.

## 3. ¿Qué esperábamos encontrar y no estaba?

Esperábamos algo sobre **datos**, y el curso no dice nada de eso. Habla de pruebas de código, evals, revisión de PRs y despliegue a producción, pero nada de contratos de datos, valores faltantes, calidad de los datos ni tableros. Lo más cercano es validar esquemas de APIs. Para nosotros el riesgo principal no era que el código truene, sino que el tablero muestre un número que se ve bien y está mal (por ejemplo, «0 líneas morosas» cuando en realidad no hay dato). Ninguna lección dice cómo probar eso.

Tampoco está pensado para un equipo como el nuestro. Supone una empresa regulada con *code owners*, *branch protection*, configuración administrada y gente que trabaja desde la terminal con Claude Code. Nosotros somos 4–7 estudiantes que suben archivos desde la página de GitHub, con un repo que es de una sola cuenta, y con chats separados que no comparten archivos. El curso no tiene un ejemplo resuelto de un trabajo que no sea de software, y la parte de Plan (`intent.md`) supone que hay un *product owner* que lo revisa.

Lo que sí nos sirvió, aunque fuera de contexto, es la idea de que cada etapa deje un archivo versionado. Nuestro `contrato-datos.md` funciona como el `spec.md` del curso: la app y el pipeline leen la misma tabla.

## 4. Tres cambios a nuestro proceso

| # | Qué cambiamos | Dónde | Por qué ahí |
|---|---|---|---|
| 1 | **(Dentro del pipeline)** `validar_datos.py` revisa el CSV contra `contrato-datos.md` en cada push (tipos, rangos, columnas, celdas vacías). Ya está funcionando. Además, le agregaríamos las cifras de control (5,960 solicitudes y 19.95 %) como prueba de regresión del incidente de las 5,953. | `.github/workflows/validar-datos.yml` | Un error de datos tiene que detenerse antes de llegar a la app que ve el usuario. La lección 9 dice que cada incidente debe dejar una prueba nueva, y el nuestro no la dejó. |
| 2 | **(Fuera del pipeline)** Escribir el `CLAUDE.md` con el significado de las columnas, los errores que ya cometimos, las cifras de control y los comandos para verificar. | Raíz del repo | Es conocimiento que la IA no puede deducir del código (que un 0 a veces significa «no hay dato») y que hoy se pierde entre chats y personas. |
| 3 | **(Fuera del pipeline)** Antes de pedirle a la IA una propuesta del contrato, tomar las decisiones de la sección 4 en una llamada del equipo. Cualquier cambio a esas decisiones o una columna nueva se revisa entre dos personas antes de subirse. | `contrato-datos.md`, sección 4, y la llamada del equipo | Son decisiones de negocio y el profe dice que no las puede tomar la IA. Esta semana la IA las propuso primero y solo las confirmamos. Es la idea de los *approval gates* de la lección 11, pero hecha por personas y no con *hooks*. |

Fuentes: [AI-Native SDLC Playbook, Anthropic Academy](https://academy.claude.com/courses/ai-native-sdlc-playbook/introduction) · [The AI-native SDLC playbook, blog de Claude](https://claude.com/blog/the-ai-native-sdlc-playbook) · `prompts/contrato-prompts.md` de este repo y las conversaciones del equipo con Claude de esta semana.
