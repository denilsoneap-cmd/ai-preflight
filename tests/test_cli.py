from ai_preflight.cli import main


def test_main_retorna_1_quando_ha_achado_critico(capsys):
    codigo = main(["tests/fixtures/silent_package_install_perigoso.py"])
    saida = capsys.readouterr().out
    assert codigo == 1
    assert "silent-package-install" in saida


def test_main_retorna_0_quando_arquivo_e_seguro(capsys):
    codigo = main(["tests/fixtures/silent_package_install_seguro.py"])
    assert codigo == 0


def test_main_retorna_2_quando_arquivo_nao_existe(capsys):
    codigo = main(["nao_existe.py"])
    saida = capsys.readouterr().out
    assert codigo == 2
    assert "nao encontrado" in saida.lower()


def test_main_retorna_2_quando_arquivo_nao_e_py(capsys, tmp_path):
    arquivo_txt = tmp_path / "nota.txt"
    arquivo_txt.write_text("ola")
    codigo = main([str(arquivo_txt)])
    assert codigo == 2


def test_main_retorna_2_quando_arquivo_tem_erro_de_sintaxe(capsys, tmp_path):
    arquivo_py = tmp_path / "quebrado.py"
    arquivo_py.write_text("def f(:\n")
    codigo = main([str(arquivo_py)])
    saida = capsys.readouterr().out
    assert codigo == 2
    assert "nao foi possivel interpretar" in saida.lower()


def test_main_retorna_2_quando_caminho_e_diretorio(capsys, tmp_path):
    diretorio_py = tmp_path / "pasta.py"
    diretorio_py.mkdir()
    codigo = main([str(diretorio_py)])
    saida = capsys.readouterr().out
    assert codigo == 2
    assert "nao foi possivel ler" in saida.lower()
