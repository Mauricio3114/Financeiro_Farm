from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Usuario, Farmacia, UsuarioFarmacia

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


def admin_required():
    return current_user.is_authenticated and current_user.is_admin()


@usuarios_bp.route("/")
@login_required
def listar_usuarios():
    if not admin_required():
        flash("Apenas admin pode acessar usuários.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    usuarios = Usuario.query.order_by(Usuario.nome.asc()).all()
    return render_template("usuarios.html", usuarios=usuarios)


@usuarios_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo_usuario():
    if not admin_required():
        flash("Apenas admin pode cadastrar usuários.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    farmacias = Farmacia.query.order_by(Farmacia.nome_fantasia.asc()).all()

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "").strip()
        perfil = request.form.get("perfil", "financeiro").strip()
        ativo = request.form.get("ativo") == "1"
        farmacia_ids = request.form.getlist("farmacias")

        if not nome or not email or not senha:
            flash("Preencha nome, e-mail e senha.", "danger")
            return render_template(
                "usuario_form.html",
                usuario=None,
                farmacias=farmacias,
                vinculados=[]
            )

        existente = Usuario.query.filter_by(email=email).first()
        if existente:
            flash("Já existe usuário com esse e-mail.", "danger")
            return render_template(
                "usuario_form.html",
                usuario=None,
                farmacias=farmacias,
                vinculados=[]
            )

        usuario = Usuario(
            nome=nome,
            email=email,
            perfil=perfil,
            ativo=ativo
        )
        usuario.set_senha(senha)

        db.session.add(usuario)
        db.session.flush()

        for farmacia_id in farmacia_ids:
            db.session.add(
                UsuarioFarmacia(usuario_id=usuario.id, farmacia_id=int(farmacia_id))
            )

        db.session.commit()
        flash("Usuário cadastrado com sucesso.", "success")
        return redirect(url_for("usuarios.listar_usuarios"))

    return render_template(
        "usuario_form.html",
        usuario=None,
        farmacias=farmacias,
        vinculados=[]
    )


@usuarios_bp.route("/editar/<int:usuario_id>", methods=["GET", "POST"])
@login_required
def editar_usuario(usuario_id):
    if not admin_required():
        flash("Apenas admin pode editar usuários.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    usuario = Usuario.query.get_or_404(usuario_id)
    farmacias = Farmacia.query.order_by(Farmacia.nome_fantasia.asc()).all()
    vinculados = [v.farmacia_id for v in usuario.vinculacoes]

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "").strip()
        perfil = request.form.get("perfil", "financeiro").strip()
        ativo = request.form.get("ativo") == "1"
        farmacia_ids = [int(fid) for fid in request.form.getlist("farmacias")]

        if not nome or not email:
            flash("Preencha nome e e-mail.", "danger")
            return render_template(
                "usuario_form.html",
                usuario=usuario,
                farmacias=farmacias,
                vinculados=vinculados
            )

        existente = Usuario.query.filter(Usuario.email == email, Usuario.id != usuario.id).first()
        if existente:
            flash("Já existe outro usuário com esse e-mail.", "danger")
            return render_template(
                "usuario_form.html",
                usuario=usuario,
                farmacias=farmacias,
                vinculados=vinculados
            )

        usuario.nome = nome
        usuario.email = email
        usuario.perfil = perfil
        usuario.ativo = ativo

        if senha:
            usuario.set_senha(senha)

        UsuarioFarmacia.query.filter_by(usuario_id=usuario.id).delete()

        for farmacia_id in farmacia_ids:
            db.session.add(
                UsuarioFarmacia(usuario_id=usuario.id, farmacia_id=farmacia_id)
            )

        db.session.commit()
        flash("Usuário atualizado com sucesso.", "success")
        return redirect(url_for("usuarios.listar_usuarios"))

    return render_template(
        "usuario_form.html",
        usuario=usuario,
        farmacias=farmacias,
        vinculados=vinculados
    )