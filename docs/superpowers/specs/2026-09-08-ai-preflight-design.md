# ai-preflight — Design

## Contexto e motivação
Nasceu de um caso real: durante uma sessão de otimização de tokens, um script gerado por outra IA (`setup_ultra_token_ecosystem.py`) continha uma função de "auto-heal" que reescrevia arquivos `.py`/`.js`/`.ts` do projeto com uma regex quebrada, corrompendo código sem aviso, backup ou revisão. Outro script da mesma sessão instalava um pacote npm de terceiro não verificado, de forma silenciosa. Ambos foram pegos por revisão manual, não por ferramenta.

`ai-preflight` automatiza esse tipo específico de checagem: antes de rodar um script `.py` que uma IA (qualquer uma — Gemini, ChatGPT, Claude, etc.) te deu, você roda `ai-preflight` nele primeiro.

## Objetivo
Detectar, por análise estática de texto (regex), padrões de comportamento perigoso em scripts Python de automação/setup gerados por IA — especificamente os que **agem sozinhos sem pedir confirmação**: instalar pacotes, reescrever arquivos em massa, executar código baixado da internet, deletar coisas, ou se instalar como hook do Git.

**Não é objetivo** (fora de escopo da v1):
- Detectar bugs de segurança genéricos (isso já é o trabalho de ferramentas como `bandit`).
- Analisar Shell/Bash, JavaScript ou outras linguagens (só `.py` na v1).
- "Consertar" o script automaticamente — a ferramenta só avisa, nunca edita o arquivo analisado.
- Garantir 100% de detecção — é um alarme complementar à leitura humana, não uma prova de segurança.

## Arquitetura

```
ai-preflight/
  ai_preflight/
    __init__.py
    rules.py      # lista de regras: regex + severidade + descrição
    scanner.py     # le o arquivo, aplica as regras linha a linha, retorna achados
    report.py      # formata os achados como relatorio de terminal
    cli.py         # entry point: le argumento de linha de comando, chama scanner + report
  tests/
    test_rules.py  # cada regra tem 1 caso que deve disparar + 1 caso parecido que nao deve
    fixtures/       # scripts de exemplo (perigosos e inofensivos) usados nos testes
  README.md
  LICENSE           # MIT
  pyproject.toml    # empacotamento minimo (permite `pip install -e .` e o comando `ai-preflight`)
```

Cada módulo tem uma responsabilidade só:
- `rules.py`: só dados (lista de regras). Não tem lógica.
- `scanner.py`: só lógica de varredura. Recebe caminho de arquivo + lista de regras, devolve lista de achados (sem imprimir nada).
- `report.py`: só formatação. Recebe achados, devolve texto formatado (sem lógica de detecção).
- `cli.py`: cola tudo junto e cuida de argumentos/erros de linha de comando.

Essa separação permite testar `scanner.py` sem precisar rodar o CLI inteiro, e trocar o formato do relatório sem tocar na lógica de detecção.

## Formato de uma regra (`rules.py`)
Existem dois tipos de regra, porque nem todo padrão perigoso cabe em uma única linha:

**Regra de linha única** (`tipo: "linha"`) — o padrão inteiro aparece numa linha só:
```python
{
    "id": "silent-package-install",
    "tipo": "linha",
    "severidade": "CRITICA",
    "padrao": r'subprocess\.(run|call|Popen)\(.*\b(pip|npm)\b.*install',
    "mensagem": "Instalacao de pacote embutida no script, sem pedir confirmacao.",
}
```

**Regra de coocorrência** (`tipo: "coocorrencia"`) — dois padrões que, aparecendo JUNTOS em qualquer parte do mesmo arquivo, indicam risco (mesmo em linhas diferentes):
```python
{
    "id": "mass-file-rewrite",
    "tipo": "coocorrencia",
    "severidade": "CRITICA",
    "padrao_a": r'os\.walk\(',
    "padrao_b": r"open\([^)]*['\"]w['\"]",
    "mensagem": "Arquivo varre o projeto (os.walk) e reescreve arquivos (open com modo 'w') no mesmo script — risco de reescrita em massa sem confirmacao.",
}
```
Regra de coocorrência não aponta uma linha exata — aponta o arquivo inteiro como suspeito e mostra as linhas onde cada padrão (A e B) foi encontrado, para o usuário decidir.

