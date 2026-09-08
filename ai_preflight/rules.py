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
    {
        "id": "mass-file-rewrite",
        "tipo": RULE_COOCORRENCIA,
        "severidade": "CRITICA",
        "padrao_a": r"os\.walk\(",
        "padrao_b": r"open\([^)]*['\"]w['\"]",
        "mensagem": "Arquivo varre o projeto (os.walk) e reescreve arquivos (open com modo 'w') no mesmo script.",
    },
    {
        "id": "remote-shell-pipe",
        "tipo": RULE_LINHA,
        "severidade": "CRITICA",
        "padrao": r"curl\s.*\|\s*(bash|sh)\b",
        "mensagem": "Comando baixa conteudo da internet e executa direto no shell (curl | bash).",
    },
]
