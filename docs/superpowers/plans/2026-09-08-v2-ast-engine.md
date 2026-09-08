# ai-preflight v2 Fase 1 (Motor AST) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ai-preflight's regex-based detection engine (`rules.py` + line/co-occurrence scanning) with a real Python AST-based engine that understands import aliases and structural containment (e.g. "is this `open()` really inside this `for` loop's body").

**Architecture:** `ast.parse()` the target file, attach `.pai` (parent) pointers to every node via `arvore.py`, resolve import aliases to canonical dotted names via `resolver.py`, then run 7 independent checker functions in `checadores.py` (each `(tree, resolver) -> list[dict]`) that walk the tree and use `primeiro_ancestral`/`resolver_chamada` instead of regex. `scanner.py` becomes a thin orchestrator; `report.py` is untouched.

**Tech Stack:** Python stdlib only (`ast`, `re` for one sub-pattern inside checker 3). No new dependencies. `pytest` for tests (via `python -m pytest`, not bare `pytest`, in this environment).

## Global Constraints

- Stdlib only — no new dependency added to `pyproject.toml` (per spec "Decisao de abordagem").
- `escanear_arquivo` signature changes from `(caminho, regras)` to `(caminho)` — breaking change, this is a deliberate contract change for v2 (per spec "Mudanca de contrato").
- Every finding's `"linha"` must be a real line number, never `None` (per spec "Mudanca de contrato").
- `ai_preflight/rules.py` and the v1 fixtures under `tests/fixtures/` (root level, not `tests/fixtures/v2/`) are kept as-is, untouched, still exercised by `tests/test_rules.py` — do not delete or modify them (per spec "O que muda" / final paragraph before "Tratamento de erros").
- All new v2 fixtures live under `tests/fixtures/v2/`.
- `requires-python = ">=3.9"` in `pyproject.toml` stays as-is — `ast.unparse` (used for the `"trecho"` field) requires 3.9+, which is already satisfied.
- Finish this phase by bumping `pyproject.toml` version to `2.0.0` (breaking change to `escanear_arquivo` = major version, per spec "Versionamento").
- Every commit message in this project must end with the trailer `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.
- Test runner in this environment: `python -m pytest` (bare `pytest` is not on PATH).

---

## File Structure

```
ai_preflight/
  arvore.py          # NEW — anexar_pais(tree), primeiro_ancestral(node, tipo)
  resolver.py         # NEW — ResolvedorDeImports
  checadores.py        # NEW — 7 checar_*(tree, resolver) functions + TODOS_CHECADORES
  scanner.py            # REWRITTEN — escanear_arquivo(caminho) -> list[dict]
  cli.py                  # MODIFIED — drop ALL_RULES, handle SyntaxError
  report.py              # UNCHANGED
  rules.py                # UNCHANGED (kept for v1 history, unused by v2 engine)
tests/
  test_arvore.py       # NEW
  test_resolver.py      # NEW
  test_checadores.py     # NEW
  test_scanner.py          # REWRITTEN (v1 version deleted/replaced)
  test_cli.py                # MODIFIED (add SyntaxError case)
  test_rules.py                # UNCHANGED
  fixtures/
    v2/                         # NEW directory, all v2 fixtures live here
      silent_package_install_perigoso.py
      silent_package_install_seguro.py
      silent_package_install_apelido_perigoso.py
      mass_file_rewrite_perigoso.py
      mass_file_rewrite_seguro.py
      mass_file_rewrite_falso_positivo_estrutural_seguro.py
      remote_shell_pipe_perigoso.py
      remote_shell_pipe_seguro.py
      remote_code_execution_perigoso.py
      remote_code_execution_seguro.py
      dynamic_eval_exec_perigoso.py
      dynamic_eval_exec_seguro.py
      mass_delete_perigoso.py
      mass_delete_seguro.py
      git_hook_injection_perigoso.py
      git_hook_injection_seguro.py
      git_hook_injection_os_path_join_perigoso.py
```

---

### Task 1: Setup — feature branch

**Files:** none (git only)

- [ ] **Step 1: Create and switch to the feature branch**

Run: `git checkout -b feature/v2-ast-engine-fase1`
Expected: `Switched to a new branch 'feature/v2-ast-engine-fase1'`

- [ ] **Step 2: Confirm starting state is clean**

Run: `git status`
Expected: `nothing to commit, working tree clean`

---

### Task 2: `arvore.py` — parent pointers

**Files:**
- Create: `ai_preflight/arvore.py`
- Test: `tests/test_arvore.py`

**Interfaces:**
- Produces: `anexar_pais(tree: ast.AST) -> ast.AST` (mutates in place, also returns tree), `primeiro_ancestral(node: ast.AST, tipo) -> ast.AST | None` (`tipo` may be a single AST class or a tuple of classes, per `isinstance` semantics).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_arvore.py`:

