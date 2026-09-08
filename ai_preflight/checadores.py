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
        tokens = []
        for s in literais:
            tokens.extend(s.split())
        tem_gerenciador = any(t in ("pip", "pip3", "npm") for t in tokens)
        tem_install = "install" in tokens
        if tem_gerenciador and tem_install:
            achados.append(_achado(
                "silent-package-install", "CRITICA", node,
                "Instalacao de pacote embutida no script, sem pedir confirmacao.",
            ))
    return achados


def _modo_de_abertura(node):
    if len(node.args) >= 2:
        arg = node.args[1]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return kw.value.value
    return None


def _e_modo_de_escrita(modo):
    if not modo:
        return False
    base = modo.lstrip("btU+")
    return base.startswith(("w", "a", "x"))


def _iter_e_os_walk(for_node, resolver):
    it = for_node.iter
    if isinstance(it, ast.Call):
        return resolver.resolver_chamada(it) == "os.walk"
    return False


def checar_reescrita_em_massa(tree, resolver):
    achados = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if resolver.resolver_chamada(node) not in ("open", "io.open"):
            continue
        if not _e_modo_de_escrita(_modo_de_abertura(node)):
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
    nivel_modulo = [
        node for node in tree.body
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    escopos.append(_andar_sem_descer_em_escopos_aninhados(nivel_modulo))

    pendentes = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    while pendentes:
        no = pendentes.pop()
        escopos.append(_andar_sem_descer_em_escopos_aninhados(no.body))
        pendentes.extend(
            sub for sub in no.body
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        )
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
        if not isinstance(node, ast.Call):
            continue
        if resolver.resolver_chamada(node) not in ("open", "io.open"):
            continue
        if not _e_modo_de_escrita(_modo_de_abertura(node)):
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
