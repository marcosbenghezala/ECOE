import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import gspread
from gspread.utils import a1_range_to_grid_range

from text_utils import normalize_text

FORMULA_SEPARATOR = os.getenv("SHEETS_FORMULA_SEPARATOR", ";")
DEFAULT_END_ROW = int(os.getenv("SHEETS_FORMAT_MAX_ROWS", "5000"))

PALETTE = {
    "header_dark": "#1F4E79",
    "header_medium": "#2E75B6",
    "header_light": "#5B9BD5",
    "green_light": "#C6EFCE",
    "yellow_light": "#FFEB9C",
    "red_light": "#FFC7CE",
    "gray_light": "#F2F2F2",
    "gray_medium": "#D9D9D9",
    "white": "#FFFFFF",
    "estudiante_bg": "#DEEAF6",
    "paciente_bg": "#E2EFDA",
}

RESUMEN_COLUMN_WIDTHS = {
    "A": 18.0,
    "B": 25.0,
    "C": 28.0,
    "D": 20.0,
    "E": 10.0,
    "F": 12.0,
    "G": 10.0,
    "H": 12.0,
    "I": 12.0,
    "J": 10.0,
    "K": 12.0,
}

DETAIL_COLUMN_WIDTHS = {
    "A": 12.0,
    "B": 45.0,
    "C": 50.0,
    "D": 12.0,
    "E": 12.0,
    "F": 12.0,
    "G": 12.0,
}

RAW_JSON_COLUMN_WIDTHS = {
    "A": 25.0,
    "B": 20.0,
    "C": 80.0,
    "D": 50.0,
}


def _width_to_pixels(width: float) -> int:
    return int(width * 7 + 5)


def _hex_to_color(hex_value: str) -> Dict[str, float]:
    value = hex_value.lstrip("#")
    r = int(value[0:2], 16) / 255.0
    g = int(value[2:4], 16) / 255.0
    b = int(value[4:6], 16) / 255.0
    return {"red": r, "green": g, "blue": b}


def _grid_range(worksheet: "gspread.Worksheet", a1_range: str) -> Dict[str, int]:
    return a1_range_to_grid_range(a1_range, worksheet.id)


def _batch_update(worksheet: "gspread.Worksheet", requests: List[Dict]) -> None:
    if not requests:
        return
    worksheet.spreadsheet.batch_update({"requests": requests})


def _merge_safe(worksheet: "gspread.Worksheet", a1_range: str) -> None:
    try:
        worksheet.merge_cells(a1_range)
    except Exception:
        return


def _set_column_widths(worksheet: "gspread.Worksheet", widths: Dict[int, int]) -> None:
    requests = []
    for col_index, width in widths.items():
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": worksheet.id,
                        "dimension": "COLUMNS",
                        "startIndex": col_index - 1,
                        "endIndex": col_index,
                    },
                    "properties": {"pixelSize": width},
                    "fields": "pixelSize",
                }
            }
        )
    _batch_update(worksheet, requests)


def _set_column_widths_from_letters(worksheet: "gspread.Worksheet", widths: Dict[str, float]) -> None:
    requests = []
    for col_letter, width in widths.items():
        col_index = ord(col_letter.upper()) - ord("A") + 1
        pixel = _width_to_pixels(width)
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": worksheet.id,
                        "dimension": "COLUMNS",
                        "startIndex": col_index - 1,
                        "endIndex": col_index,
                    },
                    "properties": {"pixelSize": pixel},
                    "fields": "pixelSize",
                }
            }
        )
    _batch_update(worksheet, requests)


def _set_row_heights(worksheet: "gspread.Worksheet", heights: Dict[int, int]) -> None:
    requests = []
    for row_index, height in heights.items():
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": worksheet.id,
                        "dimension": "ROWS",
                        "startIndex": row_index - 1,
                        "endIndex": row_index,
                    },
                    "properties": {"pixelSize": height},
                    "fields": "pixelSize",
                }
            }
        )
    _batch_update(worksheet, requests)


def _set_row_height_range(worksheet: "gspread.Worksheet", start_row: int, end_row: int, height: int) -> None:
    requests = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": worksheet.id,
                    "dimension": "ROWS",
                    "startIndex": start_row - 1,
                    "endIndex": end_row,
                },
                "properties": {"pixelSize": height},
                "fields": "pixelSize",
            }
        }
    ]
    _batch_update(worksheet, requests)


