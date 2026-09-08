import ast


def anexar_pais(tree):
    for pai in ast.walk(tree):
        for filho in ast.iter_child_nodes(pai):
            filho.pai = pai
    tree.pai = None
    return tree


def primeiro_ancestral(node, tipo):
    atual = getattr(node, "pai", None)
    while atual is not None:
        if isinstance(atual, tipo):
            return atual
        atual = getattr(atual, "pai", None)
    return None
