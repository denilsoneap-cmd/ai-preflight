import os


def lista_arquivos(pasta):
    for raiz, _, arquivos in os.walk(pasta):
        print(raiz, arquivos)


def grava_configuracao(caminho):
    with open(caminho, "w") as f:
        f.write("config=1")
