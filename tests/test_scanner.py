from ai_preflight.rules import ALL_RULES
from ai_preflight.scanner import escanear_arquivo


def _regra(id_da_regra):
    return [r for r in ALL_RULES if r["id"] == id_da_regra]


def test_detecta_silent_package_install_no_arquivo_perigoso():
    regra = _regra("silent-package-install")
    achados = escanear_arquivo("tests/fixtures/silent_package_install_perigoso.py", regra)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "silent-package-install"
    assert achados[0]["severidade"] == "CRITICA"
    assert achados[0]["linha"] == 3


def test_nao_detecta_no_arquivo_seguro():
    regra = _regra("silent-package-install")
    achados = escanear_arquivo("tests/fixtures/silent_package_install_seguro.py", regra)
    assert achados == []


def test_detecta_mass_file_rewrite_no_arquivo_perigoso():
    regra = _regra("mass-file-rewrite")
    achados = escanear_arquivo("tests/fixtures/mass_file_rewrite_perigoso.py", regra)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "mass-file-rewrite"
    assert achados[0]["linha"] is None


def test_nao_detecta_mass_file_rewrite_no_arquivo_seguro():
    regra = _regra("mass-file-rewrite")
    achados = escanear_arquivo("tests/fixtures/mass_file_rewrite_seguro.py", regra)
    assert achados == []
