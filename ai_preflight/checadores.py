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
