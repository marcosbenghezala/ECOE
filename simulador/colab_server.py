#!/usr/bin/env python3
"""
ECOE Backend Server - Para Colab
Sirve el frontend y gestiona la comunicación con OpenAI Realtime API
VERSIÓN CORREGIDA: Arquitectura async con threading
"""

import os
import json
import asyncio
import uuid
import threading
import queue
import pickle
import time
from datetime import datetime, timezone
from pathlib import Path
from functools import wraps
from collections import defaultdict
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sock import Sock
from dotenv import load_dotenv

# Cargar .env del directorio padre (TO_GITHUB/)
load_dotenv(Path(__file__).parent.parent / '.env')

# Configuración robusta de Eventlet (Railway)
os.environ.setdefault("EVENTLET_NO_GREENDNS", "yes")
os.environ.setdefault("EVENTLET_HUB", "poll")

# Monkey patch eventlet para soporte robusto de WebSockets en Gunicorn.
# Debe hacerse ANTES de importar requests/urllib3
try:
    import eventlet
    eventlet.monkey_patch(socket=True, select=True, time=True, thread=False)
    print("✅ Eventlet monkey patched (socket, select, time)")
except ImportError:
    print("⚠️  Eventlet no disponible")
except Exception as e:
    print(f"⚠️  Error monkey patching eventlet: {e}")

# Voz por género (Realtime)
VOICE_MAPPING = {
    "female": "nova",
    "male": "echo",
    "default": "nova",
}


def get_voice_for_case(case_data: dict) -> str:
    info_paciente = case_data.get("informacion_paciente", {}) or {}
    genero_raw = (
        info_paciente.get("genero")
        or case_data.get("gender")
        or case_data.get("genero")
        or ""
    )
    genero = str(genero_raw).strip().lower()

    if genero in {"female", "f", "mujer", "hembra", "femenino"}:
        return VOICE_MAPPING["female"]
    if "mujer" in genero or "femenin" in genero:
        return VOICE_MAPPING["female"]

    if genero in {"male", "m", "hombre", "masculino"}:
        return VOICE_MAPPING["male"]
    if "hombre" in genero or "masculin" in genero:
        return VOICE_MAPPING["male"]

    return VOICE_MAPPING["default"]

# Importar módulos del proyecto
from evaluator_production import EvaluatorProduction
from realtime_voice import RealtimeVoiceManager

# Verificar que existe el frontend compilado
FRONTEND_DIST = Path(__file__).parent / 'frontend' / 'dist'
if not FRONTEND_DIST.exists():
    print(f"⚠️  ADVERTENCIA: Frontend no encontrado en {FRONTEND_DIST}")
    print(f"    Ejecuta: cd frontend && npm run build")
else:
    print(f"✅ Frontend encontrado en {FRONTEND_DIST}")

app = Flask(__name__, static_folder='frontend/dist', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})
sock = Sock(app)

# Configuración
BASE_DIR = Path(__file__).parent.parent
CASES_DIR = BASE_DIR / 'casos_procesados'
DATA_DIR = BASE_DIR / 'data'
SESSIONS_DIR = BASE_DIR / 'sessions'

# Inicializar ProxyClient (soporta proxy o conexión directa)
try:
    from proxy_client import ProxyClient
    proxy_client = ProxyClient()
    print("✅ ProxyClient inicializado")
except Exception as e:
    print(f"⚠️  Error inicializando ProxyClient: {e}")
    proxy_client = None

# Inicializar OpenAI client (necesario para evaluación con GPT-4)
# Se usa tanto con proxy (Realtime API) como sin proxy (directo)
openai_client = None
try:
    from openai import OpenAI
    openai_client = OpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        timeout=30.0,
        max_retries=2
    )
    print("✅ OpenAI client inicializado")
except Exception as e:
    # Si falla con parámetros, intentar solo con api_key
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        print("✅ OpenAI client inicializado (modo compatible)")
    except Exception as e2:
        print(f"⚠️  Error inicializando OpenAI client: {e2}")
        openai_client = None

