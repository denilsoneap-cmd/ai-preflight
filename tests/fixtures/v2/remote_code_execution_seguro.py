import requests


def baixa_dados():
    resposta = requests.get("https://exemplo.com/dados.json")
    return resposta.json()


def calcula():
    return eval("1 + 1")
