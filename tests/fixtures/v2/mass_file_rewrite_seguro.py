import os


def apenas_lista(pasta):
    for raiz, _, arquivos in os.walk(pasta):
        print(raiz, arquivos)
