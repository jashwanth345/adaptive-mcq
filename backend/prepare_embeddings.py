"""Explicit, one-time download of FREE / OPEN SOURCE Apache-2.0 model files."""

import json
import urllib.request

from backend.app.rag.model_files import (
    COMMIT,
    FILES,
    MODEL_DIR,
    MODEL_NAME,
    digest,
    verify_snapshot,
)


def main():
    try:
        verify_snapshot()
        print("Pinned embedding snapshot is already complete.")
        return
    except (OSError, ValueError, KeyError):
        pass
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in FILES:
        target = MODEL_DIR / name
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".part")
        url = f"https://huggingface.co/{MODEL_NAME}/resolve/{COMMIT}/{name}"
        print(f"Downloading {name}", flush=True)
        try:
            with (
                urllib.request.urlopen(url, timeout=90) as response,
                temporary.open("wb") as stream,
            ):
                total = 0
                while data := response.read(1024 * 1024):
                    total += len(data)
                    if total > 110 * 1024 * 1024:
                        raise ValueError("Unexpected model file size")
                    stream.write(data)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        hashes[name] = digest(target)
    (MODEL_DIR / "snapshot.json").write_text(
        json.dumps({"model": MODEL_NAME, "commit": COMMIT, "files": hashes}, indent=2),
        encoding="utf-8",
    )
    verify_snapshot()
    print("Local embedding snapshot prepared and checked. Runtime requires no network.")


if __name__ == "__main__":
    main()
