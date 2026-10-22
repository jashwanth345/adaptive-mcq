"""Explicit offline AI startup. Never downloads models or edits .env."""
import os
import socket
import subprocess
import sys
import time

from backend.app.auth.security import AuthError
from backend.app.config import load_settings
from backend.app.generator.client import OllamaGenerator
from backend.app.generator.prompt import tokenizer
from backend.app.hardware import snapshot
from backend.app.rag.model_files import verify_snapshot
from backend.run_ollama import environment, executable
from deployment.local import NO_WINDOW, ROOT, OperationError, start
from deployment.native import start as start_database


def prerequisites():
    manifest = ROOT / 'models/ollama/manifests/registry.ollama.ai/library/qwen2.5/0.5b-instruct-q4_K_M'
    if not manifest.is_file():
        raise OperationError('The small local model is not installed. See docs/question-generation.md. No model was downloaded.')
    tokenizer()
    verify_snapshot()
    return executable()


def main():
    process = None
    try:
        binary = prerequisites()
        # Refuse to take over an existing runtime with unknown cloud settings.
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 11434))
        start_database()
        os.environ['GENERATOR_MODE'] = os.environ['VERIFIER_MODE'] = 'ollama'
        settings = load_settings()
        (ROOT / 'logs').mkdir(exist_ok=True)
        with (ROOT / 'logs/ollama-local.log').open('a', encoding='utf-8') as log:
            process = subprocess.Popen([str(binary), 'serve'], env=environment(),
                                       stdout=log, stderr=log, creationflags=NO_WINDOW)
            client = OllamaGenerator(settings)
            deadline = time.monotonic() + 20
            while True:
                try:
                    # Serving the website does not load model weights. Enforce
                    # the memory guard before each inference, not before login.
                    client.inspect(require_memory=False)
                    break
                except AuthError as error:
                    if error.code != 'GENERATOR_OFFLINE' or time.monotonic() >= deadline or process.poll() is not None:
                        raise
                    time.sleep(0.3)
            print('Local AI enabled for this run only. Hardware-validated model selection: pending quality evaluation.', flush=True)
            memory = snapshot()
            if memory.get('available_ram_gib', 0) < 1.5:
                print('Website available; generation will wait for at least 1.5 GiB free RAM. No model is loaded at startup.', flush=True)
            start(settings)
        return 0
    except (OperationError, AuthError, OSError, ValueError) as error:
        print(error.code if isinstance(error, AuthError) else str(error), file=sys.stderr)
        return 1
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == '__main__':
    raise SystemExit(main())
