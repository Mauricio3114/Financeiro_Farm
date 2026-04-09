from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para acessar o sistema."
    login_manager.login_message_category = "warning"

    from app.models.usuario import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.farmacias import farmacias_bp
    from app.routes.boletos import boletos_bp
    from app.routes.usuarios import usuarios_bp
    from app.routes.despesas import despesas_bp
    from app.routes.vendas import vendas_bp
    from app.routes.entregadores import entregadores_bp
    from app.routes.motos import motos_bp
    from app.routes.despesas_motos import despesas_motos_bp
    from app.routes.relatorios import relatorios_bp
    from app.routes.contas_receber import contas_receber_bp
    from app.routes.caixa import caixa_bp
    from app.routes.despesas_fixas import despesas_fixas_bp
    from app.routes.agenda import agenda_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(farmacias_bp)
    app.register_blueprint(boletos_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(despesas_bp)
    app.register_blueprint(vendas_bp)
    app.register_blueprint(entregadores_bp)
    app.register_blueprint(motos_bp)
    app.register_blueprint(despesas_motos_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(contas_receber_bp)
    app.register_blueprint(caixa_bp)
    app.register_blueprint(despesas_fixas_bp)
    app.register_blueprint(agenda_bp)

    @app.context_processor
    def inject_usuario():
        return dict(usuario_logado=current_user)

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.dashboard"))
        return redirect(url_for("auth.login"))

    return app