"""Módulo de identidad: instituciones, usuarios, perfiles por rol, consentimiento y tokens.

Este es el ÚNICO módulo que contiene datos personales. Los módulos de aprendizaje e investigación
solo referencian ``students.id``/``teachers.id`` (UUID opacos) y ``participant_code``.
"""