Adicionar uma regra nova = adicionar um dicionário na lista. Não requer mexer em `scanner.py`.

## Regras da v1 (as 6 já validadas no design)
1. `silent-package-install` — linha única — CRÍTICA — `pip install`/`npm install -g` disparado via `subprocess` dentro do script.
2. `mass-file-rewrite` — coocorrência — CRÍTICA — `os.walk` e `open(..., 'w')` aparecem no mesmo arquivo.
3. `remote-shell-pipe` — linha única — CRÍTICA — padrão `curl ... | bash`/`sh` dentro de uma string de comando.
4. `remote-code-execution` — coocorrência — CRÍTICA — `requests.get`/`urllib` e `exec`/`eval` aparecem no mesmo arquivo.
5. `dynamic-eval-exec` — linha única — ALTA — uso de `eval(` ou `exec(` sobre uma string que não é um literal fixo.
6. `mass-delete` — coocorrência — ALTA — `for`/`while` e (`shutil.rmtree` ou `os.remove`) aparecem no mesmo arquivo.
7. `git-hook-injection` — linha única — MÉDIA — escrita de arquivo dentro de `.git/hooks/`.

(A regra 3 do design original virou duas regras separadas — 3 e 4 — porque eram dois padrões diferentes disfarçados de um só. A regra 5 (antiga "mass-delete") também foi corrigida de "linha única" pra "coocorrência", pelo mesmo motivo.)

## Fluxo de dados
1. `cli.py` recebe o caminho do arquivo via argumento (`sys.argv` ou `argparse`).
2. `scanner.py` lê o arquivo inteiro uma vez. Para regras de **linha única**, testa cada linha contra o padrão. Para regras de **coocorrência**, testa se `padrao_a` e `padrao_b` aparecem em qualquer lugar do conteúdo completo.
3. Cada correspondência vira um achado: `{regra_id, severidade, linha (ou None, se coocorrência), mensagem, trecho}`.
4. `report.py` recebe a lista de achados, ordena por severidade (CRÍTICA → ALTA → MÉDIA), imprime no terminal. Se a lista estiver vazia, imprime mensagem de "nenhum padrão perigoso encontrado" (deixando claro que isso não é garantia de segurança).
5. `cli.py` define o código de saída do processo: `1` se houver algum achado CRÍTICO (útil futuramente para uso em CI), `0` caso contrário.

## Tratamento de erros
- Arquivo não encontrado → mensagem clara, sai com código de erro, sem stack trace cru.
- Arquivo não é `.py` → aviso de que a v1 só suporta Python, sai sem tentar analisar.
- Erro de encoding ao ler o arquivo → tenta novamente ignorando caracteres inválidos (`errors="ignore"`), avisa que a leitura foi parcial.

## Testes
Para cada uma das 7 regras, em `tests/fixtures/`:
- Um arquivo `<regra>_perigoso.py` que **deve** disparar a regra.
- Um arquivo `<regra>_seguro.py` parecido (mesmas palavras-chave, contexto diferente) que **não deve** disparar — isso prova que a regra não é feita de falso positivo grosseiro (o mesmo erro que corrigimos hoje no `ia_code_auditor.py` com o `any`/`Company`).

`test_rules.py` roda o scanner contra cada fixture e confere o resultado esperado.

## Fora de escopo (v1) / próximos passos possíveis
- Suporte a Shell/PowerShell e JavaScript.
- Publicar no PyPI.
- Integração como pre-commit hook opcional (usando o framework `pre-commit`, não um hook caseiro).
- Banco de regras compartilhado/comunitário.

## Licença e publicação
MIT, repositório `ai-preflight` no GitHub do usuário.
