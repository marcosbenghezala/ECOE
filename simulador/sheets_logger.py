import base64
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import gspread

from sheet_formatting import (
    formatear_hoja_resumen,
    formatear_hoja_detalle,
    formatear_hoja_raw_json,
)
try:
    from oauth2client.service_account import ServiceAccountCredentials
except Exception:  # pragma: no cover
    ServiceAccountCredentials = None  # type: ignore

FORMULA_SEPARATOR = os.getenv("SHEETS_FORMULA_SEPARATOR", ";")


@dataclass(frozen=True)
class SheetsConfig:
    enabled: bool
    spreadsheet_id: str
    credentials_json: str
    resumen_sheet_name: str = "RESUMEN"


class SheetsLogger:
    def __init__(self) -> None:
        """
        Inicializa conexión con Google Sheets usando:
        - GOOGLE_SHEETS_CREDENTIALS (JSON como string) o GOOGLE_SHEETS_CREDENTIALS_JSON
        - GOOGLE_SHEETS_SPREADSHEET_ID (o GOOGLE_SHEETS_ID como fallback)
        """
        self.config = _load_config()
        self.client = _build_gspread_client(self.config.credentials_json)
        self.spreadsheet = self.client.open_by_key(self.config.spreadsheet_id)

    def log_simulation(self, simulation_data: Dict[str, Any]) -> bool:
        """
        Guarda una simulación completa en Google Sheets.

        simulation_data incluye al menos:
            - student_name: str
            - student_email: str
            - case_name: str
            - duration_seconds: int
            - total_score: int (0-100 recomendado)
            - timestamp: str (ISO) (opcional)
            - conversation_evaluation: dict (opcional)
            - development_questions: list (opcional)
            - survey_responses: list | dict (opcional)
            - transcript: str | list[str] (opcional)
        """
        ok, _detail = self._log_simulation_internal(simulation_data)
        try:
            raw_ws = self.spreadsheet.worksheet("RAW_JSON")
            formatear_hoja_raw_json(raw_ws)
        except Exception:
            pass
        return ok

    def log_simulation_with_details(self, simulation_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        return self._log_simulation_internal(simulation_data)

    def append_survey_to_detail(self, detail_sheet_name: str, survey_responses: Any) -> None:
        if not self.config.enabled:
            return
        worksheet = self._get_or_raise(detail_sheet_name)
        start_row = len(worksheet.get_all_values()) + 1
        rows: List[List[str]] = []
        rows.append([""])
        rows.append(["🗳️ ENCUESTA FINAL"])
        rows.extend(_format_survey_responses(survey_responses))
        worksheet.update(f"A{start_row}", rows, value_input_option="USER_ENTERED")

    def _log_simulation_internal(self, simulation_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        if not self.config.enabled:
            return False, None

        detail_sheet_name, detail_gid = self._create_detail_sheet(simulation_data)
        row_number = self._add_summary_row(simulation_data, detail_sheet_name)
        self._write_detail_link(row_number, detail_gid)
        return True, {"title": detail_sheet_name, "gid": detail_gid}

    def _add_summary_row(self, data: Dict[str, Any], detail_sheet_name: str) -> int:
        """
        Añade una fila a 'RESUMEN' y devuelve el número de fila.
        """
        worksheet = self._get_or_raise(self.config.resumen_sheet_name)
        formatear_hoja_resumen(worksheet)

        timestamp = _as_str(data.get("timestamp")) or datetime.now(timezone.utc).isoformat()
        student_name = _as_str(data.get("student_name")) or "Sin nombre"
        student_email = _as_str(data.get("student_email")) or "sin-email"
        case_name = _as_str(data.get("case_name")) or "caso"

        duration_seconds = _as_int(data.get("duration_seconds"), default=0)
        duration_min = round(duration_seconds / 60.0, 1)
        score = _as_int(data.get("total_score"), default=0)

        values = [
            timestamp,
            student_name,
            student_email,
            case_name,
            duration_min,
            score,
            "Ver Detalles",
        ]

        # Append row and parse updatedRange to get row number.
        resp = worksheet.append_row(values, value_input_option="USER_ENTERED")
        row_number = _extract_row_number_from_append_response(resp)
        if row_number is None:
            # Fallback: safest guess is last non-empty row.
            row_number = len(worksheet.get_all_values())

        return row_number

    def _create_detail_sheet(self, data: Dict[str, Any]) -> Tuple[str, int]:
        """
        Crea una pestaña de detalle, escribe el contenido base y devuelve (nombre, gid).
        """
        student_name = _as_str(data.get("student_name")) or "Sin_nombre"
        ts = _as_str(data.get("timestamp")) or datetime.now(timezone.utc).isoformat()
        dt = _parse_dt(ts) or datetime.now(timezone.utc)

        sheet_name = _build_detail_sheet_name(student_name, dt)
        worksheet = self._create_unique_worksheet(sheet_name)
        self._format_detail_sheet(worksheet, data)
        return worksheet.title, int(worksheet.id)

    def _format_detail_sheet(self, worksheet: "gspread.Worksheet", data: Dict[str, Any]) -> None:
        """
        Escribe el contenido base y aplica un formato básico.
        """
        student_name = _as_str(data.get("student_name")) or "Sin nombre"
        student_email = _as_str(data.get("student_email")) or "sin-email"
        case_name = _as_str(data.get("case_name")) or "caso"
        timestamp = _as_str(data.get("timestamp")) or datetime.now(timezone.utc).isoformat()

        duration_seconds = _as_int(data.get("duration_seconds"), default=0)
        duration_min = round(duration_seconds / 60.0, 1)
        score = _as_int(data.get("total_score"), default=0)

        conversation_eval = data.get("conversation_evaluation")
        development_questions = data.get("development_questions")
        survey_responses = (
            data.get("survey_responses")
            or data.get("survey")
            or data.get("encuesta")
        )
        transcript = data.get("transcript")

        rows: List[List[str]] = []
        rows.append(["RESULTADO SIMULACIÓN ECOE"])
        rows.append([""])
        rows.append(["📋 INFORMACIÓN GENERAL"])
        rows.append([f"Estudiante: {student_name}"])
        rows.append([f"Email: {student_email}"])
        rows.append([f"Fecha: {timestamp}"])
        rows.append([f"Caso: {case_name}"])
        rows.append([f"Duración: {duration_min} min"])
        rows.append([""])
        rows.append([f"🎯 PUNTUACIÓN TOTAL: {score}/100"])
        rows.append([""])
        rows.append(["💬 EVALUACIÓN DE CONVERSACIÓN"])
        rows.extend(_format_conversation_eval(conversation_eval))
        rows.append([""])
        rows.append(["📝 PREGUNTAS DE DESARROLLO"])
        rows.extend(_format_development_questions(development_questions))
        rows.append([""])
        if survey_responses:
            rows.append(["🗳️ ENCUESTA FINAL"])
            rows.extend(_format_survey_responses(survey_responses))
            rows.append([""])
        rows.append(["🧾 TRANSCRIPCIÓN"])
        rows.extend(_format_transcript(transcript))

        worksheet.update("A1", rows, value_input_option="USER_ENTERED")

        try:
            formatear_hoja_detalle(worksheet)
        except Exception as e:
            print(f"[Sheets] ⚠️ No se pudo aplicar formato: {e}")

    def _write_detail_link(self, resumen_row_number: int, detail_gid: int) -> None:
        worksheet = self._get_or_raise(self.config.resumen_sheet_name)
        detail_url = f"https://docs.google.com/spreadsheets/d/{self.config.spreadsheet_id}/edit#gid={detail_gid}"
        formula = f'=HYPERLINK("{detail_url}"{FORMULA_SEPARATOR} "Ver Detalles")'
        worksheet.update(f"G{resumen_row_number}", [[formula]], value_input_option="USER_ENTERED")

    def _get_or_raise(self, sheet_name: str) -> "gspread.Worksheet":
        try:
            return self.spreadsheet.worksheet(sheet_name)
        except Exception as e:
            raise RuntimeError(
                f"No existe la pestaña '{sheet_name}'. Crea la hoja con cabeceras antes de usar SheetsLogger."
            ) from e

    def _create_unique_worksheet(self, base_title: str) -> "gspread.Worksheet":
        title = base_title[:90]
        for idx in range(0, 20):
            attempt = title if idx == 0 else f"{title}_{idx}"
            try:
                ws = self.spreadsheet.add_worksheet(title=attempt, rows=200, cols=10)
                return ws
            except Exception:
                continue
        raise RuntimeError("No se pudo crear pestaña de detalle (nombres colisionan).")

    def _set_column_width(self, worksheet: "gspread.Worksheet", column_index: int, pixel_size: int) -> None:
        # Google Sheets API uses 0-based indices.
        self.spreadsheet.batch_update(
            {
                "requests": [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": worksheet.id,
                                "dimension": "COLUMNS",
                                "startIndex": column_index,
                                "endIndex": column_index + 1,
                            },
                            "properties": {"pixelSize": pixel_size},
                            "fields": "pixelSize",
                        }
                    }
                ]
            }
        )


