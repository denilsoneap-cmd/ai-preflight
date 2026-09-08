import ast

from ai_preflight.arvore import anexar_pais
from ai_preflight.resolver import ResolvedorDeImports
from ai_preflight import checadores


def _preparar(caminho_fixture):
    with open(caminho_fixture, "r", encoding="utf-8") as f:
        codigo = f.read()
    tree = ast.parse(codigo)
    anexar_pais(tree)
    resolvedor = ResolvedorDeImports(tree)
    return tree, resolvedor


def test_checar_pacote_instalado_detecta_no_arquivo_perigoso():
    tree, resolvedor = _preparar("tests/fixtures/v2/silent_package_install_perigoso.py")
    achados = checadores.checar_pacote_instalado_silenciosamente(tree, resolvedor)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "silent-package-install"
    assert achados[0]["severidade"] == "CRITICA"
    assert achados[0]["linha"] == 3


def test_checar_pacote_instalado_nao_detecta_no_arquivo_seguro():
    tree, resolvedor = _preparar("tests/fixtures/v2/silent_package_install_seguro.py")
    achados = checadores.checar_pacote_instalado_silenciosamente(tree, resolvedor)
    assert achados == []


def test_checar_pacote_instalado_detecta_mesmo_com_apelido_de_import():
    tree, resolvedor = _preparar("tests/fixtures/v2/silent_package_install_apelido_perigoso.py")
    achados = checadores.checar_pacote_instalado_silenciosamente(tree, resolvedor)
    assert len(achados) == 1


def test_checar_reescrita_detecta_no_arquivo_perigoso():
    tree, resolvedor = _preparar("tests/fixtures/v2/mass_file_rewrite_perigoso.py")
    achados = checadores.checar_reescrita_em_massa(tree, resolvedor)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "mass-file-rewrite"
    assert achados[0]["linha"] is not None


def test_checar_reescrita_nao_detecta_no_arquivo_seguro():
    tree, resolvedor = _preparar("tests/fixtures/v2/mass_file_rewrite_seguro.py")
    achados = checadores.checar_reescrita_em_massa(tree, resolvedor)
    assert achados == []


def test_checar_reescrita_nao_detecta_falso_positivo_estrutural():
    tree, resolvedor = _preparar(
        "tests/fixtures/v2/mass_file_rewrite_falso_positivo_estrutural_seguro.py"
    )
    achados = checadores.checar_reescrita_em_massa(tree, resolvedor)
    assert achados == []
