"""Demo Linux Server Monitoring — Flask entrypoint (local demo only)."""

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_wtf import CSRFProtect, FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Length

from auth import (
    authenticate,
    is_authenticated,
    login_required,
    login_user,
    logout_user,
)
from config import ConfigError, load_admin_config

csrf = CSRFProtect()


class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(max=64)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(max=256)],
    )


def create_app(test_config=None):
    """Application factory — validates admin hash config at startup."""
    application = Flask(__name__)

    if test_config is not None:
        application.config.update(test_config)
    else:
        application.config.update(load_admin_config())

    password_hash = (application.config.get("ADMIN_PASSWORD_HASH") or "").strip()
    if not password_hash:
        raise ConfigError(
            "ADMIN_PASSWORD_HASH is required. "
            "Generate one with: python scripts/generate_password_hash.py"
        )
    application.config["ADMIN_PASSWORD_HASH"] = password_hash

    if not (application.config.get("ADMIN_USERNAME") or "").strip():
        raise ConfigError("ADMIN_USERNAME must not be empty.")

    if not application.config.get("SECRET_KEY"):
        application.config["SECRET_KEY"] = "dev-only-change-me"

    # Session defaults if not provided by test_config / load_admin_config
    application.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    application.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    application.config.setdefault("SESSION_COOKIE_SECURE", False)
    application.config.setdefault("WTF_CSRF_ENABLED", True)

    csrf.init_app(application)

    @application.context_processor
    def inject_auth():
        return {"logged_in": is_authenticated()}

    @application.route("/")
    def home():
        if is_authenticated():
            return redirect(url_for("overview"))
        return redirect(url_for("login"))

    @application.route("/login", methods=["GET", "POST"])
    def login():
        if is_authenticated():
            return redirect(url_for("overview"))

        form = LoginForm()
        if form.validate_on_submit():
            username = form.username.data.strip()
            password = form.password.data
            # Never log password / form.password
            if authenticate(username, password):
                login_user(username)
                next_url = request.args.get("next") or url_for("overview")
                if not next_url.startswith("/"):
                    next_url = url_for("overview")
                return redirect(next_url)
            flash("Invalid username or password.", "error")

        return render_template("login.html", form=form)

    @application.route("/logout", methods=["POST", "GET"])
    def logout():
        logout_user()
        flash("Signed out.", "info")
        return redirect(url_for("login"))

    @application.route("/overview")
    @login_required
    def overview():
        return render_template("overview.html")

    @application.route("/servers/add")
    @login_required
    def add_server():
        return render_template("add_server.html")

    @application.route("/servers/<server_id>")
    @login_required
    def server_detail(server_id):
        return render_template("server_detail.html", server_id=server_id)

    return application


# Optional module-level app when env is already configured (e.g. flask run).
try:
    app = create_app()
except ConfigError:
    app = None


if __name__ == "__main__":
    try:
        application = app or create_app()
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc

    # Listen on all interfaces so the demo is reachable from any host.
    # use_reloader=False avoids orphaned parent processes that leave port 5100 dead.
    application.run(host="0.0.0.0", port=5100, debug=True, use_reloader=False)
