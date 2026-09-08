from ai_preflight.rules import ALL_RULES, RULE_LINHA


def test_regra_silent_package_install_existe():
    encontradas = [r for r in ALL_RULES if r["id"] == "silent-package-install"]
    assert len(encontradas) == 1
    regra = encontradas[0]
    assert regra["tipo"] == RULE_LINHA
    assert regra["severidade"] == "CRITICA"
    assert "padrao" in regra
    assert "mensagem" in regra