try:
    evaluator_production = EvaluatorProduction()
    print("✅ EvaluatorProduction inicializado")
except Exception as e:
    print(f"⚠️  Error inicializando evaluador Production: {e}")
    evaluator_production = None


# Almacenamiento de sesiones y conexiones WebSocket
sessions = {}
websocket_connections = {}

# Rate limiting
request_counts = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # segundos
RATE_LIMIT_MAX_REQUESTS = 100  # máximo de requests por ventana


# ========== RATE LIMITING ==========

def rate_limit(max_requests=RATE_LIMIT_MAX_REQUESTS, window=RATE_LIMIT_WINDOW):
    """
    Decorador para limitar el número de requests por IP
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Obtener IP del cliente
            ip = request.remote_addr
            current_time = time.time()

            # Limpiar requests antiguos
            request_counts[ip] = [
                req_time for req_time in request_counts[ip]
                if current_time - req_time < window
            ]

            # Verificar límite
            if len(request_counts[ip]) >= max_requests:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Máximo {max_requests} requests por {window} segundos'
                }), 429

            # Registrar request
            request_counts[ip].append(current_time)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ========== PERSISTENCIA DE SESIONES ==========

def save_session_to_disk(session_id):
    """Guardar sesión en disco"""
    if session_id not in sessions:
        return

    try:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

        # Crear copia sin objetos no serializables
        session_copy = sessions[session_id].copy()
        session_copy.pop('ws_queue', None)
        session_copy.pop('active', None)

        session_file = SESSIONS_DIR / f"{session_id}.pkl"
        with open(session_file, 'wb') as f:
            pickle.dump(session_copy, f)

        print(f"💾 Sesión guardada: {session_id}")
    except Exception as e:
        print(f"❌ Error guardando sesión {session_id}: {e}")


def load_session_from_disk(session_id):
    """Cargar sesión desde disco"""
    try:
        session_file = SESSIONS_DIR / f"{session_id}.pkl"
        if not session_file.exists():
            return None

        with open(session_file, 'rb') as f:
            session_data = pickle.load(f)

        # Restaurar campos no serializables
        session_data['ws_queue'] = queue.Queue()
        session_data['active'] = False

        print(f"📂 Sesión cargada: {session_id}")
        return session_data
    except Exception as e:
        print(f"❌ Error cargando sesión {session_id}: {e}")
        return None


def get_all_sessions():
    """Obtener todas las sesiones guardadas"""
    if not SESSIONS_DIR.exists():
        return []

    session_list = []
    for session_file in SESSIONS_DIR.glob('*.pkl'):
        try:
            with open(session_file, 'rb') as f:
                session_data = pickle.load(f)
                session_list.append({
                    'session_id': session_data.get('session_id'),
                    'case_id': session_data.get('case_id'),
                    'student': session_data.get('student'),
                    'start_time': session_data.get('start_time'),
                    'transcript_length': len(session_data.get('transcript', ''))
                })
        except Exception as e:
            print(f"Error cargando {session_file}: {e}")
            continue

    return session_list


# ========== FRONTEND ==========

@app.route('/')
def index():
    """Servir el frontend"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    """Servir archivos estáticos (CSS, JS)"""
    return send_from_directory(app.static_folder, path)


# ========== API REST ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for Railway deployment"""
    return jsonify({
        'status': 'healthy',
        'openai_configured': bool(os.getenv('OPENAI_API_KEY')),
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/api/admin/test-sheets', methods=['POST'])
def admin_test_sheets():
    """
    Endpoint temporal para verificar Google Sheets en Railway.
    Deshabilitado por defecto. Para habilitar:
    - SHEETS_TEST_ENDPOINT_ENABLED=true
    - (opcional) SHEETS_TEST_TOKEN=...
      y enviar header: X-Admin-Token: <token>
    """
    if os.getenv("SHEETS_TEST_ENDPOINT_ENABLED", "false").lower() != "true":
        return jsonify({'error': 'Not found'}), 404

    expected = os.getenv("SHEETS_TEST_TOKEN", "").strip()
    if expected:
        provided = (request.headers.get("X-Admin-Token") or "").strip()
        if provided != expected:
            return jsonify({'error': 'Unauthorized'}), 401

    if os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() != "true":
        return jsonify({'error': 'GOOGLE_SHEETS_ENABLED=false'}), 400

    try:
        from sheets_logger import get_sheets_logger

        payload = request.json or {}
        now = datetime.now(timezone.utc)
        simulation_data = {
            "student_name": payload.get("student_name") or "Estudiante Test",
            "student_email": payload.get("student_email") or "test@example.com",
            "case_name": payload.get("case_name") or "TEST_SHEETS",
            "duration_seconds": int(payload.get("duration_seconds") or 437),
            "timestamp": payload.get("timestamp") or now.isoformat(),
            "evaluation_result": payload.get("evaluation_result") or {"schema_version": "evaluation.production.v1"},
            "transcript": payload.get("transcript") or [
                "[ESTUDIANTE] Hola, soy el doctor.",
                "[PACIENTE] Hola, doctor.",
                "[ESTUDIANTE] ¿Qué le pasa?",
                "[PACIENTE] Me duele el pecho.",
            ],
        }

        ok = get_sheets_logger().log_simulation(simulation_data)
        return jsonify({"ok": bool(ok)})
    except Exception as e:
        print(f"[Sheets] Error en test-sheets: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/cases', methods=['GET'])
def get_cases():
    """Obtener lista de casos disponibles (JSON + pickle)"""
    try:
        cases = []

        if not CASES_DIR.exists():
            print(f"⚠️  Directorio de casos no existe: {CASES_DIR}")
            return jsonify([])

        # Prioridad: JSON primero, luego .bin (pickle).
        # - Ignorar plantillas/archivos auxiliares que empiezan por "_"
        # - Evitar duplicados cuando existen .json y .bin con el mismo stem
        json_files = [p for p in CASES_DIR.glob('*.json') if not p.name.startswith('_')]
        bin_files = [p for p in CASES_DIR.glob('*.bin') if not p.name.startswith('_')]

        json_stems = {p.stem for p in json_files}
        bin_files = [p for p in bin_files if p.stem not in json_stems]

        all_case_files = list(json_files) + list(bin_files)

        for case_file in all_case_files:
            if case_file.stem.startswith("_"):
                continue
            try:
                # Cargar según extensión
                if case_file.suffix == '.json':
                    with open(case_file, 'r', encoding='utf-8') as f:
                        case_data = json.load(f)
                else:  # .bin
                    with open(case_file, 'rb') as f:
                        case_data = pickle.load(f)

                descripcion_corta = case_data.get('descripcion_corta') or case_data.get('motivo_consulta') or ''
                cases.append({
                    'id': case_file.stem,
                    'titulo': case_data.get('titulo', 'Sin título'),
                    'especialidad': case_data.get('especialidad', 'General'),
                    'dificultad': case_data.get('dificultad'),  # Opcional - no default
                    'duracion_estimada': case_data.get('duracion_estimada', 15),
                    'motivo_consulta': case_data.get('motivo_consulta', 'Sin motivo de consulta'),
                    'descripcion_corta': descripcion_corta if descripcion_corta else 'Sin descripción',
                    'informacion_paciente': case_data.get('informacion_paciente', {})
                })
            except Exception as e:
                print(f"Error loading case {case_file}: {e}")
                continue

        print(f"📊 Casos cargados: {len(cases)}")
        return jsonify(cases)

    except Exception as e:
        print(f"❌ Error en /api/cases: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cases/<case_id>', methods=['GET'])
def get_case(case_id):
    """Obtener un caso específico (JSON + pickle)"""
    try:
        if str(case_id).startswith('_'):
            return jsonify({'error': 'Case not found'}), 404

        # Buscar JSON primero, luego .bin
        case_file_json = CASES_DIR / f"{case_id}.json"
        case_file_bin = CASES_DIR / f"{case_id}.bin"

        if case_file_json.exists():
            with open(case_file_json, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
        elif case_file_bin.exists():
            with open(case_file_bin, 'rb') as f:
                case_data = pickle.load(f)
        else:
            return jsonify({'error': 'Case not found'}), 404

        return jsonify({
            'id': case_id,
            'titulo': case_data.get('titulo'),
            'especialidad': case_data.get('especialidad'),
            'dificultad': case_data.get('dificultad'),  # Opcional
            'motivo_consulta': case_data.get('motivo_consulta'),
            'informacion_paciente': case_data.get('informacion_paciente', {}),
            'duracion_estimada': case_data.get('duracion_estimada', 15),
            'instrucciones': case_data.get('instrucciones', ''),
            'multimedia': case_data.get('multimedia', [])
        })

    except Exception as e:
        print(f"❌ Error en /api/cases/{case_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cases/<case_id>/questions', methods=['GET'])
def get_case_questions(case_id):
    """
    Obtener preguntas de desarrollo para un caso específico.

    Las preguntas se definen en el propio caso (preguntas_reflexion).
    """
    try:
        if str(case_id).startswith('_'):
            return jsonify({'error': 'Case not found'}), 404

        case_file_json = CASES_DIR / f"{case_id}.json"
        case_file_bin = CASES_DIR / f"{case_id}.bin"

        if case_file_json.exists():
            with open(case_file_json, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
        elif case_file_bin.exists():
            with open(case_file_bin, 'rb') as f:
                case_data = pickle.load(f)
        else:
            return jsonify({'error': 'Case not found'}), 404

        questions = case_data.get("preguntas_reflexion") or []
        if not isinstance(questions, list) or not questions:
            return jsonify({'error': 'No hay preguntas configuradas para este caso'}), 404

        return jsonify({
            'case_id': case_id,
            'questions': questions,
            'source': 'case',
            'count': len(questions)
        })

    except Exception as e:
        print(f"❌ Error en /api/cases/{case_id}/questions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/simulation/start', methods=['POST'])
@rate_limit(max_requests=10, window=60)  # Máximo 10 simulaciones por minuto
def start_simulation():
    """Iniciar sesión de simulación"""
    try:
        data = request.json
        case_id = data.get('case_id')
        student_data = data.get('student', {})

        if not case_id or str(case_id).startswith('_'):
            return jsonify({'error': 'Case not found'}), 404

        # Buscar JSON primero, luego .bin (pickle)
        case_file_json = CASES_DIR / f"{case_id}.json"
        case_file_bin = CASES_DIR / f"{case_id}.bin"

        if case_file_json.exists():
            with open(case_file_json, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
        elif case_file_bin.exists():
            import pickle
            with open(case_file_bin, 'rb') as f:
                case_data = pickle.load(f)
        else:
            return jsonify({'error': 'Case not found'}), 404

        session_id = str(uuid.uuid4())

        # Determinar voz según género
        info_paciente = case_data.get("informacion_paciente", {}) or {}
        genero_raw = (
            info_paciente.get("genero")
            or case_data.get("gender")
            or case_data.get("genero")
            or ""
        )
        voice = get_voice_for_case(case_data)
        print(f"🗣️ Voice detect: genero='{str(genero_raw).strip()}' -> {voice}")

        sessions[session_id] = {
            'session_id': session_id,
            'case_id': case_id,
            'case_data': case_data,
            'student': student_data,
            'voice': voice,
            'start_time': datetime.now().isoformat(),
            'transcript': '',
            'events': [],
            'ws_queue': queue.Queue(),  # Cola para comunicación con async thread
            'active': True
        }

        print(f"✅ Sesión iniciada: {session_id} (voz: {voice})")

        return jsonify({
            'session_id': session_id,
            'voice': voice,
            'case_info': {
                'titulo': case_data.get('titulo'),
                'informacion_paciente': case_data.get('informacion_paciente')
            }
        })

    except Exception as e:
        print(f"❌ Error en /api/simulation/start: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/simulation/evaluate', methods=['POST'])
@rate_limit(max_requests=20, window=60)
def evaluate_simulation():
    """
    Evaluar simulación completa: transcript + reflexión clínica
    Devuelve resultados detallados para la pantalla de resultados
    """
    try:
        data = request.json
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid request body'}), 400
        session_id = data.get('session_id')

        if not session_id or session_id not in sessions:
            return jsonify({'error': 'Sesión no encontrada'}), 404

        session = sessions[session_id]
        case_data = session.get('case_data')
        if not case_data:
            return jsonify({'error': 'Session incomplete or expired'}), 400
        transcript = session.get('transcript', '')
        reflection = data.get('reflection', {})
        if not isinstance(reflection, dict):
            print("⚠️  reflection no es dict, usando objeto vacío")
            reflection = {}

        print(f"📊 Evaluando simulación {session_id}")
        print(f"   - Transcript: {len(transcript)} chars")
        print(f"   - Reflexión: {reflection.keys()}")

        # Analizar transcript con GPT-4 para detectar ítems preguntados
        items_asked_by_ai = []
        if openai_client and transcript:
            try:
                print("🤖 Analizando transcript con GPT-4 para detección inteligente de ítems...")
                from transcript_analyzer import analyze_transcript_with_gpt4
                items_asked_by_ai = analyze_transcript_with_gpt4(transcript, openai_client)
                print(f"   ✅ GPT-4 detectó {len(items_asked_by_ai)} ítems")
            except Exception as e:
                print(f"   ⚠️ Error en análisis GPT-4: {e}")
                items_asked_by_ai = []

        if not evaluator_production:
            raise ValueError("EvaluatorProduction no disponible")

        try:
            result = evaluator_production.evaluate(
                transcription=transcript,
                case_metadata=case_data,
                reflection_answers=reflection,
                survey=session.get("survey") or {},
                items_asked_by_ai=items_asked_by_ai,
            )
        except Exception as e:
            print(f"❌ Error en EvaluatorProduction para sesión {session_id}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f"Evaluation failed: {e}", 'traceback': traceback.format_exc()}), 500

        session["evaluation"] = result
        save_session_to_disk(session_id)

        sheets_status = {
            "enabled": os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true",
            "saved": False,
        }
        if sheets_status["enabled"]:
            print("📤 Saving to Sheets...")
            try:
                from sheets_logger import get_sheets_logger

                student = session.get("student") or {}
                student_name = (
                    student.get("nombre")
                    or student.get("name")
                    or student.get("student_name")
                    or "Sin nombre"
                )
                student_email = (
                    student.get("email")
                    or student.get("correo")
                    or student.get("student_email")
                    or "sin-email"
                )

                duration_seconds = 0
                try:
                    start_dt = datetime.fromisoformat(str(session.get("start_time", "")).replace("Z", "+00:00"))
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    duration_seconds = int((datetime.now(timezone.utc) - start_dt).total_seconds())
                except Exception:
                    duration_seconds = 0

                case_name = case_data.get("titulo") or case_data.get("id") or "caso"
                total_score = int(round(float(result.get("score_total", 0) or 0)))

                logger = get_sheets_logger()
                ok, detail_info = logger.log_simulation_with_details(
                    {
                        "student_name": student_name,
                        "student_email": student_email,
                        "case_name": case_name,
                        "duration_seconds": duration_seconds,
                        "total_score": total_score,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "evaluation_result": result,
                        "reflection_answers": reflection,
                        "survey_responses": session.get("survey"),
                        "transcript": transcript,
                    }
                )
                if ok and detail_info:
                    session["sheets_detail_title"] = detail_info.get("title")
                    session["sheets_detail_gid"] = detail_info.get("gid")
                    save_session_to_disk(session_id)
                    sheets_status["saved"] = True
                    sheets_status["detail"] = detail_info
                else:
                    sheets_status["error"] = "Sheets logger returned no detail info"
                print("✅ Sheets saved successfully" if sheets_status["saved"] else "⚠️ Sheets not saved")
            except Exception as e:
                print(f"❌ Sheets save failed: {e}")
                import traceback
                traceback.print_exc()
                sheets_status["error"] = str(e)

        result["sheets_status"] = sheets_status

        print(f"✅ Evaluación completada: {result.get('score_total', 0):.1f}%")

        return jsonify(result)

    except Exception as e:
        print(f"❌ Error en /api/simulation/evaluate: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500




@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Obtener lista de todas las sesiones guardadas"""
    try:
        session_list = get_all_sessions()
        return jsonify(session_list)
    except Exception as e:
        print(f"❌ Error en /api/sessions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Obtener una sesión específica"""
    try:
        # Intentar cargar desde memoria
        if session_id in sessions:
            session_data = sessions[session_id].copy()
            session_data.pop('ws_queue', None)
            session_data.pop('case_data', None)  # No enviar caso completo
            return jsonify(session_data)

        # Intentar cargar desde disco
        session_data = load_session_from_disk(session_id)
        if session_data:
            session_data.pop('case_data', None)
            return jsonify(session_data)

        return jsonify({'error': 'Session not found'}), 404

    except Exception as e:
        print(f"❌ Error en /api/sessions/{session_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/survey', methods=['POST'])
def save_survey(session_id):
    """Guardar respuestas de encuesta final"""
    try:
        if session_id not in sessions:
            return jsonify({'error': 'Session not found'}), 404

        payload = request.json or {}
        session = sessions[session_id]
        session['survey'] = payload
        save_session_to_disk(session_id)

        if os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true":
            try:
                from sheets_logger import get_sheets_logger

                detail_sheet_name = session.get("sheets_detail_title")
                if detail_sheet_name:
                    get_sheets_logger().append_survey_to_detail(detail_sheet_name, payload)
            except Exception as e:
                print(f"[Sheets] Error guardando encuesta en Sheets: {e}")

        return jsonify({"ok": True})
    except Exception as e:
        print(f"❌ Error en /api/session/{session_id}/survey: {e}")
        return jsonify({'error': str(e)}), 500


# ========== WEBSOCKET (REALTIME API) ==========

@sock.route('/ws/realtime/<session_id>')
def websocket_realtime(ws, session_id):
    """WebSocket para OpenAI Realtime API - con threading para async"""

    print(f"🔌 WebSocket /ws/realtime/{session_id} - cliente conectado")

    if session_id not in sessions:
        print(f"❌ Sesión {session_id} no encontrada")
        ws.send(json.dumps({'error': 'Invalid session'}))
        ws.close()
        return

    session = sessions[session_id]
    websocket_connections[session_id] = ws
    print(f"✅ WebSocket guardado para sesión {session_id}")

    # Cola thread-safe para enviar mensajes al frontend desde callbacks (RealtimeVoiceManager corre en otro thread).
    # Evita enviar directamente por `ws.send()` desde el thread async (puede corromper frames y causar "Invalid frame header").
    if session.get('ws_queue') is None:
        session['ws_queue'] = queue.Queue()
    outgoing_queue: "queue.Queue" = session['ws_queue']

    audio_throttle_s = float(os.getenv("WS_AGENT_AUDIO_THROTTLE_SECONDS", "0.01"))
    max_outgoing_per_tick = int(os.getenv("WS_OUTGOING_MAX_SENDS_PER_TICK", "20"))
    receive_timeout_s = float(os.getenv("WS_RECEIVE_TIMEOUT_SECONDS", "0.01"))
    print(
        "🔧 WS throttling: "
        f"audio_throttle={audio_throttle_s}s "
        f"max_outgoing_per_tick={max_outgoing_per_tick} "
        f"receive_timeout={receive_timeout_s}s"
    )

    def enqueue_to_frontend(payload: dict) -> None:
        try:
            outgoing_queue.put(payload)
        except Exception as e:
            print(f"⚠️  Error encolando mensaje al frontend: {e}")

    def drain_outgoing_messages() -> None:
        sent = 0
        while sent < max_outgoing_per_tick:
            try:
                payload = outgoing_queue.get_nowait()
            except queue.Empty:
                break

            ws.send(json.dumps(payload))
            sent += 1

            # Throttle específico para audio del agente (evita ráfagas de frames)
            if payload.get("type") == "agent_audio" and audio_throttle_s > 0:
                time.sleep(audio_throttle_s)

    # Callback para reenviar eventos al frontend
    def on_event_handler(event):
        if session_id in sessions:
            sessions[session_id]['events'].append({
                'timestamp': datetime.now().isoformat(),
                'event': event
            })

        # Reenviar al frontend (thread-safe)
        enqueue_to_frontend(event)

    def on_transcript_handler(text):
        print(f"📝 Transcript recibido: {text[:100]}...")  # DEBUG
        if session_id in sessions:
            sessions[session_id]['transcript'] += text + '\n'
            print(f"📊 Transcript total: {len(sessions[session_id]['transcript'])} chars")  # DEBUG

        # Enviar transcripción al frontend (thread-safe)
        enqueue_to_frontend({'type': 'transcript_update', 'text': text})

    # Crear RealtimeVoiceManager
    print(f"🔧 DEBUG: Creando RealtimeVoiceManager para session {session_id}")
    try:
        rtv = RealtimeVoiceManager(
            case_data=session['case_data'],
            voice_name=session['voice'],
            on_transcript=on_transcript_handler,
            on_event=on_event_handler
        )
        print(f"✅ RealtimeVoiceManager creado correctamente")
    except Exception as e:
        print(f"❌ Error creando RealtimeVoiceManager: {e}")
        import traceback
        traceback.print_exc()
        ws.send(json.dumps({'error': f'Error inicializando voice manager: {str(e)}'}))
        ws.close()
        return

    # Thread para manejar asyncio
    async_loop = asyncio.new_event_loop()
    connection_ready = threading.Event()
    connection_error = None

    def run_async_loop():
        nonlocal connection_error
        print(f"🔧 DEBUG: Iniciando async thread para session {session_id}")
        asyncio.set_event_loop(async_loop)
        try:
            print(f"🔧 DEBUG: Llamando a rtv.connect()...")
            async_loop.run_until_complete(rtv.connect())
            connection_ready.set()
            print(f"✅ OpenAI Realtime API conectada: {session_id}")
            # Mantener loop corriendo para escuchar eventos
            async_loop.run_forever()
        except Exception as e:
            connection_error = e
            connection_ready.set()
            print(f"❌ Error conectando a OpenAI: {e}")
            import traceback
            traceback.print_exc()

    async_thread = threading.Thread(target=run_async_loop, daemon=True)
    async_thread.start()

    # Esperar a que OpenAI conecte (configurable en Railway).
    # Por defecto, alineado con OPENAI_REALTIME_* de realtime_voice.py.
    connect_ready_timeout_env = os.getenv("OPENAI_REALTIME_CONNECT_READY_TIMEOUT")
    if connect_ready_timeout_env is not None:
        connect_ready_timeout_s = float(connect_ready_timeout_env)
    else:
        open_timeout_s = float(os.getenv("OPENAI_REALTIME_OPEN_TIMEOUT", "30"))
        max_attempts = int(os.getenv("OPENAI_REALTIME_MAX_CONNECT_ATTEMPTS", "3"))
        backoff_s = float(os.getenv("OPENAI_REALTIME_CONNECT_BACKOFF_SECONDS", "1.5"))
        connect_ready_timeout_s = (
            (open_timeout_s * max_attempts)
            + (backoff_s * (max_attempts - 1) * max_attempts / 2)
            + 5.0
        )
    if not connection_ready.wait(timeout=connect_ready_timeout_s):
        error_msg = f"Timeout conectando a OpenAI Realtime API ({int(connect_ready_timeout_s)}s)"
        print(f"❌ {error_msg}")
        ws.send(json.dumps({'type': 'error', 'error': error_msg}))
        async_loop.call_soon_threadsafe(async_loop.stop)
        ws.close()
        return

    if connection_error:
        error_msg = f'Error conectando a OpenAI: {str(connection_error)}'
        print(f"❌ {error_msg}")
        ws.send(json.dumps({'type': 'error', 'error': error_msg}))
        async_loop.call_soon_threadsafe(async_loop.stop)
        ws.close()
        return

    # Enviar confirmación al frontend
    ws.send(json.dumps({
        'type': 'connected',
        'message': 'OpenAI Realtime API conectada'
    }))

    print(f"✅ WebSocket conectado: {session_id}")

    try:
        # Loop síncrono para recibir mensajes del frontend
        message_count = 0
        while session['active']:
            try:
                # Enviar mensajes pendientes al frontend antes de leer (control de flujo + orden)
                drain_outgoing_messages()

                message = ws.receive(timeout=receive_timeout_s)
                if message is None:
                    continue

                data = json.loads(message)
                msg_type = data.get('type')

                if msg_type == 'audio':
                    # Enviar audio a OpenAI (ejecutar en el event loop async)
                    audio_b64 = data.get('audio')

                    if message_count == 0:
                        print(f"🎤 Primer chunk de audio recibido (tamaño: {len(audio_b64)} bytes)")

                    asyncio.run_coroutine_threadsafe(
                        rtv.send_audio(audio_b64),
                        async_loop
                    )

                    # Guardar sesión cada 100 mensajes
                    message_count += 1
                    if message_count % 100 == 0:
                        print(f"📊 {message_count} chunks de audio enviados")
                        save_session_to_disk(session_id)

                elif msg_type == 'interrupt':
                    print(f"⏸️  Interrupción solicitada")
                    asyncio.run_coroutine_threadsafe(
                        rtv.interrupt(),
                        async_loop
                    )

                elif msg_type == 'end':
                    print(f"🛑 Fin de simulación solicitado")
                    session['active'] = False
                    break
                else:
                    print(f"⚠️  Tipo de mensaje desconocido: {msg_type}")

            except json.JSONDecodeError as e:
                print(f"⚠️  Error parseando JSON: {e}")
                continue

    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        ws.send(json.dumps({'error': str(e)}))

    finally:
        print(f"🔌 Cerrando WebSocket: {session_id}")
        session['active'] = False

        # Guardar sesión final
        save_session_to_disk(session_id)

        # Desconectar Realtime API
        asyncio.run_coroutine_threadsafe(
            rtv.disconnect(),
            async_loop
        ).result(timeout=5)

        # Detener event loop
        async_loop.call_soon_threadsafe(async_loop.stop)

        # Limpiar
        if session_id in websocket_connections:
            del websocket_connections[session_id]

        ws.close()


# ========== INICIALIZACIÓN ==========

def init_app():
    """Inicializar directorios y recursos (se ejecuta al importar)"""
    port = int(os.environ.get('PORT', 8080))

    print("="*60)
    print("🏥 ECOE Backend Server")
    print("="*60)
    print(f"API: http://localhost:{port}/api")
    print(f"Casos: {CASES_DIR}")
    print("="*60)

    # Verificar directorios
    if not CASES_DIR.exists():
        print(f"⚠️  Creando directorio de casos: {CASES_DIR}")
        CASES_DIR.mkdir(parents=True, exist_ok=True)

    if not SESSIONS_DIR.exists():
        print(f"⚠️  Creando directorio de sesiones: {SESSIONS_DIR}")
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    """Punto de entrada para desarrollo local (python colab_server.py)"""
    init_app()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)


# Inicializar cuando se importa (para Gunicorn)
init_app()

if __name__ == '__main__':
    main()
