#Change this only
API_KEY     = '6579001304:AAHzUFMhRN7_esi2HM5xuO5jKPoZBf-RnGg'
CHAT_ID     = '-4037448120'

receive_info    = True
receive_warning = True

#Do not touch the rest below
BASE_URL    = 'https://api.telegram.org/bot' + API_KEY + '/sendMessage?chat_id='+ CHAT_ID

def send_info_msg(message):
    if receive_info:
        import requests
        final_message =  BASE_URL + '&text=' + '[Info] ' + message
        requests.get(final_message)

def send_warning_msg(message):
    if receive_warning:
        import requests
        final_message =  BASE_URL + '&text=' + '[Warning] ' + message
        requests.get(final_message)
