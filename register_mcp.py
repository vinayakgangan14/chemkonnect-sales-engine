# register_mcp.py
"""
Registers the Chemkonnect Sales Engine MCP Server into Antigravity's global mcp_config.json.
Uses the project's dedicated .venv Python with all dependencies pre-installed.
"""
import sys
import os
import json

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CONFIG_PATH = os.path.expanduser(r"~\.gemini\config\mcp_config.json")
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SCRIPT_PATH = os.path.join(BASE_DIR, "src", "chemkonnect_mcp.py")
VENV_PYTHON = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")

def register():
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    
    config = {}
    if os.path.exists(CONFIG_PATH) and os.path.getsize(CONFIG_PATH) > 0:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["chemkonnect-sales"] = {
        "command": VENV_PYTHON,
        "args": [
            SCRIPT_PATH
        ],
        "env": {
            "PYTHONIOENCODING": "utf-8"
        }
    }

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"[SUCCESS] Registered 'chemkonnect-sales' with venv python:")
    print(f"    Python: {VENV_PYTHON}")
    print(f"    Script: {SCRIPT_PATH}")

if __name__ == "__main__":
    register()