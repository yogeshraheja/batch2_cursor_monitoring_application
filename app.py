"""Demo Linux Server Monitoring — Flask entrypoint (local demo only)."""

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_wtf import CSRFProtect, FlaskForm
from wtforms import (
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from auth import (
    authenticate,
    is_authenticated,
    login_required,
    login_user,
    logout_user,
)
from collectors.dispatch import (
    REFRESH_SECONDS,
    collect_for_server,
    enrich_for_overview,
    format_memory_line,
)
from collectors.metrics import format_bytes
from config import ConfigError, load_admin_config
from servers import (
    AUTH_KEY,
    AUTH_LOCALHOST,
    AUTH_PASSWORD,
    ServerStore,
    ValidationError,
    validate_server_payload,
)

csrf = CSRFProtect()
server_store = ServerStore()


class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(max=64)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(max=256)],
    )


class ServerForm(FlaskForm):
    name = StringField("Display name", validators=[Optional(), Length(max=128)])
    host = StringField("Host", validators=[Optional(), Length(max=253)])
    port = IntegerField(
        "SSH port",
        default=22,
        validators=[Optional(), NumberRange(min=1, max=65535)],
    )
    ssh_user = StringField("SSH username", validators=[Optional(), Length(max=64)])
    auth_type = SelectField(
        "Auth type",
        choices=[
            (AUTH_PASSWORD, "Password"),
            (AUTH_KEY, "Private key"),
            (AUTH_LOCALHOST, "Localhost (no SSH)"),
        ],
        validators=[DataRequired()],
    )
    password = PasswordField("SSH password", validators=[Optional(), Length(max=512)])
    private_key = TextAreaField(
        "Private key (paste PEM content)",
        validators=[Optional(), Length(max=16384)],
    )


def create_app(test_config=None, *, store: ServerStore | None = None):
    """Application factory — validates admin hash config at startup."""
    application = Flask(__name__)
    application.server_store = store if store is not None else ServerStore()

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

    application.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    application.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    application.config.setdefault("SESSION_COOKIE_SECURE", False)
    application.config.setdefault("WTF_CSRF_ENABLED", True)
    application.config["REFRESH_SECONDS"] = REFRESH_SECONDS

    csrf.init_app(application)

    @application.context_processor
    def inject_globals():
        return {
            "logged_in": is_authenticated(),
            "refresh_seconds": application.config["REFRESH_SECONDS"],
        }

    def _store() -> ServerStore:
        return application.server_store

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
        rows = []
        for server in _store().list():
            metrics = collect_for_server(server)
            rows.append(enrich_for_overview(server, metrics))
        return render_template(
            "overview.html",
            servers=rows,
            auto_refresh=True,
        )

    @application.route("/servers/add", methods=["GET", "POST"])
    @login_required
    def add_server():
        form = ServerForm()
        if form.validate_on_submit():
            try:
                payload = validate_server_payload(
                    name=form.name.data or "",
                    host=form.host.data or "",
                    port=form.port.data if form.port.data is not None else 22,
                    ssh_user=form.ssh_user.data or "",
                    auth_type=form.auth_type.data,
                    password=form.password.data or "",
                    private_key=form.private_key.data or "",
                    require_secrets=True,
                )
                server = _store().add(payload)
                flash(f"Added server “{server.public_dict()['display_name']}”.", "info")
                return redirect(url_for("overview"))
            except ValidationError as exc:
                flash(str(exc), "error")
        return render_template(
            "add_server.html",
            form=form,
            mode="add",
            server=None,
        )

    @application.route("/servers/<server_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_server(server_id):
        server = _store().get(server_id)
        if server is None:
            abort(404)

        form = ServerForm()
        if request.method == "GET":
            form.name.data = server.name
            form.host.data = server.host
            form.port.data = server.port
            form.ssh_user.data = server.ssh_user
            form.auth_type.data = server.auth_type
            # Never pre-fill secrets — blank means keep existing on save
            form.password.data = ""
            form.private_key.data = ""

        if form.validate_on_submit():
            try:
                payload = validate_server_payload(
                    name=form.name.data or "",
                    host=form.host.data or "",
                    port=form.port.data if form.port.data is not None else 22,
                    ssh_user=form.ssh_user.data or "",
                    auth_type=form.auth_type.data,
                    password=form.password.data or "",
                    private_key=form.private_key.data or "",
                    require_secrets=False,
                )
                # For password/key edit with blank secret, ensure existing secret remains
                if payload["auth_type"] == AUTH_PASSWORD and not payload.get("password"):
                    if not server.password:
                        raise ValidationError("Password is required for password auth.")
                if payload["auth_type"] == AUTH_KEY and not payload.get("private_key"):
                    if not server.private_key:
                        raise ValidationError(
                            "Private key content is required for key auth."
                        )
                updated = _store().update(server_id, payload)
                flash(
                    f"Updated “{updated.public_dict()['display_name']}”.",
                    "info",
                )
                return redirect(url_for("overview"))
            except ValidationError as exc:
                flash(str(exc), "error")

        return render_template(
            "add_server.html",
            form=form,
            mode="edit",
            server=server.public_dict(),
        )

    @application.route("/servers/<server_id>/delete", methods=["POST"])
    @login_required
    def delete_server(server_id):
        server = _store().get(server_id)
        if server is None:
            abort(404)
        name = server.public_dict()["display_name"]
        _store().delete(server_id)
        flash(f"Removed “{name}”.", "info")
        return redirect(url_for("overview"))

    @application.route("/servers/<server_id>")
    @login_required
    def server_detail(server_id):
        server = _store().get(server_id)
        if server is None:
            abort(404)
        metrics = collect_for_server(server)
        public = server.public_dict()
        return render_template(
            "server_detail.html",
            server=public,
            metrics=metrics,
            memory_line=format_memory_line(metrics.get("memory")),
            cpu_display=(
                f"{metrics['cpu_percent']:.1f} %"
                if isinstance(metrics.get("cpu_percent"), (int, float))
                else "— %"
            ),
            format_bytes=format_bytes,
            auto_refresh=True,
        )

    return application


# Optional module-level app when env is already configured (e.g. flask run).
try:
    app = create_app(store=server_store)
except ConfigError:
    app = None


if __name__ == "__main__":
    try:
        application = app or create_app(store=server_store)
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc

    # Listen on all interfaces so the demo is reachable from any host.
    # use_reloader=False avoids orphaned parent processes that leave port 5100 dead.
    # Demo only — not production. See docs/security.md.
    application.run(host="0.0.0.0", port=5100, debug=True, use_reloader=False)