def _hide_column(worksheet: "gspread.Worksheet", col_index: int) -> None:
    requests = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": worksheet.id,
                    "dimension": "COLUMNS",
                    "startIndex": col_index - 1,
                    "endIndex": col_index,
                },
                "properties": {"hiddenByUser": True},
                "fields": "hiddenByUser",
            }
        }
    ]
    _batch_update(worksheet, requests)


def _set_basic_filter(worksheet: "gspread.Worksheet", a1_range: str) -> None:
    grid = _grid_range(worksheet, a1_range)
    requests = [
        {
            "setBasicFilter": {
                "filter": {
                    "range": grid,
                }
            }
        }
    ]
    _batch_update(worksheet, requests)


def _clear_conditional_formatting(worksheet: "gspread.Worksheet") -> None:
    metadata = worksheet.spreadsheet.fetch_sheet_metadata()
    sheet_meta = None
    for sheet in metadata.get("sheets", []):
        if sheet.get("properties", {}).get("sheetId") == worksheet.id:
            sheet_meta = sheet
            break
    if not sheet_meta:
        return
    rules = sheet_meta.get("conditionalFormats", [])
    requests = []
    for idx in reversed(range(len(rules))):
        requests.append(
            {"deleteConditionalFormatRule": {"sheetId": worksheet.id, "index": idx}}
        )
    _batch_update(worksheet, requests)


def _add_conditional_rules(
    worksheet: "gspread.Worksheet", rules: List[Dict]
) -> None:
    requests = []
    for rule in rules:
        requests.append(
            {"addConditionalFormatRule": {"rule": rule, "index": 0}}
        )
    _batch_update(worksheet, requests)


def _number_rule(
    worksheet: "gspread.Worksheet",
    a1_range: str,
    rule_type: str,
    values: List[str],
    color_hex: str,
) -> Dict:
    return {
        "ranges": [_grid_range(worksheet, a1_range)],
        "booleanRule": {
            "condition": {
                "type": rule_type,
                "values": [{"userEnteredValue": v} for v in values],
            },
            "format": {"backgroundColor": _hex_to_color(color_hex)},
        },
    }


def _custom_formula_rule(
    worksheet: "gspread.Worksheet",
    a1_range: str,
    formula: str,
    color_hex: str,
) -> Dict:
    return {
        "ranges": [_grid_range(worksheet, a1_range)],
        "booleanRule": {
            "condition": {
                "type": "CUSTOM_FORMULA",
                "values": [{"userEnteredValue": formula}],
            },
            "format": {"backgroundColor": _hex_to_color(color_hex)},
        },
    }


def _color_scale_rule(
    worksheet: "gspread.Worksheet",
    a1_range: str,
    min_value: int,
    mid_value: int,
    max_value: int,
    min_color: str,
    mid_color: str,
    max_color: str,
) -> Dict:
    return {
        "ranges": [_grid_range(worksheet, a1_range)],
        "gradientRule": {
            "minpoint": {
                "type": "NUMBER",
                "value": str(min_value),
                "color": _hex_to_color(min_color),
            },
            "midpoint": {
                "type": "NUMBER",
                "value": str(mid_value),
                "color": _hex_to_color(mid_color),
            },
            "maxpoint": {
                "type": "NUMBER",
                "value": str(max_value),
                "color": _hex_to_color(max_color),
            },
        },
    }


def _zebra_rule(worksheet: "gspread.Worksheet", a1_range: str) -> Dict:
    return _custom_formula_rule(
        worksheet,
        a1_range,
        "=ISEVEN(ROW())",
        PALETTE["gray_light"],
    )


def _apply_common_border(worksheet: "gspread.Worksheet", a1_range: str) -> None:
    fmt = {
        "borders": {
            "top": {"style": "SOLID", "color": _hex_to_color("#BFBFBF")},
            "bottom": {"style": "SOLID", "color": _hex_to_color("#BFBFBF")},
            "left": {"style": "SOLID", "color": _hex_to_color("#BFBFBF")},
            "right": {"style": "SOLID", "color": _hex_to_color("#BFBFBF")},
        }
    }
    worksheet.format(a1_range, fmt)


def _find_row(values: List[List[str]], labels: List[str]) -> Optional[int]:
    normalized_labels = [normalize_text(label) for label in labels]
    for idx, row in enumerate(values, 1):
        if not row:
            continue
        cell = normalize_text(row[0])
        for label in normalized_labels:
            if label and label in cell:
                return idx
    return None


