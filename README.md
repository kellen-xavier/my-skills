# my-skills

I added these custom skills for my own workflows. You are welcome to download
them and adapt them to your needs and use cases.

A personal library and portability archive for agent skills. A skill is a
directory containing `SKILL.md` and, when needed, supporting references,
scripts, templates, or assets. Keep the whole directory together: copying only
`SKILL.md` can break relative links and executable helpers.

## Repository layout

| Path | Contents and use |
| --- | --- |
| `<skill-name>/` | Personal skills maintained at the repository root. These can be linked into agent skill directories. |
| `agents/skills/<skill-name>/` | Complete skill bundles imported from agent skill directories. This includes the standalone PDF packages documented below. |
| `codex/skills/<skill-name>/` | Copies of Codex skill folders kept for reference or installation. |
| `plugins/cache/<plugin>/...` | Plugin-distributed skills and their companion files. Treat these as plugin bundles; install the owning plugin when a skill depends on its tools or configuration. |

Some skills appear in more than one location because this repository contains
both personal skills and imported snapshots. Choose one source directory for a
skill when installing it; do not install duplicate copies with the same skill
name into the same agent.

## Agent skill directories

| Agent | Global skill directory |
| --- | --- |
| Codex | `~/.codex/skills/` or the shared `~/.agents/skills/` |
| Claude Code | `~/.claude/skills/` |
| OpenCode | `~/.config/opencode/skills/`; it also discovers `~/.agents/skills/` and `~/.claude/skills/` |
| Kimi | `~/.kimi-code/skills/` |

OpenCode also loads project skills from `.opencode/skills/`, `.agents/skills/`,
and `.claude/skills/`. See the [OpenCode skills documentation](https://opencode.ai/docs/skills/)
for current discovery rules. Prefer `~/.agents/skills/` when one shared copy
should serve multiple compatible agents. For OpenCode, make sure the installed
directory name matches the skill's frontmatter `name` (for example, install
the `ux-writing` skill under `ux-writing/`, even if its source folder is named
`ux-writing-skill/`).

## Install a skill

### Link a skill from this repository

On the target machine, clone or copy this repository, then link the complete
skill directory into the agent's global skills directory. For a root-level
skill:

```bash
REPO="$HOME/Projects/my-skills"
SKILL="my-skill"
mkdir -p "$HOME/.agents/skills"
ln -s "$REPO/$SKILL" "$HOME/.agents/skills/$SKILL"
```

For an imported bundle under `agents/skills/`, set `SKILL` to its directory
name and use this source path instead:

```bash
REPO="$HOME/Projects/my-skills"
SKILL="pdf-leitura-extensa"
mkdir -p "$HOME/.agents/skills"
ln -s "$REPO/agents/skills/$SKILL" "$HOME/.agents/skills/$SKILL"
```

Use `~/.codex/skills/`, `~/.claude/skills/`, or
`~/.config/opencode/skills/` as the destination when you want the skill
available only to that agent. Keep each destination as a directory and add a
separate link for each skill; do not replace a directory that already has
other skills or agent-specific files. If the destination already exists,
inspect it before linking.

### Copy a skill for a standalone installation

To make a separate copy rather than a link, copy the entire skill folder:

```bash
REPO="$HOME/Projects/my-skills"
SKILL="pdf-leitura-extensa"
mkdir -p "$HOME/.agents/skills"
cp -a "$REPO/agents/skills/$SKILL" "$HOME/.agents/skills/"
```

The resulting `~/.agents/skills/pdf-leitura-extensa/` must contain its
`SKILL.md`, references, Rust source, Cargo manifest, and `scripts/` wrapper.
Use the same procedure for any other bundle, changing `SKILL` to that
directory's name. Keep supporting files beside `SKILL.md` so relative links
continue to work.

### Review root-level personal skills

List root-level skill directories before choosing which ones to install:

```bash
REPO="$HOME/Projects/my-skills"
find "$REPO" -mindepth 2 -maxdepth 2 -name SKILL.md -print
```

The source directory name and the skill's frontmatter name can differ. For
example, the `ux-writing` skill is stored in `ux-writing-skill/`. Use the
frontmatter `name` for the destination name when the agent requires it:

```bash
REPO="$HOME/Projects/my-skills"
SOURCE_DIR="$REPO/ux-writing-skill"
SKILL_NAME="ux-writing"
mkdir -p "$HOME/.agents/skills"
ln -s "$SOURCE_DIR" "$HOME/.agents/skills/$SKILL_NAME"
```

