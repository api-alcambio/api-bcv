import re
from datetime import datetime
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
import urllib3

# Desactivar warnings de SSL para el sitio del BCV que tiene certificado inválido
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="API BCV", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
BCV_URL = "https://www.bcv.org.ve/"

def extraer():
    usd, eur = 0.0, 0.0
    fecha = None
    try:
        print("Consultando BCV...")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(BCV_URL, headers=headers, timeout=15, verify=False)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        html = resp.text
        
        # Buscar valores en el HTML - el BCV usa formato español (coma como decimal)
        # Ejemplo: 462,66870000
        patron_numero = r'(\d{1,3}(?:\.\d{3})*,\d+)'
        
        # Buscar USD - usualmente aparece junto a "DÓLAR" o en el bloque del dólar
        m_usd = re.search(r'USD[^>]*>.*?' + patron_numero, html, re.IGNORECASE | re.DOTALL)
        if not m_usd:
            # Intentar buscando por la palabra Dólar
            m_usd = re.search(r'D[oó]lar[^<]*</[^>]*>.*?' + patron_numero, html, re.IGNORECASE | re.DOTALL)
        if m_usd:
            valor = m_usd.group(1).replace('.', '').replace(',', '.')
            usd = float(valor)
        
        # Buscar EUR - Euro
        m_eur = re.search(r'EUR[^>]*>.*?' + patron_numero, html, re.IGNORECASE | re.DOTALL)
        if not m_eur:
            m_eur = re.search(r'Euro[^<]*</[^>]*>.*?' + patron_numero, html, re.IGNORECASE | re.DOTALL)
        if m_eur:
            valor = m_eur.group(1).replace('.', '').replace(',', '.')
            eur = float(valor)
        
        # Buscar fecha - formato: "Miércoles, 25 Marzo 2026"
        m_fecha = re.search(r'([LlMmJjVvSsDd][aáeéiíoóuúñAÁEÉIÍOÓUÚÑ]+,?\s*\d{1,2}\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+\s+\d{4})', html)
        if m_fecha:
            fecha = m_fecha.group(1)
        
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