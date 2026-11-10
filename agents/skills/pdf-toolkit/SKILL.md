---
name: pdf-toolkit
description: >
  Executa operações de manipulação de arquivo PDF: mesclar, dividir, girar
  páginas, extrair texto, extrair imagens, ver metadados, comprimir,
  proteger com senha (criptografar), remover senha (descriptografar) e
  aplicar marca d'água. Use esta skill sempre que o usuário mencionar um
  arquivo .pdf e pedir para juntar, unir, separar, girar/rotacionar,
  extrair texto/tabelas de, extrair imagens de, comprimir, proteger,
  descriptografar ou carimbar/marcar um PDF. Para ler e resumir um PDF
  muito extenso (1.000+ páginas), use a skill `pdf-leitura-extensa`.
---

# PDF Toolkit

## Índice

- [Visão Geral](#visão-geral)
- [Script: `script/`](#script-script)
- [Uso](#uso)
- [Comandos](#comandos)
- [Pré-requisitos](#pré-requisitos)
- [Referências](#referências)

## Visão Geral

Kit de linha de comando independente para as operações mais comuns de
**manipulação** de PDF, baseado no skill oficial
[`pdf`](https://github.com/anthropics/skills/tree/main/skills/pdf) da
Anthropic, porém reimplementado em **Rust** para seguir o padrão deste
repositório (binário único, sem runtime Python; wrapper Bash para Linux e
macOS).

Assim como `docx_to_pdf.rs` e `juntar_pdfs.rb`, o programa **não
reimplementa o formato PDF**: ele orquestra ferramentas maduras e
amplamente testadas — `qpdf`, `poppler-utils`
(`pdftotext`/`pdfimages`/`pdfinfo`) e `ghostscript` — validando entradas e
relatando o resultado.

Esta skill cobre manipulação de arquivo e inclui seu próprio código e
processo de compilação. Ler e resumir um PDF muito grande (milhares de
páginas) é coberto pela skill independente **`pdf-leitura-extensa`**, que
inclui separadamente apenas os comandos de leitura necessários.

## Script: `script/`

Programa Rust autocontido (**apenas a `std`**, sem crates externos),
dividido em módulos curtos e objetivos — um arquivo por subcomando — no
mesmo espírito dos scripts individuais do
[skill de referência](https://github.com/anthropics/skills/tree/main/skills/pdf/scripts):

```
script/
  main.rs              # CLI: parseia o subcomando e despacha
  common.rs            # logging, deteccao de ferramentas, execucao de processos
  commands/
    mod.rs
    merge.rs            extract_text.rs      encrypt.rs
    split.rs             extract_images.rs    decrypt.rs
    rotate.rs            metadata.rs          watermark.rs
    compress.rs          inventory.rs         rasterize.rs
    read_large.rs
```

Cada `commands/<nome>.rs` expõe `run_cmd(args)` e `print_help()` e não
ultrapassa ~125 linhas. `common.rs` reúne apenas o que é compartilhado
entre os subcomandos (logging, verificação de ferramentas externas no
PATH, execução de processos, helpers de caminho). `inventory.rs`,
`read_large.rs` e `rasterize.rs` também vivem aqui — mesmo binário —
mas sua documentação de uso fica na skill `pdf-leitura-extensa`.

## Uso

```bash
"$SKILL_DIR/scripts/pdf_toolkit" --help
```

Defina `SKILL_DIR` como a pasta que contém este `SKILL.md`. O wrapper
compila o binário na primeira execução e guarda a compilação no cache do
usuário. Esta skill funciona sem o repositório original ou sem a skill
`pdf-leitura-extensa`.

## Comandos

| Comando | Faz | Ferramenta |
|---|---|---|
| `merge` | Mescla vários PDFs em um só, na ordem informada | `qpdf` |
| `split` | Divide um PDF (por página ou por intervalos) | `qpdf` |
| `rotate` | Gira páginas em múltiplos de 90° | `qpdf` |
| `extract-text` | Extrai o texto do PDF (com ou sem layout) | `pdftotext` |
| `extract-images` | Extrai as imagens embutidas no PDF | `pdfimages` |
| `metadata` | Exibe título, autor, nº de páginas, criptografia… | `pdfinfo` |
| `compress` | Reduz o tamanho comprimindo imagens embutidas | `ghostscript` |
| `encrypt` | Protege o PDF com senha (AES-256) | `qpdf` |
| `decrypt` | Remove a senha/criptografia de um PDF protegido | `qpdf` |
| `watermark` | Sobrepõe (ou coloca atrás) as páginas de outro PDF | `qpdf` |

Flags detalhadas de cada comando, com exemplos:
[`reference/comandos.md`](reference/comandos.md).

Para `inventory`, `read-large` e `rasterize` (leitura de PDF extenso), veja
a skill **`pdf-leitura-extensa`** — o `--help` de cada um também funciona
normalmente (`$SKILL_DIR/scripts/pdf_toolkit read-large --help`).

```bash
"$SKILL_DIR/scripts/pdf_toolkit" --help
"$SKILL_DIR/scripts/pdf_toolkit" <comando> --help   # opções detalhadas de cada comando
```

## Pré-requisitos

```bash
sudo apt install qpdf poppler-utils ghostscript   # Debian / Ubuntu
sudo pacman -S qpdf poppler ghostscript           # Arch Linux / Omarchy
sudo pacman -S rust                               # Rust/Cargo para compilar na primeira execução
```

Detalhes por SO, tabela ferramenta → comando, e as limitações do toolkit
em relação ao skill original (tabelas, criação de PDF do zero, OCR,
formulários): [`reference/pre-requisitos.md`](reference/pre-requisitos.md).

## Referências

- [`reference/comandos.md`](reference/comandos.md) — flags detalhadas dos
  10 comandos de manipulação, com exemplos de uso.
- [`reference/pre-requisitos.md`](reference/pre-requisitos.md) —
  instalação por SO, tabela ferramenta → comando, limitações conhecidas.
- Skill `pdf-leitura-extensa` — leitura e resumo de PDFs muito extensos
  (1.000+ páginas), incluindo o caso de PDF escaneado (sem camada de
  texto).
