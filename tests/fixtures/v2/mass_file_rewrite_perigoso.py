import os


def reescreve_tudo(pasta):
    for raiz, _, arquivos in os.walk(pasta):
        for nome in arquivos:
            with open(nome, "w") as f:
                f.write("")
