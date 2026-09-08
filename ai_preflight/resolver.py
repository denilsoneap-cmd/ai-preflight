import ast


class ResolvedorDeImports:
    def __init__(self, tree):
        self.apelidos_modulo = {}
        self.apelidos_funcao = {}
        self._atribuicoes = {}
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
            elif isinstance(node, ast.Assign):
                for alvo in node.targets:
                    if isinstance(alvo, ast.Name):
                        self._atribuicoes.setdefault(alvo.id, []).append(node.value)

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

    def resolver_valor(self, node):
        if not isinstance(node, ast.Name):
            return None
        valores = self._atribuicoes.get(node.id)
        if valores is None or len(valores) != 1:
            return None
        return valores[0]
