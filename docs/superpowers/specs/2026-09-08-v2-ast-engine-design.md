# ai-preflight v2, Fase 1 — Motor de deteccao baseado em AST

## Contexto e motivacao
A v1 detecta padroes perigosos com regex sobre o texto do arquivo. Isso tem limites conhecidos e aceitos na v1: falso positivo por coincidencia textual, incapacidade de entender apelidos de import (`import subprocess as sp`), e checagem de "coocorrencia" que so prova que dois padroes existem no MESMO ARQUIVO, nao que estao de fato relacionados (ex: um `os.walk` numa funcao e um `open(..., 'w')` sem nenhuma relacao numa funcao completamente diferente dispara a regra da v1 do mesmo jeito que o caso perigoso de verdade).

A v2 Fase 1 troca o motor por analise da arvore de sintaxe (AST) do proprio Python, resolvendo essas tres limitacoes especificas, mantendo a mesma filosofia da v1: biblioteca padrao apenas, sem dependencia externa, cada checagem prontamente testavel.

## Decisao de abordagem
Avaliadas 3 abordagens:
1. **AST da biblioteca padrao, visitor customizado com injecao de ponteiros de pai** (escolhida) — zero dependencia externa, controle total, mesma filosofia da v1.
2. Bibliotecas de analise semantica prontas (`astroid`, `libcst`) — mais poder pronto, mas viram caixa-preta, adicionam dependencia externa, contradizem a filosofia "stdlib only" da v1.
3. Motor de plugins estilo `bandit` — complexidade desnecessaria pro escopo atual.

## O que muda
- `ai_preflight/rules.py` (dicionarios de regex) e removido.
- `ai_preflight/scanner.py` e reescrito: em vez de ler linhas de texto, faz `ast.parse()` do arquivo.
- Novo `ai_preflight/arvore.py`: injeta um atributo `.pai` em cada no da arvore (o modulo `ast` do Python nao guarda isso nativamente), permitindo perguntar "esse no esta contido dentro de um laco de tipo X?".
- Novo `ai_preflight/resolver.py`: le todos os `import`/`from...import` do arquivo e monta uma tabela de apelidos, permitindo resolver `sp.run(...)` para o nome canonico `subprocess.run` mesmo com `import subprocess as sp`.
- Novo `ai_preflight/checadores.py`: um conjunto de funcoes Python (uma por regra), cada uma navegando a arvore e o resolvedor. Substitui os dicionarios declarativos da v1 — a logica de deteccao agora e codigo, nao dado.
- `ai_preflight/report.py` e `ai_preflight/cli.py` sao mantidos com o minimo de alteracao possivel (so trocam a chamada para o novo `escanear_arquivo`).

## Mudanca de contrato: `escanear_arquivo`
Na v1: `escanear_arquivo(caminho: str, regras: list[dict]) -> list[dict]` (regras eram dados injetaveis).
Na v2: `escanear_arquivo(caminho: str) -> list[dict]` (os 7 checadores sao fixos, embutidos no motor — nao ha mais "regras como dado" porque a logica de deteccao agora depende de navegacao estrutural, nao apenas de um padrao). Cada checador individual continua testavel isoladamente, recebendo `(tree, resolver)` diretamente — o equivalente ao antigo `_regra(id)` dos testes da v1.

O formato de cada achado (finding) ganha uma melhoria real: `linha` deixa de poder ser `None`. Todo no da AST carrega `.lineno`, entao toda regra agora aponta uma linha exata — inclusive as que na v1 eram "coocorrencia" e apontavam `arquivo inteiro`.

## Arquitetura

```
ai_preflight/
  arvore.py          # anexar_pais(tree), primeiro_ancestral(node, tipo)
  resolver.py         # ResolvedorDeImports: apelidos de modulo/funcao, resolver_chamada(node)
  checadores.py        # 7 funcoes checar_*(tree, resolver) -> list[dict], + TODOS_CHECADORES
  scanner.py            # escanear_arquivo(caminho) -> list[dict]: parseia, prepara, roda os checadores
  report.py              # inalterado
  cli.py                  # so troca a chamada a escanear_arquivo
```

