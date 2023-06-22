from send_order import create_order
from impulse_macd import recession_check, side_check
from telegram_bot import send_message
import time

symbol = "LTCUSDT"
side = "BUY"
waiting = 0  # 1 or 0
leverage = 1
size = 5      #percent
TP = 15      #percent
SL = 10         #percent
calibration_perc = 1
time_in_force = "GTC"
number_of_successive_zeros = 8
pct_decrease_to_sell = 3 # pct
pct_increase_to_buy = 3 #pct



while True:
    if recession_check(number_of_successive_zeros):
        position = side_check(symbol, pct_increase_to_buy, pct_decrease_to_sell)
        print("opportunity spotted")
        create_order(TP, SL, leverage, symbol, size, waiting, calibration_perc, time_in_force, position)
        break
    else:
        time.sleep(3)
        send_message("We're still runnings")