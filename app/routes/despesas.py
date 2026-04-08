from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Farmacia, UsuarioFarmacia, Despesa

despesas_bp = Blueprint("despesas", __name__, url_prefix="/despesas")


def farmacias_do_usuario(usuario):
    if usuario.is_admin():
        return Farmacia.query.order_by(Farmacia.nome_fantasia.asc()).all()

    vinculacoes = UsuarioFarmacia.query.filter_by(usuario_id=usuario.id).all()
    ids = [v.farmacia_id for v in vinculacoes]

    if not ids:
        return []

    return Farmacia.query.filter(Farmacia.id.in_(ids)).order_by(Farmacia.nome_fantasia.asc()).all()


def usuario_tem_acesso_farmacia(usuario, farmacia_id):
    farmacias = farmacias_do_usuario(usuario)
    return any(f.id == farmacia_id for f in farmacias)


@despesas_bp.route("/")
@login_required
def listar_despesas():
    farmacias = farmacias_do_usuario(current_user)
    farmacia_ids = [f.id for f in farmacias]

    filtro_farmacia_id = request.args.get("farmacia_id", type=int)

    despesas = []
    if farmacia_ids:
        query = Despesa.query.filter(Despesa.farmacia_id.in_(farmacia_ids))
        if filtro_farmacia_id:
            query = query.filter(Despesa.farmacia_id == filtro_farmacia_id)
        despesas = query.order_by(Despesa.data_despesa.desc()).all()

    return render_template(
        "despesas.html",
        despesas=despesas,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id
    )


@despesas_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova_despesa():
    farmacias = farmacias_do_usuario(current_user)

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        categoria = request.form.get("categoria", "").strip()
        centro_custo = request.form.get("centro_custo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        valor = request.form.get("valor", "0").replace(",", ".")
        data_despesa = request.form.get("data_despesa")
        forma_pagamento = request.form.get("forma_pagamento", "").strip()
        observacao = request.form.get("observacao", "").strip()

        if not farmacia_id or not categoria or not descricao or not data_despesa:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("despesa_form.html", farmacias=farmacias, despesa=None)

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("despesas.listar_despesas"))

        despesa = Despesa(
            farmacia_id=farmacia_id,
            categoria=categoria,
            centro_custo=centro_custo or None,
            descricao=descricao,
            valor=float(valor or 0),
            data_despesa=datetime.strptime(data_despesa, "%Y-%m-%d").date(),
            forma_pagamento=forma_pagamento,
            observacao=observacao
        )

        db.session.add(despesa)
        db.session.commit()

        flash("Despesa cadastrada com sucesso.", "success")
        return redirect(url_for("despesas.listar_despesas"))

    return render_template("despesa_form.html", farmacias=farmacias, despesa=None)


@despesas_bp.route("/editar/<int:despesa_id>", methods=["GET", "POST"])
@login_required
def editar_despesa(despesa_id):
    despesa = Despesa.query.get_or_404(despesa_id)
    farmacias = farmacias_do_usuario(current_user)

    if not usuario_tem_acesso_farmacia(current_user, despesa.farmacia_id):
        flash("Você não tem acesso a essa despesa.", "danger")
        return redirect(url_for("despesas.listar_despesas"))

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        categoria = request.form.get("categoria", "").strip()
        centro_custo = request.form.get("centro_custo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        valor = request.form.get("valor", "0").replace(",", ".")
        data_despesa = request.form.get("data_despesa")
        forma_pagamento = request.form.get("forma_pagamento", "").strip()
        observacao = request.form.get("observacao", "").strip()

        if not farmacia_id or not categoria or not descricao or not data_despesa:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("despesa_form.html", farmacias=farmacias, despesa=despesa)

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("despesas.listar_despesas"))

        despesa.farmacia_id = farmacia_id
        despesa.categoria = categoria
        despesa.centro_custo = centro_custo or None
        despesa.descricao = descricao
        despesa.valor = float(valor or 0)
        despesa.data_despesa = datetime.strptime(data_despesa, "%Y-%m-%d").date()
        despesa.forma_pagamento = forma_pagamento
        despesa.observacao = observacao

        db.session.commit()

        flash("Despesa atualizada com sucesso.", "success")
        return redirect(url_for("despesas.listar_despesas"))

    return render_template("despesa_form.html", farmacias=farmacias, despesa=despesa)


@despesas_bp.route("/excluir/<int:despesa_id>", methods=["POST"])
@login_required
def excluir_despesa(despesa_id):
    despesa = Despesa.query.get_or_404(despesa_id)

    if not usuario_tem_acesso_farmacia(current_user, despesa.farmacia_id):
        flash("Você não tem acesso a essa despesa.", "danger")
        return redirect(url_for("despesas.listar_despesas"))

    db.session.delete(despesa)
    db.session.commit()

    flash("Despesa excluída com sucesso.", "success")
    return redirect(url_for("despesas.listar_despesas"))