Install skills individually after checking for an existing destination. Do
not bulk-link `agents/`, `codex/`, or `plugins/` as if each were a single skill.
Install an individual nested bundle using its own source directory.

Agents may scan skill directories at startup. Restart the agent or open a new
session if a newly linked skill does not appear.

## Install the PDF skill packages

`pdf-leitura-extensa` and `pdf-toolkit` are separate, self-contained bundles
under `agents/skills/`. Either one can be installed without the other. Both
include their Rust source and compile their own `pdf_toolkit` binary into a
user cache on first use; no binary needs to be copied between machines.

The wrappers use Bash. The documented setup supports Linux and macOS. For
Windows, use a Linux environment such as WSL; the included wrapper is not a
native PowerShell or Command Prompt script.

### PDF reading skill

`pdf-leitura-extensa` reads and prepares very large PDFs. It needs Rust/Cargo,
qpdf, and Poppler utilities (`pdfinfo`, `pdffonts`, `pdfimages`, `pdfdetach`,
`pdftotext`, and `pdftoppm`). It does not require the `pdf-toolkit` skill or
Ghostscript.

Install system dependencies on the target machine:

```bash
# Arch Linux / Omarchy
sudo pacman -S --needed rust qpdf poppler

# Debian / Ubuntu
sudo apt install rustc cargo qpdf poppler-utils

# macOS with Homebrew
brew install rust qpdf poppler
```

Install the skill using the copy or link instructions above. Then run its
wrapper once to compile it and confirm the available commands:

```bash
SKILL_DIR="$HOME/.agents/skills/pdf-leitura-extensa"
"$SKILL_DIR/scripts/pdf_toolkit" --help
```

### PDF manipulation skill

`pdf-toolkit` handles operations such as merging, splitting, rotating,
extracting, compressing, encrypting, and watermarking PDFs. It is independent
of `pdf-leitura-extensa`. In addition to Rust/Cargo, qpdf, and Poppler, it
requires Ghostscript for compression.

Install dependencies on the target machine:

```bash
# Arch Linux / Omarchy
sudo pacman -S --needed rust qpdf poppler ghostscript

# Debian / Ubuntu
sudo apt install rustc cargo qpdf poppler-utils ghostscript

# macOS with Homebrew
brew install rust qpdf poppler ghostscript
```

Install the skill into the shared agent directory, then compile and inspect
its commands:

```bash
SKILL_DIR="$HOME/.agents/skills/pdf-toolkit"
"$SKILL_DIR/scripts/pdf_toolkit" --help
```

The first wrapper run needs Cargo. Later runs reuse the binary under
`~/.cache/codex-skills/` (or `$XDG_CACHE_HOME/codex-skills/` when that variable
is set). The two skills use separate cache directories even though both
binaries are named `pdf_toolkit`.

## Skills and plugin bundles not installed individually

- `omarchy` and `diagnose-crash` are owned by the Omarchy system package and
  may be replaced during system updates.
- `oh-my-opencode-slim` is an OpenCode-only plugin and its config skill belongs
  with that plugin.
- `assess-team` and `assess-partners` live in separate private repositories.
  Do not publish their assessment methods, templates, or reports here.
- `.system` skills are Codex-internal.
- Plugin caches under `plugins/cache/` may need plugin manifests, tools, or
  configuration. Preserve the plugin structure or install the plugin through
  its manager instead of copying only a nested `SKILL.md`.
- Vendor bundles such as `~/.grok/bundled/skills`,
  `~/.config/crush/anthropic_skills/`, and
  `~/.gemini/antigravity-cli/builtin/skills` are managed by their applications.

## Repository rules

`.gitignore` blocks `.venv/`, `__pycache__/`, and binaries (`*.pdf`, images,
archives). Assessment PDFs in particular must never be committed here.

`humanizer` is vendored from <https://github.com/blader/humanizer> with its
`.git` stripped. Re-pull upstream manually if it needs updating.

## Add a personal skill

Create a directory at the repository root containing `SKILL.md`, then link it
to the desired agent directories using the commands in [Install a skill](#install-a-skill).
For example:

```bash
mkdir "$HOME/Projects/my-skills/my-skill"
touch "$HOME/Projects/my-skills/my-skill/SKILL.md"
```
