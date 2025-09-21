import time
import csv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://catalogonacionalmhi.inah.gob.mx/consultaPublica"
ARCHIVO_CSV = "monumentos_por_estado_municipio_v009.csv"

# =============== CONFIGURACIÓN ===============
# Lista de estados a procesar. Si está vacía, recorre todos los disponibles.
ESTADOS_OBJETIVO = ["Morelos"]
# Si es True, abre Chrome en modo headless (sin ventana).
MODO_HEADLESS = False
# ============================================

def iniciar_navegador(headless=False):
    """Configura y abre el navegador Chrome."""
    opciones = webdriver.ChromeOptions()
    if headless:
        opciones.add_argument("--headless=new")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opciones
    )
    driver.set_window_size(1280, 900)
    return driver

def abrir_busqueda_avanzada(driver):
    """Abre la página inicial y muestra el panel de 'Búsqueda avanzada'."""
    print("-> Abriendo página…")
    driver.get(URL)
    time.sleep(2)
    # Como el portal no permite avanzar sin abrir la búsqueda avanzada, se presiona el botón
    print("-> Mostrando 'Búsqueda avanzada'…")
    driver.find_element(By.ID, "mostrarCriterios").click()
    time.sleep(1)

def listar_estados(driver):
    """Devuelve una lista de estados disponibles en el selector."""
    sel = Select(driver.find_element(By.ID, "entidad_federativa_id"))
    estados = [op.text for op in sel.options if op.get_attribute("value")]
    return estados

def seleccionar_estado(driver, nombre_estado):
    """Selecciona un estado específico en el menú desplegable."""
    print(f"-> Estado: {nombre_estado}")
    sel = Select(driver.find_element(By.ID, "entidad_federativa_id"))
    sel.select_by_visible_text(nombre_estado)
    time.sleep(2)

def listar_municipios(driver):
    """Obtiene la lista de municipios según el estado seleccionado."""
    sel = Select(driver.find_element(By.ID, "municipio_id"))
    municipios = [op.text for op in sel.options if op.get_attribute("value")]
    print(f"   Municipios encontrados: {len(municipios)}")
    return municipios

def seleccionar_municipio(driver, nombre_municipio):
    """Selecciona un municipio en el menú desplegable."""
    sel = Select(driver.find_element(By.ID, "municipio_id"))
    sel.select_by_visible_text(nombre_municipio)
    time.sleep(0.5)

def _click_con_scroll_y_js(driver, elemento):
    """Hace scroll hasta el elemento y luego intenta dar click (normal o vía JS)."""
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elemento)
    time.sleep(0.2)
    try:
        elemento.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", elemento)

def dar_click_buscar(driver):
    """Presiona el botón 'Buscar' para mostrar resultados de estado/municipio."""
    boton = driver.find_element(By.ID, "buscarObjeto")
    _click_con_scroll_y_js(driver, boton)
    print("   - Buscando…")
    time.sleep(2)

def _leer_texto_o_cero(driver, css):
    """Lee el texto de un selector CSS; si no hay dígitos devuelve '0'."""
    try:
        txt = driver.find_element(By.CSS_SELECTOR, css).text.strip()
        return txt if any(ch.isdigit() for ch in txt) else "0"
    except:
        return "0"

def leer_contadores(driver, espera_seg=6):
    """Espera unos segundos y luego lee los totales de monumentos y fichas."""
    fin = time.time() + espera_seg
    while time.time() < fin:
        monumentos = _leer_texto_o_cero(driver, "span.total-historico-cp")
        conjuntos  = _leer_texto_o_cero(driver, "span.total-arquitectonico-cp")
        bvc        = _leer_texto_o_cero(driver, "span.total-cultutral-cp")
        sin_clas   = _leer_texto_o_cero(driver, "span.total-generico-cp")
        if any(v != "0" for v in (monumentos, conjuntos, bvc, sin_clas)):
            return monumentos, conjuntos, bvc, sin_clas
        time.sleep(0.5)
    return (
        _leer_texto_o_cero(driver, "span.total-historico-cp"),
        _leer_texto_o_cero(driver, "span.total-arquitectonico-cp"),
        _leer_texto_o_cero(driver, "span.total-cultutral-cp"),
        _leer_texto_o_cero(driver, "span.total-generico-cp"),
    )

def guardar_csv_append(fila, ruta=ARCHIVO_CSV):
    """Guarda los resultados en un archivo CSV (agrega filas si ya existe)."""
    encabezados = ["Estado", "Municipio",
                   "Monumentos", "Conjuntos Arquitectónicos",
                   "Bienes Inmuebles con Valor Cultural", "Fichas sin Clasificación"]
    import os
    nuevo = not os.path.exists(ruta)
    with open(ruta, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(encabezados)
        w.writerow(fila)

def main():
    """Ejecuta el flujo completo: abre navegador, recorre estados y municipios, guarda CSV."""
    driver = iniciar_navegador(headless=MODO_HEADLESS)
    try:
        abrir_busqueda_avanzada(driver)
        todos_estados = listar_estados(driver)
        if ESTADOS_OBJETIVO:
            estados_a = [e for e in todos_estados if e in ESTADOS_OBJETIVO]
            if not estados_a:
                print("! Ningún estado coincide con ESTADOS_OBJETIVO. Recorriendo TODOS…")
                estados_a = todos_estados
        else:
            estados_a = todos_estados

        for estado in estados_a:
            seleccionar_estado(driver, estado)
            municipios = listar_municipios(driver)
            for municipio in municipios:
                print(f"   -> Municipio: {municipio}")
                seleccionar_municipio(driver, municipio)
                dar_click_buscar(driver)
                m, cj, bvc, sc = leer_contadores(driver)
                print(f"      Totales => M:{m} | Cj:{cj} | BVC:{bvc} | SC:{sc}")
                guardar_csv_append([estado, municipio, m, cj, bvc, sc])
                time.sleep(0.3)
        print("-> Proceso finalizado.")
    finally:
        driver.quit()
        print("-> Navegador cerrado.")

if __name__ == "__main__":
    main()
