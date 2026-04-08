from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import Farmacia, UsuarioFarmacia, MovimentoCaixa

caixa_bp = Blueprint("caixa", __name__, url_prefix="/caixa")


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


def parse_date(value):
    try:
        if value:
            return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
    return None


@caixa_bp.route("/")
@login_required
def listar_caixa():
    farmacias = farmacias_do_usuario(current_user)
    farmacia_ids = [f.id for f in farmacias]

    filtro_farmacia_id = request.args.get("farmacia_id", type=int)
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    movimentos = []
    entradas = 0
    saidas = 0

    if farmacia_ids:
        query = MovimentoCaixa.query.filter(MovimentoCaixa.farmacia_id.in_(farmacia_ids))

        if filtro_farmacia_id:
            query = query.filter(MovimentoCaixa.farmacia_id == filtro_farmacia_id)

        if data_inicio:
            query = query.filter(MovimentoCaixa.data_movimento >= data_inicio)

        if data_fim:
            query = query.filter(MovimentoCaixa.data_movimento <= data_fim)

        movimentos = query.order_by(MovimentoCaixa.data_movimento.desc(), MovimentoCaixa.id.desc()).all()

        entradas = sum(m.valor for m in movimentos if m.tipo == "entrada")
        saidas = sum(m.valor for m in movimentos if m.tipo == "saida")

    saldo = entradas - saidas

    resumo_mensal = []
    if farmacia_ids:
        resumo_query = db.session.query(
            func.strftime("%Y-%m", MovimentoCaixa.data_movimento),
            MovimentoCaixa.tipo,
            func.sum(MovimentoCaixa.valor)
        ).filter(MovimentoCaixa.farmacia_id.in_(farmacia_ids))

        if filtro_farmacia_id:
            resumo_query = resumo_query.filter(MovimentoCaixa.farmacia_id == filtro_farmacia_id)

        resumo_mensal = resumo_query.group_by(
            func.strftime("%Y-%m", MovimentoCaixa.data_movimento),
            MovimentoCaixa.tipo
        ).order_by(func.strftime("%Y-%m", MovimentoCaixa.data_movimento).desc()).all()

    return render_template(
        "caixa.html",
        movimentos=movimentos,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=data_inicio.strftime("%Y-%m-%d") if data_inicio else "",
        data_fim=data_fim.strftime("%Y-%m-%d") if data_fim else "",
        entradas=entradas,
        saidas=saidas,
        saldo=saldo,
        resumo_mensal=resumo_mensal
    )


@caixa_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo_movimento():
    farmacias = farmacias_do_usuario(current_user)

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        tipo = request.form.get("tipo", "").strip()
        categoria = request.form.get("categoria", "").strip()
        descricao = request.form.get("descricao", "").strip()
        valor = request.form.get("valor", "0").replace(",", ".")
        data_movimento = request.form.get("data_movimento")
        origem = request.form.get("origem", "").strip()
        observacao = request.form.get("observacao", "").strip()

        if not farmacia_id or not tipo or not categoria or not descricao or not data_movimento:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("movimento_caixa_form.html", farmacias=farmacias)

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("caixa.listar_caixa"))

        movimento = MovimentoCaixa(
            farmacia_id=farmacia_id,
            tipo=tipo,
            categoria=categoria,
            descricao=descricao,
            valor=float(valor or 0),
            data_movimento=datetime.strptime(data_movimento, "%Y-%m-%d").date(),
            origem=origem,
            observacao=observacao
        )

        db.session.add(movimento)
        db.session.commit()

        flash("Movimento de caixa cadastrado com sucesso.", "success")
        return redirect(url_for("caixa.listar_caixa"))

    return render_template("movimento_caixa_form.html", farmacias=farmacias)