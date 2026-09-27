"""Motor adaptativo (Sistema Tutor Inteligente).

Funciones PURAS sin acceso a base de datos ni red:

    evidence.extract_evidence   OBSERVAR   → Evidence (multiseñal, ventana configurable)
    bayes.infer                 INTERPRETAR→ Posterior P(estado | evidencias) — auxiliar
    rules.evaluate_rules        DECIDIR    → estado, nivel, tipo de intervención, fading (reglas legibles)
    scaffolding.select_scaffold ADAPTAR    → andamiaje concreto del banco con memoria de intervención
    decision.ScaffoldDecision   EXPLICAR   → qué observó, qué evidencia, qué estado, qué regla, por qué

``orchestrator.AdaptivePolicy`` conecta el motor con la persistencia (RECORDAR).
"""
