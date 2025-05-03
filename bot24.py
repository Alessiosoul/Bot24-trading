import time
import math
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException

# === CREDENZIALI BINANCE E TELEGRAM ===
api_key = '1Vuc0QLG5aYonI2RRSxGK1JKbxKg4bzUlaHLJ7Bg6VgvOdPrey5T8htKRDpXrWmo'
api_secret = 'OjTHhg6TeOh61k89mjyK2cRVFIG4nL5LYGJpwaNpAyk56OBGtV2SKfLo4nGGa1G4'
telegram_token = '7821995611:AAHuRo27fo07bptMxVPUhdcXdxJqQcW-ZWc'
telegram_chat_id = '167367006'

# === CONFIG ===
client = Client(api_key, api_secret)
symbol = 'BTCUSDC'
quantità_base = 0.0001
percentuale_range = 0.4
griglie_base = 4
soglia_reinvestimento = 5
percentuale_stop = 7  # STOP-LOSS dinamico al 7%

# === FUNZIONI BASE ===
def get_prezzo_corrente():
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

def calcola_range(prezzo, percentuale):
    offset = prezzo * (percentuale / 100)
    return round(prezzo - offset, 2), round(prezzo + offset, 2)

def crea_griglie(min_price, max_price, numero):
    intervallo = (max_price - min_price) / (numero + 1)
    return [round(min_price + i * intervallo, 2) for i in range(1, numero + 1)]

def cancella_ordini():
    try:
        ordini = client.get_open_orders(symbol=symbol)
        for ordine in ordini:
            client.cancel_order(symbol=symbol, orderId=ordine['orderId'])
    except Exception as e:
        invia_notifica(f"Errore cancellazione ordini: {e}")

def invia_notifica(msg):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {"chat_id": telegram_chat_id, "text": msg}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Errore Telegram:", e)

# === STRATEGIA GRID ===
def piazza_griglia(prezzo, griglie, quantità):
    min_r, max_r = calcola_range(prezzo, percentuale_range)
    griglie_prezzi = crea_griglie(min_r, max_r, griglie)
    cancella_ordini()
    for p in griglie_prezzi:
        try:
            if p < prezzo:
                client.order_limit_buy(symbol=symbol, quantity=str(quantità), price=str(p))
            else:
                client.order_limit_sell(symbol=symbol, quantity=str(quantità), price=str(p))
        except BinanceAPIException as e:
            invia_notifica(f"Errore ordine: {e.message}")

# === COMPOUND E GESTIONE CAPITALE ===
def get_saldo():
    saldo = client.get_asset_balance(asset='USDC')
    return float(saldo['free']) if saldo else 0

def calcola_quantità(capitale):
    qty = quantità_base * (capitale / 50)
    return round(qty - (qty % 0.00001), 5)  # Arrotondato per evitare errori LOT_SIZE

def aggiorna_griglie(capitale):
    if capitale >= 400:
        return 8
    elif capitale >= 250:
        return 6
    return griglie_base

def check_stop_loss(capitale, capitale_iniziale):
    soglia = capitale_iniziale * ((100 - percentuale_stop) / 100)
    return capitale < soglia

# === LOOP ===
def main():
    capitale_iniziale = get_saldo()
    while True:
        try:
            capitale_attuale = get_saldo()
            if check_stop_loss(capitale_attuale, capitale_iniziale):
                invia_notifica(f"[BOT STOP] Capitale sotto soglia sicurezza (-{percentuale_stop}%). Attuale: {capitale_attuale} USDC")
                cancella_ordini()
                break
            prezzo = get_prezzo_corrente()
            quantità = calcola_quantità(capitale_attuale)
            griglie = aggiorna_griglie(capitale_attuale)
            piazza_griglia(prezzo, griglie, quantità)
            if capitale_attuale - capitale_iniziale >= soglia_reinvestimento:
                capitale_iniziale = capitale_attuale
                invia_notifica(f"[COMPOUND] Nuovo capitale: {capitale_attuale} USDC – quantità BTC aggiornata: {quantità}")
            time.sleep(3600)
        except Exception as e:
            invia_notifica(f"Errore bot: {e}")
            time.sleep(3600)

if __name__ == "__main__":
    main()
0

