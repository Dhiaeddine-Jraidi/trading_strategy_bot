import requests
import hashlib
import hmac
import time
from binance.client import Client
import threading

api_key = "b90ffa21e951fc1b50781ea36db8f2623be678526331574ad34fd4b8ec0a5514"
api_secret = "37ca3613d089de53eec79d7215bdbe68d99d65cc5f70d1c3339c83a824e5bb0f"
base_url = "https://testnet.binancefuture.com"

def call_available_balance(api_key, api_secret, base_url):
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    payload = {"timestamp": timestamp , "signature": signature }
    response = requests.get(base_url + "/fapi/v2/account", params=payload, headers={"X-MBX-APIKEY": api_key})
    if response.status_code == 200:
        return response.json()['availableBalance']
    else:
        return "Balance extraction failed"

def last_price(base_url, symbol, side, waiting, calibration_perc):
    url = base_url + '/fapi/v1/depth'
    params = {'symbol': symbol, 'limit': 10}
    order_book = requests.get(url, params=params).json()
    buy_price = float(order_book['asks'][0][0])
    sell_price = float(order_book['bids'][0][0])
    if side == "BUY" and waiting == 1:
        price = buy_price / (1 + (calibration_perc / 100))
    else:
        if side == "BUY" and waiting == 0:
            price = buy_price
        else:
            if side == "SELL" and waiting == 1:
                price = sell_price * (1 + (calibration_perc / 100))
            else:
                price = sell_price
    return price

def change_leverage(base_url, symbol, leverage, api_key, api_secret):
    url = base_url + '/fapi/v1/leverage'
    timestamp = int(time.time() * 1000)
    payload = {'symbol': symbol, 'leverage': leverage, 'timestamp': timestamp}
    query_string = '&'.join([f'{key}={payload[key]}' for key in payload])
    signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    payload['signature'] = signature
    headers = {'X-MBX-APIKEY': api_key}
    response = requests.post(url, params=payload, headers=headers)
    if response.status_code == 200:
        return 1
    else:
        return 0

def setting_TP_SL(api_key, api_secret, symbol, SL, TP, price, side):
    client = Client(api_key=api_key, api_secret=api_secret, testnet=True)
    if side == "BUY":
        exit_price_TP = round(price * (1 + (TP / 100)), 2)
        exit_price_SL = round(price / (1 + (SL / 100)), 2)
        client.futures_create_order(symbol=symbol, side='SELL', type='STOP_MARKET', stopPrice=exit_price_SL,
                                    closePosition='true')
        client.futures_create_order(symbol=symbol, side='SELL', type='TAKE_PROFIT_MARKET', stopPrice=exit_price_TP,
                                    closePosition='true')
    else:
        exit_price_TP = round(price / (1 + (TP / 100)), 2)
        exit_price_SL = round(price * (1 + (SL / 100)), 2)
        client.futures_create_order(symbol=symbol, side='BUY', type='STOP_MARKET', stopPrice=exit_price_SL,
                                    closePosition='true')
        client.futures_create_order(symbol=symbol, side='BUY', type='TAKE_PROFIT_MARKET', stopPrice=exit_price_TP,
                                    closePosition='true')

def create_order(TP, SL, leverage, symbol, size, waiting, calibration_perc, time_in_force, side):
    def change_leverage_async():
        nonlocal leverage_response
        leverage_response = change_leverage(base_url, symbol, leverage, api_key, api_secret)

    def call_available_balance_async():
        nonlocal available_balance
        available_balance = float(call_available_balance(api_key, api_secret, base_url))

    def last_price_async():
        nonlocal price
        price = round(float(last_price(base_url, symbol, side, waiting, calibration_perc)), 2)

    def create_order_async():
        nonlocal response
        leverage_thread.join()
        available_balance_thread.join()
        last_price_thread.join()

        balance_to_use = available_balance * (size / 100) * leverage
        quantity = round(balance_to_use / price, 2)

        type = "LIMIT"
        timestamp = int(time.time() * 1000)
        query_string = f"symbol={symbol}&side={side}&type={type}&quantity={quantity}&price={price}&timeInForce={time_in_force}&timestamp={timestamp}"
        signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        payload = {"symbol": symbol, "side": side, "type": type, "quantity": quantity, "price": price,
                   "timeInForce": time_in_force, "timestamp": timestamp, "signature": signature}
        response = requests.post(base_url + "/fapi/v1/order", params=payload, headers={"X-MBX-APIKEY": api_key})
        if response.status_code == 200:
            client = Client(api_key=api_key, api_secret=api_secret, testnet=True)
            if side == "BUY":
                exit_price_TP = round(price * (1 + (TP / 100)), 2)
                exit_price_SL = round(price / (1 + (SL / 100)), 2)
                client.futures_create_order(symbol=symbol, side='SELL', type='STOP_MARKET', stopPrice=exit_price_SL,
                                            closePosition='true')
                client.futures_create_order(symbol=symbol, side='SELL', type='TAKE_PROFIT_MARKET',
                                            stopPrice=exit_price_TP, closePosition='true')
            else:
                exit_price_TP = round(price / (1 + (TP / 100)), 2)
                exit_price_SL = round(price * (1 + (SL / 100)), 2)
                client.futures_create_order(symbol=symbol, side='BUY', type='STOP_MARKET', stopPrice=exit_price_SL,
                                            closePosition='true')
                client.futures_create_order(symbol=symbol, side='BUY', type='TAKE_PROFIT_MARKET',
                                            stopPrice=exit_price_TP, closePosition='true')

            print("Order request successful!")
            print(response.json())
        else:
            print("Order request failed!")
            print(response.text)

    leverage_response = None
    available_balance = None
    price = None
    response = None

    leverage_thread = threading.Thread(target=change_leverage_async)
    available_balance_thread = threading.Thread(target=call_available_balance_async)
    last_price_thread = threading.Thread(target=last_price_async)
    create_order_thread = threading.Thread(target=create_order_async)

    leverage_thread.start()
    available_balance_thread.start()
    last_price_thread.start()
    create_order_thread.start()