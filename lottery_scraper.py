import requests
import time
import threading
import schedule
from datetime import datetime
from bs4 import BeautifulSoup

# ================= CONFIGURACIÓN =================
MAX_REINTENTOS = 15          # 15 minutos máximo esperando (1 minuto cada intento)
INTERVALO_REINTENTO = 60     # 1 minuto entre reintentos

# Horarios de los sorteos (en UTC, ajusta según tu zona)
HORARIOS_SCRAPING = ["12:09", "22:00"]  # 2 PM y 10 PM UTC

# Variable global para la aplicación Flask
_flask_app = None

# ============ FUNCIONES DE SCRAPING POR ESTADO ============

def scrape_florida(tipo_sorteo="Evening"):
    """
    Intenta obtener los resultados de Florida (Pick 3 y Pick 4).
    Reintenta cada minuto hasta conseguir datos o superar MAX_REINTENTOS.
    """
    url = "https://www.flalottery.com/pick3"  # página de Pick 3
    headers = {"User-Agent": "Mozilla/5.0"}
    intentos = 0
    while intentos < MAX_REINTENTOS:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            # Buscar números (ejemplo - debes ajustar el selector real)
            numbers_div = soup.find('div', class_='winning-numbers')
            if numbers_div:
                numbers_text = numbers_div.get_text(strip=True)
                numeros = '-'.join(numbers_text.split())
                resultado = {
                    'estado': 'Florida',
                    'juego': 'Pick 3',
                    'sorteo': tipo_sorteo,
                    'numeros': numeros,
                    'fecha_sorteo': datetime.utcnow(),
                    'fireball': None
                }
                return [resultado]
            else:
                print(f"Florida: aún no hay resultados. Reintento {intentos+1}")
                time.sleep(INTERVALO_REINTENTO)
                intentos += 1
        except Exception as e:
            print(f"Error scraping Florida: {e}")
            time.sleep(INTERVALO_REINTENTO)
            intentos += 1
    print("Florida: no se obtuvieron resultados después de varios reintentos.")
    return []

def scrape_ny(tipo_sorteo="Evening"):
    """
    Scraping de Nueva York usando dataset CSV oficial.
    """
    import csv, io
    url = "https://data.ny.gov/api/views/kyjy-7prn/rows.csv?accessType=DOWNLOAD"
    intentos = 0
    while intentos < MAX_REINTENTOS:
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            reader = csv.DictReader(io.StringIO(response.text))
            resultados = []
            for row in reader:
                game = row.get('GAME', '')
                if 'Numbers' not in game and 'Win 4' not in game:
                    continue
                fecha = datetime.strptime(row['DRAW_DATE'], '%Y-%m-%d')
                numeros = '-'.join(row['WINNING_NUMBERS'].split())
                sorteo = 'Evening' if 'E' in row.get('DRAW_TIME', '') else 'Midday'
                juego = 'Pick 3' if 'Numbers' in game else 'Pick 4'
                resultados.append({
                    'estado': 'New York',
                    'juego': juego,
                    'sorteo': sorteo,
                    'numeros': numeros,
                    'fecha_sorteo': fecha,
                    'fireball': None
                })
            if resultados:
                return resultados
            else:
                print("NY: CSV descargado pero sin resultados. Reintentando...")
                time.sleep(INTERVALO_REINTENTO)
                intentos += 1
        except Exception as e:
            print(f"Error scraping NY: {e}")
            time.sleep(INTERVALO_REINTENTO)
            intentos += 1
    return []

def scrape_georgia(tipo_sorteo="Evening"):
    """
    Scraping de Georgia desde lotteryusa.com con reintentos.
    """
    url = "https://www.lotteryusa.com/georgia/"
    intentos = 0
    while intentos < MAX_REINTENTOS:
        try:
            response = requests.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            resultados = []
            for game in soup.find_all('div', class_='draw-game'):
                name = game.find('h3')
                if not name:
                    continue
                name_text = name.get_text().lower()
                if 'cash 3' in name_text:
                    juego = 'Pick 3'
                elif 'cash 4' in name_text:
                    juego = 'Pick 4'
                else:
                    continue
                numbers_div = game.find('div', class_='numbers')
                if numbers_div:
                    numeros = '-'.join(numbers_div.get_text().split())
                    date_span = game.find('span', class_='draw-date')
                    fecha = datetime.utcnow()
                    if date_span:
                        try:
                            fecha = datetime.strptime(date_span.get_text(), '%b %d, %Y')
                        except:
                            pass
                    resultados.append({
                        'estado': 'Georgia',
                        'juego': juego,
                        'sorteo': tipo_sorteo,
                        'numeros': numeros,
                        'fecha_sorteo': fecha,
                        'fireball': None
                    })
            if resultados:
                return resultados
            else:
                print("Georgia: aún sin números. Reintentando...")
                time.sleep(INTERVALO_REINTENTO)
                intentos += 1
        except Exception as e:
            print(f"Error scraping Georgia: {e}")
            time.sleep(INTERVALO_REINTENTO)
            intentos += 1
    return []

# ============ FUNCIONES PARA GUARDAR EN BD ============

def guardar_resultados(resultados):
    """Guarda en BD si no existen ya (evita duplicados)."""
    if not resultados:
        return
    from models import db, ResultadoLoteria
    for res in resultados:
        existe = ResultadoLoteria.query.filter_by(
            estado=res['estado'],
            juego=res['juego'],
            sorteo=res['sorteo'],
            fecha_sorteo=res['fecha_sorteo'].date()
        ).first()
        if not existe:
            nuevo = ResultadoLoteria(**res)
            db.session.add(nuevo)
    db.session.commit()

# ============ FUNCIÓN PRINCIPAL QUE DISPARA SCRAPING ============

def ejecutar_scraping_completo():
    """Ejecuta scraping dentro del contexto de la aplicación."""
    global _flask_app
    if _flask_app is None:
        print("Error: Scheduler no inicializado correctamente")
        return
    
    with _flask_app.app_context():
        print(f"[{datetime.now()}] Iniciando scraping programado...")
        # Llamar a cada scraping
        fl_results = scrape_florida()
        guardar_resultados(fl_results)
        ny_results = scrape_ny()
        guardar_resultados(ny_results)
        ga_results = scrape_georgia()
        guardar_resultados(ga_results)
        print(f"[{datetime.now()}] Scraping finalizado.")

# ============ SCHEDULER INTERNO ============

def iniciar_scheduler(app):
    """Configura el scheduler con la instancia de Flask."""
    global _flask_app
    _flask_app = app
    print("🟢 Scheduler de scraping iniciado")
    
    for hora in HORARIOS_SCRAPING:
        schedule.every().day.at(hora).do(ejecutar_scraping_completo)
    
    def run_loop():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()