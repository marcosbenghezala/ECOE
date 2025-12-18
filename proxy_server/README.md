# SimuPaciente UMH - Proxy Server

Servidor proxy para ocultar la API key de OpenAI de los estudiantes.

## 🚀 Deploy en Render.com (100% GRATIS)

### Paso 1: Crear cuenta en Render

1. Ve a https://render.com
2. Click en **"Get Started"**
3. Selecciona **"Sign up with GitHub"**
4. Autoriza Render (NO requiere tarjeta de crédito)

### Paso 2: Crear nuevo Web Service

1. En el dashboard de Render, click en **"New +"**
2. Selecciona **"Web Service"**
3. Click en **"Connect a repository"**
4. Busca y selecciona tu repositorio **`marcosbenghezala/ECOE`**
5. Click en **"Connect"**

### Paso 3: Configurar el servicio

Render detectará automáticamente el archivo `render.yaml`, pero verifica:

- **Name:** `simu-paciente-umh-proxy`
- **Region:** Frankfurt (más cercano a España)
- **Branch:** `main`
- **Root Directory:** `proxy_server`
- **Runtime:** Python 3
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn -w 2 -b 0.0.0.0:$PORT app:app --timeout 120`
- **Plan:** **Free** ⚠️ IMPORTANTE

### Paso 4: Añadir variables de entorno

1. Scroll hasta la sección **"Environment Variables"**
2. Click en **"Add Environment Variable"**
3. Añade:
   - **Key:** `OPENAI_API_KEY`
   - **Value:** Tu API key de OpenAI (ej: `sk-proj-...`)
4. Click en **"Add"**

### Paso 5: Deploy

1. Click en **"Create Web Service"**
2. Render comenzará a construir tu aplicación (2-5 minutos)
3. Verás los logs en tiempo real

### Paso 6: Obtener la URL pública

1. Una vez desplegado (status: "Live"), verás la URL en la parte superior:
   ```
   https://simu-paciente-umh-proxy.onrender.com
   ```
2. **¡COPIA ESTA URL!** La necesitarás para el notebook

### Paso 7: Verificar que funciona

1. Abre en tu navegador:
   ```
   https://simu-paciente-umh-proxy.onrender.com/health
   ```

2. Deberías ver:
   ```json
   {
     "status": "healthy",
     "openai_key_configured": true,
     "timestamp": "2025-12-18T..."
   }
   ```

✅ **¡Proxy desplegado correctamente!**

---

## 📊 Límites del plan gratuito de Render

- ✅ **750 horas/mes** de ejecución (suficiente para 24/7)
- ✅ **512 MB RAM** (suficiente para proxy)
- ✅ **0.1 vCPU** (suficiente para proxy)
- ✅ **HTTPS automático**
- ✅ **Ancho de banda ilimitado**
- ⚠️ **Inactividad:** El servicio puede "dormirse" después de 15 min sin requests (primera request tarda ~30s en despertar)

**Para SimuPaciente UMH:**
- 20-50 estudiantes/mes
- ~30-50 horas de uso activo/mes
- ✅ **Bien dentro de los límites**

---

## 🔄 Auto-deploy desde GitHub

Render está conectado a tu repositorio. Cada vez que hagas `git push` a `main`:

1. Render detecta el cambio
2. Ejecuta build automático
3. Despliega la nueva versión
4. Cero downtime

---

## 📝 Endpoints disponibles

- `GET /` - Home page con información del servicio
- `GET /health` - Health check detallado
- `POST /api/chat` - Proxy para chat completions (GPT-4o-mini)
- `POST /api/embeddings` - Proxy para embeddings
- `POST /api/realtime/url` - Obtener URL de Realtime API con auth

---

## 🐛 Troubleshooting

### Problema: "API key not configured"

**Solución:**
1. Ve a Render Dashboard → Tu servicio
2. Click en "Environment" (barra lateral izquierda)
3. Verifica que `OPENAI_API_KEY` existe y es correcta
4. Si la editaste, haz manual redeploy: "Manual Deploy" → "Deploy latest commit"

### Problema: "Service Unavailable" o 503

**Causa:** El servicio se durmió por inactividad

**Solución:**
- Es normal en el plan gratuito
- La primera request lo despierta (~30s)
- Las siguientes requests son rápidas

### Problema: Build falla

**Solución:**
1. Revisa los logs de build en Render
2. Verifica que `requirements.txt` está en `proxy_server/`
3. Verifica que todas las dependencias son compatibles

### Problema: Servicio corre pero no responde

**Solución:**
1. Verifica que el Start Command es: `gunicorn -w 2 -b 0.0.0.0:$PORT app:app --timeout 120`
2. Chequea los logs en Render → "Logs"
3. Verifica que el puerto se lee de la variable `PORT` (no hardcoded)

---

## 💰 Costos

- **Render:** $0/mes (plan Free permanente)
- **OpenAI:** ~$2-5 por estudiante por sesión
- **Total:** Solo pagas OpenAI

**Recomendación:** Configura límite de $50-100/mes en OpenAI Platform

---

## 🔒 Seguridad

- ✅ API key en variables de entorno (no en código)
- ✅ HTTPS automático
- ✅ Logs de acceso disponibles
- ✅ Variables de entorno encriptadas en Render
- ✅ Los estudiantes NO pueden ver la API key

---

## 📧 Soporte

**Render:**
- Documentación: https://render.com/docs
- Community: https://community.render.com

**SimuPaciente UMH:**
- GitHub: https://github.com/marcosbenghezala/ECOE
- Universidad Miguel Hernández de Elche
