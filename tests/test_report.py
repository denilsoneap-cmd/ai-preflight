from ai_preflight.report import formatar_relatorio


def test_relatorio_vazio():
    texto = formatar_relatorio([])
    assert "Nenhum padrao perigoso encontrado" in texto


def test_relatorio_ordena_por_severidade():
    achados = [
        {"regra_id": "r-media", "severidade": "MEDIA", "linha": 5, "mensagem": "m", "trecho": "t"},
        {"regra_id": "r-critica", "severidade": "CRITICA", "linha": 1, "mensagem": "m", "trecho": "t"},
        {"regra_id": "r-alta", "severidade": "ALTA", "linha": 2, "mensagem": "m", "trecho": "t"},
    ]
    texto = formatar_relatorio(achados)
    posicao_critica = texto.index("r-critica")
    posicao_alta = texto.index("r-alta")
    posicao_media = texto.index("r-media")
    assert posicao_critica < posicao_alta < posicao_media


def test_relatorio_mostra_arquivo_inteiro_quando_linha_e_none():
    achados = [{"regra_id": "r-coocorrencia", "severidade": "CRITICA", "linha": None, "mensagem": "m", "trecho": "t"}]
    texto = formatar_relatorio(achados)
    assert "arquivo inteiro" in texto
