from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Farmacia, UsuarioFarmacia, Entregador

entregadores_bp = Blueprint("entregadores", __name__, url_prefix="/entregadores")


def farmacias_do_usuario(usuario):
    if usuario.is_admin():
        return Farmacia.query.order_by(Farmacia.nome_fantasia.asc()).all()

    vinculacoes = UsuarioFarmacia.query.filter_by(usuario_id=usuario.id).all()
    ids = [v.farmacia_id for v in vinculacoes]

    if not ids:
        return []

    return Farmacia.query.filter(Farmacia.id.in_(ids)).order_by(Farmacia.nome_fantasia.asc()).all()


def usuario_tem_acesso_farmacia(usuario, farmacia_id):
    return any(f.id == farmacia_id for f in farmacias_do_usuario(usuario))


@entregadores_bp.route("/")
@login_required
def listar_entregadores():
    farmacias = farmacias_do_usuario(current_user)
    farmacia_ids = [f.id for f in farmacias]
    filtro_farmacia_id = request.args.get("farmacia_id", type=int)

    entregadores = []

    if farmacia_ids:
        query = Entregador.query.filter(Entregador.farmacia_id.in_(farmacia_ids))

        if filtro_farmacia_id:
            query = query.filter(Entregador.farmacia_id == filtro_farmacia_id)

        entregadores = query.order_by(Entregador.nome.asc()).all()

    return render_template(
        "entregadores.html",
        entregadores=entregadores,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id
    )


@entregadores_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo_entregador():
    farmacias = farmacias_do_usuario(current_user)

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        cpf = request.form.get("cpf", "").strip()
        observacao = request.form.get("observacao", "").strip()
        ativo = request.form.get("ativo") == "1"

        if not farmacia_id or not nome:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("entregador_form.html", farmacias=farmacias, entregador=None)

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("entregadores.listar_entregadores"))

        entregador = Entregador(
            farmacia_id=farmacia_id,
            nome=nome,
            telefone=telefone,
            cpf=cpf,
            observacao=observacao,
            ativo=ativo
        )

        db.session.add(entregador)
        db.session.commit()

        flash("Entregador cadastrado com sucesso.", "success")
        return redirect(url_for("entregadores.listar_entregadores"))

    return render_template("entregador_form.html", farmacias=farmacias, entregador=None)


@entregadores_bp.route("/editar/<int:entregador_id>", methods=["GET", "POST"])
@login_required
def editar_entregador(entregador_id):
    entregador = Entregador.query.get_or_404(entregador_id)
    farmacias = farmacias_do_usuario(current_user)

    if not usuario_tem_acesso_farmacia(current_user, entregador.farmacia_id):
        flash("Você não tem acesso a esse entregador.", "danger")
        return redirect(url_for("entregadores.listar_entregadores"))

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        cpf = request.form.get("cpf", "").strip()
        observacao = request.form.get("observacao", "").strip()
        ativo = request.form.get("ativo") == "1"

        if not farmacia_id or not nome:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("entregador_form.html", farmacias=farmacias, entregador=entregador)

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("entregadores.listar_entregadores"))

        entregador.farmacia_id = farmacia_id
        entregador.nome = nome
        entregador.telefone = telefone
        entregador.cpf = cpf
        entregador.observacao = observacao
        entregador.ativo = ativo

        db.session.commit()

        flash("Entregador atualizado com sucesso.", "success")
        return redirect(url_for("entregadores.listar_entregadores"))

    return render_template("entregador_form.html", farmacias=farmacias, entregador=entregador)


@entregadores_bp.route("/excluir/<int:entregador_id>", methods=["POST"])
@login_required
def excluir_entregador(entregador_id):
    entregador = Entregador.query.get_or_404(entregador_id)

    if not usuario_tem_acesso_farmacia(current_user, entregador.farmacia_id):
        flash("Você não tem acesso a esse entregador.", "danger")
        return redirect(url_for("entregadores.listar_entregadores"))

    db.session.delete(entregador)
    db.session.commit()

    flash("Entregador excluído com sucesso.", "success")
    return redirect(url_for("entregadores.listar_entregadores"))