```python
import ast

from ai_preflight.arvore import anexar_pais, primeiro_ancestral


def test_anexar_pais_define_pai_em_no_filho():
    tree = ast.parse("for x in y:\n    open('a', 'w')\n")
    anexar_pais(tree)
    for_node = tree.body[0]
    expr_node = for_node.body[0]
    assert expr_node.pai is for_node


def test_anexar_pais_raiz_tem_pai_none():
    tree = ast.parse("x = 1\n")
    anexar_pais(tree)
    assert tree.pai is None


def test_primeiro_ancestral_encontra_for_ancestral():
    tree = ast.parse("for x in y:\n    open('a', 'w')\n")
    anexar_pais(tree)
    call_node = tree.body[0].body[0].value
    resultado = primeiro_ancestral(call_node, ast.For)
    assert resultado is tree.body[0]


def test_primeiro_ancestral_retorna_none_quando_nao_ha_ancestral():
    tree = ast.parse("open('a', 'w')\n")
    anexar_pais(tree)
    call_node = tree.body[0].value
    resultado = primeiro_ancestral(call_node, ast.For)
    assert resultado is None


def test_primeiro_ancestral_aceita_tupla_de_tipos():
    tree = ast.parse("while True:\n    open('a', 'w')\n")
    anexar_pais(tree)
    call_node = tree.body[0].body[0].value
    resultado = primeiro_ancestral(call_node, (ast.For, ast.While))
    assert resultado is tree.body[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_arvore.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ai_preflight.arvore'`

- [ ] **Step 3: Write the implementation**

Create `ai_preflight/arvore.py`:

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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_arvore.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add ai_preflight/arvore.py tests/test_arvore.py
git commit -m "$(cat <<'EOF'
feat(v2): add arvore.py for AST parent-pointer tracking

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `resolver.py` — import alias resolution

**Files:**
- Create: `ai_preflight/resolver.py`
- Test: `tests/test_resolver.py`

**Interfaces:**
- Produces: `class ResolvedorDeImports(tree: ast.AST)` with method `resolver_chamada(node: ast.Call) -> str | None`, and attributes `apelidos_modulo: dict[str, str]`, `apelidos_funcao: dict[str, str]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_resolver.py`:

```python
import ast

from ai_preflight.resolver import ResolvedorDeImports


def test_resolve_chamada_direta_sem_import():
    tree = ast.parse("eval('1')\n")
    resolvedor = ResolvedorDeImports(tree)
    call_node = tree.body[0].value
    assert resolvedor.resolver_chamada(call_node) == "eval"


def test_resolve_atributo_com_import_simples():
    tree = ast.parse("import subprocess\nsubprocess.run(['ls'])\n")
    resolvedor = ResolvedorDeImports(tree)
    call_node = tree.body[1].value
    assert resolvedor.resolver_chamada(call_node) == "subprocess.run"


def test_resolve_atributo_com_apelido_de_import():
    tree = ast.parse("import subprocess as sp\nsp.run(['ls'])\n")
    resolvedor = ResolvedorDeImports(tree)
    call_node = tree.body[1].value
    assert resolvedor.resolver_chamada(call_node) == "subprocess.run"


def test_resolve_from_import_com_apelido():
    tree = ast.parse("from os import remove as apagar\napagar('a.txt')\n")
    resolvedor = ResolvedorDeImports(tree)
    call_node = tree.body[1].value
    assert resolvedor.resolver_chamada(call_node) == "os.remove"


def test_resolve_atributo_encadeado_os_path_join():
    tree = ast.parse("import os\nos.path.join('.git', 'hooks')\n")
    resolvedor = ResolvedorDeImports(tree)
    call_node = tree.body[1].value
    assert resolvedor.resolver_chamada(call_node) == "os.path.join"


def test_resolve_import_com_ponto_e_apelido():
    tree = ast.parse("import urllib.request as ur\nur.urlopen('x')\n")
    resolvedor = ResolvedorDeImports(tree)
    call_node = tree.body[1].value
    assert resolvedor.resolver_chamada(call_node) == "urllib.request.urlopen"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_resolver.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ai_preflight.resolver'`

- [ ] **Step 3: Write the implementation**

Create `ai_preflight/resolver.py`:

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
        if isinstance(node.func, ast.Name):
            if node.func.id in self.apelidos_funcao:
                return self.apelidos_funcao[node.func.id]
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return self._nome_pontilhado(node.func)
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_resolver.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add ai_preflight/resolver.py tests/test_resolver.py
git commit -m "$(cat <<'EOF'
feat(v2): add resolver.py for import alias resolution

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `checadores.py` — checker 1 (silent package install)

**Files:**
- Create: `ai_preflight/checadores.py`
- Create: `tests/fixtures/v2/silent_package_install_perigoso.py`
- Create: `tests/fixtures/v2/silent_package_install_seguro.py`
- Create: `tests/fixtures/v2/silent_package_install_apelido_perigoso.py`
- Create: `tests/test_checadores.py`

**Interfaces:**
- Consumes: `ai_preflight.arvore.primeiro_ancestral` (imported now, used starting Task 5), `ai_preflight.resolver.ResolvedorDeImports.resolver_chamada`.
- Produces: `_achado(regra_id, severidade, node, mensagem) -> dict`, `_extrair_strings(node) -> list[str]`, `_literais_de_string(call_node) -> list[str]`, `checar_pacote_instalado_silenciosamente(tree, resolver) -> list[dict]`. These helpers are consumed by every later task in this file.

- [ ] **Step 1: Create the fixtures**

Create `tests/fixtures/v2/silent_package_install_perigoso.py`:

```python
import subprocess

subprocess.run(["pip", "install", "requests"], check=True)
```

