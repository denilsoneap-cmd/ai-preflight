import ast

from ai_preflight.resolver import ResolvedorDeImports


def test_resolve_chamada_direta_sem_import():
    tree = ast.parse("eval('1')\n")
    resolvedor = ResolvedorDeImports(tree)
    call_node = tree.body[0].value
    assert resolvedor.resolver_chamada(call_node) == "eval"


def test_resolve_atributo_com_import_simples():
    tree = ast.parse("import subprocess\nsubprocess.run(['ls'])\n")
    resolvedor = ResolvedorDeImports(tree)
    call_node = tree.body[1].value
    assert resolvedor.resolver_chamada(call_node) == "subprocess.run"


def test_resolve_atributo_com_apelido_de_import():
    tree = ast.parse("import subprocess as sp\nsp.run(['ls'])\n")
    resolvedor = ResolvedorDeImports(tree)
    call_node = tree.body[1].value
    assert resolvedor.resolver_chamada(call_node) == "subprocess.run"


def test_resolve_from_import_com_apelido():
    tree = ast.parse("from os import remove as apagar\napagar('a.txt')\n")
    resolvedor = ResolvedorDeImports(tree)
    call_node = tree.body[1].value
    assert resolvedor.resolver_chamada(call_node) == "os.remove"


def test_resolve_atributo_encadeado_os_path_join():
    tree = ast.parse("import os\nos.path.join('.git', 'hooks')\n")
    resolvedor = ResolvedorDeImports(tree)
    call_node = tree.body[1].value
    assert resolvedor.resolver_chamada(call_node) == "os.path.join"


def test_resolve_import_com_ponto_e_apelido():
    tree = ast.parse("import urllib.request as ur\nur.urlopen('x')\n")
    resolvedor = ResolvedorDeImports(tree)
    call_node = tree.body[1].value
    assert resolvedor.resolver_chamada(call_node) == "urllib.request.urlopen"
