import os

arquivo = "temporario.txt"
if os.path.exists(arquivo):
    os.remove(arquivo)