Create `tests/fixtures/v2/silent_package_install_seguro.py`:

```python
import subprocess

subprocess.run(["echo", "eu uso pip no meu dia a dia"])
```

Create `tests/fixtures/v2/silent_package_install_apelido_perigoso.py`:

```python
import subprocess as sp

sp.run(["pip", "install", "requests"])
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_checadores.py`:

```python
import ast

from ai_preflight.arvore import anexar_pais
from ai_preflight.resolver import ResolvedorDeImports
from ai_preflight import checadores


def _preparar(caminho_fixture):
    with open(caminho_fixture, "r", encoding="utf-8") as f:
        codigo = f.read()
    tree = ast.parse(codigo)
    anexar_pais(tree)
    resolvedor = ResolvedorDeImports(tree)
    return tree, resolvedor


def test_checar_pacote_instalado_detecta_no_arquivo_perigoso():
    tree, resolvedor = _preparar("tests/fixtures/v2/silent_package_install_perigoso.py")
    achados = checadores.checar_pacote_instalado_silenciosamente(tree, resolvedor)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "silent-package-install"
    assert achados[0]["severidade"] == "CRITICA"
    assert achados[0]["linha"] == 3


def test_checar_pacote_instalado_nao_detecta_no_arquivo_seguro():
    tree, resolvedor = _preparar("tests/fixtures/v2/silent_package_install_seguro.py")
    achados = checadores.checar_pacote_instalado_silenciosamente(tree, resolvedor)
    assert achados == []


def test_checar_pacote_instalado_detecta_mesmo_com_apelido_de_import():
    tree, resolvedor = _preparar("tests/fixtures/v2/silent_package_install_apelido_perigoso.py")
    achados = checadores.checar_pacote_instalado_silenciosamente(tree, resolvedor)
    assert len(achados) == 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ai_preflight.checadores'`

- [ ] **Step 4: Write the implementation**

Create `ai_preflight/checadores.py`:

```python
import ast
import re

from ai_preflight.arvore import primeiro_ancestral

FUNCOES_SHELL = ("subprocess.run", "subprocess.call", "subprocess.Popen", "os.system", "os.popen")
FUNCOES_DELETE = ("shutil.rmtree", "os.remove")
_PADRAO_CURL_PIPE = re.compile(r"curl\s.*\|\s*(bash|sh)\b")


def _achado(regra_id, severidade, node, mensagem):
    return {
        "regra_id": regra_id,
        "severidade": severidade,
        "linha": node.lineno,
        "mensagem": mensagem,
        "trecho": ast.unparse(node),
    }


def _extrair_strings(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, (ast.List, ast.Tuple)):
        resultado = []
        for elt in node.elts:
            resultado.extend(_extrair_strings(elt))
        return resultado
    return []


def _literais_de_string(call_node):
    literais = []
    for arg in call_node.args:
        literais.extend(_extrair_strings(arg))
    for kw in call_node.keywords:
        if kw.arg is not None:
            literais.extend(_extrair_strings(kw.value))
    return literais


def checar_pacote_instalado_silenciosamente(tree, resolver):
    achados = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if resolver.resolver_chamada(node) not in ("subprocess.run", "subprocess.call", "subprocess.Popen"):
            continue
        literais = _literais_de_string(node)
        tem_gerenciador = any(s in ("pip", "npm") for s in literais)
        tem_install = any(s == "install" for s in literais)
        if tem_gerenciador and tem_install:
            achados.append(_achado(
                "silent-package-install", "CRITICA", node,
                "Instalacao de pacote embutida no script, sem pedir confirmacao.",
            ))
    return achados
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add ai_preflight/checadores.py tests/test_checadores.py tests/fixtures/v2/silent_package_install_perigoso.py tests/fixtures/v2/silent_package_install_seguro.py tests/fixtures/v2/silent_package_install_apelido_perigoso.py
git commit -m "$(cat <<'EOF'
feat(v2): add checadores.py with checar_pacote_instalado_silenciosamente

Proves import-alias resolution: detects subprocess.run via `import
subprocess as sp` without the literal word "subprocess" near the call.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: checker 2 (mass file rewrite, structural containment)

**Files:**
- Modify: `ai_preflight/checadores.py`
- Create: `tests/fixtures/v2/mass_file_rewrite_perigoso.py`
- Create: `tests/fixtures/v2/mass_file_rewrite_seguro.py`
- Create: `tests/fixtures/v2/mass_file_rewrite_falso_positivo_estrutural_seguro.py`
- Modify: `tests/test_checadores.py`

**Interfaces:**
- Consumes: `primeiro_ancestral` (Task 2), `resolver.resolver_chamada` (Task 3), `_achado`, `_literais_de_string` (Task 4).
- Produces: `_modo_de_abertura(node) -> str | None`, `_iter_e_os_walk(for_node, resolver) -> bool`, `checar_reescrita_em_massa(tree, resolver) -> list[dict]`. `_modo_de_abertura` is reused by checker 7 (Task 10).

- [ ] **Step 1: Create the fixtures**

Create `tests/fixtures/v2/mass_file_rewrite_perigoso.py`:

```python
import os


def reescreve_tudo(pasta):
    for raiz, _, arquivos in os.walk(pasta):
        for nome in arquivos:
            with open(nome, "w") as f:
                f.write("")
