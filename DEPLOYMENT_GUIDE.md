# 🚀 Guía de Deployment - SimuPaciente UMH

Guía paso a paso para desplegar el proxy server y configurar el sistema para estudiantes.

---

## 📋 Resumen

Para que los estudiantes puedan usar SimuPaciente sin configurar su propia API key:

1. **Tú** despliegas un proxy server en Render.com (100% gratis, sin tarjeta)
2. El proxy tiene tu API key (oculta)
3. **Estudiantes** usan el notebook de Colab que se conecta al proxy
4. ✅ Los estudiantes NO ven tu API key

---

## Parte 1: Desplegar Proxy en Render.com (10 minutos) - 100% GRATIS

### Paso 1: Crear cuenta en Render

1. Ve a https://render.com
2. Click en **"Get Started"**
3. Selecciona **"Sign up with GitHub"**
4. Autoriza Render (NO requiere tarjeta de crédito ✅)

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
- **Plan:** **Free** ⚠️ IMPORTANTE - Selecciona "Free"

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
3. Verás los logs de build en tiempo real
4. Espera a que el status cambie a **"Live"** (verde)

### Paso 6: Obtener la URL pública

1. Una vez desplegado, verás la URL en la parte superior del dashboard:
   ```
   https://simu-paciente-umh-proxy.onrender.com
   ```
2. **¡COPIA ESTA URL!** La necesitarás para el notebook

### Paso 7: Verificar que funciona

1. Abre en tu navegador:
   ```
   https://simu-paciente-umh-proxy.onrender.com/health
   ```

2. Deberías ver algo como:
   ```json
   {
     "status": "healthy",
     "openai_key_configured": true,
     "timestamp": "2025-12-18T12:00:00.000000"
   }
   ```

✅ **¡Proxy desplegado correctamente!**

### 📊 Límites del plan gratuito

- ✅ 750 horas/mes (suficiente para 24/7)
- ✅ 512 MB RAM
- ✅ HTTPS automático
- ⚠️ El servicio se duerme después de 15 min sin uso (primera request tarda ~30s en despertar)

---

## Parte 2: Actualizar Notebook de Colab

### Paso 1: Abrir el notebook en Colab

1. Ve a https://colab.research.google.com
2. File → Open notebook → GitHub
3. Busca `marcosbenghezala/ECOE`
4. Abre `SimuPaciente_UMH_Demo.ipynb`

### Paso 2: Modificar la configuración

En la **Celda 5** (Configurar API Keys), reemplaza TODO el contenido por:

```python
import os

# ============================================
# ✅ CONFIGURACIÓN AUTOMÁTICA VÍA PROXY
# ============================================
#
# Tu API key está en el servidor proxy
# Los estudiantes NO necesitan configurar nada
#
# ============================================

# URL del proxy server (desplegado en Render)
PROXY_URL = "https://TU-URL-DE-RENDER-AQUI.onrender.com"

# Configurar para usar el proxy
os.environ['PROXY_URL'] = PROXY_URL

print("="*50)
print("✅ Configuración completada automáticamente")
print(f"🔒 Usando proxy server: {PROXY_URL}")
print("="*50)
print("\n📝 No necesitas hacer nada más")
print("👉 Continúa ejecutando las siguientes celdas")
```

**⚠️ IMPORTANTE:** Reemplaza `TU-URL-DE-RENDER-AQUI` con la URL que copiaste en el Paso 6 anterior.

### Paso 3: Guardar el notebook

1. File → Save a copy in Drive
2. Renómbralo a algo como `SimuPaciente_UMH_Estudiantes.ipynb`

### Paso 4: Compartir con estudiantes

1. En Colab, click en **"Share"**
2. Configura:
   - **"Anyone with the link"** → **"Viewer"**
3. Copia el link

**Envía este link a tus estudiantes con estas instrucciones:**

```
🏥 SimuPaciente UMH - Instrucciones para Estudiantes

1. Abre este link: [LINK DE COLAB]
2. File → Save a copy in Drive
3. Runtime → Run all
4. ¡Espera a que aparezca la URL del simulador!
5. Click en el botón "🚀 Abrir Aplicación"

✅ No necesitas configurar ninguna API key
```

---

## Parte 3: Mantenimiento

### Ver logs del servidor

1. En Render, ve a tu dashboard
2. Click en tu servicio
3. Ve a **"Logs"** en la barra lateral
4. Verás los logs en tiempo real

### Detener el servidor (si es necesario)

1. En Render, ve a tu servicio
2. Click en **"Settings"** (barra lateral)
3. Scroll hasta abajo hasta "Delete Web Service"
4. Click en **"Delete Web Service"**
5. Confirma

El servidor se eliminará completamente.

### Limitar uso (recomendado)

En OpenAI Platform:
1. Ve a https://platform.openai.com/usage
2. Settings → Limits
3. Configura límites mensuales (ej: $50/mes)
4. Esto evita gastos inesperados

---

## 📊 Costos y Límites

### Render.com (100% GRATIS)
- ✅ 750 horas/mes de ejecución (suficiente para 24/7)
- ✅ 512 MB RAM
- ✅ HTTPS automático
- ✅ NO requiere tarjeta de crédito
- ⚠️ El servicio se duerme después de 15 min sin uso (primera request tarda ~30s)
- 💡 Suficiente para 20-50 estudiantes/mes

### OpenAI
- Realtime API: ~$0.06 por minuto de conversación
- GPT-4o-mini (evaluación): ~$0.0001 por respuesta
- **Estimado:** ~$2-5 por estudiante por sesión completa

**Recomendación:** Configura un límite de $50-100/mes en OpenAI

---

## 🐛 Solución de Problemas

### Problema: "API key not configured"

**Causa:** La variable `OPENAI_API_KEY` no está en Render

**Solución:**
1. Ve a Render → Tu servicio → Environment
2. Verifica que `OPENAI_API_KEY` existe
3. Verifica que el valor es correcto (empieza con `sk-proj-` o `sk-`)
4. Haz manual redeploy: "Manual Deploy" → "Deploy latest commit"

### Problema: "Connection refused" o "500 Server Error"

**Causa:** El servidor no está corriendo

**Solución:**
1. Ve a Render → Tu servicio → Logs
2. Verifica que el servicio está "Live" (verde)
3. Chequea los logs por errores
4. Redespliega si es necesario

### Problema: El servidor responde muy lento

**Causa:** Render duerme servicios inactivos

**Solución:**
- La primera request después de 15 min inactivo tarda ~30 segundos (spin-up)
- Esto es normal en el tier gratis
- Las siguientes requests son rápidas

### Problema: Los estudiantes ven errores en Colab

**Causa:** URL del proxy incorrecta

**Solución:**
1. Verifica que la URL en el notebook es correcta
2. Debe ser HTTPS (no HTTP)
3. No debe tener "/" al final
4. Ejemplo correcto: `https://abc.up.railway.app`

---

## 🎓 Flujo Completo para Estudiantes

```
┌──────────────────┐
│   Estudiante     │
│  abre Colab      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Save a copy     │
│  in Drive        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Runtime →       │
│  Run all         │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Notebook se     │
│  conecta al      │
│  PROXY           │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Proxy usa       │
│  TU API KEY      │
│  (oculta)        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  OpenAI          │
│  Realtime API    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Estudiante      │
│  practica        │
│  ✅              │
└──────────────────┘
```

---

## 📧 Soporte

¿Problemas con el deployment?

1. Chequea los logs en Render → Tu servicio → Logs
2. Verifica la configuración paso a paso
3. Consulta la documentación de Render: https://render.com/docs

**Universidad Miguel Hernández de Elche**
