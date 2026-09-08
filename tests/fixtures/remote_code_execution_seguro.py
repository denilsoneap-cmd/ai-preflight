import requests

resposta = requests.get("https://exemplo.com/dados.json")
dados = resposta.json()
print(dados)