```

Create `tests/fixtures/v2/mass_file_rewrite_seguro.py`:

```python
import os


def apenas_lista(pasta):
    for raiz, _, arquivos in os.walk(pasta):
        print(raiz, arquivos)
```

Create `tests/fixtures/v2/mass_file_rewrite_falso_positivo_estrutural_seguro.py`:

```python
import os


def lista_arquivos(pasta):
    for raiz, _, arquivos in os.walk(pasta):
        print(raiz, arquivos)


def grava_configuracao(caminho):
    with open(caminho, "w") as f:
        f.write("config=1")
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_checadores.py`:

```python


def test_checar_reescrita_detecta_no_arquivo_perigoso():
    tree, resolvedor = _preparar("tests/fixtures/v2/mass_file_rewrite_perigoso.py")
    achados = checadores.checar_reescrita_em_massa(tree, resolvedor)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "mass-file-rewrite"
    assert achados[0]["linha"] is not None


def test_checar_reescrita_nao_detecta_no_arquivo_seguro():
    tree, resolvedor = _preparar("tests/fixtures/v2/mass_file_rewrite_seguro.py")
    achados = checadores.checar_reescrita_em_massa(tree, resolvedor)
    assert achados == []


def test_checar_reescrita_nao_detecta_falso_positivo_estrutural():
    tree, resolvedor = _preparar(
        "tests/fixtures/v2/mass_file_rewrite_falso_positivo_estrutural_seguro.py"
    )
    achados = checadores.checar_reescrita_em_massa(tree, resolvedor)
    assert achados == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: FAIL with `AttributeError: module 'ai_preflight.checadores' has no attribute 'checar_reescrita_em_massa'`

- [ ] **Step 4: Write the implementation**

Append to `ai_preflight/checadores.py` (after `checar_pacote_instalado_silenciosamente`):

```python


def _modo_de_abertura(node):
    if len(node.args) >= 2:
        arg = node.args[1]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return kw.value.value
    return None


def _iter_e_os_walk(for_node, resolver):
    it = for_node.iter
    if isinstance(it, ast.Call):
        return resolver.resolver_chamada(it) == "os.walk"
    return False


def checar_reescrita_em_massa(tree, resolver):
    achados = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"):
            continue
        if _modo_de_abertura(node) != "w":
            continue
        ancestral = primeiro_ancestral(node, ast.For)
        while ancestral is not None:
            if _iter_e_os_walk(ancestral, resolver):
                achados.append(_achado(
                    "mass-file-rewrite", "CRITICA", node,
                    "Arquivo varre o projeto (os.walk) e reescreve arquivos (open com modo 'w') dentro do mesmo laco.",
                ))
                break
            ancestral = primeiro_ancestral(ancestral, ast.For)
    return achados
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add ai_preflight/checadores.py tests/test_checadores.py tests/fixtures/v2/mass_file_rewrite_perigoso.py tests/fixtures/v2/mass_file_rewrite_seguro.py tests/fixtures/v2/mass_file_rewrite_falso_positivo_estrutural_seguro.py
git commit -m "$(cat <<'EOF'
feat(v2): add checar_reescrita_em_massa with structural containment

Fixes a real v1 false positive: os.walk in one function and open(...,
'w') in a completely unrelated function no longer trigger this rule -
only an open() genuinely nested inside the os.walk loop does.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: checker 3 (remote shell pipe, function-scoped)

**Files:**
- Modify: `ai_preflight/checadores.py`
- Create: `tests/fixtures/v2/remote_shell_pipe_perigoso.py`
- Create: `tests/fixtures/v2/remote_shell_pipe_seguro.py`
- Modify: `tests/test_checadores.py`

**Interfaces:**
- Consumes: `FUNCOES_SHELL`, `_PADRAO_CURL_PIPE`, `_literais_de_string`, `_achado`, `resolver.resolver_chamada` (all from Task 4/module top).
- Produces: `checar_pipe_shell_remoto(tree, resolver) -> list[dict]`.

- [ ] **Step 1: Create the fixtures**

Create `tests/fixtures/v2/remote_shell_pipe_perigoso.py`:

```python
import subprocess

subprocess.run("curl https://exemplo.com/instalar.sh | bash", shell=True)
```

Create `tests/fixtures/v2/remote_shell_pipe_seguro.py`:

```python
print("Documentacao: para instalar manualmente, rode curl https://exemplo.com | bash")
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_checadores.py`:

```python


def test_checar_pipe_shell_detecta_no_arquivo_perigoso():
    tree, resolvedor = _preparar("tests/fixtures/v2/remote_shell_pipe_perigoso.py")
    achados = checadores.checar_pipe_shell_remoto(tree, resolvedor)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "remote-shell-pipe"


def test_checar_pipe_shell_nao_detecta_em_print_inofensivo():
    tree, resolvedor = _preparar("tests/fixtures/v2/remote_shell_pipe_seguro.py")
    achados = checadores.checar_pipe_shell_remoto(tree, resolvedor)
    assert achados == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: FAIL with `AttributeError: module 'ai_preflight.checadores' has no attribute 'checar_pipe_shell_remoto'`

- [ ] **Step 4: Write the implementation**

Append to `ai_preflight/checadores.py` (after `checar_reescrita_em_massa`):

