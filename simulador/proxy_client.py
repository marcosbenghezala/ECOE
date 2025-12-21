#!/usr/bin/env python3
"""
Cliente para comunicarse con el proxy server
Oculta la lógica de llamadas al proxy
"""

import os
import requests
from typing import Optional, Dict, List, Any


class ProxyClient:
    """Cliente para interactuar con el proxy server"""

    def __init__(self, proxy_url: Optional[str] = None):
        """
        Args:
            proxy_url: URL del proxy server. Si es None, usa conexión directa a OpenAI.
        """
        self.proxy_url = proxy_url or os.getenv('PROXY_URL')
        self.use_proxy = bool(self.proxy_url)

        if self.use_proxy:
            print(f"✅ Usando proxy server: {self.proxy_url}")
        else:
            print("⚠️  Usando conexión directa a OpenAI (requiere API key local)")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Llama al endpoint de chat completion a través del proxy o directamente

        Args:
            messages: Lista de mensajes del chat
            model: Modelo a usar
            temperature: Temperatura de generación
            max_tokens: Máximo de tokens a generar

        Returns:
            Respuesta del modelo
        """
        if self.use_proxy:
            return self._chat_via_proxy(messages, model, temperature, max_tokens)
        else:
            return self._chat_direct(messages, model, temperature, max_tokens)

    def _chat_via_proxy(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Llama a chat completion vía proxy"""
        url = f"{self.proxy_url}/api/chat"

        response = requests.post(
            url,
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )

        response.raise_for_status()
        return response.json()

    def _chat_direct(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Llama a chat completion directamente a OpenAI"""
        from openai import OpenAI

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY no configurada")

        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return {
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
        }

    def embeddings(
        self,
        text: str,
        model: str = "text-embedding-3-small"
    ) -> List[float]:
        """
        Obtiene embeddings de un texto

        Args:
            text: Texto a embedder
            model: Modelo de embeddings

        Returns:
            Vector de embeddings
        """
        if self.use_proxy:
            return self._embeddings_via_proxy(text, model)
        else:
            return self._embeddings_direct(text, model)

    def _embeddings_via_proxy(self, text: str, model: str) -> List[float]:
        """Obtiene embeddings vía proxy"""
        url = f"{self.proxy_url}/api/embeddings"

        response = requests.post(
            url,
            json={
                "model": model,
                "input": text
            },
            timeout=30
        )

        response.raise_for_status()
        data = response.json()
        return data['data'][0]['embedding']

    def _embeddings_direct(self, text: str, model: str) -> List[float]:
        """Obtiene embeddings directamente de OpenAI"""
        from openai import OpenAI

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY no configurada")

        client = OpenAI(api_key=api_key)

        response = client.embeddings.create(
            model=model,
            input=text
        )

        return response.data[0].embedding

    def get_realtime_config(
        self,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene configuración para conectarse a Realtime API

        Args:
            model: Modelo de Realtime API

        Returns:
            Dict con 'url' y 'headers' para WebSocket
        """
        if model is None:
            model = os.getenv("OPENAI_REALTIME_MODEL") or "gpt-4o-realtime-preview-2024-12-17"
        if self.use_proxy:
            return self._realtime_via_proxy(model)
        else:
            return self._realtime_direct(model)

    def _realtime_via_proxy(self, model: str) -> Dict[str, Any]:
        """Obtiene config de Realtime vía proxy"""
        url = f"{self.proxy_url}/api/realtime/url"

        response = requests.post(
            url,
            json={"model": model},
            timeout=10
        )

        response.raise_for_status()
        return response.json()

    def _realtime_direct(self, model: str) -> Dict[str, Any]:
        """Obtiene config de Realtime directamente"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY no configurada")

        return {
            "url": f"wss://api.openai.com/v1/realtime?model={model}",
            "headers": {
                "Authorization": f"Bearer {api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
        }