def _find_section_end(values: List[List[str]], start_row: int, labels: List[str]) -> int:
    normalized_labels = [normalize_text(label) for label in labels]
    for idx in range(start_row, len(values) + 1):
        row = values[idx - 1] if idx - 1 < len(values) else []
        cell = normalize_text(row[0]) if row else ""
        for label in normalized_labels:
            if label and label in cell:
                return idx - 1
    return len(values)


def _build_ratio_formula(row: int) -> str:
    sep = FORMULA_SEPARATOR
    return (
        f"=IFERROR(VALUE(LEFT(H{row}{sep}FIND(\"/\"{sep}H{row})-1))"
        f"/VALUE(MID(H{row}{sep}FIND(\"/\"{sep}H{row})+1{sep}10)){sep}\"\")"
    )


def formatear_hoja_resumen(
    worksheet: "gspread.Worksheet",
    start_row: int = 5,
    end_row: Optional[int] = None,
) -> None:
    end_row = end_row or DEFAULT_END_ROW
    title = "📊 DASHBOARD DE SIMULACIONES ECOE"
    subtitle = "Resumen de resultados por estudiante | Generado automáticamente"

    _merge_safe(worksheet, "A1:K1")
    _merge_safe(worksheet, "A2:K2")

    worksheet.update("A1", [[title]])
    worksheet.update("A2", [[subtitle]])

    headers = [
        "Timestamp",
        "Estudiante",
        "Email",
        "Caso",
        "Duración\n(min)",
        "Puntuación\nTotal",
        "% Conv.",
        "Críticos",
        "Media\nDesarrollo",
        "Media\nEncuesta",
        "Detalles",
    ]
    worksheet.update("A4:K4", [headers])

    header_fmt = {
        "backgroundColor": _hex_to_color(PALETTE["header_dark"]),
        "textFormat": {
            "bold": True,
            "foregroundColor": _hex_to_color(PALETTE["white"]),
            "fontSize": 11,
        },
        "horizontalAlignment": "CENTER",
        "verticalAlignment": "MIDDLE",
        "wrapStrategy": "WRAP",
    }
    title_fmt = {
        "backgroundColor": _hex_to_color(PALETTE["header_dark"]),
        "textFormat": {
            "bold": True,
            "foregroundColor": _hex_to_color(PALETTE["white"]),
            "fontSize": 16,
        },
        "horizontalAlignment": "CENTER",
        "verticalAlignment": "MIDDLE",
    }
    subtitle_fmt = {
        "backgroundColor": _hex_to_color(PALETTE["header_medium"]),
        "textFormat": {
            "bold": False,
            "foregroundColor": _hex_to_color(PALETTE["white"]),
            "fontSize": 10,
        },
        "horizontalAlignment": "CENTER",
        "verticalAlignment": "MIDDLE",
    }
    worksheet.format("A1:K1", title_fmt)
    worksheet.format("A2:K2", subtitle_fmt)
    worksheet.format("A4:K4", header_fmt)
    _apply_common_border(worksheet, "A4:K4")

    data_fmt = {
        "textFormat": {"fontSize": 10},
        "verticalAlignment": "MIDDLE",
        "wrapStrategy": "WRAP",
    }
    data_range = f"A{start_row}:K{end_row}"
    worksheet.format(data_range, data_fmt)
    _apply_common_border(worksheet, data_range)

    number_formats = {
        f"E{start_row}:E{end_row}": "0.0",
        f"G{start_row}:G{end_row}": "0",
        f"I{start_row}:I{end_row}": "0",
        f"J{start_row}:J{end_row}": "0.0",
    }
    for a1_range, pattern in number_formats.items():
        worksheet.format(
            a1_range,
            {"numberFormat": {"type": "NUMBER", "pattern": pattern}},
        )

    _set_column_widths_from_letters(worksheet, RESUMEN_COLUMN_WIDTHS)

    _set_row_heights(worksheet, {1: 35, 2: 20, 3: 10, 4: 35})
    _set_row_height_range(worksheet, start_row, end_row, 22)
    worksheet.freeze(rows=4)
    _set_basic_filter(worksheet, f"A4:K{end_row}")

    ratio_formulas = [[_build_ratio_formula(row)] for row in range(start_row, end_row + 1)]
    worksheet.update(f"L{start_row}:L{end_row}", ratio_formulas, value_input_option="USER_ENTERED")
    _hide_column(worksheet, 12)

    _clear_conditional_formatting(worksheet)
    rules = [
        _zebra_rule(worksheet, data_range),
        _number_rule(worksheet, f"G{start_row}:G{end_row}", "NUMBER_LESS", ["40"], PALETTE["red_light"]),
        _number_rule(worksheet, f"G{start_row}:G{end_row}", "NUMBER_BETWEEN", ["40", "70"], PALETTE["yellow_light"]),
        _number_rule(worksheet, f"G{start_row}:G{end_row}", "NUMBER_GREATER_THAN", ["70"], PALETTE["green_light"]),
        _number_rule(worksheet, f"I{start_row}:I{end_row}", "NUMBER_LESS", ["40"], PALETTE["red_light"]),
        _number_rule(worksheet, f"I{start_row}:I{end_row}", "NUMBER_BETWEEN", ["40", "70"], PALETTE["yellow_light"]),
        _number_rule(worksheet, f"I{start_row}:I{end_row}", "NUMBER_GREATER_THAN", ["70"], PALETTE["green_light"]),
        _custom_formula_rule(worksheet, f"H{start_row}:H{end_row}", f"=$L{start_row}<0.4", PALETTE["red_light"]),
        _custom_formula_rule(worksheet, f"H{start_row}:H{end_row}", f"=($L{start_row}>=0.4)*($L{start_row}<0.7)", PALETTE["yellow_light"]),
        _custom_formula_rule(worksheet, f"H{start_row}:H{end_row}", f"=$L{start_row}>=0.7", PALETTE["green_light"]),
        _color_scale_rule(
            worksheet,
            f"J{start_row}:J{end_row}",
            1,
            3,
            5,
            PALETTE["red_light"],
            PALETTE["yellow_light"],
            PALETTE["green_light"],
        ),
    ]
    _add_conditional_rules(worksheet, rules)


