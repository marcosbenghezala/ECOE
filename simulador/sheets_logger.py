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
            - timestamp: str (ISO) (opcional)
            - evaluation_result: dict (schema evaluation.production.v1)
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
        values = worksheet.get_all_values()
        survey_row = _find_row(values, ["encuesta de satisfaccion", "encuesta"])
        likert, abiertas, media = _split_survey_responses(survey_responses)
        rows: List[List[str]] = []
        if survey_row:
            start_row = survey_row + 1
        else:
            start_row = len(values) + 1
            rows.append(["⭐ ENCUESTA DE SATISFACCIÓN"])
        rows.append(["Media general:", f"{_as_float(media, default=0.0)} / 5"])
        rows.append([""])
        rows.append(["Pregunta", "Respuesta"])
        for item in likert:
            rows.append([_as_str(item.get("pregunta")) or "-", f"{_as_int(item.get('valor'), default=0)} / 5"])
        for item in abiertas:
            rows.append([""])
            rows.append([_as_str(item.get("pregunta")) or "-"])
            rows.append([_as_str(item.get("respuesta")) or ""])
        worksheet.update(f"A{start_row}", rows, value_input_option="USER_ENTERED")
        _update_summary_satisfaction(worksheet, media)
        self._update_resumen_encuesta_by_gid(int(worksheet.id), media)
        try:
            formatear_hoja_detalle(worksheet)
        except Exception:
            pass

    def _log_simulation_internal(self, simulation_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        if not self.config.enabled:
            return False, None

        sim = _build_simulation_report(simulation_data)
        detail_sheet_name, detail_gid = self._create_detail_sheet(sim)
        self._add_summary_row(sim, detail_gid)
        return True, {"title": detail_sheet_name, "gid": detail_gid}

    def _add_summary_row(self, sim: Dict[str, Any], detail_gid: int) -> int:
        """
        Añade una fila a 'RESUMEN' y devuelve el número de fila.
        """
        worksheet = self._get_or_create_resumen()
        try:
            formatear_hoja_resumen(worksheet)
        except Exception as e:
            print(f"[Sheets] ⚠️ No se pudo aplicar formato RESUMEN: {e}")

        detail_url = f"https://docs.google.com/spreadsheets/d/{self.config.spreadsheet_id}/edit#gid={detail_gid}"
        formula = f'=HYPERLINK("{detail_url}"{FORMULA_SEPARATOR} "Ver →")'

        values = [
            _as_str(sim.get("timestamp")) or datetime.now(timezone.utc).isoformat(),
            _as_str(sim.get("estudiante")) or "Sin nombre",
            _as_str(sim.get("email")) or "sin-email",
            _as_str(sim.get("caso")) or "caso",
            _as_int(sim.get("duracion"), default=0),
            f"{_as_int(sim.get('score_total'), default=0)}/{_as_int(sim.get('score_max'), default=0)}",
            _as_int(sim.get("pct_conversacion"), default=0),
            f"{_as_int(sim.get('criticos_hechos'), default=0)}/{_as_int(sim.get('criticos_total'), default=0)}",
            _as_int(sim.get("media_desarrollo"), default=0),
            _as_float(sim.get("media_encuesta"), default=0.0),
            formula,
        ]

        try:
            resp = worksheet.append_row(values, value_input_option="USER_ENTERED")
            row_number = _extract_row_number_from_append_response(resp)
            if row_number is None:
                row_number = len(worksheet.get_all_values())
        except Exception as e:
            print(f"[Sheets] ⚠️ append_row falló, usando update directo: {e}")
            row_number = len(worksheet.get_all_values()) + 1
            worksheet.update(
                f"A{row_number}:K{row_number}",
                [values],
                value_input_option="USER_ENTERED",
            )

        return row_number

    def _create_detail_sheet(self, sim: Dict[str, Any]) -> Tuple[str, int]:
        """
        Crea una pestaña de detalle, escribe el contenido base y devuelve (nombre, gid).
        """
        student_name = _as_str(sim.get("estudiante")) or "Sin_nombre"
        ts = _as_str(sim.get("timestamp")) or datetime.now(timezone.utc).isoformat()
        dt = _parse_dt(ts) or datetime.now(timezone.utc)

        sheet_name = _build_detail_sheet_name(student_name, dt)
        worksheet = self._create_unique_worksheet(sheet_name)
        self._format_detail_sheet(worksheet, sim)
        return worksheet.title, int(worksheet.id)

    def _format_detail_sheet(self, worksheet: "gspread.Worksheet", sim: Dict[str, Any]) -> None:
        """
        Escribe el contenido base y aplica un formato básico.
        """
        rows = _build_detail_rows(sim)
        worksheet.update("A1", rows, value_input_option="USER_ENTERED")

        try:
            formatear_hoja_detalle(worksheet)
        except Exception as e:
            print(f"[Sheets] ⚠️ No se pudo aplicar formato: {e}")

    def _write_detail_link(self, resumen_row_number: int, detail_gid: int) -> None:
        worksheet = self._get_or_raise(self.config.resumen_sheet_name)
        detail_url = f"https://docs.google.com/spreadsheets/d/{self.config.spreadsheet_id}/edit#gid={detail_gid}"
        formula = f'=HYPERLINK("{detail_url}"{FORMULA_SEPARATOR} "Ver →")'
        worksheet.update(f"K{resumen_row_number}", [[formula]], value_input_option="USER_ENTERED")

    def _get_or_raise(self, sheet_name: str) -> "gspread.Worksheet":
        try:
            return self.spreadsheet.worksheet(sheet_name)
        except Exception as e:
            raise RuntimeError(
                f"No existe la pestaña '{sheet_name}'. Crea la hoja con cabeceras antes de usar SheetsLogger."
            ) from e

    def _get_or_create_resumen(self) -> "gspread.Worksheet":
        try:
            worksheet = self.spreadsheet.worksheet(self.config.resumen_sheet_name)
        except Exception:
            worksheet = self.spreadsheet.add_worksheet(
                title=self.config.resumen_sheet_name,
                rows=200,
                cols=11,
            )
        try:
            _ensure_resumen_headers(worksheet)
        except Exception as e:
            print(f"[Sheets] ⚠️ No se pudieron asegurar cabeceras RESUMEN: {e}")
        return worksheet

    def _update_resumen_encuesta_by_gid(self, detail_gid: int, media: float) -> None:
        try:
            resumen_ws = self._get_or_create_resumen()
            values = resumen_ws.get_all_values()
        except Exception:
            return

        target = f"gid={detail_gid}"
        for idx, row in enumerate(values, 1):
            if any(target in (cell or "") for cell in row):
                resumen_ws.update(
                    f"J{idx}",
                    [[_as_float(media, default=0.0)]],
                    value_input_option="USER_ENTERED",
                )
                return

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


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    s = _as_str(value)
    try:
        return float(s)
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


def _ensure_resumen_headers(worksheet: "gspread.Worksheet") -> None:
    headers = [
        "Timestamp",
        "Estudiante",
        "Email",
        "Caso",
        "Min",
        "Score",
        "%Conv",
        "Críticos",
        "Desarrollo",
        "Encuesta",
        "Ver",
    ]
    existing = worksheet.row_values(1)
    if existing[: len(headers)] != headers:
        worksheet.update("A1:K1", [headers], value_input_option="USER_ENTERED")


def _normalize_text(value: Any) -> str:
    text = _as_str(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _find_row(values: List[List[str]], labels: List[str]) -> Optional[int]:
    normalized_labels = [_normalize_text(label) for label in labels]
    for idx, row in enumerate(values, 1):
        if not row:
            continue
        cell = _normalize_text(row[0])
        for label in normalized_labels:
            if label and label in cell:
                return idx
    return None


def _build_simulation_report(data: Dict[str, Any]) -> Dict[str, Any]:
    eval_result = data.get("evaluation_result") or {}
    if not isinstance(eval_result, dict):
        eval_result = {}

    schema_version = eval_result.get("schema_version")
    if schema_version != "evaluation.production.v1":
        raise ValueError(f"Unsupported schema_version: {schema_version!r}")

    scores = eval_result.get("scores") or {}
    global_scores = scores.get("global") or {}
    checklist_scores = scores.get("checklist") or {}
    development_scores = scores.get("development") or {}

    timestamp = _as_str(data.get("timestamp") or eval_result.get("timestamp")) or datetime.now(timezone.utc).isoformat()
    estudiante = _as_str(data.get("student_name") or data.get("estudiante") or "")
    email = _as_str(data.get("student_email") or data.get("email") or "")
    caso = _as_str(data.get("case_name") or data.get("caso") or "")

    duration_seconds = _as_int(data.get("duration_seconds"), default=0)
    duracion = int(round(duration_seconds / 60.0)) if duration_seconds else _as_int(data.get("duracion"), default=0)

    score_total = _as_int(global_scores.get("score"), default=0)
    score_max = _as_int(global_scores.get("max"), default=100)
    pct_conversacion = _as_int(checklist_scores.get("percentage"), default=0)

    items_criticos = _extract_items_criticos_production(eval_result)
    criticos_hechos = _count_criticos_done(items_criticos)
    criticos_total = len(items_criticos)

    preguntas_desarrollo = _build_preguntas_desarrollo_production(eval_result)
    media_desarrollo = _as_int(
        development_scores.get("percentage"),
        default=_media_desarrollo_from_questions(preguntas_desarrollo),
    )

    encuesta_likert, encuesta_abiertas, media_encuesta = _split_survey_responses(
        data.get("survey_responses") or data.get("survey") or data.get("encuesta") or eval_result.get("survey")
    )

    prod_survey = eval_result.get("survey") or {}
    if prod_survey:
        encuesta_likert = prod_survey.get("likert") or []
        encuesta_abiertas = prod_survey.get("open") or []
        media_encuesta = _as_float(prod_survey.get("average"), default=media_encuesta)

    transcripcion = _parse_transcripcion(data.get("transcript") or data.get("transcripcion"))

    return {
        "timestamp": timestamp,
        "estudiante": estudiante or "Sin nombre",
        "email": email or "sin-email",
        "caso": caso or "caso",
        "duracion": duracion,
        "score_total": score_total,
        "score_max": score_max,
        "pct_conversacion": pct_conversacion,
        "criticos_hechos": criticos_hechos,
        "criticos_total": criticos_total,
        "media_desarrollo": media_desarrollo,
        "media_encuesta": media_encuesta,
        "items_criticos": items_criticos,
        "preguntas_desarrollo": preguntas_desarrollo,
        "transcripcion": transcripcion,
        "encuesta_likert": encuesta_likert,
        "encuesta_abiertas": encuesta_abiertas,
    }


def _extract_items_criticos_production(eval_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in eval_result.get("items", []) or []:
        if not item.get("critical"):
            continue
        out.append(
            {
                "id": _as_str(item.get("id")) or "-",
                "descripcion": _as_str(item.get("descripcion")) or "-",
                "capa": _as_str(item.get("bloque")) or "-",
                "done": bool(item.get("done")),
                "score": _as_int(item.get("score"), default=0),
                "max_score": _as_int(item.get("max_score"), default=0),
            }
        )
    return out


def _count_criticos_done(items: List[Dict[str, Any]]) -> int:
    return sum(1 for item in items if item.get("done"))


def _build_preguntas_desarrollo_production(eval_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    questions = (eval_result.get("development") or {}).get("questions") or []
    out: List[Dict[str, Any]] = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        pregunta = _as_str(item.get("question") or item.get("pregunta"))
        respuesta = _as_str(item.get("answer") or item.get("respuesta"))
        score = _as_int(item.get("score"), default=0)
        if pregunta or respuesta or score:
            out.append(
                {
                    "pregunta": pregunta or "-",
                    "respuesta": respuesta,
                    "score": score,
                }
            )
    return out


def _media_desarrollo_from_questions(questions: List[Dict[str, Any]]) -> int:
    if not questions:
        return 0
    scores = [_as_int(q.get("score"), default=0) for q in questions]
    return int(round(sum(scores) / len(scores))) if scores else 0


def _split_survey_responses(survey: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float]:
    if not survey:
        return [], [], 0.0

    if isinstance(survey, dict):
        media = _as_float(survey.get("media_satisfaccion"), default=0.0)
        likert = survey.get("likert") or survey.get("likert_responses") or []
        abiertas = survey.get("abiertas") or survey.get("open") or []
    else:
        media = 0.0
        likert = []
        abiertas = []

    if isinstance(survey, dict) and not likert and not abiertas:
        payload = survey.get("responses") or survey.get("respuestas")
        if payload:
            survey = payload

    if isinstance(survey, list):
        for item in survey:
            if not isinstance(item, dict):
                continue
            pregunta = _as_str(item.get("pregunta") or item.get("question") or item.get("titulo"))
            valor = item.get("valor") or item.get("score") or item.get("value")
            respuesta = item.get("respuesta")
            if valor is None and isinstance(respuesta, str) and respuesta.strip().isdigit():
                valor = respuesta.strip()
            if valor is not None and isinstance(valor, (int, float, str)):
                likert.append({"pregunta": pregunta or "-", "valor": _as_int(valor, default=0)})
                continue
            respuesta = _as_str(item.get("respuesta") or item.get("answer") or item.get("texto"))
            if pregunta or respuesta:
                abiertas.append({"pregunta": pregunta or "-", "respuesta": respuesta})

    if isinstance(likert, list) and likert:
        cleaned = []
        for item in likert:
            if not isinstance(item, dict):
                continue
            pregunta = _as_str(item.get("pregunta") or item.get("question") or item.get("titulo"))
            valor = _as_int(item.get("valor") or item.get("value") or item.get("score"), default=0)
            cleaned.append({"pregunta": pregunta or "-", "valor": valor})
        likert = cleaned

    if isinstance(abiertas, list) and abiertas:
        cleaned = []
        for item in abiertas:
            if not isinstance(item, dict):
                continue
            pregunta = _as_str(item.get("pregunta") or item.get("question") or item.get("titulo"))
            respuesta = _as_str(item.get("respuesta") or item.get("answer") or item.get("texto"))
            if pregunta or respuesta:
                cleaned.append({"pregunta": pregunta or "-", "respuesta": respuesta})
        abiertas = cleaned

    if media <= 0 and likert:
        media = round(sum(item.get("valor", 0) for item in likert) / max(len(likert), 1), 2)

    return likert, abiertas, media


def _parse_transcripcion(transcript: Any) -> List[Dict[str, Any]]:
    if not transcript:
        return []

    if isinstance(transcript, list):
        if all(isinstance(item, dict) for item in transcript):
            out = []
            for idx, item in enumerate(transcript, 1):
                rol = _as_str(item.get("rol") or item.get("role") or "")
                texto = _as_str(item.get("texto") or item.get("text") or "")
                out.append({"turno": idx, "rol": rol or "DESCONOCIDO", "texto": texto})
            return out
        lines = [_as_str(item) for item in transcript if _as_str(item)]
    else:
        text = _as_str(transcript)
        lines = [line.strip() for line in text.splitlines() if line.strip()]

    out: List[Dict[str, Any]] = []
    for idx, line in enumerate(lines, 1):
        rol, texto = _split_role_line(line)
        out.append({"turno": idx, "rol": rol, "texto": texto})
    return out


def _split_role_line(line: str) -> Tuple[str, str]:
    raw = line.strip()
    if not raw:
        return "DESCONOCIDO", ""
    variants = [
        ("[ESTUDIANTE]", "ESTUDIANTE"),
        ("[PACIENTE]", "PACIENTE"),
        ("ESTUDIANTE:", "ESTUDIANTE"),
        ("PACIENTE:", "PACIENTE"),
        ("ESTUDIANTE", "ESTUDIANTE"),
        ("PACIENTE", "PACIENTE"),
    ]
    upper = raw.upper()
    for prefix, role in variants:
        if upper.startswith(prefix):
            texto = raw[len(prefix):].lstrip(" :-")
            return role, texto or raw
    return "DESCONOCIDO", raw


def _build_detail_rows(sim: Dict[str, Any]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    width = 5

    def pad(values: List[Any]) -> List[Any]:
        return values + [""] * (width - len(values))

    rows.append(pad(["📋 DATOS DE LA SIMULACIÓN"]))
    ficha = [
        ("Estudiante", sim.get("estudiante")),
        ("Email", sim.get("email")),
        ("Fecha", sim.get("timestamp")),
        ("Caso", sim.get("caso")),
        ("Duración", f"{_as_int(sim.get('duracion'), default=0)} minutos"),
    ]
    for label, value in ficha:
        rows.append(pad([label, _as_str(value)]))
    rows.append(pad([""]))

    rows.append(pad(["📊 RESUMEN DE RESULTADOS"]))
    rows.append(pad(["Métrica", "Valor", "Porcentaje"]))
    resultados = [
        ("Puntuación Total", f"{_as_int(sim.get('score_total'), default=0)}/{_as_int(sim.get('score_max'), default=0)}",
         _as_int(sim.get("pct_conversacion"), default=0)),
        ("Ítems Críticos", f"{_as_int(sim.get('criticos_hechos'), default=0)}/{_as_int(sim.get('criticos_total'), default=0)}",
         _ratio_pct(sim.get("criticos_hechos"), sim.get("criticos_total"))),
        ("Media Desarrollo", f"{_as_int(sim.get('media_desarrollo'), default=0)}/100",
         _as_int(sim.get("media_desarrollo"), default=0)),
        ("Satisfacción", f"{_as_float(sim.get('media_encuesta'), default=0.0)}/5",
         _ratio_pct(sim.get("media_encuesta"), 5)),
    ]
    for metrica, valor, pct in resultados:
        rows.append(pad([metrica, valor, f"{pct}%"]))

    rows.append(pad([""]))
    rows.append(pad(["🔴 ÍTEMS CRÍTICOS"]))
    rows.append(pad(["ID", "Descripción", "Capa", "¿Hecho?", "Puntos"]))
    for item in sim.get("items_criticos", []) or []:
        hecho = "✔" if item.get("done") else "✖"
        rows.append(
            pad(
                [
                    _as_str(item.get("id")) or "-",
                    _as_str(item.get("descripcion")) or "-",
                    _as_str(item.get("capa")) or "-",
                    hecho,
                    f"{_as_int(item.get('score'), default=0)}/{_as_int(item.get('max_score'), default=0)}",
                ]
            )
        )

    rows.append(pad([""]))
    rows.append(pad(["📝 PREGUNTAS DE DESARROLLO"]))
    rows.append(pad(["#", "Pregunta", "Respuesta", "Score"]))
    for idx, item in enumerate(sim.get("preguntas_desarrollo", []) or [], 1):
        rows.append(
            pad(
                [
                    idx,
                    _as_str(item.get("pregunta")) or "-",
                    _as_str(item.get("respuesta")) or "",
                    _as_int(item.get("score"), default=0),
                ]
            )
        )

    rows.append(pad([""]))
    rows.append(pad(["💬 TRANSCRIPCIÓN"]))
    rows.append(pad(["#", "Rol", "Texto"]))
    for turno in sim.get("transcripcion", []) or []:
        rows.append(
            pad(
                [
                    _as_int(turno.get("turno"), default=0),
                    _as_str(turno.get("rol")) or "DESCONOCIDO",
                    _as_str(turno.get("texto")),
                ]
            )
        )

    rows.append(pad([""]))
    rows.append(pad(["⭐ ENCUESTA DE SATISFACCIÓN"]))
    rows.append(pad(["Media general:", f"{_as_float(sim.get('media_encuesta'), default=0.0)} / 5"]))
    rows.append(pad([""]))
    rows.append(pad(["Pregunta", "Respuesta"]))
    for item in sim.get("encuesta_likert", []) or []:
        rows.append(
            pad(
                [
                    _as_str(item.get("pregunta")) or "-",
                    f"{_as_int(item.get('valor'), default=0)} / 5",
                ]
            )
        )
    for item in sim.get("encuesta_abiertas", []) or []:
        rows.append(pad([""]))
        rows.append(pad([_as_str(item.get("pregunta")) or "-"]))
        rows.append(pad([_as_str(item.get("respuesta")) or ""]))

    return rows


def _ratio_pct(value: Any, total: Any) -> int:
    total_val = _as_float(total, default=0.0)
    if total_val <= 0:
        return 0
    return int(round((_as_float(value, default=0.0) / total_val) * 100))


def _update_summary_satisfaction(worksheet: "gspread.Worksheet", media: float) -> None:
    try:
        values = worksheet.get_all_values()
    except Exception:
        return
    row = _find_row(values, ["satisfaccion"])
    if not row:
        return
    percent = _ratio_pct(media, 5)
    worksheet.update(
        f"B{row}:C{row}",
        [[f"{_as_float(media, default=0.0)}/5", f"{percent}%"]],
        value_input_option="USER_ENTERED",
    )


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