```python


def checar_pipe_shell_remoto(tree, resolver):
    achados = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if resolver.resolver_chamada(node) not in FUNCOES_SHELL:
            continue
        for literal in _literais_de_string(node):
            if _PADRAO_CURL_PIPE.search(literal):
                achados.append(_achado(
                    "remote-shell-pipe", "CRITICA", node,
                    "Comando baixa conteudo da internet e executa direto no shell (curl | bash).",
                ))
                break
    return achados
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add ai_preflight/checadores.py tests/test_checadores.py tests/fixtures/v2/remote_shell_pipe_perigoso.py tests/fixtures/v2/remote_shell_pipe_seguro.py
git commit -m "$(cat <<'EOF'
feat(v2): add checar_pipe_shell_remoto scoped to real shell calls

Fixes a v1 false positive: a print() containing the literal text
"curl ... | bash" no longer triggers - only subprocess.run/call/Popen,
os.system and os.popen calls do.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: checker 4 (remote code execution, scope co-occurrence)

**Files:**
- Modify: `ai_preflight/checadores.py`
- Create: `tests/fixtures/v2/remote_code_execution_perigoso.py`
- Create: `tests/fixtures/v2/remote_code_execution_seguro.py`
- Modify: `tests/test_checadores.py`

**Interfaces:**
- Consumes: `_achado`, `resolver.resolver_chamada`.
- Produces: `_andar_sem_descer_em_escopos_aninhados(nos) -> list[ast.AST]`, `_escopos_de_execucao(tree) -> list[list[ast.AST]]`, `checar_execucao_remota(tree, resolver) -> list[dict]`.

- [ ] **Step 1: Create the fixtures**

Create `tests/fixtures/v2/remote_code_execution_perigoso.py`:

```python
import requests


def executa_script_remoto():
    resposta = requests.get("https://exemplo.com/script.py")
    exec(resposta.text)
```

Create `tests/fixtures/v2/remote_code_execution_seguro.py`:

```python
import requests


def baixa_dados():
    resposta = requests.get("https://exemplo.com/dados.json")
    return resposta.json()


def calcula():
    return eval("1 + 1")
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_checadores.py`:

```python


def test_checar_execucao_remota_detecta_no_arquivo_perigoso():
    tree, resolvedor = _preparar("tests/fixtures/v2/remote_code_execution_perigoso.py")
    achados = checadores.checar_execucao_remota(tree, resolvedor)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "remote-code-execution"


def test_checar_execucao_remota_nao_detecta_quando_em_escopos_diferentes():
    tree, resolvedor = _preparar("tests/fixtures/v2/remote_code_execution_seguro.py")
    achados = checadores.checar_execucao_remota(tree, resolvedor)
    assert achados == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: FAIL with `AttributeError: module 'ai_preflight.checadores' has no attribute 'checar_execucao_remota'`

- [ ] **Step 4: Write the implementation**

Append to `ai_preflight/checadores.py` (after `checar_pipe_shell_remoto`):

```python


def _andar_sem_descer_em_escopos_aninhados(nos):
    resultado = []
    pilha = list(nos)
    while pilha:
        node = pilha.pop()
        resultado.append(node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        pilha.extend(ast.iter_child_nodes(node))
    return resultado


def _escopos_de_execucao(tree):
    escopos = []
    nivel_modulo = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            escopos.append(_andar_sem_descer_em_escopos_aninhados(node.body))
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    escopos.append(_andar_sem_descer_em_escopos_aninhados(sub.body))
        else:
            nivel_modulo.append(node)
    escopos.append(_andar_sem_descer_em_escopos_aninhados(nivel_modulo))
    return escopos


def checar_execucao_remota(tree, resolver):
    achados = []
    for escopo in _escopos_de_execucao(tree):
        chamada_download = None
        chamada_exec = None
        for node in escopo:
            if not isinstance(node, ast.Call):
                continue
            nome = resolver.resolver_chamada(node)
            if nome is None:
                continue
            if nome == "requests.get" or nome.startswith("urllib.request."):
                chamada_download = chamada_download or node
            elif nome in ("eval", "exec"):
                chamada_exec = chamada_exec or node
        if chamada_download is not None and chamada_exec is not None:
            achados.append(_achado(
                "remote-code-execution", "CRITICA", chamada_exec,
                "Script baixa conteudo da internet (requests/urllib) e executa (exec/eval) no mesmo escopo.",
            ))
    return achados
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: 10 passed

- [ ] **Step 6: Commit**

```bash
git add ai_preflight/checadores.py tests/test_checadores.py tests/fixtures/v2/remote_code_execution_perigoso.py tests/fixtures/v2/remote_code_execution_seguro.py
git commit -m "$(cat <<'EOF'
feat(v2): add checar_execucao_remota with scope-based co-occurrence

Fixes a v1 false positive: requests.get in one function and eval in a
completely unrelated function no longer trigger this rule - v1 only
checked same-file co-occurrence with no scope awareness at all.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: checker 5 (dynamic eval/exec)

**Files:**
- Modify: `ai_preflight/checadores.py`
- Create: `tests/fixtures/v2/dynamic_eval_exec_perigoso.py`
- Create: `tests/fixtures/v2/dynamic_eval_exec_seguro.py`
- Modify: `tests/test_checadores.py`

