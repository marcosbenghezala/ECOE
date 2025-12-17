"""
Utilidades para procesamiento de texto - VERSIÓN CANÓNICA V2
Consolidado desde checklist_evaluator_v2.py para evitar duplicación.

Regla CRÍTICA: evaluar SOLO líneas del [ESTUDIANTE], ignorar [PACIENTE].
"""

import re
import unicodedata
from typing import Any, Dict, List


def normalize_text(text: str) -> str:
    """
    Normaliza texto para matching:
    - Minúsculas
    - Sin acentos (NFD decomposition)
    - Puntuación → espacios
    - Espacios normalizados

    Args:
        text: Texto a normalizar

    Returns:
        Texto normalizado

    Examples:
        >>> normalize_text("¿Cómo está?")
        'como esta'
        >>> normalize_text("  Múltiples   espacios  ")
        'multiples espacios'
    """
    if not text:
        return ""

    text = text.lower()

    # Eliminar acentos (NFD decomposition)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))

    # Reemplazar puntuación por espacios
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)

    # Normalizar espacios múltiples
    text = re.sub(r"\s+", " ", text, flags=re.UNICODE)

    return text.strip()


def extract_student_lines(transcript: str) -> List[str]:
    """
    Extrae SOLO las líneas del [ESTUDIANTE].

    CRÍTICO: Ignorar líneas del [PACIENTE] para evitar falsos positivos.

    Soporta formatos:
    - [ESTUDIANTE]: texto
    - [ESTUDIANTE] texto
    - [STUDENT]: texto (legacy, inglés)
    - [STUDENT] texto

    Args:
        transcript: Transcripción con tags de speaker

    Returns:
        Lista de líneas del estudiante (sin tags)

    Examples:
        >>> extract_student_lines("[ESTUDIANTE]: Hola\\n[PACIENTE]: Hola")
        ['Hola']
        >>> extract_student_lines("[ESTUDIANTE] Hola\\n[ESTUDIANTE]: ¿Qué tal?")
        ['Hola', '¿Qué tal?']
    """
    student_lines: List[str] = []

    for raw_line in transcript.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Detectar [ESTUDIANTE] con o sin ":"
        if line.startswith("[ESTUDIANTE]"):
            content = line[len("[ESTUDIANTE]") :].lstrip()
            if content.startswith(":"):
                content = content[1:].lstrip()
            if content:
                student_lines.append(content)
            continue

        # Detectar [STUDENT] (legacy, inglés)
        if line.startswith("[STUDENT]"):
            content = line[len("[STUDENT]") :].lstrip()
            if content.startswith(":"):
                content = content[1:].lstrip()
            if content:
                student_lines.append(content)
            continue

    # Fallback: si no hay tags, asumir que todo es del estudiante (MVP)
    if not student_lines and transcript.strip():
        student_lines = [transcript.strip()]

    return student_lines


def preprocess_transcript(transcript: str) -> Dict[str, Any]:
    """
    Preprocesa transcripción para evaluación.

    Pipeline:
    1. Extrae solo líneas del estudiante
    2. Normaliza cada línea
    3. Combina en texto único normalizado

    Args:
        transcript: Transcripción completa con tags

    Returns:
        {
            "student_lines": [...],  # Líneas originales del estudiante
            "student_lines_normalized": [...],  # Líneas normalizadas
            "student_text_normalized": "..."  # Texto concatenado normalizado
        }

    Examples:
        >>> result = preprocess_transcript("[ESTUDIANTE]: ¿Hola, cómo está?")
        >>> result["student_text_normalized"]
        'hola como esta'
        >>> len(result["student_lines"])
        1
    """
    student_lines = extract_student_lines(transcript)
    normalized_lines = [normalize_text(line) for line in student_lines]
    combined_normalized = " ".join(line for line in normalized_lines if line)

    return {
        "student_lines": student_lines,
        "student_lines_normalized": normalized_lines,
        "student_text_normalized": combined_normalized,
    }