@lru_cache(maxsize=1)
def get_sheets_logger() -> SheetsLogger:
    return SheetsLogger()


def _load_config() -> SheetsConfig:
    enabled = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
    spreadsheet_id = (
        os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        or os.getenv("GOOGLE_SHEETS_ID")
        or os.getenv("GOOGLE_SHEETS_ID_RESULTADOS")
        or ""
    ).strip()

    credentials = os.getenv("GOOGLE_SHEETS_CREDENTIALS") or os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON") or ""
    credentials = credentials.strip()

    if not enabled:
        return SheetsConfig(enabled=False, spreadsheet_id=spreadsheet_id, credentials_json=credentials)

    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID no configurado")

    if not credentials:
        raise ValueError("GOOGLE_SHEETS_CREDENTIALS no configurado")

    return SheetsConfig(enabled=True, spreadsheet_id=spreadsheet_id, credentials_json=credentials)


def _build_gspread_client(credentials_json: str) -> "gspread.Client":
    creds_dict = _parse_credentials_json(credentials_json)
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    if ServiceAccountCredentials is not None:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes=scopes)
        return gspread.authorize(creds)

    # Fallback moderno (google-auth), por si oauth2client no está disponible.
    return gspread.service_account_from_dict(creds_dict)


def _parse_credentials_json(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("{"):
        return json.loads(raw)

    # Permitir base64 opcional (útil en algunos deploys)
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        if decoded.strip().startswith("{"):
            return json.loads(decoded)
    except Exception:
        pass

    raise ValueError("GOOGLE_SHEETS_CREDENTIALS no es JSON válido (ni base64 JSON).")


def _build_detail_sheet_name(student_name: str, dt: datetime) -> str:
    safe_name = _slugify(student_name)
    suffix = dt.strftime("%Y%m%d_%H%M%S")
    return f"{safe_name}_{suffix}"


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.strip().lower()
    text = re.sub(r"\\s+", "_", text)
    text = re.sub(r"[^a-z0-9_]+", "", text)
    return text or "estudiante"


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    s = _as_str(value)
    try:
        return int(float(s))
    except Exception:
        return default


def _parse_dt(value: str) -> Optional[datetime]:
    v = (value or "").strip()
    if not v:
        return None
    try:
        # Soportar ISO con/ sin zona.
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _extract_row_number_from_append_response(resp: Any) -> Optional[int]:
    if not isinstance(resp, dict):
        return None
    updates = resp.get("updates") or {}
    updated_range = updates.get("updatedRange") or ""
    if not isinstance(updated_range, str):
        return None
    # Example: 'RESUMEN!A12:G12'
    match = re.search(r"!A(\\d+):", updated_range)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _format_conversation_eval(conversation_eval: Any) -> List[List[str]]:
    if conversation_eval is None:
        return [["(Sin datos)"]]
    if isinstance(conversation_eval, str):
        return [[conversation_eval]]
    try:
        pretty = json.dumps(conversation_eval, ensure_ascii=False, indent=2)
        return [[pretty]]
    except Exception:
        return [[str(conversation_eval)]]


def _format_development_questions(questions: Any) -> List[List[str]]:
    if not questions:
        return [["(Sin preguntas)"]]
    if isinstance(questions, list):
        if all(isinstance(q, dict) for q in questions):
            rows = [["Pregunta", "Respuesta del estudiante"]]
            for q in questions:
                pregunta = _as_str(
                    q.get("pregunta")
                    or q.get("question")
                    or q.get("titulo")
                    or q.get("title")
                )
                respuesta = _as_str(
                    q.get("respuesta")
                    or q.get("answer")
                    or q.get("respuesta_estudiante")
                )
                if not pregunta and not respuesta:
                    continue
                rows.append([pregunta or "-", respuesta])
            return rows if len(rows) > 1 else [["(Sin preguntas)"]]

        out = []
        for q in questions:
            s = _as_str(q)
            if s:
                out.append([f"- {s}"])
        return out or [["(Sin preguntas)"]]
    return [[_as_str(questions) or "(Sin preguntas)"]]


def _format_survey_responses(survey: Any) -> List[List[str]]:
    if not survey:
        return [["(Sin respuestas)"]]

    if isinstance(survey, dict):
        survey = survey.get("responses") or survey.get("respuestas") or survey

    if isinstance(survey, list):
        if all(isinstance(q, dict) for q in survey):
            rows = [["Pregunta", "Respuesta del estudiante"]]
            for q in survey:
                pregunta = _as_str(
                    q.get("pregunta")
                    or q.get("question")
                    or q.get("titulo")
                    or q.get("title")
                )
                respuesta = _as_str(
                    q.get("respuesta")
                    or q.get("answer")
                    or q.get("respuesta_estudiante")
                    or q.get("valor")
                )
                if not pregunta and not respuesta:
                    continue
                rows.append([pregunta or "-", respuesta])
            return rows if len(rows) > 1 else [["(Sin respuestas)"]]

        out = []
        for q in survey:
            s = _as_str(q)
            if s:
                out.append([f"- {s}"])
        return out or [["(Sin respuestas)"]]

    return [[_as_str(survey) or "(Sin respuestas)"]]


def _format_transcript(transcript: Any) -> List[List[str]]:
    if not transcript:
        return [["(Sin transcripción)"]]

    if isinstance(transcript, list):
        lines = [_as_str(x) for x in transcript if _as_str(x)]
    else:
        text = _as_str(transcript)
        lines = [line.strip() for line in text.splitlines() if line.strip()]

    return [[line] for line in lines] if lines else [["(Sin transcripción)"]]