def formatear_hoja_detalle(worksheet: "gspread.Worksheet") -> None:
    _merge_safe(worksheet, "A1:G1")
    _merge_safe(worksheet, "A2:G2")
    _merge_safe(worksheet, "B3:G7")
    _merge_safe(worksheet, "A9:G9")
    _merge_safe(worksheet, "A14:G14")
    _merge_safe(worksheet, "A26:G26")
    _merge_safe(worksheet, "A34:G34")
    _merge_safe(worksheet, "A46:G46")
    _merge_safe(worksheet, "A57:B57")
    _merge_safe(worksheet, "A60:B60")
    _merge_safe(worksheet, "A63:G63")
    _merge_safe(worksheet, "A64:C69")

    worksheet.format(
        "A1:G1",
        {
            "backgroundColor": _hex_to_color(PALETTE["header_dark"]),
            "textFormat": {
                "bold": True,
                "foregroundColor": _hex_to_color(PALETTE["white"]),
                "fontSize": 14,
            },
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
        },
    )
    worksheet.format(
        "A2:G2",
        {
            "backgroundColor": _hex_to_color(PALETTE["gray_light"]),
            "textFormat": {"bold": True, "fontSize": 12},
            "horizontalAlignment": "LEFT",
            "verticalAlignment": "MIDDLE",
        },
    )
    worksheet.format(
        "A3:A7",
        {
            "textFormat": {"bold": True, "fontSize": 10},
            "horizontalAlignment": "RIGHT",
            "verticalAlignment": "MIDDLE",
        },
    )
    worksheet.format(
        "B3:G7",
        {
            "textFormat": {"fontSize": 10},
            "horizontalAlignment": "LEFT",
            "verticalAlignment": "MIDDLE",
            "wrapStrategy": "WRAP",
        },
    )

    worksheet.format(
        "A9:G9",
        {
            "backgroundColor": _hex_to_color(PALETTE["gray_light"]),
            "textFormat": {"bold": True, "fontSize": 12},
            "horizontalAlignment": "LEFT",
            "verticalAlignment": "MIDDLE",
        },
    )
    worksheet.format(
        "A10:G10",
        {
            "backgroundColor": _hex_to_color(PALETTE["header_light"]),
            "textFormat": {
                "bold": True,
                "foregroundColor": _hex_to_color(PALETTE["white"]),
                "fontSize": 10,
            },
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
            "wrapStrategy": "WRAP",
        },
    )
    worksheet.format(
        "A11:G11",
        {
            "textFormat": {"bold": True, "fontSize": 12},
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
        },
    )

    _set_column_widths_from_letters(worksheet, DETAIL_COLUMN_WIDTHS)
    _set_row_heights(
        worksheet,
        {
            1: 30,
            3: 18,
            4: 18,
            5: 18,
            6: 18,
            7: 18,
            10: 30,
            11: 35,
            15: 25,
            16: 22,
            17: 22,
            18: 22,
            19: 22,
            20: 22,
            21: 22,
            22: 22,
            23: 22,
            27: 25,
            28: 45,
            29: 45,
            30: 45,
            31: 45,
            35: 25,
            36: 35,
            37: 35,
            38: 35,
            39: 35,
            40: 35,
            41: 35,
            42: 35,
            43: 35,
            49: 25,
            50: 22,
            51: 22,
            52: 22,
            53: 22,
            54: 22,
            57: 45,
            60: 45,
        },
    )

    values = worksheet.get_all_values()
    critical_row = _find_row(values, ["items criticos", "items críticos"])
    dev_row = _find_row(values, ["preguntas de desarrollo", "desarrollo"])
    transcript_row = _find_row(values, ["transcripcion", "transcripción"])
    survey_row = _find_row(values, ["encuesta final", "encuesta"])

    _clear_conditional_formatting(worksheet)
    rules: List[Dict] = []

    if critical_row:
        header_row = critical_row + 1
        worksheet.format(
            f"A{critical_row}:G{critical_row}",
            {
                "backgroundColor": _hex_to_color(PALETTE["gray_light"]),
                "textFormat": {"bold": True, "fontSize": 12},
            },
        )
        worksheet.format(
            f"A{header_row}:E{header_row}",
            {
                "backgroundColor": _hex_to_color(PALETTE["header_dark"]),
                "textFormat": {
                    "bold": True,
                    "foregroundColor": _hex_to_color(PALETTE["white"]),
                    "fontSize": 10,
                },
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
            },
        )

    if dev_row:
        header_row = dev_row + 1
        data_start = header_row + 1
        data_end = _find_section_end(values, data_start, ["transcripcion", "encuesta", "json"])
        worksheet.format(
            f"A{dev_row}:G{dev_row}",
            {
                "backgroundColor": _hex_to_color(PALETTE["gray_light"]),
                "textFormat": {"bold": True, "fontSize": 12},
            },
        )
        worksheet.format(
            f"A{header_row}:D{header_row}",
            {
                "backgroundColor": _hex_to_color(PALETTE["header_dark"]),
                "textFormat": {
                    "bold": True,
                    "foregroundColor": _hex_to_color(PALETTE["white"]),
                    "fontSize": 10,
                },
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
                "wrapStrategy": "WRAP",
            },
        )
        worksheet.format(
            f"B{data_start}:C{data_end}",
            {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"},
        )
        rules.extend(
            [
                _number_rule(worksheet, f"D{data_start}:D{data_end}", "NUMBER_LESS", ["40"], PALETTE["red_light"]),
                _number_rule(worksheet, f"D{data_start}:D{data_end}", "NUMBER_BETWEEN", ["40", "70"], PALETTE["yellow_light"]),
                _number_rule(worksheet, f"D{data_start}:D{data_end}", "NUMBER_GREATER_THAN", ["70"], PALETTE["green_light"]),
            ]
        )

    if transcript_row:
        header_row = transcript_row + 1
        data_start = header_row + 1
        data_end = _find_section_end(values, data_start, ["encuesta", "json"])
        worksheet.format(
            f"A{transcript_row}:G{transcript_row}",
            {
                "backgroundColor": _hex_to_color(PALETTE["gray_light"]),
                "textFormat": {"bold": True, "fontSize": 12},
            },
        )
        worksheet.format(
            f"A{header_row}:C{header_row}",
            {
                "backgroundColor": _hex_to_color(PALETTE["header_dark"]),
                "textFormat": {
                    "bold": True,
                    "foregroundColor": _hex_to_color(PALETTE["white"]),
                    "fontSize": 10,
                },
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
            },
        )
        rules.extend(
            [
                _custom_formula_rule(
                    worksheet,
                    f"A{data_start}:C{data_end}",
                    f'=$B{data_start}="ESTUDIANTE"',
                    PALETTE["estudiante_bg"],
                ),
                _custom_formula_rule(
                    worksheet,
                    f"A{data_start}:C{data_end}",
                    f'=$B{data_start}="PACIENTE"',
                    PALETTE["paciente_bg"],
                ),
            ]
        )

    if survey_row:
        header_row = None
        for idx in range(survey_row + 1, len(values) + 1):
            row = values[idx - 1] if idx - 1 < len(values) else []
            cell = normalize_text(row[0]) if row else ""
            if cell == "pregunta":
                header_row = idx
                break
        if header_row is None:
            header_row = survey_row + 3
        data_start = header_row + 1
        data_end = _find_section_end(values, data_start, ["json"])
        worksheet.format(
            f"A{survey_row}:G{survey_row}",
            {
                "backgroundColor": _hex_to_color(PALETTE["gray_light"]),
                "textFormat": {"bold": True, "fontSize": 12},
            },
        )
        worksheet.format(
            f"A{header_row}:B{header_row}",
            {
                "backgroundColor": _hex_to_color(PALETTE["header_dark"]),
                "textFormat": {
                    "bold": True,
                    "foregroundColor": _hex_to_color(PALETTE["white"]),
                    "fontSize": 10,
                },
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
                "wrapStrategy": "WRAP",
            },
        )
        rules.append(
            _color_scale_rule(
                worksheet,
                f"B{data_start}:B{data_end}",
                1,
                3,
                5,
                PALETTE["red_light"],
                PALETTE["yellow_light"],
                PALETTE["green_light"],
            )
        )

    comment_row = _find_row(values, ["comentario abierto"])
    if comment_row:
        worksheet.format(
            f"A{comment_row}:B{comment_row}",
            {
                "backgroundColor": _hex_to_color(PALETTE["gray_light"]),
                "textFormat": {"bold": True, "fontSize": 10},
                "horizontalAlignment": "LEFT",
                "verticalAlignment": "MIDDLE",
            },
        )

    improve_row = _find_row(values, ["que mejorarias", "qué mejorarías"])
    if improve_row:
        worksheet.format(
            f"A{improve_row}:B{improve_row}",
            {
                "backgroundColor": _hex_to_color(PALETTE["gray_light"]),
                "textFormat": {"bold": True, "fontSize": 10},
                "horizontalAlignment": "LEFT",
                "verticalAlignment": "MIDDLE",
            },
        )

    json_row = _find_row(values, ["datos tecnicos", "datos técnicos", "json"])
    if json_row:
        worksheet.format(
            f"A{json_row}:G{json_row}",
            {
                "backgroundColor": _hex_to_color(PALETTE["gray_light"]),
                "textFormat": {"bold": True, "fontSize": 11},
            },
        )
        worksheet.format(
            f"A{json_row + 1}:C{json_row + 6}",
            {
                "textFormat": {"fontFamily": "Consolas", "fontSize": 9},
                "wrapStrategy": "WRAP",
                "verticalAlignment": "TOP",
            },
        )

    if rules:
        _add_conditional_rules(worksheet, rules)


def formatear_hoja_raw_json(worksheet: "gspread.Worksheet") -> None:
    title = "📦 DATOS JSON EN BRUTO"
    subtitle = "Esta hoja contiene los datos JSON completos de cada simulación para propósitos de debug y auditoría."
    headers = ["Estudiante", "Timestamp", "JSON Evaluación", "JSON Encuesta"]

    _merge_safe(worksheet, "A1:D1")
    _merge_safe(worksheet, "A2:D2")

    worksheet.update("A1", [[title]])
    worksheet.update("A2", [[subtitle]])
    worksheet.update("A4:D4", [headers])

    worksheet.format(
        "A1:D1",
        {
            "backgroundColor": _hex_to_color(PALETTE["header_dark"]),
            "textFormat": {
                "bold": True,
                "foregroundColor": _hex_to_color(PALETTE["white"]),
                "fontSize": 11,
            },
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
        },
    )
    worksheet.format(
        "A2:D2",
        {
            "backgroundColor": _hex_to_color(PALETTE["gray_light"]),
            "textFormat": {"fontSize": 10},
            "horizontalAlignment": "LEFT",
            "verticalAlignment": "MIDDLE",
            "wrapStrategy": "WRAP",
        },
    )
    worksheet.format(
        "A4:D4",
        {
            "backgroundColor": _hex_to_color(PALETTE["header_dark"]),
            "textFormat": {
                "bold": True,
                "foregroundColor": _hex_to_color(PALETTE["white"]),
                "fontSize": 11,
            },
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
        },
    )

    _set_column_widths_from_letters(worksheet, RAW_JSON_COLUMN_WIDTHS)
    _set_row_heights(worksheet, {1: 30})
    worksheet.freeze(rows=4)
    worksheet.format(
        "C5:D",
        {
            "textFormat": {"fontFamily": "Consolas", "fontSize": 9},
            "wrapStrategy": "WRAP",
            "verticalAlignment": "TOP",
        },
    )
