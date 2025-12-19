# Plan de Migración a Railway - SimuPaciente UMH

## DIAGNÓSTICO DEL PROBLEMA

### Problema Real Identificado:
El frontend tiene **MÚLTIPLES referencias hardcodeadas a localhost**:

1. **`api.ts` línea 13:** `API_BASE_URL = import.meta.env.VITE_API_URL || ""`
   - ✅ CORRECTO (ya usa string vacío para URLs relativas)

2. **`simulation-interface.tsx` línea 32:** `WS_URL = import.meta.env.VITE_API_URL?.replace('http', 'ws') || "ws://localhost:8080"`
   - ❌ PROBLEMA: Fallback a localhost para WebSocket

3. **`vite.config.ts` líneas 16-23:** Proxy de desarrollo apunta a localhost
   - ✅ OK: Solo para desarrollo local, NO afecta producción

### Por qué el build no cambia:
- Vite genera los mismos hashes porque `api.ts` YA tiene `|| ""`
- Pero `simulation-interface.tsx` SIGUE teniendo `|| "ws://localhost:8080"`
- El navegador intenta conectar WebSocket a localhost y falla

---

## SOLUCIÓN: 3 PASOS

### PASO 1: Arreglar WebSocket URL (simulation-interface.tsx)

**Cambiar:**
```typescript
const WS_URL = import.meta.env.VITE_API_URL?.replace('http', 'ws') || "ws://localhost:8080"
```

**Por:**
```typescript
// Use relative WebSocket URL (window.location automatically)
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
```

**Justificación:**
- `window.location.host` automáticamente usa el dominio actual
- En Railway: `wss://web-production-e4cd.up.railway.app`
- En localhost: `ws://localhost:8080`
- NO necesita variables de entorno


### PASO 2: Limpiar archivos innecesarios de Colab

**Eliminar completamente:**
1. `DEPLOYMENT_GUIDE.md` - Ya eliminado ✓
2. `SimuPaciente_UMH_Demo.ipynb` - Ya eliminado ✓
3. Cualquier script en `/scripts` que mencione Colab (verificar)

**Mantener:**
- `DEPLOY_RAILWAY.md` - Guía de deployment
- `DEMO_PROFESORES.md` - Presentación para profesores
- `proxy_server/` - Servidor proxy en Render.com


### PASO 3: Verificar configuración de Railway

**Variables de entorno necesarias:**
- `OPENAI_API_KEY` - API key de OpenAI (ya configurada)
- `PROXY_URL` - URL del proxy server (ya configurada)
- `GOOGLE_SHEETS_CREDENTIALS` - Opcional para después

**NO necesita:**
- `VITE_API_URL` - NO es necesario con URLs relativas

---

## EJECUCIÓN DEL PLAN

### Acción 1: Actualizar simulation-interface.tsx
```typescript
// Línea 32, reemplazar por:
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_URL = `${protocol}//${window.location.host}`
```

### Acción 2: Commit y push
```bash
git add simulador/frontend/src/components/simulation-interface.tsx
git commit -m "fix: Use dynamic WebSocket URL based on window.location"
git push
```

### Acción 3: Esperar rebuild de Railway
- Build time estimado: ~30 segundos
- Los hashes de JS **CAMBIARÁN** (simulation-interface.tsx cambió)
- Nuevo hash esperado: `index-XXXXXXX.js` (diferente a `C7qB8cra`)

### Acción 4: Verificar en producción
1. Abrir https://web-production-e4cd.up.railway.app en incógnito
2. Verificar en F12 Network:
   - ✅ Peticiones a `/api/cases` (sin localhost)
   - ✅ WebSocket conecta a `wss://web-production-e4cd.up.railway.app/ws/realtime/...`
3. Verificar en logs de Railway:
   - ✅ `GET /api/cases HTTP/1.1 200`
   - ✅ WebSocket upgrade requests

---

## RESULTADO ESPERADO

**Antes (ACTUAL):**
```
Browser console: ERR_CONNECTION_REFUSED localhost:8080
Railway logs: (no peticiones a /api/cases)
```

**Después (ESPERADO):**
```
Browser console: Conectando a wss://web-production-e4cd.up.railway.app/ws/realtime/...
Railway logs: GET /api/cases 200, WebSocket /ws/realtime/... 101
Frontend: Muestra lista de casos clínicos
```

---

## ARCHIVOS A MODIFICAR

1. `simulador/frontend/src/components/simulation-interface.tsx` - Línea 32

## ARCHIVOS A ELIMINAR (LIMPIEZA)

Ninguno adicional (ya eliminados Colab files)

## ESTIMACIÓN DE TIEMPO

- Modificar código: 30 segundos
- Build en Railway: 30 segundos
- Verificación: 2 minutos
- **Total: ~3 minutos**

---

## CONFIRMACIÓN ANTES DE PROCEDER

¿Aprobar este plan y ejecutar?
- ✅ SÍ: Modificar `simulation-interface.tsx` y deployar
- ❌ NO: Ajustar plan según feedback
