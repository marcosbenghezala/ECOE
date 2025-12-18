# SimuPaciente UMH - Proxy Server

Servidor proxy para ocultar la API key de OpenAI de los estudiantes.

## 🚀 Deploy en Railway (GRATIS)

### Paso 1: Crear cuenta en Railway

1. Ve a https://railway.app
2. Click en "Login" → "Login with GitHub"
3. Autoriza Railway

### Paso 2: Crear nuevo proyecto

1. Click en "New Project"
2. Selecciona "Deploy from GitHub repo"
3. Selecciona tu repositorio `marcosbenghezala/ECOE`
4. Railway detectará automáticamente el código

### Paso 3: Configurar

1. En el dashboard de Railway, click en tu proyecto
2. Click en "Variables"
3. Añade esta variable:
   - **Key:** `OPENAI_API_KEY`
   - **Value:** `tu-api-key-de-openai`
4. Click en "Settings" → "Root Directory"
5. Cambia a: `proxy_server`
6. Click en "Deploy"

### Paso 4: Obtener la URL

1. Una vez desplegado, verás la URL en el dashboard
2. Será algo como: `https://simulador-umh-production.up.railway.app`
3. Copia esta URL

### Paso 5: Actualizar el notebook

Reemplaza en el notebook de Colab la URL del proxy:

```python
PROXY_URL = "https://tu-url-de-railway.up.railway.app"
```

## 🧪 Verificar que funciona

Abre en tu navegador:
```
https://tu-url-de-railway.up.railway.app/health
```

Deberías ver:
```json
{
  "status": "healthy",
  "openai_key_configured": true,
  "timestamp": "2025-12-18T..."
}
```

## 📊 Límites gratuitos de Railway

- ✅ 500 horas/mes de ejecución (más que suficiente)
- ✅ $5 de crédito gratis al mes
- ✅ Después de eso, se duerme automáticamente (sin cargos)

## 🔒 Seguridad

- ✅ La API key está en las variables de entorno de Railway
- ✅ NO está visible en el código
- ✅ Los estudiantes NO pueden verla
- ✅ Puedes desactivar el servidor cuando quieras

## 📝 Endpoints disponibles

- `GET /` - Home page
- `GET /health` - Health check
- `POST /api/chat` - Proxy para chat completions
- `POST /api/embeddings` - Proxy para embeddings
- `POST /api/realtime/url` - Obtener URL de Realtime API con auth

## 🐛 Troubleshooting

**Problema: "API key not configured"**
- Verifica que añadiste la variable `OPENAI_API_KEY` en Railway
- Redeploya el servicio después de añadir la variable

**Problema: "Application failed to start"**
- Verifica que el Root Directory está configurado a `proxy_server`
- Chequea los logs en Railway

**Problema: El servidor se duerme**
- Railway duerme servicios inactivos en el tier gratis
- La primera request después de dormir tardará 10-15 segundos
- Es normal y gratuito
