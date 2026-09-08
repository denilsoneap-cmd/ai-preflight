import io
import os

for pasta, _, arquivos in os.walk("."):
    for nome in arquivos:
        with io.open(os.path.join(pasta, nome), "w") as f:
            f.write("")
