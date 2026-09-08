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