### `arvore.py`
```python
import ast


def anexar_pais(tree):
    for pai in ast.walk(tree):
        for filho in ast.iter_child_nodes(pai):
            filho.pai = pai
    tree.pai = None
    return tree


def primeiro_ancestral(node, tipo):
    atual = getattr(node, "pai", None)
    while atual is not None:
        if isinstance(atual, tipo):
            return atual
        atual = getattr(atual, "pai", None)
    return None
```

### `resolver.py`
```python
import ast


class ResolvedorDeImports:
    def __init__(self, tree):
        self.apelidos_modulo = {}
        self.apelidos_funcao = {}
        self._coletar(tree)

    def _coletar(self, tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    nome_local = alias.asname or alias.name
                    self.apelidos_modulo[nome_local] = alias.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    nome_local = alias.asname or alias.name
                    self.apelidos_funcao[nome_local] = f"{node.module}.{alias.name}"

    def _nome_pontilhado(self, node):
        partes = []
        atual = node
        while isinstance(atual, ast.Attribute):
            partes.append(atual.attr)
            atual = atual.value
        if isinstance(atual, ast.Name):
            base = self.apelidos_modulo.get(atual.id, atual.id)
            partes.append(base)
            partes.reverse()
            return ".".join(partes)
        return None

    def resolver_chamada(self, node):
        """Recebe um ast.Call. Devolve o nome qualificado canonico (ex: 'subprocess.run') ou None."""
        if isinstance(node.func, ast.Name):
            if node.func.id in self.apelidos_funcao:
                return self.apelidos_funcao[node.func.id]
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return self._nome_pontilhado(node.func)
        return None
```

Nota de implementacao: em `_nome_pontilhado`, a lista `partes` acumula os atributos de fora pra dentro (ex: para `os.path.join`, acumula `["join", "path"]`), depois adiciona a base (`"os"`) e inverte — resultando em `["os", "path", "join"]` antes de juntar com `.`.

### `checadores.py` — as 7 checagens

Cada checador devolve uma lista de achados no formato `{"regra_id", "severidade", "linha", "mensagem", "trecho"}`.

1. **`checar_pacote_instalado_silenciosamente`** — para cada `ast.Call` cujo `resolver_chamada` seja `subprocess.run`, `subprocess.call` ou `subprocess.Popen`: inspeciona os argumentos posicionais (listas/tuplas de strings, ou uma string unica) procurando `"pip"`/`"npm"` E `"install"` entre os elementos literais.
2. **`checar_reescrita_em_massa`** — para cada `ast.Call` de `open(...)` cujo segundo argumento (ou `mode=`) seja o literal `"w"`: verifica com `primeiro_ancestral(node, ast.For)` se existe um laco `for` ancestral cujo `.iter` seja um `ast.Call` que resolve para `os.walk`.
3. **`checar_pipe_shell_remoto`** — para cada `ast.Call` cujo `resolver_chamada` seja `subprocess.run`, `subprocess.call`, `subprocess.Popen`, `os.system` ou `os.popen` (ou seja, funcoes que de fato mandam algo pro shell): inspeciona os argumentos literais de string procurando o padrao `curl`, `|` e (`bash` ou `sh`) juntos. Restringir a essas funcoes evita disparar em algo inofensivo como `print("use curl ... | bash")`.
4. **`checar_execucao_remota`** — verifica co-ocorrencia por escopo: para o corpo de cada `ast.FunctionDef` (usando `ast.walk` mas sem descer para dentro de uma `FunctionDef`/`ClassDef` aninhada, pra nao contar uma chamada de uma funcao interna como parte do escopo externo) e, separadamente, para os statements de nivel de modulo fora de qualquer funcao/classe, verifica se existe um `ast.Call` resolvido para `requests.get` ou `urllib.request.*` E um `ast.Call` de `eval`/`exec` dentro do mesmo escopo assim delimitado. Fora de escopo: rastrear se o valor baixado especificamente e o que entra no `exec` (isso seria analise de fluxo de dados completa — nao entra na v2).
5. **`checar_eval_exec_dinamico`** — para cada `ast.Call` resolvido para `eval`/`exec`: dispara se o primeiro argumento **nao** for um `ast.Constant` de string.
6. **`checar_delecao_em_massa`** — para cada `ast.Call` resolvido para `shutil.rmtree` ou `os.remove`: verifica com `primeiro_ancestral` se existe um `ast.For` ou `ast.While` ancestral (sem exigir relacao com o que esta sendo iterado, ao contrario da regra 2 — deletar dentro de qualquer laco ja e o sinal de risco).
7. **`checar_injecao_git_hook`** — para cada `ast.Call` de `open(...)` com modo `"w"`: verifica se o primeiro argumento e um literal de string contendo `.git/hooks` OU uma chamada a `os.path.join(...)` cujos argumentos literais incluem `".git"` e `"hooks"` (fecha uma lacuna real da v1 — o script perigoso desta sessao usava exatamente `os.path.join('.git', 'hooks', 'pre-commit')`).

