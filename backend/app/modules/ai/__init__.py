"""IA generativa OPCIONAL y subordinada (Fase 7).

El LLM nunca decide si intervenir, cuándo ni con qué nivel: esas decisiones ya las tomó el motor de
reglas. Solo produce PROPUESTAS (reformular una ayuda del banco, interpretar una explicación con un
vocabulario cerrado) que pasan por tres validadores (pedagógico, seguridad, dominio). Nada no
validado llega al estudiante; ante cualquier rechazo o fallo se usa el banco (fallback). Cada llamada
queda registrada en ``learning.ai_interactions``.
"""