**Interfaces:**
- Consumes: `_achado`, `resolver.resolver_chamada`.
- Produces: `checar_eval_exec_dinamico(tree, resolver) -> list[dict]`.

- [ ] **Step 1: Create the fixtures**

Create `tests/fixtures/v2/dynamic_eval_exec_perigoso.py`:

```python
entrada_usuario = input("Digite uma expressao: ")
eval(entrada_usuario)
```

Create `tests/fixtures/v2/dynamic_eval_exec_seguro.py`:

```python
eval("1 + 1")
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_checadores.py`:

```python


def test_checar_eval_exec_dinamico_detecta_no_arquivo_perigoso():
    tree, resolvedor = _preparar("tests/fixtures/v2/dynamic_eval_exec_perigoso.py")
    achados = checadores.checar_eval_exec_dinamico(tree, resolvedor)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "dynamic-eval-exec"
    assert achados[0]["severidade"] == "ALTA"


def test_checar_eval_exec_dinamico_nao_detecta_texto_fixo():
    tree, resolvedor = _preparar("tests/fixtures/v2/dynamic_eval_exec_seguro.py")
    achados = checadores.checar_eval_exec_dinamico(tree, resolvedor)
    assert achados == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: FAIL with `AttributeError: module 'ai_preflight.checadores' has no attribute 'checar_eval_exec_dinamico'`

- [ ] **Step 4: Write the implementation**

Append to `ai_preflight/checadores.py` (after `checar_execucao_remota`):

```python


def checar_eval_exec_dinamico(tree, resolver):
    achados = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if resolver.resolver_chamada(node) not in ("eval", "exec"):
            continue
        if not node.args:
            continue
        primeiro = node.args[0]
        if not (isinstance(primeiro, ast.Constant) and isinstance(primeiro.value, str)):
            achados.append(_achado(
                "dynamic-eval-exec", "ALTA", node,
                "eval/exec chamado sobre uma variavel, nao um texto fixo - risco de executar codigo desconhecido.",
            ))
    return achados
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: 12 passed

- [ ] **Step 6: Commit**

```bash
git add ai_preflight/checadores.py tests/test_checadores.py tests/fixtures/v2/dynamic_eval_exec_perigoso.py tests/fixtures/v2/dynamic_eval_exec_seguro.py
git commit -m "$(cat <<'EOF'
feat(v2): add checar_eval_exec_dinamico

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: checker 6 (mass delete)

**Files:**
- Modify: `ai_preflight/checadores.py`
- Create: `tests/fixtures/v2/mass_delete_perigoso.py`
- Create: `tests/fixtures/v2/mass_delete_seguro.py`
- Modify: `tests/test_checadores.py`

**Interfaces:**
- Consumes: `FUNCOES_DELETE`, `primeiro_ancestral`, `_achado`, `resolver.resolver_chamada`.
- Produces: `checar_delecao_em_massa(tree, resolver) -> list[dict]`.

- [ ] **Step 1: Create the fixtures**

Create `tests/fixtures/v2/mass_delete_perigoso.py`:

```python
import os


def limpa_arquivos(lista):
    for nome in lista:
        os.remove(nome)
```

Create `tests/fixtures/v2/mass_delete_seguro.py`:

```python
import os


def remove_um(nome):
    os.remove(nome)
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_checadores.py`:

```python


def test_checar_delecao_em_massa_detecta_no_arquivo_perigoso():
    tree, resolvedor = _preparar("tests/fixtures/v2/mass_delete_perigoso.py")
    achados = checadores.checar_delecao_em_massa(tree, resolvedor)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "mass-delete"
    assert achados[0]["severidade"] == "ALTA"


def test_checar_delecao_em_massa_nao_detecta_delete_avulso():
    tree, resolvedor = _preparar("tests/fixtures/v2/mass_delete_seguro.py")
    achados = checadores.checar_delecao_em_massa(tree, resolvedor)
    assert achados == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: FAIL with `AttributeError: module 'ai_preflight.checadores' has no attribute 'checar_delecao_em_massa'`

- [ ] **Step 4: Write the implementation**

Append to `ai_preflight/checadores.py` (after `checar_eval_exec_dinamico`):

```python


def checar_delecao_em_massa(tree, resolver):
    achados = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if resolver.resolver_chamada(node) not in FUNCOES_DELETE:
            continue
        if primeiro_ancestral(node, (ast.For, ast.While)) is not None:
            achados.append(_achado(
                "mass-delete", "ALTA", node,
                "Deleta arquivos (shutil.rmtree/os.remove) dentro de um laco - risco de apagar mais do que deveria.",
            ))
    return achados
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: 14 passed

- [ ] **Step 6: Commit**

```bash
git add ai_preflight/checadores.py tests/test_checadores.py tests/fixtures/v2/mass_delete_perigoso.py tests/fixtures/v2/mass_delete_seguro.py
git commit -m "$(cat <<'EOF'
feat(v2): add checar_delecao_em_massa

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: checker 7 (git hook injection) + `TODOS_CHECADORES`

**Files:**
- Modify: `ai_preflight/checadores.py`
- Create: `tests/fixtures/v2/git_hook_injection_perigoso.py`
- Create: `tests/fixtures/v2/git_hook_injection_seguro.py`
- Create: `tests/fixtures/v2/git_hook_injection_os_path_join_perigoso.py`
- Modify: `tests/test_checadores.py`

