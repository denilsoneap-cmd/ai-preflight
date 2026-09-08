ORDEM_SEVERIDADE = {"CRITICA": 0, "ALTA": 1, "MEDIA": 2}


def formatar_relatorio(achados):
    if not achados:
        return (
            "Nenhum padrao perigoso encontrado.\n"
            "Isso nao garante que o script e seguro — revise manualmente antes de rodar."
        )

    achados_ordenados = sorted(achados, key=lambda a: ORDEM_SEVERIDADE.get(a["severidade"], 99))

    linhas_saida = ["RELATORIO DE PREFLIGHT", "=" * 40]
    for achado in achados_ordenados:
        local = f"linha {achado['linha']}" if achado["linha"] is not None else "arquivo inteiro"
        linhas_saida.append(f"[{achado['severidade']}] {achado['regra_id']} ({local})")
        linhas_saida.append(f"  {achado['mensagem']}")
        linhas_saida.append(f"  Trecho: {achado['trecho']}")
        linhas_saida.append("")

    return "\n".join(linhas_saida)
