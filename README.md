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
