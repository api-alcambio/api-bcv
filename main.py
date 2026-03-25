import re, time, os
from datetime import datetime
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Configuración para Render/Linux
    opts.binary_location = "/usr/bin/chromium"
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--remote-debugging-port=9222")
    
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=opts)

def extraer():
    driver = None
    tasas = {
        "USD": {"tasa": 0.0, "nombre": "Dolar", "simbolo": "$"},
        "EUR": {"tasa": 0.0, "nombre": "Euro", "simbolo": "E"},
        "CNY": {"tasa": 0.0, "nombre": "Yuan", "simbolo": "Y"},
        "TRY": {"tasa": 0.0, "nombre": "Lira", "simbolo": "L"},
        "RUB": {"tasa": 0.0, "nombre": "Rublo", "simbolo": "R"}
    }
    fecha = None
    try:
        print("Iniciando Chrome...")
        driver = get_driver()
        driver.set_page_load_timeout(30)
        print("Cargando BCV...")
        driver.get(BCV_URL)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        html = driver.page_source
        try:
            texto = driver.execute_script("return document.body.innerText") or ""
        except:
            texto = ""
        contenido = html + texto
        print("Buscando tasas...")
        for codigo in tasas:
            match = re.search(rf'{codigo}\s*[:\s]*\s*(\d+(?:[.,]\d+)?)', contenido, re.IGNORECASE)
            if match:
                tasas[codigo]["tasa"] = float(match.group(1).replace(",", "."))
                print(f"  {codigo}: {tasas[codigo]['tasa']}")
        match_fecha = re.search(r'Fecha\s+Valor[:\s]+([A-Za-záéíóúñÁÉÍÓÚÑ]+,?\s*\d{1,2}\s+[A-Za-záéíóúñÁÉÍÓÚÑ]+\s+\d{4})', contenido, re.IGNORECASE)
        if match_fecha:
            fecha = match_fecha.group(1)
        print("OK!")
    except Exception as e:
        print(f"ERROR: {e}")
        fecha = f"Error: {str(e)}"
    finally:
        if driver:
            try: driver.quit()
            except: pass
    return tasas, fecha

_cache = {"data": None, "ts": 0}

def obtener(cache=True):
    import time as t
    now = t.time()
    if cache and _cache["data"] and (now - _cache["ts"] < 3600):
        return _cache["data"]
    tasas, fecha = extraer()
    _cache["data"] = (tasas, fecha)
    _cache["ts"] = now
    return tasas, fecha

@app.get("/")
def info():
    return {"api": "API BCV", "version": "1.0.0", "endpoints": ["/tasas", "/dolar", "/euro", "/health"]}

@app.get("/tasas")
def get_tasas(cache: bool = Query(True)):
    tasas, fecha = obtener(cache)
    lista = [{"codigo": c, "nombre": i["nombre"], "tasa": i["tasa"], "simbolo": i["simbolo"]} for c, i in tasas.items()]
    return {"fuente": "BCV", "fecha_valor": fecha, "fecha_consulta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "tasas": lista}

@app.get("/dolar")
def get_dolar(cache: bool = Query(True)):
    tasas, fecha = obtener(cache)
    i = tasas["USD"]
    return {"codigo": "USD", "nombre": i["nombre"], "tasa": i["tasa"], "simbolo": i["simbolo"], "fecha_valor": fecha}

@app.get("/euro")
def get_euro(cache: bool = Query(True)):
    tasas, fecha = obtener(cache)
    i = tasas["EUR"]
    return {"codigo": "EUR", "nombre": i["nombre"], "tasa": i["tasa"], "simbolo": i["simbolo"], "fecha_valor": fecha}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)