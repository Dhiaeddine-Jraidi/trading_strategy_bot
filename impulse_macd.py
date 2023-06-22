import ccxt
import pandas as pd
import numpy as np
from binance import ThreadedWebsocketManager

def impulse_df(symbol):
    BB_squeeze_threshold = 0.015
    limit=1000
    timeframe= '1h'
    exchange = ccxt.binance()
    ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    data = []
    for candle in ohlcv_data:
        timestamp, open_price, high_price, low_price, close_price, volume = candle
        data.append([timestamp, open_price, high_price, low_price, close_price, volume])
    df = pd.DataFrame(data, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
    def calc_smma(src, length):
        smma = np.empty(len(src))
        smma[0] = np.nan
        for i in range(1, len(src)):
            if np.isnan(smma[i-1]):
                smma[i] = np.mean(src[:i+1])
            else:
                smma[i] = (smma[i-1] * (length - 1) + src[i]) / length
        return smma
    
    def calc_zlema(src, length):
        ema1 = pd.Series(src).ewm(span=length).mean()
        ema2 = ema1.ewm(span=length).mean()
        d = ema1 - ema2
        return ema1 + d
    
    lengthMA = 34
    lengthSignal = 9
    src = df['Close']
    hi = calc_smma(df['High'], lengthMA)
    lo = calc_smma(df['Low'], lengthMA)
    mi = calc_zlema(src, lengthMA)
    md = np.where(mi > hi, mi - hi, np.where(mi < lo, mi - lo, 0))
    sb = pd.Series(md).rolling(window=lengthSignal).mean()
    sh = md - sb
    df['ImpulseMACD'] = md
    df['ImpulseHisto'] = sh
    df['ImpulseMACDCDSignal'] = sb
    period = 20 
    std = df['Close'].rolling(window=period).std()
    df['BollingerMid'] = df['Close'].rolling(window=period).mean()
    df['BollingerUpper'] = df['BollingerMid'] + 2 * std
    df['BollingerLower'] = df['BollingerMid'] - 2 * std
    df['BollingerSqueeze'] = np.where((df['BollingerUpper'] - df['BollingerLower']) / df['BollingerMid'] < BB_squeeze_threshold, True, False)
    return df



def recession_check(number_of_successive_zeros):
    symbol = 'BTC/USDT'
    recent_rows = impulse_df(symbol).tail(number_of_successive_zeros)
    zeros = recent_rows['ImpulseMACDCDSignal'] == 0
    if zeros.all():
        return True
    else:
        return False
    

def side_check(symbol, pct_increase_to_buy, pct_decrease_to_sell):
    df1 = impulse_df(symbol)
    midprice = df1.at[df1.index[-1], 'BollingerMid']
    target_price_to_buy = midprice + (midprice * (pct_increase_to_buy / 100))
    target_price_to_sell = midprice - (midprice * (pct_decrease_to_sell / 100))
    
    def handle_socket_message(msg):
        # Extract relevant information from the received message
        #symbol = msg['s']  # Trading pair symbol
        price = float(msg['c'])  # Current price

        # Process the data as per your requirements
        #print(f"{symbol} - Price: {price}")
        return price

    twm = ThreadedWebsocketManager()
    twm.start()

    # Create variables to store the current prices
    current_price = None

    def on_message(msg):
        nonlocal current_price
        current_price = handle_socket_message(msg)

    # Subscribe to the symbol's ticker WebSocket feed
    twm.start_symbol_ticker_socket(callback=on_message, symbol=symbol)

    # Enter a loop to keep the WebSocket connection active
    while True:
        # Compare the current price with the target prices
        if current_price and current_price <= target_price_to_sell:
            twm.stop()
            return "SELL"
        
        if current_price and current_price >= target_price_to_buy:
            twm.stop()
            return "BUY"
        


impulse_df("BTCUSDT")