**Interfaces:**
- Consumes: `_modo_de_abertura` (Task 5), `_literais_de_string`, `_achado`, `resolver.resolver_chamada`.
- Produces: `_e_caminho_git_hooks(node, resolver) -> bool`, `checar_injecao_git_hook(tree, resolver) -> list[dict]`, `TODOS_CHECADORES: list[callable]` — the list `scanner.py` (Task 11) iterates over.

- [ ] **Step 1: Create the fixtures**

Create `tests/fixtures/v2/git_hook_injection_perigoso.py`:

```python
with open(".git/hooks/pre-commit", "w") as f:
    f.write("#!/bin/sh\necho oi\n")
```

Create `tests/fixtures/v2/git_hook_injection_seguro.py`:

```python
with open("relatorio.txt", "w") as f:
    f.write("ok")
```

Create `tests/fixtures/v2/git_hook_injection_os_path_join_perigoso.py`:

```python
import os

with open(os.path.join(".git", "hooks", "pre-commit"), "w") as f:
    f.write("#!/bin/sh\necho oi\n")
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_checadores.py`:

```python


def test_checar_injecao_git_hook_detecta_caminho_literal():
    tree, resolvedor = _preparar("tests/fixtures/v2/git_hook_injection_perigoso.py")
    achados = checadores.checar_injecao_git_hook(tree, resolvedor)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "git-hook-injection"
    assert achados[0]["severidade"] == "MEDIA"


def test_checar_injecao_git_hook_nao_detecta_arquivo_comum():
    tree, resolvedor = _preparar("tests/fixtures/v2/git_hook_injection_seguro.py")
    achados = checadores.checar_injecao_git_hook(tree, resolvedor)
    assert achados == []


def test_checar_injecao_git_hook_detecta_via_os_path_join():
    tree, resolvedor = _preparar("tests/fixtures/v2/git_hook_injection_os_path_join_perigoso.py")
    achados = checadores.checar_injecao_git_hook(tree, resolvedor)
    assert len(achados) == 1


def test_todos_checadores_tem_sete_funcoes():
    assert len(checadores.TODOS_CHECADORES) == 7
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: FAIL with `AttributeError: module 'ai_preflight.checadores' has no attribute 'checar_injecao_git_hook'`

- [ ] **Step 4: Write the implementation**

Append to `ai_preflight/checadores.py` (after `checar_delecao_em_massa`):

```python


def _e_caminho_git_hooks(node, resolver):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return ".git" in node.value and "hooks" in node.value
    if isinstance(node, ast.Call) and resolver.resolver_chamada(node) == "os.path.join":
        literais = _literais_de_string(node)
        return ".git" in literais and "hooks" in literais
    return False


def checar_injecao_git_hook(tree, resolver):
    achados = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"):
            continue
        if _modo_de_abertura(node) != "w":
            continue
        if not node.args:
            continue
        if _e_caminho_git_hooks(node.args[0], resolver):
            achados.append(_achado(
                "git-hook-injection", "MEDIA", node,
                "Escreve dentro de .git/hooks - instala automacao que roda em todo commit, sem voce perceber.",
            ))
    return achados


