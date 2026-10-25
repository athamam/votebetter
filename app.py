"""Start VoteBetter:  python app.py   then open http://127.0.0.1:8000

Runs a single server process with auto-reload off, so an edit never spawns a
second server. Stop it with Ctrl+C.
"""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"VoteBetter running at http://127.0.0.1:{port}  (Ctrl+C to stop)")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=False, log_level="warning")
