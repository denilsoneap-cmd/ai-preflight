from ai_preflight.scanner import escanear_arquivo


def test_escanear_arquivo_detecta_silent_package_install():
    achados = escanear_arquivo("tests/fixtures/v2/silent_package_install_perigoso.py")
    ids = [a["regra_id"] for a in achados]
    assert "silent-package-install" in ids


def test_escanear_arquivo_nao_detecta_nada_no_arquivo_seguro():
    achados = escanear_arquivo("tests/fixtures/v2/silent_package_install_seguro.py")
    assert achados == []


def test_escanear_arquivo_todo_achado_tem_linha_definida():
    achados = escanear_arquivo("tests/fixtures/v2/mass_file_rewrite_perigoso.py")
    assert len(achados) >= 1
    assert all(a["linha"] is not None for a in achados)


def test_escanear_arquivo_roda_todos_os_checadores_sem_erro_em_arquivo_vazio(tmp_path):
    arquivo = tmp_path / "vazio.py"
    arquivo.write_text("")
    achados = escanear_arquivo(str(arquivo))
    assert achados == []