TODOS_CHECADORES = [
    checar_pacote_instalado_silenciosamente,
    checar_reescrita_em_massa,
    checar_pipe_shell_remoto,
    checar_execucao_remota,
    checar_eval_exec_dinamico,
    checar_delecao_em_massa,
    checar_injecao_git_hook,
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_checadores.py -v`
Expected: 18 passed

- [ ] **Step 6: Commit**

```bash
git add ai_preflight/checadores.py tests/test_checadores.py tests/fixtures/v2/git_hook_injection_perigoso.py tests/fixtures/v2/git_hook_injection_seguro.py tests/fixtures/v2/git_hook_injection_os_path_join_perigoso.py
git commit -m "$(cat <<'EOF'
feat(v2): add checar_injecao_git_hook and TODOS_CHECADORES

Closes a real v1 gap: os.path.join('.git', 'hooks', 'pre-commit') as
the open() target is now detected, not just a literal string path.
All 7 checkers are now wired into TODOS_CHECADORES.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: rewrite `scanner.py`

**Files:**
- Modify: `ai_preflight/scanner.py` (full rewrite)
- Modify: `tests/test_scanner.py` (full rewrite)

**Interfaces:**
- Consumes: `ai_preflight.arvore.anexar_pais`, `ai_preflight.resolver.ResolvedorDeImports`, `ai_preflight.checadores.TODOS_CHECADORES`.
- Produces: `escanear_arquivo(caminho: str) -> list[dict]` — the new contract, consumed by `cli.py` in Task 12.

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `tests/test_scanner.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scanner.py -v`
Expected: FAIL — `escanear_arquivo()` still takes 2 positional args (`caminho, regras`), calling it with 1 raises `TypeError`.

- [ ] **Step 3: Write the implementation**

Replace the full contents of `ai_preflight/scanner.py`:

```python
import ast

from ai_preflight.arvore import anexar_pais
from ai_preflight.resolver import ResolvedorDeImports
from ai_preflight.checadores import TODOS_CHECADORES


def escanear_arquivo(caminho):
    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
        conteudo = f.read()

    tree = ast.parse(conteudo, filename=caminho)
    anexar_pais(tree)
    resolver = ResolvedorDeImports(tree)

    achados = []
    for checador in TODOS_CHECADORES:
        achados.extend(checador(tree, resolver))
    return achados
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scanner.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add ai_preflight/scanner.py tests/test_scanner.py
git commit -m "$(cat <<'EOF'
feat(v2)!: rewrite scanner.py to use the AST engine

BREAKING CHANGE: escanear_arquivo(caminho, regras) -> escanear_arquivo(caminho).
The 7 checkers are now fixed and built into the engine instead of being
passed in as regex rule data.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: update `cli.py` (drop `ALL_RULES`, handle `SyntaxError`)

**Files:**
- Modify: `ai_preflight/cli.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Consumes: `ai_preflight.scanner.escanear_arquivo(caminho)` (Task 11).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cli.py`:

```python


def test_main_retorna_2_quando_arquivo_tem_erro_de_sintaxe(capsys, tmp_path):
    arquivo_py = tmp_path / "quebrado.py"
    arquivo_py.write_text("def f(:\n")
    codigo = main([str(arquivo_py)])
    saida = capsys.readouterr().out
    assert codigo == 2
    assert "nao foi possivel interpretar" in saida.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL — `cli.py` still imports `ALL_RULES` and calls `escanear_arquivo(args.arquivo, ALL_RULES)`, which now raises `TypeError` (too many args) instead of returning exit code 2 for the syntax-error case; also `ai_preflight.rules` import stays valid but is no longer meant to be used here.

- [ ] **Step 3: Write the implementation**

Replace the full contents of `ai_preflight/cli.py`:

```python
import argparse
import sys

from ai_preflight.scanner import escanear_arquivo
from ai_preflight.report import formatar_relatorio


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="ai-preflight",
        description="Analisa um script Python em busca de padroes perigosos antes de voce rodar.",
    )
    parser.add_argument("arquivo", help="Caminho do arquivo .py a ser analisado")
    args = parser.parse_args(argv)

    if not args.arquivo.endswith(".py"):
        print("ai-preflight so analisa arquivos .py na versao atual.")
        return 2

    try:
        achados = escanear_arquivo(args.arquivo)
    except FileNotFoundError:
        print(f"Arquivo nao encontrado: {args.arquivo}")
        return 2
    except SyntaxError as erro:
        print(f"Nao foi possivel interpretar o arquivo como Python valido: {erro}")
        return 2

    print(formatar_relatorio(achados))

    if any(a["severidade"] == "CRITICA" for a in achados):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add ai_preflight/cli.py tests/test_cli.py
git commit -m "$(cat <<'EOF'
feat(v2): wire cli.py to the AST engine and handle SyntaxError

Invalid Python files now report a clear message and exit 2 instead of
crashing with an uncaught SyntaxError.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: version bump, full suite, wrap-up

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Bump the version**

In `pyproject.toml`, change:

```toml
version = "0.1.0"
```

to:

```toml
version = "2.0.0"
```

- [ ] **Step 2: Run the full test suite**

Run: `python -m pytest -v`
Expected: all tests pass — v1 tests (`test_rules.py`, `test_report.py`, root `test_cli.py` cases using root fixtures) plus all new v2 tests (`test_arvore.py`, `test_resolver.py`, `test_checadores.py`, `test_scanner.py`), no failures.

- [ ] **Step 3: Manually smoke-test the CLI against the original dangerous script from this session**

Run: `python -m ai_preflight.cli tests/fixtures/v2/git_hook_injection_os_path_join_perigoso.py`
Expected: exit code 1, report shows `git-hook-injection` at the exact line of the `open(...)` call.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "$(cat <<'EOF'
chore(v2): bump version to 2.0.0

escanear_arquivo's signature change (caminho, regras) -> (caminho) is
a breaking change, justifying the major version bump.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

- **Spec coverage:** All 7 checkers (spec lines 114-120) → Tasks 4-10. `arvore.py` (spec lines 40-60) → Task 2. `resolver.py` (spec lines 62-106) → Task 3. Contract change on `escanear_arquivo` (spec line 22-26, every finding has a real `linha`) → Task 11, verified explicitly in `test_escanear_arquivo_todo_achado_tem_linha_definida`. `report.py`/`cli.py` "minimal change" (spec line 20) → Task 12 only touches the two lines that reference the old signature/import. Error handling for `SyntaxError` (spec lines 132-134) → Task 12. All 3 proof fixtures (spec lines 125-128) → import-alias in Task 4, structural false-positive in Task 5, `os.path.join` in Task 10. `rules.py` and root fixtures kept untouched (spec line 130) → Global Constraints, no task modifies them. Versioning (spec lines 142-143) → Task 13.
- **Placeholder scan:** no TBD/TODO, no "add error handling", no "similar to Task N" — every step has literal code or an exact command with expected output.
- **Type consistency:** `_achado`, `_extrair_strings`, `_literais_de_string`, `_modo_de_abertura`, `primeiro_ancestral`, `resolver_chamada`, `TODOS_CHECADORES` are spelled identically everywhere they're defined and reused across Tasks 4-12; checked pass by pass.
