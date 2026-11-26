# Claude Shorthand

> Extend your context window and slash token costs.

This plugin integrates **LLMLingua-2** directly into your Claude Code workflow to automatically compress massive prompts and stack traces by **up to 60%**, without losing critical debugging details.

---

## Features

- **Smart Shorthanding.** Uses BERT-based compression to strip redundant boilerplate while keeping your code logic intact.
- **Multi-language.** Protects tokens across PHP, Python, JS/TS, Ruby, Go, Java, Rust, and more out of the box.
- **Configurable.** Tune compression rate, threshold, and protected tokens via `config.json`.
- **Token Stats Logging.** Every compression is logged with timestamp and savings to `compress.log`.
- **Log Rotation.** Log is automatically trimmed to 200 lines when it exceeds 50KB.
- **Dynamic Toggle.** Enable, disable, or switch to dry-run mode with `/shorthand`.
- **Global.** Applies to every project automatically. No per-project setup needed.

---

## Requirements

- Python 3.9+
- `pip3` available on PATH
- Claude Code (CLI)

---

## Installation

### Option A: Claude Code Marketplace (recommended)

```bash
/plugin install claude-shorthand@gladehq
```

Then install the Python dependency:

```bash
pip3 install llmlingua
```

Restart Claude Code to activate.

### Option B: Manual install

1. **Clone or extract** the repository into your preferred directory.

2. **Navigate to the folder:**
   ```bash
   cd claude-shorthand
   ```

3. **Run the installer:**
   ```bash
   ./install.sh
   ```
   This will:
   - Install `llmlingua` and its dependencies via `pip3`
   - Copy plugin files to `~/.claude/plugins/shorthand/`
   - Copy the `/shorthand` skill to `~/.claude/skills/shorthand/`
   - Copy `config.json` to `~/.claude/plugins/shorthand/` (skipped if one already exists)
   - Auto-register the `UserPromptSubmit` hook in `~/.claude/settings.json`
   - Pre-download the LLMLingua-2 BERT model (~400MB) so first use is instant

4. **Restart Claude Code** to activate.

---

## Uninstallation

```bash
./uninstall.sh
```

This removes all plugin files, the skill, and the hook entry from `settings.json`.

---

## How to Use

### Automatic Mode

Every prompt over **800 characters** is automatically compressed before being sent to Claude. Stats are logged silently:

```
15:29:54 [Shorthand] 📉 5462 -> 2701 tokens (-50.5%)
```

### Monitoring Stats

```bash
tail -f ~/.claude/plugins/shorthand/compress.log
```

### Slash Commands

| Command | Description |
|---|---|
| `/shorthand on` | Enable compression (default) |
| `/shorthand off` | Disable compression |
| `/shorthand dry-run` | Log stats but send original prompt unchanged |
| `/shorthand status` | Show current mode and last 5 log entries |

---

## Configuration

Edit `~/.claude/plugins/shorthand/config.json` to customise behaviour:

```json
{
  "rate": 0.4,
  "threshold": 800,
  "extra_force_tokens": ["MyClass", "myFunction", ".blade.php"]
}
```

