import os

for pasta, _, arquivos in os.walk("."):
    for nome in arquivos:
        with open(os.path.join(pasta, nome), "r+b") as f:
            f.read()
