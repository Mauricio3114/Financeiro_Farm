from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Farmacia, UsuarioFarmacia, Entregador, Moto

motos_bp = Blueprint("motos", __name__, url_prefix="/motos")


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


def entregadores_disponiveis(usuario, farmacia_id=None):
    farmacias = farmacias_do_usuario(usuario)
    farmacia_ids = [f.id for f in farmacias]

    if not farmacia_ids:
        return []

    query = Entregador.query.filter(
        Entregador.farmacia_id.in_(farmacia_ids),
        Entregador.ativo == True
    )

    if farmacia_id:
        query = query.filter(Entregador.farmacia_id == farmacia_id)

    return query.order_by(Entregador.nome.asc()).all()


@motos_bp.route("/")
@login_required
def listar_motos():
    farmacias = farmacias_do_usuario(current_user)
    farmacia_ids = [f.id for f in farmacias]
    filtro_farmacia_id = request.args.get("farmacia_id", type=int)

    motos = []

    if farmacia_ids:
        query = Moto.query.filter(Moto.farmacia_id.in_(farmacia_ids))

        if filtro_farmacia_id:
            query = query.filter(Moto.farmacia_id == filtro_farmacia_id)

        motos = query.order_by(Moto.modelo.asc()).all()

    return render_template(
        "motos.html",
        motos=motos,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id
    )


@motos_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova_moto():
    farmacias = farmacias_do_usuario(current_user)
    entregadores = entregadores_disponiveis(current_user)

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        entregador_id = request.form.get("entregador_id", type=int)
        modelo = request.form.get("modelo", "").strip()
        placa = request.form.get("placa", "").strip()
        ano = request.form.get("ano", "").strip()
        cor = request.form.get("cor", "").strip()
        km_atual = request.form.get("km_atual", "").strip()
        km_ultima_revisao = request.form.get("km_ultima_revisao", "").strip()
        observacao = request.form.get("observacao", "").strip()
        ativa = request.form.get("ativa") == "1"

        if not farmacia_id or not modelo:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template(
                "moto_form.html",
                farmacias=farmacias,
                entregadores=entregadores,
                moto=None
            )

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("motos.listar_motos"))

        if entregador_id:
            entregador = Entregador.query.get(entregador_id)
            if not entregador or entregador.farmacia_id != farmacia_id:
                flash("Entregador inválido para essa farmácia.", "danger")
                return render_template(
                    "moto_form.html",
                    farmacias=farmacias,
                    entregadores=entregadores,
                    moto=None
                )
        else:
            entregador_id = None

        moto = Moto(
            farmacia_id=farmacia_id,
            entregador_id=entregador_id,
            modelo=modelo,
            placa=placa,
            ano=ano,
            cor=cor,
            km_atual=int(km_atual) if km_atual else None,
            km_ultima_revisao=int(km_ultima_revisao) if km_ultima_revisao else None,
            observacao=observacao,
            ativa=ativa
        )

        db.session.add(moto)
        db.session.commit()

        flash("Moto cadastrada com sucesso.", "success")
        return redirect(url_for("motos.listar_motos"))

    return render_template(
        "moto_form.html",
        farmacias=farmacias,
        entregadores=entregadores,
        moto=None
    )


@motos_bp.route("/editar/<int:moto_id>", methods=["GET", "POST"])
@login_required
def editar_moto(moto_id):
    moto = Moto.query.get_or_404(moto_id)
    farmacias = farmacias_do_usuario(current_user)

    if not usuario_tem_acesso_farmacia(current_user, moto.farmacia_id):
        flash("Você não tem acesso a essa moto.", "danger")
        return redirect(url_for("motos.listar_motos"))

    entregadores = entregadores_disponiveis(current_user)

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        entregador_id = request.form.get("entregador_id", type=int)
        modelo = request.form.get("modelo", "").strip()
        placa = request.form.get("placa", "").strip()
        ano = request.form.get("ano", "").strip()
        cor = request.form.get("cor", "").strip()
        km_atual = request.form.get("km_atual", "").strip()
        km_ultima_revisao = request.form.get("km_ultima_revisao", "").strip()
        observacao = request.form.get("observacao", "").strip()
        ativa = request.form.get("ativa") == "1"

        if not farmacia_id or not modelo:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template(
                "moto_form.html",
                farmacias=farmacias,
                entregadores=entregadores,
                moto=moto
            )

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("motos.listar_motos"))

        if entregador_id:
            entregador = Entregador.query.get(entregador_id)
            if not entregador or entregador.farmacia_id != farmacia_id:
                flash("Entregador inválido para essa farmácia.", "danger")
                return render_template(
                    "moto_form.html",
                    farmacias=farmacias,
                    entregadores=entregadores,
                    moto=moto
                )
        else:
            entregador_id = None

        moto.farmacia_id = farmacia_id
        moto.entregador_id = entregador_id
        moto.modelo = modelo
        moto.placa = placa
        moto.ano = ano
        moto.cor = cor
        moto.km_atual = int(km_atual) if km_atual else None
        moto.km_ultima_revisao = int(km_ultima_revisao) if km_ultima_revisao else None
        moto.observacao = observacao
        moto.ativa = ativa

        db.session.commit()

        flash("Moto atualizada com sucesso.", "success")
        return redirect(url_for("motos.listar_motos"))

    return render_template(
        "moto_form.html",
        farmacias=farmacias,
        entregadores=entregadores,
        moto=moto
    )


@motos_bp.route("/excluir/<int:moto_id>", methods=["POST"])
@login_required
def excluir_moto(moto_id):
    moto = Moto.query.get_or_404(moto_id)

    if not usuario_tem_acesso_farmacia(current_user, moto.farmacia_id):
        flash("Você não tem acesso a essa moto.", "danger")
        return redirect(url_for("motos.listar_motos"))

    db.session.delete(moto)
    db.session.commit()

    flash("Moto excluída com sucesso.", "success")
    return redirect(url_for("motos.listar_motos"))