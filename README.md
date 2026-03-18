# Finanzer 📊

Aplicación de análisis financiero completo con scoring propietario, valoración intrínseca y reportes PDF profesionales.

## Stack

- **Frontend**: Next.js 15 + TypeScript + Tailwind CSS + Recharts
- **Backend**: FastAPI + Python 3 (reportlab, curl_cffi)
- **Datos**: Yahoo Finance (endpoints directos)

## Funcionalidades

- 🎯 **Score Finanzer** (0-100): Modelo adaptativo que evalúa valoración, rentabilidad, solidez, crecimiento y estabilidad
- 📊 **7 tabs de análisis**: Valoración, Rentabilidad, Solidez Financiera, Histórico, Comparativa Sectorial, Evaluación Institucional, Valor Intrínseco
- 🧮 **Valor Intrínseco**: Graham Number + DCF multi-etapa + Análisis de sensibilidad
- 📈 **Altman Z-Score** y **Piotroski F-Score** completos
- ❓ **Tooltips informativos** en cada indicador (60+ explicaciones)
- 📄 **PDF profesional** de 8-9 páginas descargable
- 🔍 **Búsqueda** con autocompletado (base local + Yahoo)

## Instalación

### Backend
```bash
cd backend
pip install fastapi uvicorn curl_cffi reportlab
python3 -m uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

La app estará en `http://localhost:3000`

## Uso Personal

Este proyecto está diseñado para uso personal/educativo. Los datos provienen de Yahoo Finance (sin API key necesaria).

---

*No constituye asesoría financiera.*