## Testes
Mesmo padrao da v1 — cada checador ganha fixtures "perigoso" (deve disparar) e "seguro" (nao deve disparar), em `tests/fixtures/v2/`.

Fixtures adicionais especificas da v2 (provam a evolucao real sobre a v1):
- **Apelido de import**: `import subprocess as sp; sp.run(["pip", "install", "x"])` — deve disparar a checagem 1 mesmo sem a palavra literal `subprocess` aparecer antes da chamada.
- **Falso positivo estrutural da v1, corrigido na v2**: um arquivo com `os.walk(...)` dentro de uma funcao E `open(caminho, "w")` dentro de OUTRA funcao completamente independente. A v1 dispararia (mesmo arquivo). A v2 nao deve disparar (nao estao no mesmo laco). Um teste explicito prova essa melhoria.
- **`os.path.join` em `.git/hooks`**: prova que a checagem 7 pega o padrao real encontrado nesta sessao, que a v1 nao pegava.

`ai_preflight/rules.py` e os arquivos `tests/fixtures/*.py` da v1 (raiz de `fixtures/`) sao mantidos no repositorio (nao apagados) para nao quebrar o historico de commits da v1 — mas deixam de ser usados pelo motor. Isso e revisado explicitamente: se o time (ou o usuario, sozinho) decidir mais tarde remover o codigo morto da v1, isso e uma limpeza separada, fora do escopo desta fase.

## Tratamento de erros
- `ast.parse()` lanca `SyntaxError` se o arquivo nao for Python valido: `escanear_arquivo` deixa a excecao subir; `cli.py` captura e imprime mensagem clara ("Nao foi possivel interpretar o arquivo como Python valido: <erro>"), retorna codigo de saida `2` (mesma familia dos erros de uso da v1).
- Mantidos os tratamentos ja existentes na v1 (arquivo nao encontrado, extensao != `.py`).

## Fora de escopo (Fase 1)
- Rastreamento de fluxo de dados completo entre funcoes (taint tracking) — pesquisa, nao engenharia de produto.
- Deteccao de ofuscacao via `getattr`/concatenacao dinamica de nomes (ex: `getattr(__builtins__, "ex"+"ec")`) — mencionado como limitacao conhecida no README.
- Shell/Bash, JavaScript — isso e a Fase 2.
- PyPI, pre-commit, GitHub Action — isso e a Fase 3.

## Versionamento
Esta fase fecha como `v2.0.0` do pacote (mudanca de contrato em `escanear_arquivo` = breaking change, justifica major version).
