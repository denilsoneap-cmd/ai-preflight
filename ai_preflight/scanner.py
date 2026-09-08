import ast

from ai_preflight.arvore import anexar_pais
from ai_preflight.resolver import ResolvedorDeImports
from ai_preflight.checadores import TODOS_CHECADORES


def escanear_arquivo(caminho):
    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
        conteudo = f.read()

    tree = ast.parse(conteudo, filename=caminho)
    anexar_pais(tree)
    resolver = ResolvedorDeImports(tree)

    achados = []
    for checador in TODOS_CHECADORES:
        achados.extend(checador(tree, resolver))
    return achados
