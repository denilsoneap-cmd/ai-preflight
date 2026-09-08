import requests


def executa_script_remoto():
    resposta = requests.get("https://exemplo.com/script.py")
    exec(resposta.text)
