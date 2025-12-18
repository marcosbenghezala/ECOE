# 🚀 Guía de Deployment - SimuPaciente UMH

Guía paso a paso para desplegar el proxy server y configurar el sistema para estudiantes.

---

## 📋 Resumen

Para que los estudiantes puedan usar SimuPaciente sin configurar su propia API key:

1. **Tú** despliegas un proxy server en Railway (gratis)
2. El proxy tiene tu API key (oculta)
3. **Estudiantes** usan el notebook de Colab que se conecta al proxy
4. ✅ Los estudiantes NO ven tu API key

---

## Parte 1: Desplegar Proxy en Railway (15 minutos)

### Paso 1: Crear cuenta en Railway

1. Ve a https://railway.app
2. Click en **"Login"**
3. Selecciona **"Login with GitHub"**
4. Autoriza Railway para acceder a tu cuenta de GitHub

### Paso 2: Crear nuevo proyecto

1. En el dashboard de Railway, click en **"New Project"**
2. Selecciona **"Deploy from GitHub repo"**
3. Busca y selecciona tu repositorio **`marcosbenghezala/ECOE`**
4. Railway comenzará a detectar el código

### Paso 3: Configurar el servicio

1. Railway creará automáticamente un servicio
2. Click en el servicio que se creó
3. Ve a **"Settings"** (⚙️ en la barra lateral)
4. En la sección **"Service Settings"**:
   - **Root Directory**: Cambia a `proxy_server`
   - **Start Command**: Debería detectar automáticamente `gunicorn app:app`
5. Click en **"Deploy"** (arriba a la derecha)

### Paso 4: Añadir variables de entorno

1. En la barra lateral, click en **"Variables"** (📝)
2. Click en **"+ New Variable"**
3. Añade:
   - **Variable name:** `OPENAI_API_KEY`
   - **Value:** Tu API key de OpenAI (ej: `sk-proj-...`)
4. Click en **"Add"**
5. El servicio se redesplegar á automáticamente

### Paso 5: Obtener la URL pública

1. Ve a **"Settings"** → **"Networking"**
2. En la sección **"Public Networking"**:
   - Click en **"Generate Domain"**
3. Railway te dará una URL como:
   ```
   https://simulador-umh-production.up.railway.app
   ```
4. **¡COPIA ESTA URL!** La necesitarás para el notebook

### Paso 6: Verificar que funciona

1. Abre en tu navegador:
   ```
   https://TU-URL-DE-RAILWAY.up.railway.app/health
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

# URL del proxy server (desplegado en Railway)
PROXY_URL = "https://TU-URL-DE-RAILWAY-AQUI.up.railway.app"

# Configurar para usar el proxy
os.environ['PROXY_URL'] = PROXY_URL

print("="*50)
print("✅ Configuración completada automáticamente")
print(f"🔒 Usando proxy server: {PROXY_URL}")
print("="*50)
print("\n📝 No necesitas hacer nada más")
print("👉 Continúa ejecutando las siguientes celdas")
```

**⚠️ IMPORTANTE:** Reemplaza `TU-URL-DE-RAILWAY-AQUI` con la URL que copiaste en el Paso 5 anterior.

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

1. En Railway, ve a tu proyecto
2. Click en el servicio
3. Ve a **"Deployments"**
4. Click en el deployment activo
5. Verás los logs en tiempo real

### Detener el servidor (si es necesario)

1. En Railway, ve a **"Settings"**
2. Scroll hasta abajo
3. Click en **"Remove Service"**
4. Confirma

El servidor se detendrá y dejará de consumir recursos.

### Limitar uso (recomendado)

En OpenAI Platform:
1. Ve a https://platform.openai.com/usage
2. Settings → Limits
3. Configura límites mensuales (ej: $50/mes)
4. Esto evita gastos inesperados

---

## 📊 Costos y Límites

### Railway (Gratis)
- ✅ 500 horas/mes de ejecución
- ✅ $5 USD de crédito gratis
- ⚠️ Después se duerme (no hay cargos)
- 💡 Suficiente para ~20-30 estudiantes simultáneos

### OpenAI
- Realtime API: ~$0.06 por minuto de conversación
- GPT-4o-mini (evaluación): ~$0.0001 por respuesta
- **Estimado:** ~$2-5 por estudiante por sesión completa

**Recomendación:** Configura un límite de $50-100/mes en OpenAI

---

## 🐛 Solución de Problemas

### Problema: "API key not configured"

**Causa:** La variable `OPENAI_API_KEY` no está en Railway

**Solución:**
1. Ve a Railway → Variables
2. Verifica que `OPENAI_API_KEY` existe
3. Verifica que el valor es correcto (empieza con `sk-proj-` o `sk-`)
4. Redesplega el servicio

### Problema: "Connection refused" o "500 Server Error"

**Causa:** El servidor no está corriendo

**Solución:**
1. Ve a Railway → Deployments
2. Verifica que hay un deployment activo
3. Chequea los logs por errores
4. Redespliega si es necesario

### Problema: El servidor responde muy lento

**Causa:** Railway duerme servicios inactivos

**Solución:**
- La primera request después de dormir tarda 10-20 segundos
- Esto es normal en el tier gratis
- Considera el tier Pro de Railway ($5/mes) para evitar sleep

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

1. Chequea los logs en Railway
2. Verifica la configuración paso a paso
3. Contacta al equipo técnico

**Universidad Miguel Hernández de Elche**
