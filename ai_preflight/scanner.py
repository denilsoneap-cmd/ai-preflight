import re


def escanear_arquivo(caminho, regras):
    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
        linhas = f.readlines()
    conteudo = "".join(linhas)

    achados = []
    for regra in regras:
        if regra["tipo"] == "linha":
            achados.extend(_escanear_regra_linha(regra, linhas))
        elif regra["tipo"] == "coocorrencia":
            achado = _escanear_regra_coocorrencia(regra, conteudo, linhas)
            if achado is not None:
                achados.append(achado)
    return achados


def _escanear_regra_linha(regra, linhas):
    achados = []
    padrao = re.compile(regra["padrao"])
    for numero, linha in enumerate(linhas, start=1):
        if padrao.search(linha):
            achados.append({
                "regra_id": regra["id"],
                "severidade": regra["severidade"],
                "linha": numero,
                "mensagem": regra["mensagem"],
                "trecho": linha.strip(),
            })
    return achados


def _escanear_regra_coocorrencia(regra, conteudo, linhas):
    padrao_a = re.compile(regra["padrao_a"])
    padrao_b = re.compile(regra["padrao_b"])
    if padrao_a.search(conteudo) and padrao_b.search(conteudo):
        return {
            "regra_id": regra["id"],
            "severidade": regra["severidade"],
            "linha": None,
            "mensagem": regra["mensagem"],
            "trecho": (
                f"padrao A na linha {_primeira_linha_com_padrao(padrao_a, linhas)}, "
                f"padrao B na linha {_primeira_linha_com_padrao(padrao_b, linhas)}"
            ),
        }
    return None


def _primeira_linha_com_padrao(padrao, linhas):
    for numero, linha in enumerate(linhas, start=1):
        if padrao.search(linha):
            return numero
    return None
