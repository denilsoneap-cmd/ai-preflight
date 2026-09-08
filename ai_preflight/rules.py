RULE_LINHA = "linha"
RULE_COOCORRENCIA = "coocorrencia"

ALL_RULES = [
    {
        "id": "silent-package-install",
        "tipo": RULE_LINHA,
        "severidade": "CRITICA",
        "padrao": r"subprocess\.(run|call|Popen)\(.*\b(pip|npm)\b.*install",
        "mensagem": "Instalacao de pacote embutida no script, sem pedir confirmacao.",
    },
]
