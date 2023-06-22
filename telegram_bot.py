import requests

def send_message(message):
    bot_token = '6177479067:AAE8t93A1fpwfRynh7WX68E5wMxs-pWxucQ'
    chat_id = '-963685658'
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': message
    }
    requests.post(url, data=data)
