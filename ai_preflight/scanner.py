import re


def escanear_arquivo(caminho, regras):
    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
        linhas = f.readlines()

    achados = []
    for regra in regras:
        if regra["tipo"] == "linha":
            achados.extend(_escanear_regra_linha(regra, linhas))
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
