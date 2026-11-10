"""Local launcher. Production: gunicorn "crosspay:create_app('prod')" (see Procfile).

    python app.py            # port from $PORT, default 5000
    python app.py 5001       # explicit port
"""
import os
import sys

from crosspay import create_app

app = create_app()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.getenv("PORT", "5000"))
    app.run(port=port, debug=app.config["FLASK_DEBUG"])
