import re, time
from datetime import datetime
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = FastAPI(title="API BCV", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
BCV_URL = "https://www.bcv.org.ve/"

def get_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-images")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    opts.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=opts)

def extraer():
    driver = None
    usd, eur = 0.0, 0.0
    fecha = None
    try:
        print("Cargando BCV...")
        driver = get_driver()
        driver.set_page_load_timeout(20)
        driver.get(BCV_URL)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        html = driver.page_source
        
        m_usd = re.search(r'USD\s*[:\s]*\s*(\d+(?:[.,]\d+)?)', html, re.IGNORECASE)
        if m_usd: usd = float(m_usd.group(1).replace(",", "."))
        
        m_eur = re.search(r'EUR\s*[:\s]*\s*(\d+(?:[.,]\d+)?)', html, re.IGNORECASE)
        if m_eur: eur = float(m_eur.group(1).replace(",", "."))
        
        m_fecha = re.search(r'Fecha\s+Valor[:\s]+([A-Za-záéíóúñÁÉÍÓÚÑ]+,?\s*\d{1,2}\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+\s+\d{4})', html, re.IGNORECASE)
        if m_fecha: fecha = m_fecha.group(1)
        print(f"USD: {usd}, EUR: {eur}")
    except Exception as e:
        print(f"ERROR: {e}")
        fecha = f"Error: {str(e)[:80]}"
    finally:
        if driver:
            try: driver.quit()
            except: pass
    return usd, eur, fecha

_cache = {"data": None, "ts": 0}

def obtener(cache=True):
    import time as t
    now = t.time()
    if cache and _cache["data"] and (now - _cache["ts"] < 3600):
        return _cache["data"]
    usd, eur, fecha = extraer()
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)