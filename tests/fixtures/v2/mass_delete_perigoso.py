import os


def limpa_arquivos(lista):
    for nome in lista:
        os.remove(nome)
