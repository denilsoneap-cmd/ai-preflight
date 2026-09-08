import os

for root, dirs, files in os.walk("."):
    for nome in files:
        caminho = os.path.join(root, nome)
        with open(caminho, "r") as fh:
            conteudo = fh.read()
