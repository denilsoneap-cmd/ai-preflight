import os

arquivos = ["a.txt", "b.txt", "c.txt"]
[os.remove(f) for f in arquivos]
