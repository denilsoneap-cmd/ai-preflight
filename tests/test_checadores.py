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


def test_checar_pipe_shell_detecta_no_arquivo_perigoso():
    tree, resolvedor = _preparar("tests/fixtures/v2/remote_shell_pipe_perigoso.py")
    achados = checadores.checar_pipe_shell_remoto(tree, resolvedor)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "remote-shell-pipe"


def test_checar_pipe_shell_nao_detecta_em_print_inofensivo():
    tree, resolvedor = _preparar("tests/fixtures/v2/remote_shell_pipe_seguro.py")
    achados = checadores.checar_pipe_shell_remoto(tree, resolvedor)
    assert achados == []


def test_checar_execucao_remota_detecta_no_arquivo_perigoso():
    tree, resolvedor = _preparar("tests/fixtures/v2/remote_code_execution_perigoso.py")
    achados = checadores.checar_execucao_remota(tree, resolvedor)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "remote-code-execution"


def test_checar_execucao_remota_nao_detecta_quando_em_escopos_diferentes():
    tree, resolvedor = _preparar("tests/fixtures/v2/remote_code_execution_seguro.py")
    achados = checadores.checar_execucao_remota(tree, resolvedor)
    assert achados == []


def test_checar_eval_exec_dinamico_detecta_no_arquivo_perigoso():
    tree, resolvedor = _preparar("tests/fixtures/v2/dynamic_eval_exec_perigoso.py")
    achados = checadores.checar_eval_exec_dinamico(tree, resolvedor)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "dynamic-eval-exec"
    assert achados[0]["severidade"] == "ALTA"


def test_checar_eval_exec_dinamico_nao_detecta_texto_fixo():
    tree, resolvedor = _preparar("tests/fixtures/v2/dynamic_eval_exec_seguro.py")
    achados = checadores.checar_eval_exec_dinamico(tree, resolvedor)
    assert achados == []
