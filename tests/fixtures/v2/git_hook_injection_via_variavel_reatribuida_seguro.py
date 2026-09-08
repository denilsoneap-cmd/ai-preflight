import os

hook_path = os.path.join(".git", "hooks", "pre-commit")
hook_path = "relatorio.txt"
with open(hook_path, "w") as f:
    f.write("dados do relatorio\n")
