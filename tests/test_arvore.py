import ast

from ai_preflight.arvore import anexar_pais, primeiro_ancestral


def test_anexar_pais_define_pai_em_no_filho():
    tree = ast.parse("for x in y:\n    open('a', 'w')\n")
    anexar_pais(tree)
    for_node = tree.body[0]
    expr_node = for_node.body[0]
    assert expr_node.pai is for_node


def test_anexar_pais_raiz_tem_pai_none():
    tree = ast.parse("x = 1\n")
    anexar_pais(tree)
    assert tree.pai is None


def test_primeiro_ancestral_encontra_for_ancestral():
    tree = ast.parse("for x in y:\n    open('a', 'w')\n")
    anexar_pais(tree)
    call_node = tree.body[0].body[0].value
    resultado = primeiro_ancestral(call_node, ast.For)
    assert resultado is tree.body[0]


def test_primeiro_ancestral_retorna_none_quando_nao_ha_ancestral():
    tree = ast.parse("open('a', 'w')\n")
    anexar_pais(tree)
    call_node = tree.body[0].value
    resultado = primeiro_ancestral(call_node, ast.For)
    assert resultado is None


def test_primeiro_ancestral_aceita_tupla_de_tipos():
    tree = ast.parse("while True:\n    open('a', 'w')\n")
    anexar_pais(tree)
    call_node = tree.body[0].body[0].value
    resultado = primeiro_ancestral(call_node, (ast.For, ast.While))
    assert resultado is tree.body[0]
