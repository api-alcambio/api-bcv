import re
from datetime import datetime
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup

app = FastAPI(title="API BCV", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
BCV_URL = "https://www.bcv.org.ve/"

def extraer():
    usd, eur = 0.0, 0.0
    fecha = None
    try:
        print("Consultando BCV...")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(BCV_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        texto = soup.get_text()
        html = resp.text
        contenido = texto + html
        
        m_usd = re.search(r'USD\s*[:\s]*\s*(\d+(?:[.,]\d+)?)', contenido, re.IGNORECASE)
        if m_usd: usd = float(m_usd.group(1).replace(",", "."))
        
        m_eur = re.search(r'EUR\s*[:\s]*\s*(\d+(?:[.,]\d+)?)', contenido, re.IGNORECASE)
        if m_eur: eur = float(m_eur.group(1).replace(",", "."))
        
        m_fecha = re.search(r'Fecha\s+Valor[:\s]+([A-Za-záéíóúñÁÉÍÓÚÑ]+,?\s*\d{1,2}\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+\s+\d{4})', contenido, re.IGNORECASE)
        if m_fecha: fecha = m_fecha.group(1)
        
        print(f"USD: {usd}, EUR: {eur}, Fecha: {fecha}")
    except Exception as e:
        print(f"ERROR: {e}")
        fecha = f"Error: {str(e)[:80]}"
    return usd, eur, fecha

_cache = {"data": None, "ts": 0}

def obtener(cache=True):
    import time
    now = time.time()
    if cache and _cache["data"] and (now - _cache["ts"] < 3600):
        return _cache["data"]
    usd, eur, fecha = extraer()
    if usd > 0 or eur > 0:
        _cache["data"] = (usd, eur, fecha)
        _cache["ts"] = now
    return usd, eur, fecha

@app.get("/")
def info():
    return {"api": "API BCV", "version": "1.0.0", "endpoints": ["/tasas", "/dolar", "/euro"]}

@app.get("/tasas")
def get_tasas(cache: bool = Query(True)):
    usd, eur, fecha = obtener(cache)
    return {
        "fuente": "BCV",
        "fecha_valor": fecha,
        "fecha_consulta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tasas": [
            {"codigo": "USD", "nombre": "Dolar", "tasa": usd},
            {"codigo": "EUR", "nombre": "Euro", "tasa": eur}
        ]
    }

@app.get("/dolar")
def get_dolar(cache: bool = Query(True)):
    usd, _, fecha = obtener(cache)
    return {"codigo": "USD", "nombre": "Dolar", "tasa": usd, "fecha_valor": fecha}

@app.get("/euro")
def get_euro(cache: bool = Query(True)):
    _, eur, fecha = obtener(cache)
    return {"codigo": "EUR", "nombre": "Euro", "tasa": eur, "fecha_valor": fecha}

@app.get("/health")
def health():
    return {"status": "ok"}