#!/usr/bin/env python3
"""
Script manual para crear un libro de prueba y aplicar formatos.
Requiere credenciales de Google Sheets (GOOGLE_SHEETS_CREDENTIALS_JSON)
y permiso de escritura en la cuenta.
"""
import os
import json
import sys
from datetime import datetime
from pathlib import Path

import gspread

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sheet_formatting import (
    formatear_hoja_resumen,
    formatear_hoja_detalle,
    formatear_hoja_raw_json,
)


def _load_credentials() -> dict:
    raw = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON") or os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not raw:
        raise RuntimeError("Faltan credenciales GOOGLE_SHEETS_CREDENTIALS_JSON.")
    raw = raw.strip()
    if raw.startswith("{"):
        return json.loads(raw)
    raise RuntimeError("Credenciales no estan en JSON.")


def main() -> None:
    creds = _load_credentials()
    client = gspread.service_account_from_dict(creds)
    sh = client.create(f"ECOE_Formato_Demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    resumen = sh.sheet1
    resumen.update_title("RESUMEN")
    formatear_hoja_resumen(resumen, end_row=20)

    resumen.update(
        "A2:K4",
        [
            [
                "2025-01-15 10:30",
                "Maria Garcia",
                "maria@example.com",
                "Dolor Toracico",
                12,
                "75/100",
                75,
                "12/16",
                68,
                4.2,
                "Ver Detalles",
            ],
            [
                "2025-01-15 11:45",
                "Carlos Rodriguez",
                "carlos@example.com",
                "Cefalea Aguda",
                15,
                "82/100",
                82,
                "14/16",
                85,
                4.5,
                "Ver Detalles",
            ],
            [
                "2025-01-15 14:20",
                "Ana Martinez",
                "ana@example.com",
                "Dolor Abdominal",
                10,
                "45/100",
                45,
                "6/16",
                35,
                3.1,
                "Ver Detalles",
            ],
        ],
        value_input_option="USER_ENTERED",
    )

    detalle = sh.add_worksheet(title="Detalle_1", rows=200, cols=10)
    detalle.update(
        "A1",
        [
            ["📋 DATOS DE LA SIMULACIÓN"],
            ["Estudiante", "Maria Garcia"],
            ["Email", "maria@example.com"],
            ["Fecha", "2025-01-15 10:30"],
            ["Caso", "Dolor Torácico - Síndrome Coronario Agudo"],
            ["Duración", "12 minutos"],
            [""],
            ["📊 RESUMEN DE RESULTADOS"],
            ["Métrica", "Valor", "Porcentaje"],
            ["Puntuación Total", "75/100", "75%"],
            ["Ítems Críticos", "12/16", "75%"],
            ["Media Desarrollo", "68/100", "68%"],
            ["Satisfacción", "4.2/5", "84%"],
            [""],
            ["🔴 ÍTEMS CRÍTICOS"],
            ["ID", "Descripción", "Capa", "¿Hecho?", "Puntos"],
            ["C01", "Preguntar por características del dolor", "PRINCIPAL", "✔", "5/5"],
            ["C02", "Indagar sobre síntomas acompañantes", "PRINCIPAL", "✔", "5/5"],
            ["C03", "Preguntar por antecedentes cardiovasculares", "PRINCIPAL", "✔", "5/5"],
            ["C04", "Explorar factores de riesgo cardiovascular", "PRINCIPAL", "✖", "0/5"],
            ["C05", "Descartar origen musculoesquelético", "DIFERENCIAL", "✔", "5/5"],
            ["C06", "Preguntar por traumatismos recientes", "DIFERENCIAL", "✖", "0/5"],
            ["C07", "Investigar síntomas respiratorios asociados", "SCREENING", "✔", "5/5"],
            ["C08", "Preguntar sobre consumo de tóxicos", "SCREENING", "✖", "0/5"],
            [""],
            ["📝 PREGUNTAS DE DESARROLLO"],
            ["#", "Pregunta", "Respuesta", "Score"],
            ["1", "Diagnóstico diferencial principal", "IAM, considerar TEP y disección aórtica.", 85],
            ["2", "Pruebas complementarias urgentes", "ECG, troponinas, analítica básica.", 92],
            ["3", "Actitud terapéutica inicial", "Monitorización, AAS, nitroglicerina.", 78],
            ["4", "Signos de alarma", "Inestabilidad hemodinámica.", 45],
            [""],
            ["💬 TRANSCRIPCIÓN"],
            ["#", "Rol", "Texto"],
            [1, "ESTUDIANTE", "Buenos días, soy el estudiante de medicina."],
            [2, "PACIENTE", "Me duele el pecho desde hace dos horas."],
            [3, "ESTUDIANTE", "¿Puede describir el dolor?"],
            [4, "PACIENTE", "Es opresivo y me irradia al brazo."],
            [5, "ESTUDIANTE", "¿Ha tenido sudoración o náuseas?"],
            [6, "PACIENTE", "Sí, he sudado mucho."],
            [7, "ESTUDIANTE", "¿Tiene antecedentes de hipertensión?"],
            [8, "PACIENTE", "Soy hipertenso y fumador."],
            [""],
            ["⭐ ENCUESTA DE SATISFACCIÓN"],
            ["Media general:", "4.2 / 5"],
            [""],
            ["Pregunta", "Respuesta"],
            ["El caso clínico me pareció realista", "4 / 5"],
            ["Las instrucciones fueron claras", "5 / 5"],
            ["El tiempo disponible fue adecuado", "3 / 5"],
            ["El sistema respondió de forma coherente", "5 / 5"],
            ["Recomendaría esta herramienta a otros estudiantes", "4 / 5"],
            [""],
            ["Comentario abierto:"],
            ["Me ha gustado mucho la experiencia."],
            [""],
            ["¿Qué mejorarías?"],
            ["Añadir más variedad de casos."],
        ],
        value_input_option="USER_ENTERED",
    )
    formatear_hoja_detalle(detalle)

    raw = sh.add_worksheet(title="RAW_JSON", rows=100, cols=4)
    formatear_hoja_raw_json(raw)
    raw.update(
        "A5:D5",
        [
            [
                "Maria Garcia",
                "2025-01-15 10:30",
                "{\"total_score\": 75, \"max_score\": 100}",
                "{\"satisfaccion_media\": 4.2}",
            ]
        ],
        value_input_option="USER_ENTERED",
    )

    print(f"Libro creado: {sh.url}")


if __name__ == "__main__":
    main()