| Key | Default | Description |
|---|---|---|
| `rate` | `0.4` | Compression aggressiveness. `0.2` = more aggressive, `0.6` = less |
| `threshold` | `800` | Minimum characters before compression triggers |
| `extra_force_tokens` | `[]` | Additional tokens to always preserve (merged with built-in defaults) |
| `backend` | `"llmlingua"` | `"ctxprune"` swaps in [ctxprune](https://github.com/riceharvest/ctxprune)'s drop-in `PromptCompressor` (`pip install ctxprune==0.4.0`, the version tested here): CPU-only int8 ONNX model (~143 MB, no torch) and `protect=True`, which never drops an identifier, number or path. If ctxprune cannot be constructed (not installed, missing onnxruntime, or a failed model download), the hook logs one line and falls back to llmlingua. An unrecognized value is logged and uses llmlingua. |
| `ctxprune_model` | unset | Local directory with a downloaded ctxprune model, for a pinned revision (see the ctxprune section below). Unset = ctxprune's default Hugging Face download |

#### ctxprune backend: privacy, model source and first use

- Prompts are compressed locally on CPU. Network access is the one-time model download (none when `ctxprune_model` is set, below). If you install `tiktoken` separately, ctxprune also fetches its `o200k_base` encoding on first use; the ctxprune 0.4.0 install does not include it.
- The default download is **not pinned**. ctxprune 0.4.0 fetches `darioooooo0o/ctxprune-small` (a separate Hugging Face account from the ctxprune GitHub repo) at its current head, and that head decides which tokens are dropped from every prompt. To pin it, download a reviewed revision once and point the hook at the local copy:

  ```bash
  python -m pip install "ctxprune==0.4.0" huggingface_hub
  python -c "from huggingface_hub import snapshot_download as s; print(s('darioooooo0o/ctxprune-small', revision='bb52cb4eedcbd0961bed89bce3cf508e78e01418', local_dir=\"$HOME/models/ctxprune-small-bb52cb4\"))"
  ```

  Then set `"ctxprune_model"` in `config.json` to that local directory, e.g. `"ctxprune_model": "/home/you/models/ctxprune-small-bb52cb4"`. The revision above was the model head on 2026-11-26; check the model page before you use it.
- The first use downloads ~143 MB and can exceed the hook timeout on a long prompt. Pre-warm it once, before relying on the hook:

  ```bash
  python -m pip install "ctxprune==0.4.0"
  python -c "from ctxprune.compat import PromptCompressor as P; P(model_name='microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank', use_llmlingua2=True, device_map='cpu')"
  ```

- With `protect=True`, ctxprune keeps identifiers, numbers and paths in addition to the `force_tokens` list. This is not identical to llmlingua's `force_tokens` alone.

### Default Protected Tokens

The following are protected out of the box across all languages:

- **File extensions:** `.php` `.js` `.ts` `.py` `.rb` `.go` `.java` `.cs` `.cpp` `.rs` `.vue` `.jsx` `.tsx`
- **Keywords:** `function` `class` `def` `self` `import` `async` `await` `return`
- **Errors:** `Error` `Exception` `Traceback` `TypeError` `ValueError` `KeyError` `AttributeError`
- **Database:** `SQL` `SELECT` `INSERT` `UPDATE` `DELETE` `WHERE` `JOIN`
- **HTTP/API:** `HTTP` `API` `GET` `POST` `PUT` `PATCH` `JSON`

---

## File Structure

**Repository:**
```
claude-shorthand/
├── .claude-plugin/
│   └── plugin.json       # Marketplace manifest
├── bin/
│   └── compress.py       # Hook entrypoint
├── skills/
│   └── shorthand/
│       └── SKILL.md      # /shorthand slash command
└── config.json           # Default configuration
```

**Installed (manual install via `install.sh`):**
```
~/.claude/plugins/shorthand/
├── bin/
│   ├── compress.py       # Hook entrypoint
│   └── state.json        # Runtime state (on / off / dry-run)
├── compress.log          # Token savings log (auto-rotated at 50KB)
└── config.json           # User configuration

~/.claude/skills/shorthand/
└── SKILL.md              # /shorthand slash command
```

---

## Platform Support

| Platform | Status |
|---|---|
| macOS | ✅ Fully supported |
| Linux | ✅ Fully supported |
| Windows (WSL2 / Git Bash) | ✅ Works |
| Windows (native CMD / PowerShell) | ❌ Not supported |

### Windows Limitation

`install.sh` and `uninstall.sh` are bash scripts and will not run in native Windows CMD or PowerShell. The compression core (`compress.py`) is pure Python and is already cross-platform. The only gap is the installer and uninstaller.

If you'd like to take this on, please open an issue or submit a PR. Any contribution, no matter how small, is appreciated.

---

## Changelog

### 2026-03-15
- Fixed `install.sh` to use `pip3` instead of `pip`
- Fixed skill registration path to `~/.claude/skills/shorthand/`
- Fixed LLMLingua CUDA error on macOS, added `device_map="cpu"`
- Fixed terminal corruption, stats now go to `compress.log` instead of `/dev/tty`
- `install.sh` now auto-registers the hook in `settings.json`
- `install.sh` now pre-downloads the model so first use is instant
- Added `uninstall.sh` for clean removal
- Added `config.json` for user-configurable rate, threshold, and extra force tokens
- Expanded default `force_tokens` to cover PHP, Python, JS/TS, Ruby, Go, Java, Rust, and more
- Implemented `/shorthand dry-run`, logs stats but passes original prompt unchanged
- Implemented `/shorthand status`, shows current mode and recent log activity
- Added log rotation, trims to 200 lines when file exceeds 50KB
