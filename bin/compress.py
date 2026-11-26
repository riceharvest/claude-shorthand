import sys, json, os, datetime

try:
    from llmlingua import PromptCompressor
except ImportError:
    class PromptCompressor:
        def __init__(self, **kwargs): pass
        def compress_prompt(self, p, **kwargs):
            return {"compressed_prompt": p, "origin_tokens": len(p)//4, "compressed_tokens": len(p)//4}

PLUGIN_DIR  = os.path.expanduser("~/.claude/plugins/shorthand")
STATE_FILE  = os.path.join(PLUGIN_DIR, "bin", "state.json")
LOG_FILE    = os.path.join(PLUGIN_DIR, "compress.log")
CONFIG_FILE = os.path.join(PLUGIN_DIR, "config.json")

# Expanded defaults covering multiple languages and frameworks
DEFAULT_FORCE_TOKENS = [
    # File extensions
    '.php', '.js', '.ts', '.py', '.rb', '.go', '.java', '.cs', '.cpp', '.c', '.rs',
    '.vue', '.jsx', '.tsx', '.html', '.css', '.env', '.json', '.yaml', '.yml',
    # OOP / structure
    'function', 'class', 'interface', 'abstract', 'public', 'private', 'protected', 'static',
    'def', 'self', 'import', 'export', 'return', 'async', 'await', 'yield',
    # Errors & exceptions
    'Error', 'Exception', 'Warning', 'Traceback', 'TypeError', 'ValueError',
    'KeyError', 'AttributeError', 'RuntimeError', 'null', 'undefined', 'nil', 'None',
    # Database
    'SQL', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WHERE', 'JOIN', 'FROM', 'GROUP BY',
    # HTTP / API
    'HTTP', 'API', 'URL', 'JSON', 'GET', 'POST', 'PUT', 'PATCH',
]

def load_config():
    defaults = {"rate": 0.4, "threshold": 800, "extra_force_tokens": [], "backend": "llmlingua"}
    if not os.path.exists(CONFIG_FILE):
        return defaults
    try:
        with open(CONFIG_FILE, 'r') as f:
            defaults.update(json.load(f))
    except Exception:
        pass
    return defaults

def get_state():
    if not os.path.exists(STATE_FILE):
        return "on"
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f).get("enabled", "on")
    except Exception:
        return "on"

def write_log(msg):
    try:
        # Rotate: keep last 200 lines if file exceeds 50KB
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 50 * 1024:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
            with open(LOG_FILE, 'w') as f:
                f.writelines(lines[-200:])
        with open(LOG_FILE, 'a') as f:
            f.write(msg)
    except Exception:
        pass

def main():
    os.makedirs(os.path.join(PLUGIN_DIR, "bin"), exist_ok=True)

    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            return
        data = json.loads(input_data)
        prompt = data.get("prompt", "")
    except Exception:
        prompt = ""

    config = load_config()
    state  = get_state()

    if state == "off" or len(prompt) < config["threshold"]:
        print(json.dumps({"prompt": prompt}))
        return

    dry_run = (state == "dry-run")

    try:
        force_tokens = DEFAULT_FORCE_TOKENS + config.get("extra_force_tokens", [])

        backend = config.get("backend", "llmlingua")
        if backend not in ("llmlingua", "ctxprune"):
            write_log(f"[Shorthand] unknown backend '{backend}'; using llmlingua\n")
            backend = "llmlingua"

        # model_name is the llmlingua-2 alias. ctxprune remaps it to its own model
        # (darioooooo0o/ctxprune-small), so the value is kept for llmlingua compatibility.
        init_args = dict(
            model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
            use_llmlingua2=True,
            device_map="cpu",
        )
        compressor, extra = None, {}
        if backend == "ctxprune":
            # Construction is inside the try: a missing onnxruntime or a failed model
            # download fails here and falls back to llmlingua, not to pass-through.
            try:
                # Same API and return keys as llmlingua; CPU int8 ONNX model, no torch.
                # protect=True: never drop an identifier, number or path.
                from ctxprune.compat import PromptCompressor as CtxPromptCompressor
                ctx_args = dict(init_args)
                # Optional pinned model: a local snapshot directory (see Readme). When it is
                # set, ctxprune loads these files and never queries the Hugging Face head.
                if config.get("ctxprune_model"):
                    ctx_args["model_name"] = config["ctxprune_model"]
                compressor = CtxPromptCompressor(**ctx_args)
                extra = {"protect": True}
            except Exception as e:
                write_log(f"[Shorthand] backend 'ctxprune' unavailable ({e}); using llmlingua\n")
                compressor = None
        if compressor is None:
            compressor = PromptCompressor(**init_args)

        result = compressor.compress_prompt(
            prompt,
            rate=config["rate"],
            force_tokens=force_tokens,
            **extra
        )
        compressed = result["compressed_prompt"]

        orig_t   = result.get("origin_tokens", len(prompt) // 4)
        comp_t   = result.get("compressed_tokens", len(compressed) // 4)
        savings  = round((1 - (comp_t / orig_t)) * 100, 1)
        ts       = datetime.datetime.now().strftime("%H:%M:%S")
        mode_tag = " [dry-run]" if dry_run else ""

        write_log(f"{ts} [Shorthand{mode_tag}] 📉 {orig_t} -> {comp_t} tokens (-{savings}%)\n")

        # Dry-run: log stats but send original prompt unchanged
        print(json.dumps({"prompt": prompt if dry_run else compressed}))

    except Exception as e:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        write_log(f"{ts} [Shorthand Error] {str(e)}\n")
        print(json.dumps({"prompt": prompt}))

if __name__ == "__main__":
    main()
