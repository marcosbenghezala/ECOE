#!/usr/bin/env python3
"""
SimuPaciente UMH - Proxy Server
Servidor proxy para ocultar la API key de OpenAI de los estudiantes
"""

import os
import asyncio
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import websockets
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# API Key de OpenAI (se configura en Railway como variable de entorno)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    logger.error("⚠️  OPENAI_API_KEY no configurada")
else:
    logger.info("✅ OPENAI_API_KEY configurada")


@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "SimuPaciente UMH Proxy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check con detalles"""
    has_key = bool(OPENAI_API_KEY)
    return jsonify({
        "status": "healthy" if has_key else "unhealthy",
        "openai_key_configured": has_key,
        "timestamp": datetime.now().isoformat()
    }), 200 if has_key else 503


@app.route('/api/chat', methods=['POST'])
def chat_completion():
    """
    Proxy para chat completions de OpenAI
    Usado para evaluación de reflejos
    """
    try:
        if not OPENAI_API_KEY:
            return jsonify({"error": "API key not configured"}), 500

        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        data = request.json

        # Extraer parámetros
        model = data.get('model', 'gpt-4o-mini')
        messages = data.get('messages', [])
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 1000)

        logger.info(f"Chat completion request: model={model}, messages_count={len(messages)}")

        # Llamar a OpenAI
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Devolver respuesta
        return jsonify({
            "choices": [
                {
                    "message": {
                        "role": response.choices[0].message.role,
                        "content": response.choices[0].message.content
                    }
                }
            ],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        })

    except Exception as e:
        logger.error(f"Error in chat completion: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/embeddings', methods=['POST'])
def embeddings():
    """
    Proxy para embeddings de OpenAI
    Usado para evaluación de checklist
    """
    try:
        if not OPENAI_API_KEY:
            return jsonify({"error": "API key not configured"}), 500

        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        data = request.json

        # Extraer parámetros
        model = data.get('model', 'text-embedding-3-small')
        input_text = data.get('input', '')

        logger.info(f"Embeddings request: model={model}")

        # Llamar a OpenAI
        response = client.embeddings.create(
            model=model,
            input=input_text
        )

        # Devolver respuesta
        return jsonify({
            "data": [
                {
                    "embedding": response.data[0].embedding,
                    "index": 0
                }
            ],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "total_tokens": response.usage.total_tokens
            }
        })

    except Exception as e:
        logger.error(f"Error in embeddings: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/realtime/url', methods=['POST'])
def get_realtime_url():
    """
    Endpoint para obtener URL de WebSocket de OpenAI Realtime API
    El cliente necesita la URL con la API key incluida
    """
    try:
        if not OPENAI_API_KEY:
            return jsonify({"error": "API key not configured"}), 500

        data = request.json
        model = data.get('model', 'gpt-4o-realtime-preview-2024-12-17')

        # Construir URL de WebSocket con la API key
        ws_url = f"wss://api.openai.com/v1/realtime?model={model}"

        logger.info(f"Realtime URL request: model={model}")

        # Devolver URL con headers necesarios
        return jsonify({
            "url": ws_url,
            "headers": {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
        })

    except Exception as e:
        logger.error(f"Error getting realtime URL: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"🚀 Iniciando proxy server en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
