from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from app import db
from app.models import Usuario

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "").strip()

        usuario = Usuario.query.filter_by(email=email, ativo=True).first()

        if usuario and usuario.check_senha(senha):
            login_user(usuario)
            flash("Login realizado com sucesso.", "success")
            return redirect(url_for("dashboard.dashboard"))

        flash("E-mail ou senha inválidos.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/criar-admin")
def criar_admin():
    existente = Usuario.query.filter_by(email="admin@financeirofarm.com").first()
    if existente:
        return "Admin já existe."

    admin = Usuario(
        nome="Administrador",
        email="admin@financeirofarm.com",
        perfil="admin",
        ativo=True
    )
    admin.set_senha("123456")

    db.session.add(admin)
    db.session.commit()

    return "Admin criado com sucesso. Login: admin@financeirofarm.com | Senha: 123456"