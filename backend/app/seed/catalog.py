"""Catálogo pedagógico inicial: actividades A–G, ejemplos trabajados (7 tipos) y banco de andamiajes.

Todo el contenido está diseñado para PRESERVAR la actividad intelectual del estudiante: ninguna ayuda
entrega la expresión general ni el valor pedido; los ejemplos trabajados usan patrones DISTINTOS a
los de las tareas.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.learning.models import Scaffold, Task, WorkedExample

# ------------------------------------------------------------------ tareas
# Patrón principal (mesas y sillas): figura n tiene 3n + 2 elementos → 5, 8, 11, 14, ...
# Transferencia (palillos): figura n tiene 2n + 1 palillos → 3, 5, 7, ...

TASKS: list[dict[str, Any]] = [
    {
        "code": "A-NUM-01",
        "task_type": "NUMERIC_PATTERN",
        "title": "La secuencia que crece",
        "skill": "RECURSIVE_RELATION",
        "difficulty": 1,
        "order_index": 10,
        "statement": {
            "prompt": "Observa la secuencia de números. Cada número ocupa una posición: el primero es la posición 1, el segundo la posición 2, y así sucesivamente.",
            "pattern": {"kind": "numeric", "terms": [5, 8, 11, 14]},
            "questions": [
                {
                    "id": "q1",
                    "kind": "predict",
                    "text": "¿Qué número va en la posición 5?",
                    "position": 5,
                    "representations": ["NUMERIC"],
                },
                {
                    "id": "q2",
                    "kind": "explain",
                    "text": "¿Cómo cambia la secuencia de una posición a la siguiente? Explícalo con tus palabras.",
                    "representations": ["VERBAL"],
                },
                {
                    "id": "q3",
                    "kind": "predict",
                    "text": "¿Qué número va en la posición 10?",
                    "position": 10,
                    "representations": ["NUMERIC", "TABULAR"],
                },
            ],
            "expected_time_ms": 240000,
        },
        "solution": {"expression": "3*n+2", "notes": "Relación recursiva +3; funcional 3n+2."},
    },
    {
        "code": "B-FIG-01",
        "task_type": "FIGURAL_PATTERN",
        "title": "Mesas y sillas",
        "skill": "FUNCTIONAL_RELATION",
        "difficulty": 2,
        "order_index": 20,
        "statement": {
            "prompt": "En una fiesta se unen mesas en fila. Alrededor de 1 mesa caben 5 personas; con 2 mesas unidas caben 8; con 3 mesas, 11. Observa las figuras.",
            "pattern": {"kind": "figural", "shape": "tables_chairs", "expression": "3*n+2", "shown_figures": [1, 2, 3]},
            "questions": [
                {
                    "id": "q1",
                    "kind": "describe",
                    "text": "Describe qué ves que cambia y qué se mantiene igual de una figura a la siguiente.",
                    "representations": ["VERBAL"],
                },
                {
                    "id": "q2",
                    "kind": "predict",
                    "text": "¿Cuántas personas caben con 4 mesas? Dibuja o calcula.",
                    "position": 4,
                    "representations": ["NUMERIC", "GRAPHIC"],
                },
                {
                    "id": "q3",
                    "kind": "predict",
                    "text": "¿Y con 12 mesas? Intenta no dibujar todas.",
                    "position": 12,
                    "representations": ["NUMERIC", "TABULAR"],
                },
                {
                    "id": "q4",
                    "kind": "generalize",
                    "text": "Escribe una regla que sirva para cualquier número de mesas n.",
                    "representations": ["SYMBOLIC", "VERBAL"],
                },
            ],
            "expected_time_ms": 420000,
        },
        "solution": {"expression": "3*n+2", "notes": "Cada mesa nueva aporta 3 sillas; los extremos aportan 2 fijas."},
    },
    {
        "code": "C-TAB-01",
        "task_type": "TABLE",
        "title": "Organiza la información en una tabla",
        "skill": "FUNCTIONAL_RELATION",
        "difficulty": 2,
        "order_index": 30,
        "statement": {
            "prompt": "Vuelve a la situación de las mesas y sillas. Completa la tabla que relaciona el número de mesas con el número de personas.",
            "pattern": {
                "kind": "table",
                "expression": "3*n+2",
                "positions": [1, 2, 3, 4, 5, 10, 20],
                "known": {"1": 5, "2": 8, "3": 11},
            },
            "questions": [
                {
                    "id": "q1",
                    "kind": "table",
                    "text": "Completa las casillas vacías.",
                    "positions": [4, 5, 10, 20],
                    "representations": ["TABULAR"],
                },
                {
                    "id": "q2",
                    "kind": "explain",
                    "text": "¿Qué te ayudó a llenar la casilla de 20 mesas sin pasar por todas las anteriores?",
                    "representations": ["VERBAL"],
                },
            ],
            "expected_time_ms": 300000,
        },
        "solution": {"expression": "3*n+2"},
    },
    {
        "code": "D-GRA-01",
        "task_type": "GRAPH",
        "title": "Mira la relación en un gráfico",
        "skill": "COVARIATION",
        "difficulty": 3,
        "order_index": 40,
        "statement": {
            "prompt": "Ubica en el plano los puntos (número de mesas, número de personas) para las mesas 1 a 6. Luego observa cómo se organizan.",
            "pattern": {
                "kind": "graph",
                "expression": "3*n+2",
                "x_label": "Mesas",
                "y_label": "Personas",
                "x_max": 8,
                "y_max": 30,
            },
            "questions": [
                {
                    "id": "q1",
                    "kind": "table",
                    "text": "Marca los puntos para 1 a 6 mesas.",
                    "positions": [1, 2, 3, 4, 5, 6],
                    "representations": ["GRAPHIC"],
                },
                {
                    "id": "q2",
                    "kind": "explain",
                    "text": "¿Qué forma tienen los puntos? ¿Qué te dice eso sobre cómo crece el número de personas?",
                    "representations": ["VERBAL"],
                },
            ],
            "expected_time_ms": 300000,
        },
        "solution": {"expression": "3*n+2"},
    },
    {
        "code": "E-SYM-01",
        "task_type": "SYMBOLIC",
        "title": "De la regla a la expresión",
        "skill": "SYMBOLIC_GENERALIZATION",
        "difficulty": 3,
        "order_index": 50,
        "statement": {
            "prompt": "Si n es el número de mesas, escribe una expresión que dé el número de personas. Compruébala con las figuras que ya conoces.",
            "pattern": {"kind": "figural", "shape": "tables_chairs", "expression": "3*n+2", "shown_figures": [1, 2, 3]},
            "questions": [
                {
                    "id": "q1",
                    "kind": "generalize",
                    "text": "Escribe la expresión para n mesas.",
                    "representations": ["SYMBOLIC"],
                },
                {
                    "id": "q2",
                    "kind": "predict",
                    "text": "Usa tu expresión para calcular las personas con 25 mesas.",
                    "position": 25,
                    "representations": ["NUMERIC"],
                },
            ],
            "expected_time_ms": 300000,
        },
        "solution": {"expression": "3*n+2"},
    },
    {
        "code": "F-JUS-01",
        "task_type": "JUSTIFICATION",
        "title": "¿Por qué funciona tu regla?",
        "skill": "JUSTIFICATION",
        "difficulty": 3,
        "order_index": 60,
        "statement": {
            "prompt": "Ya tienes una regla para las mesas y sillas. Ahora convence a alguien que no la ha visto.",
            "pattern": {"kind": "figural", "shape": "tables_chairs", "expression": "3*n+2", "shown_figures": [1, 2, 3]},
            "questions": [
                {
                    "id": "q1",
                    "kind": "justify",
                    "text": "¿Cómo sabes que tu regla funciona para cualquier número de mesas, incluso uno que no has dibujado?",
                    "representations": ["VERBAL"],
                },
                {
                    "id": "q2",
                    "kind": "compare",
                    "text": "Otra persona dice: 'se suma 3 cada vez'. ¿En qué se parece a tu regla y en qué se diferencia?",
                    "representations": ["VERBAL"],
                },
            ],
            "expected_time_ms": 360000,
        },
        "solution": {
            "expression": "3*n+2",
            "notes": "Se observan: referencia a la estructura (3 por mesa + 2 extremos), generalidad, contraste recursivo/funcional.",
        },
    },
    {
        "code": "G-TRA-01",
        "task_type": "TRANSFER",
        "title": "Palillos en fila",
        "skill": "TRANSFER",
        "difficulty": 4,
        "order_index": 70,
        "related_task_code": "B-FIG-01",
        "statement": {
            "prompt": "Ahora se construyen triángulos en fila con palillos: 1 triángulo usa 3 palillos; 2 triángulos unidos usan 5; 3 triángulos usan 7.",
            "pattern": {"kind": "figural", "shape": "triangles_row", "expression": "2*n+1", "shown_figures": [1, 2, 3]},
            "questions": [
                {
                    "id": "q1",
                    "kind": "transfer_predict",
                    "text": "¿Cuántos palillos se usan con 15 triángulos?",
                    "position": 15,
                    "representations": ["NUMERIC", "TABULAR"],
                },
                {
                    "id": "q2",
                    "kind": "generalize",
                    "text": "Escribe una regla para n triángulos.",
                    "representations": ["SYMBOLIC", "VERBAL"],
                },
                {
                    "id": "q3",
                    "kind": "compare",
                    "text": "¿Qué tiene en común esta situación con la de las mesas y sillas? ¿Qué cambia?",
                    "representations": ["VERBAL"],
                },
            ],
            "expected_time_ms": 420000,
        },
        "solution": {
            "expression": "2*n+1",
            "notes": "Misma estructura (a·n + b) con otros valores; observar reutilización de la relación.",
        },
    },
]

# ------------------------------------------------------------------ ejemplos trabajados
# Usan un patrón DIFERENTE (cuadrados con palillos: 3n + 1 → 4, 7, 10) para no resolver la tarea.

EXAMPLES: list[dict[str, Any]] = [
    {
        "task_code": "B-FIG-01",
        "example_type": "FULL",
        "title": "Ejemplo resuelto: cuadrados con palillos",
        "order_index": 1,
        "content": {
            "situation": "Se forman cuadrados en fila con palillos: 1 cuadrado usa 4; 2 cuadrados unidos usan 7; 3 usan 10.",
            "steps": [
                "Observo qué cambia: cada cuadrado nuevo agrega 3 palillos.",
                "Observo qué se mantiene: siempre hay 1 palillo 'extra' al inicio.",
                "Relaciono con la posición: con n cuadrados hay 3 palillos por cuadrado más 1.",
                "Escribo la regla: 3n + 1.",
                "Compruebo con la figura 3: 3·3 + 1 = 10. ✓",
            ],
        },
    },
    {
        "task_code": "B-FIG-01",
        "example_type": "PARTIAL",
        "title": "Ejemplo parcialmente resuelto",
        "order_index": 2,
        "content": {
            "situation": "Cuadrados con palillos: 4, 7, 10, ...",
            "steps": [
                "Observo qué cambia: cada cuadrado nuevo agrega 3 palillos.",
                "Observo qué se mantiene: siempre hay 1 palillo extra.",
            ],
            "your_turn": "Completa tú: ¿cómo relacionas el número de cuadrados con el total de palillos? Escribe la regla y compruébala.",
        },
    },
    {
        "task_code": "B-FIG-01",
        "example_type": "HIDDEN_STEPS",
        "title": "Ejemplo con pasos ocultos",
        "order_index": 3,
        "content": {
            "situation": "Cuadrados con palillos: 4, 7, 10, ...",
            "steps": [
                {"text": "Observo qué cambia de una figura a la siguiente.", "hidden": False},
                {
                    "text": "Cada cuadrado nuevo agrega 3 palillos.",
                    "hidden": True,
                    "prompt": "¿Cuántos palillos se agregan? Anticipa antes de revelar.",
                },
                {
                    "text": "Hay 1 palillo que no depende del número de cuadrados.",
                    "hidden": True,
                    "prompt": "¿Qué parte de la figura no cambia?",
                },
                {"text": "Regla: 3n + 1.", "hidden": True, "prompt": "Escribe tu regla antes de revelar."},
            ],
        },
    },
    {
        "task_code": "B-FIG-01",
        "example_type": "SELF_EXPLANATION",
        "title": "Explica cada paso",
        "order_index": 4,
        "content": {
            "situation": "Cuadrados con palillos: 4, 7, 10, ...",
            "steps": [
                {
                    "text": "Cada cuadrado nuevo agrega 3 palillos.",
                    "prompt": "¿Por qué 3 y no 4, si un cuadrado tiene 4 lados?",
                },
                {"text": "Con n cuadrados hay 3n palillos más 1.", "prompt": "¿De dónde sale el +1?"},
            ],
        },
    },
    {
        "task_code": "B-FIG-01",
        "example_type": "STRATEGY_COMPARISON",
        "title": "Dos estrategias para el mismo patrón",
        "order_index": 5,
        "content": {
            "situation": "Cuadrados con palillos: 4, 7, 10, ...",
            "strategies": [
                {
                    "name": "Estrategia de Ana (recursiva)",
                    "steps": ["Empiezo en 4.", "Sumo 3 cada vez: 4, 7, 10, 13, 16..."],
                    "reaches": "Para 20 cuadrados tendría que sumar 3 diecinueve veces.",
                },
                {
                    "name": "Estrategia de Luis (funcional)",
                    "steps": ["Cada cuadrado aporta 3 palillos: 3·n.", "Más el palillo del inicio: 3n + 1."],
                    "reaches": "Para 20 cuadrados: 3·20 + 1 = 61 directamente.",
                },
            ],
            "prompt": "¿Para qué sirve mejor cada estrategia? ¿Cuál te ayuda con figuras muy lejanas?",
        },
    },
    {
        "task_code": "B-FIG-01",
        "example_type": "INTENTIONAL_ERROR",
        "title": "Encuentra el error",
        "order_index": 6,
        "content": {
            "situation": "Cuadrados con palillos: 4, 7, 10, ...",
            "steps": [
                "Cada cuadrado tiene 4 lados, así que con n cuadrados hay 4n palillos.",
                "Regla: 4n.",
                "Compruebo con 2 cuadrados: 4·2 = 8.",
            ],
            "prompt": "La comprobación no coincide con la figura (7 palillos). ¿Dónde está el error de razonamiento?",
            "error_hint_dimension": "Los cuadrados unidos comparten un lado.",
        },
    },
    {
        "task_code": "G-TRA-01",
        "example_type": "TRANSFER",
        "title": "Del ejemplo a una situación nueva",
        "order_index": 7,
        "content": {
            "situation": "Ya viste cuadrados (3n + 1) y mesas (3n + 2). Ambas tienen la forma 'algo por n, más algo fijo'.",
            "prompt": "En los triángulos con palillos, ¿qué parte depende de n y qué parte es fija? Usa esa idea antes de contar.",
        },
    },
]

# ------------------------------------------------------------------ banco de andamiajes
# Nivel 1 microayuda · 2 orientación · 3 andamiaje/división · 4 cambio de representación · 5 recuperación.

SCAFFOLDS: list[dict[str, Any]] = [
    {
        "code": "FOC-CHANGE-01",
        "scaffold_type": "FOCUSING",
        "level": 1,
        "applicable_task_types": ["NUMERIC_PATTERN", "FIGURAL_PATTERN", "TABLE"],
        "content": {
            "text": "Fíjate en cómo cambia la cantidad de la figura 2 a la figura 3. ¿Cuánto se agrega?",
            "variants": [
                "Compara dos figuras seguidas: ¿qué aparece nuevo en la segunda?",
                "Cuenta solo lo que se añadió al pasar de una figura a la siguiente.",
            ],
        },
    },
    {
        "code": "FOC-STAYS-01",
        "scaffold_type": "FOCUSING",
        "level": 1,
        "applicable_task_types": ["FIGURAL_PATTERN", "SYMBOLIC", "JUSTIFICATION"],
        "content": {
            "text": "Mira qué parte de la figura se mantiene igual sin importar cuántas mesas haya.",
            "variants": ["¿Hay algo que aparece en todas las figuras exactamente igual?"],
        },
    },
    {
        "code": "META-KNOWN-01",
        "scaffold_type": "METACOGNITIVE",
        "level": 1,
        "content": {
            "text": "Antes de seguir: ¿qué sabes ya con seguridad y qué te falta averiguar?",
            "variants": ["Haz una pausa. Di en una frase qué estás buscando."],
            "follow_up": "Escríbelo en 'Explicar mi razonamiento'.",
        },
    },
    {
        "code": "META-PAUSE-01",
        "scaffold_type": "METACOGNITIVE",
        "level": 1,
        "content": {
            "text": "Antes de responder, describe el patrón con tus palabras. Luego decide el número.",
            "variants": ["Tómate un momento: ¿qué regla estás usando para responder?"],
        },
    },
    {
        "code": "GUIDE-RELATE-01",
        "scaffold_type": "GUIDING_QUESTION",
        "level": 2,
        "applicable_task_types": ["FIGURAL_PATTERN", "SYMBOLIC", "TRANSFER", "TABLE"],
        "content": {
            "text": "¿Cómo podrías relacionar el número de la figura con la cantidad total de elementos?",
            "variants": [
                "Si te dicen el número de la figura, ¿qué operación haces para llegar al total?",
                "¿Qué tiene que ver la posición con la cantidad?",
            ],
            "follow_up": "Comprueba si esa relación funciona para una figura que todavía no aparece.",
        },
    },
    {
        "code": "GUIDE-CHECK-01",
        "scaffold_type": "GUIDING_QUESTION",
        "level": 2,
        "content": {
            "text": "¿Puedes comprobar si tu respuesta funciona con una figura que ya conoces?",
            "variants": ["Prueba tu idea con la figura 1 y con la figura 3. ¿Da lo que muestra el dibujo?"],
        },
    },
    {
        "code": "SELF-EXPL-01",
        "scaffold_type": "SELF_EXPLANATION",
        "level": 2,
        "content": {
            "text": "Explica en una frase por qué elegiste ese número. ¿Qué observaste para decidirlo?",
            "variants": ["Cuéntale a alguien cómo llegaste a tu respuesta, paso a paso."],
        },
    },
    {
        "code": "HINT-STRUCT-01",
        "scaffold_type": "HINT",
        "level": 3,
        "applicable_task_types": ["FIGURAL_PATTERN", "SYMBOLIC", "NUMERIC_PATTERN", "TRANSFER"],
        "content": {
            "text": "Pista: piensa en dos partes. Una parte crece con cada figura; otra parte no cambia. Separa las dos.",
            "variants": ["Divide el total en 'lo que se repite por cada figura' y 'lo que está una sola vez'."],
        },
    },
    {
        "code": "DIV-TASK-01",
        "scaffold_type": "TASK_DIVISION",
        "level": 3,
        "content": {
            "text": "Vamos por partes. Primero: ¿cuánto se agrega de una figura a la siguiente? Escribe solo ese número.",
            "variants": ["Paso 1 de 3: encuentra cuánto aumenta cada vez. Después seguimos."],
            "follow_up": "Paso 2: ¿cuántas veces se agrega hasta la figura que te piden? Paso 3: ¿qué falta sumar?",
        },
    },
    {
        "code": "ERR-REFLECT-01",
        "scaffold_type": "ERROR_REFLECTION",
        "level": 3,
        "content": {
            "text": "Tu respuesta no coincide con lo que muestra la figura 3. ¿Qué parte de tu cálculo podría estar contando de más o de menos?",
            "variants": ["Compara tu resultado con una figura que puedas contar. ¿Dónde aparece la diferencia?"],
        },
    },
    {
        "code": "REPR-TABLE-01",
        "scaffold_type": "REPRESENTATION_CHANGE",
        "level": 4,
        "applicable_task_types": ["FIGURAL_PATTERN", "NUMERIC_PATTERN", "SYMBOLIC", "TRANSFER"],
        "content": {
            "text": "Prueba con otra mirada: organiza en una tabla el número de la figura y la cantidad. ¿Qué ves en la columna de la cantidad?",
            "variants": ["Cambia de representación: usa la pestaña Tabla y escribe las figuras 1 a 5."],
        },
    },
    {
        "code": "REPR-GRAPH-01",
        "scaffold_type": "REPRESENTATION_CHANGE",
        "level": 4,
        "applicable_task_types": ["TABLE", "SYMBOLIC"],
        "content": {
            "text": "Lleva los datos de la tabla al gráfico. ¿Cómo se alinean los puntos? ¿Qué te dice eso de la regla?",
            "variants": ["Mira los puntos en el plano: ¿suben siempre lo mismo entre una figura y la siguiente?"],
        },
    },
    {
        "code": "STRAT-COMP-01",
        "scaffold_type": "STRATEGY_COMPARISON",
        "level": 4,
        "content": {
            "text": "Abre el ejemplo 'Dos estrategias'. ¿Cuál de las dos se parece a lo que estás haciendo? ¿Cuál te serviría más ahora?",
            "variants": ["Compara tu camino con las dos estrategias del ejemplo. ¿Qué cambiarías?"],
        },
    },
    {
        "code": "RECOV-EXAMPLE-01",
        "scaffold_type": "RECOVERY",
        "level": 5,
        "content": {
            "text": "Volvamos a un caso parecido: abre el ejemplo parcialmente resuelto y complétalo. Luego regresa a esta figura con la misma idea.",
            "variants": ["Trabaja primero el ejemplo de los cuadrados hasta el final; después vuelve aquí."],
            "follow_up": "¿Qué parte del ejemplo se parece a esta tarea?",
        },
    },
]


async def seed_catalog(db: AsyncSession) -> None:
    by_code: dict[str, Task] = {}
    for spec in TASKS:
        task = await db.scalar(select(Task).where(Task.code == spec["code"]))
        if task is None:
            task = Task(**{k: v for k, v in spec.items() if k != "related_task_code"})
            db.add(task)
            await db.flush()
        by_code[task.code] = task
    for spec in TASKS:
        related = spec.get("related_task_code")
        if related and related in by_code:
            by_code[spec["code"]].related_task_id = by_code[related].id
    for spec in EXAMPLES:
        task = by_code[spec["task_code"]]
        exists = await db.scalar(
            select(WorkedExample.id).where(
                WorkedExample.task_id == task.id,
                WorkedExample.example_type == spec["example_type"],
                WorkedExample.title == spec["title"],
            )
        )
        if exists is None:
            db.add(WorkedExample(task_id=task.id, **{k: v for k, v in spec.items() if k != "task_code"}))
    for spec in SCAFFOLDS:
        if await db.scalar(select(Scaffold.id).where(Scaffold.code == spec["code"])) is None:
            db.add(Scaffold(reviewed_by="equipo pedagógico (semilla)", **spec))
    await db.flush()
