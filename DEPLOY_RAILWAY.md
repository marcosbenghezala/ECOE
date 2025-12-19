# 🚀 Guía de Deployment en Railway - SimuPaciente UMH

## ⏱️ Tiempo estimado: 10 minutos

---

## 📋 PASO 1: Crear Cuenta en Railway (2 minutos)

1. Ve a https://railway.app
2. Click en **"Start a New Project"** o **"Login"**
3. **Sign up with GitHub** (más fácil)
4. Autoriza Railway para acceder a tus repositorios

✅ **Tienes $5 de crédito gratis** (dura ~1 mes con tu uso)

---

## 📦 PASO 2: Crear Nuevo Proyecto (1 minuto)

1. En el dashboard de Railway, click **"New Project"**
2. Selecciona **"Deploy from GitHub repo"**
3. Busca y selecciona: **`marcosbenghezala/ECOE`**
4. Railway empezará a deployar automáticamente

**⏳ Espera 2-3 minutos** mientras Railway:
- Clona tu repositorio
- Instala dependencias de Python
- Builds el frontend (ya está incluido)
- Inicia el servidor

---

## 🔧 PASO 3: Configurar Variables de Entorno (3 minutos)

**IMPORTANTE:** El deploy fallará hasta que configures las variables.

### 3.1 Ir a Settings

1. Click en tu proyecto deployado
2. Click en la pestaña **"Variables"** (en el menú izquierdo)

### 3.2 Añadir Variables

Click **"New Variable"** y añade estas **una por una**:

#### Variable 1: OPENAI_API_KEY
```
OPENAI_API_KEY=tu_api_key_de_openai_aquí
```
**Donde obtenerla:** https://platform.openai.com/api-keys

#### Variable 2: PROXY_URL (Opcional)
```
PROXY_URL=https://simu-paciente-umh-proxy.onrender.com
```
**Nota:** Solo si quieres usar el proxy. Si no, omite esta variable.

#### Variable 3: GOOGLE_SHEETS_CREDENTIALS (Si usas Google Sheets)
```
GOOGLE_SHEETS_CREDENTIALS={"type":"service_account","project_id":"..."}
```
**Nota:** Pega todo el JSON de las credenciales de Google (el archivo completo)

### 3.3 Aplicar Cambios

1. Click **"Add"** después de cada variable
2. Railway **reiniciará automáticamente** el servicio

---

## 🌐 PASO 4: Obtener URL Pública (1 minuto)

1. En el dashboard del proyecto, click en tu servicio
2. Ve a la pestaña **"Settings"**
3. Scroll hasta **"Networking"** o **"Domains"**
4. Click **"Generate Domain"**
5. Railway te dará una URL tipo: `https://simu-paciente-umh.up.railway.app`

✅ **¡Esa es tu URL pública!**

---

## ✅ PASO 5: Verificar que Funciona (2 minutos)

1. Abre la URL en tu navegador
2. Deberías ver la pantalla de inicio de SimuPaciente
3. Prueba:
   - ✅ Seleccionar un caso
   - ✅ Iniciar simulación
   - ✅ Probar el micrófono
   - ✅ Hablar con el paciente virtual

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### El deploy falla

**Revisa los logs:**
1. Click en tu servicio
2. Click en la pestaña **"Deployments"**
3. Click en el deployment más reciente
4. Lee los logs para ver el error

**Errores comunes:**
- ❌ `OPENAI_API_KEY not found` → Añade la variable de entorno
- ❌ `Module not found` → Railway está instalando dependencias, espera
- ❌ `Port already in use` → Reinicia el servicio

### La aplicación se queda cargando

1. Espera 1-2 minutos (el primer inicio es lento)
2. Recarga la página
3. Si persiste, revisa logs

### No se conecta a OpenAI Realtime API

1. Verifica que `OPENAI_API_KEY` está configurada
2. Verifica que tu API key tiene acceso a Realtime API (beta)
3. Verifica que tienes créditos en OpenAI

---

## 💰 COSTOS

### Con $5 de crédito gratis:
- **~500 horas de servidor** (suficiente para 1 mes)
- **~1000 requests** de OpenAI Realtime API
- **Bandwidth ilimitado**

### Cuando se acaben los $5:
- Railway te avisará
- Puedes añadir $5 más
- O migrar a otra plataforma

**Costo mensual estimado:** $5-10 USD para 300 usuarios ocasionales

---

## 📧 SOPORTE

Si algo no funciona:
1. Revisa los logs en Railway
2. Verifica las variables de entorno
3. Contacta: marcos.benghez@umh.es

---

## 🎉 ¡Listo!

Ahora puedes compartir la URL con los profesores para la demo.

**URL de ejemplo:** `https://simu-paciente-umh.up.railway.app`

**Usuario de prueba:** Cualquier email
**Caso de prueba:** "Dolor torácico en varón de 55 años"

---

**Desarrollado por:** Marcos Bengheza
**Universidad Miguel Hernández de Elche**
**Fecha:** Diciembre 2025
