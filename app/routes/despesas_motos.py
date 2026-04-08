from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Farmacia, UsuarioFarmacia, Entregador, Moto, DespesaMoto

despesas_motos_bp = Blueprint("despesas_motos", __name__, url_prefix="/despesas-motos")


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


def motos_do_usuario(usuario):
    farmacias = farmacias_do_usuario(usuario)
    farmacia_ids = [f.id for f in farmacias]

    if not farmacia_ids:
        return []

    return Moto.query.filter(Moto.farmacia_id.in_(farmacia_ids)).order_by(Moto.modelo.asc()).all()


def entregadores_do_usuario(usuario):
    farmacias = farmacias_do_usuario(usuario)
    farmacia_ids = [f.id for f in farmacias]

    if not farmacia_ids:
        return []

    return Entregador.query.filter(Entregador.farmacia_id.in_(farmacia_ids)).order_by(Entregador.nome.asc()).all()


@despesas_motos_bp.route("/")
@login_required
def listar_despesas_motos():
    farmacias = farmacias_do_usuario(current_user)
    farmacia_ids = [f.id for f in farmacias]
    filtro_farmacia_id = request.args.get("farmacia_id", type=int)

    despesas_motos = []

    if farmacia_ids:
        query = DespesaMoto.query.filter(DespesaMoto.farmacia_id.in_(farmacia_ids))

        if filtro_farmacia_id:
            query = query.filter(DespesaMoto.farmacia_id == filtro_farmacia_id)

        despesas_motos = query.order_by(DespesaMoto.data_despesa.desc()).all()

    return render_template(
        "despesas_motos.html",
        despesas_motos=despesas_motos,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id
    )


@despesas_motos_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova_despesa_moto():
    farmacias = farmacias_do_usuario(current_user)
    motos = motos_do_usuario(current_user)
    entregadores = entregadores_do_usuario(current_user)

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        entregador_id = request.form.get("entregador_id", type=int)
        moto_id = request.form.get("moto_id", type=int)
        tipo_despesa = request.form.get("tipo_despesa", "").strip()
        descricao = request.form.get("descricao", "").strip()
        valor = request.form.get("valor", "0").replace(",", ".")
        data_despesa = request.form.get("data_despesa")
        observacao = request.form.get("observacao", "").strip()

        if not farmacia_id or not moto_id or not tipo_despesa or not descricao or not data_despesa:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template(
                "despesa_moto_form.html",
                farmacias=farmacias,
                motos=motos,
                entregadores=entregadores,
                despesa_moto=None
            )

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("despesas_motos.listar_despesas_motos"))

        moto = Moto.query.get(moto_id)
        if not moto or moto.farmacia_id != farmacia_id:
            flash("Moto inválida para essa farmácia.", "danger")
            return render_template(
                "despesa_moto_form.html",
                farmacias=farmacias,
                motos=motos,
                entregadores=entregadores,
                despesa_moto=None
            )

        if entregador_id:
            entregador = Entregador.query.get(entregador_id)
            if not entregador or entregador.farmacia_id != farmacia_id:
                flash("Entregador inválido para essa farmácia.", "danger")
                return render_template(
                    "despesa_moto_form.html",
                    farmacias=farmacias,
                    motos=motos,
                    entregadores=entregadores,
                    despesa_moto=None
                )
        else:
            entregador_id = moto.entregador_id

        despesa_moto = DespesaMoto(
            farmacia_id=farmacia_id,
            entregador_id=entregador_id,
            moto_id=moto_id,
            tipo_despesa=tipo_despesa,
            descricao=descricao,
            valor=float(valor or 0),
            data_despesa=datetime.strptime(data_despesa, "%Y-%m-%d").date(),
            observacao=observacao
        )

        db.session.add(despesa_moto)
        db.session.commit()

        flash("Despesa da moto cadastrada com sucesso.", "success")
        return redirect(url_for("despesas_motos.listar_despesas_motos"))

    return render_template(
        "despesa_moto_form.html",
        farmacias=farmacias,
        motos=motos,
        entregadores=entregadores,
        despesa_moto=None
    )


@despesas_motos_bp.route("/editar/<int:despesa_moto_id>", methods=["GET", "POST"])
@login_required
def editar_despesa_moto(despesa_moto_id):
    despesa_moto = DespesaMoto.query.get_or_404(despesa_moto_id)
    farmacias = farmacias_do_usuario(current_user)

    if not usuario_tem_acesso_farmacia(current_user, despesa_moto.farmacia_id):
        flash("Você não tem acesso a essa despesa.", "danger")
        return redirect(url_for("despesas_motos.listar_despesas_motos"))

    motos = motos_do_usuario(current_user)
    entregadores = entregadores_do_usuario(current_user)

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        entregador_id = request.form.get("entregador_id", type=int)
        moto_id = request.form.get("moto_id", type=int)
        tipo_despesa = request.form.get("tipo_despesa", "").strip()
        descricao = request.form.get("descricao", "").strip()
        valor = request.form.get("valor", "0").replace(",", ".")
        data_despesa = request.form.get("data_despesa")
        observacao = request.form.get("observacao", "").strip()

        if not farmacia_id or not moto_id or not tipo_despesa or not descricao or not data_despesa:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template(
                "despesa_moto_form.html",
                farmacias=farmacias,
                motos=motos,
                entregadores=entregadores,
                despesa_moto=despesa_moto
            )

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("despesas_motos.listar_despesas_motos"))

        moto = Moto.query.get(moto_id)
        if not moto or moto.farmacia_id != farmacia_id:
            flash("Moto inválida para essa farmácia.", "danger")
            return render_template(
                "despesa_moto_form.html",
                farmacias=farmacias,
                motos=motos,
                entregadores=entregadores,
                despesa_moto=despesa_moto
            )

        if entregador_id:
            entregador = Entregador.query.get(entregador_id)
            if not entregador or entregador.farmacia_id != farmacia_id:
                flash("Entregador inválido para essa farmácia.", "danger")
                return render_template(
                    "despesa_moto_form.html",
                    farmacias=farmacias,
                    motos=motos,
                    entregadores=entregadores,
                    despesa_moto=despesa_moto
                )
        else:
            entregador_id = moto.entregador_id

        despesa_moto.farmacia_id = farmacia_id
        despesa_moto.entregador_id = entregador_id
        despesa_moto.moto_id = moto_id
        despesa_moto.tipo_despesa = tipo_despesa
        despesa_moto.descricao = descricao
        despesa_moto.valor = float(valor or 0)
        despesa_moto.data_despesa = datetime.strptime(data_despesa, "%Y-%m-%d").date()
        despesa_moto.observacao = observacao

        db.session.commit()

        flash("Despesa da moto atualizada com sucesso.", "success")
        return redirect(url_for("despesas_motos.listar_despesas_motos"))

    return render_template(
        "despesa_moto_form.html",
        farmacias=farmacias,
        motos=motos,
        entregadores=entregadores,
        despesa_moto=despesa_moto
    )


@despesas_motos_bp.route("/excluir/<int:despesa_moto_id>", methods=["POST"])
@login_required
def excluir_despesa_moto(despesa_moto_id):
    despesa_moto = DespesaMoto.query.get_or_404(despesa_moto_id)

    if not usuario_tem_acesso_farmacia(current_user, despesa_moto.farmacia_id):
        flash("Você não tem acesso a essa despesa.", "danger")
        return redirect(url_for("despesas_motos.listar_despesas_motos"))

    db.session.delete(despesa_moto)
    db.session.commit()

    flash("Despesa da moto excluída com sucesso.", "success")
    return redirect(url_for("despesas_motos.listar_despesas_motos"))