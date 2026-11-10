"""Local launcher. Production: gunicorn "crosspay:create_app('prod')" (see Procfile)."""
from crosspay import create_app

app = create_app()

if __name__ == "__main__":
    app.run(port=5000, debug=app.config["FLASK_DEBUG"])
