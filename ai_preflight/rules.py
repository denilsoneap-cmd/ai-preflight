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
    {
        "id": "remote-code-execution",
        "tipo": RULE_COOCORRENCIA,
        "severidade": "CRITICA",
        "padrao_a": r"requests\.get\(|urllib\.request",
        "padrao_b": r"\b(exec|eval)\(",
        "mensagem": "Script baixa conteudo da internet (requests/urllib) e executa (exec/eval) no mesmo arquivo.",
    },
    {
        "id": "dynamic-eval-exec",
        "tipo": RULE_LINHA,
        "severidade": "ALTA",
        "padrao": r"\b(eval|exec)\(\s*(?![\"'])",
        "mensagem": "eval/exec chamado sobre uma variavel, nao um texto fixo — risco de executar codigo desconhecido.",
    },
]
