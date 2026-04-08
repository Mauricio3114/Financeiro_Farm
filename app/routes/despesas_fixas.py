from calendar import monthrange
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import (
    Farmacia,
    UsuarioFarmacia,
    DespesaFixa,
    DespesaFixaLancamento,
    MovimentoCaixa,
)

despesas_fixas_bp = Blueprint("despesas_fixas", __name__, url_prefix="/despesas-fixas")


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


@despesas_fixas_bp.route("/")
@login_required
def listar_despesas_fixas():
    farmacias = farmacias_do_usuario(current_user)
    farmacia_ids = [f.id for f in farmacias]
    filtro_farmacia_id = request.args.get("farmacia_id", type=int)

    despesas_fixas = []
    if farmacia_ids:
        query = DespesaFixa.query.filter(DespesaFixa.farmacia_id.in_(farmacia_ids))
        if filtro_farmacia_id:
            query = query.filter(DespesaFixa.farmacia_id == filtro_farmacia_id)
        despesas_fixas = query.order_by(DespesaFixa.nome.asc()).all()

    return render_template(
        "despesas_fixas.html",
        despesas_fixas=despesas_fixas,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id
    )


@despesas_fixas_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova_despesa_fixa():
    farmacias = farmacias_do_usuario(current_user)

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        nome = request.form.get("nome", "").strip()
        categoria = request.form.get("categoria", "").strip()
        centro_custo = request.form.get("centro_custo", "").strip()
        valor_padrao = request.form.get("valor_padrao", "0").replace(",", ".")
        dia_vencimento = request.form.get("dia_vencimento", type=int)
        tipo_valor = request.form.get("tipo_valor", "").strip()
        observacao = request.form.get("observacao", "").strip()
        ativa = request.form.get("ativa") == "1"

        if not farmacia_id or not nome or not categoria or not dia_vencimento or not tipo_valor:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("despesa_fixa_form.html", farmacias=farmacias, despesa_fixa=None)

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("despesas_fixas.listar_despesas_fixas"))

        despesa_fixa = DespesaFixa(
            farmacia_id=farmacia_id,
            nome=nome,
            categoria=categoria,
            centro_custo=centro_custo or None,
            valor_padrao=float(valor_padrao or 0),
            dia_vencimento=dia_vencimento,
            tipo_valor=tipo_valor,
            observacao=observacao,
            ativa=ativa
        )

        db.session.add(despesa_fixa)
        db.session.commit()

        flash("Despesa fixa cadastrada com sucesso.", "success")
        return redirect(url_for("despesas_fixas.listar_despesas_fixas"))

    return render_template("despesa_fixa_form.html", farmacias=farmacias, despesa_fixa=None)


@despesas_fixas_bp.route("/editar/<int:despesa_fixa_id>", methods=["GET", "POST"])
@login_required
def editar_despesa_fixa(despesa_fixa_id):
    despesa_fixa = DespesaFixa.query.get_or_404(despesa_fixa_id)
    farmacias = farmacias_do_usuario(current_user)

    if not usuario_tem_acesso_farmacia(current_user, despesa_fixa.farmacia_id):
        flash("Você não tem acesso a essa despesa fixa.", "danger")
        return redirect(url_for("despesas_fixas.listar_despesas_fixas"))

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        nome = request.form.get("nome", "").strip()
        categoria = request.form.get("categoria", "").strip()
        centro_custo = request.form.get("centro_custo", "").strip()
        valor_padrao = request.form.get("valor_padrao", "0").replace(",", ".")
        dia_vencimento = request.form.get("dia_vencimento", type=int)
        tipo_valor = request.form.get("tipo_valor", "").strip()
        observacao = request.form.get("observacao", "").strip()
        ativa = request.form.get("ativa") == "1"

        if not farmacia_id or not nome or not categoria or not dia_vencimento or not tipo_valor:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("despesa_fixa_form.html", farmacias=farmacias, despesa_fixa=despesa_fixa)

        despesa_fixa.farmacia_id = farmacia_id
        despesa_fixa.nome = nome
        despesa_fixa.categoria = categoria
        despesa_fixa.centro_custo = centro_custo or None
        despesa_fixa.valor_padrao = float(valor_padrao or 0)
        despesa_fixa.dia_vencimento = dia_vencimento
        despesa_fixa.tipo_valor = tipo_valor
        despesa_fixa.observacao = observacao
        despesa_fixa.ativa = ativa

        db.session.commit()

        flash("Despesa fixa atualizada com sucesso.", "success")
        return redirect(url_for("despesas_fixas.listar_despesas_fixas"))

    return render_template("despesa_fixa_form.html", farmacias=farmacias, despesa_fixa=despesa_fixa)


@despesas_fixas_bp.route("/excluir/<int:despesa_fixa_id>", methods=["POST"])
@login_required
def excluir_despesa_fixa(despesa_fixa_id):
    despesa_fixa = DespesaFixa.query.get_or_404(despesa_fixa_id)

    if not usuario_tem_acesso_farmacia(current_user, despesa_fixa.farmacia_id):
        flash("Você não tem acesso a essa despesa fixa.", "danger")
        return redirect(url_for("despesas_fixas.listar_despesas_fixas"))

    db.session.delete(despesa_fixa)
    db.session.commit()

    flash("Despesa fixa excluída com sucesso.", "success")
    return redirect(url_for("despesas_fixas.listar_despesas_fixas"))


@despesas_fixas_bp.route("/lancamentos")
@login_required
def listar_lancamentos():
    farmacias = farmacias_do_usuario(current_user)
    farmacia_ids = [f.id for f in farmacias]

    filtro_farmacia_id = request.args.get("farmacia_id", type=int)
    filtro_ano = request.args.get("ano", type=int) or date.today().year
    filtro_mes = request.args.get("mes", type=int) or date.today().month

    lancamentos = []
    if farmacia_ids:
        query = DespesaFixaLancamento.query.filter(
            DespesaFixaLancamento.farmacia_id.in_(farmacia_ids),
            DespesaFixaLancamento.ano == filtro_ano,
            DespesaFixaLancamento.mes == filtro_mes
        )

        if filtro_farmacia_id:
            query = query.filter(DespesaFixaLancamento.farmacia_id == filtro_farmacia_id)

        lancamentos = query.order_by(DespesaFixaLancamento.data_vencimento.asc()).all()

        for lancamento in lancamentos:
            lancamento.preparar()

        db.session.commit()

    return render_template(
        "despesas_fixas_lancamentos.html",
        lancamentos=lancamentos,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        filtro_ano=filtro_ano,
        filtro_mes=filtro_mes
    )


@despesas_fixas_bp.route("/gerar-mes", methods=["POST"])
@login_required
def gerar_mes():
    farmacia_id = request.form.get("farmacia_id", type=int)
    ano = request.form.get("ano", type=int)
    mes = request.form.get("mes", type=int)

    if not farmacia_id or not ano or not mes:
        flash("Informe farmácia, ano e mês.", "danger")
        return redirect(url_for("despesas_fixas.listar_lancamentos"))

    if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
        flash("Você não tem acesso a essa farmácia.", "danger")
        return redirect(url_for("despesas_fixas.listar_lancamentos"))

    despesas_fixas = DespesaFixa.query.filter_by(farmacia_id=farmacia_id, ativa=True).all()

    geradas = 0
    for despesa in despesas_fixas:
        existe = DespesaFixaLancamento.query.filter_by(
            despesa_fixa_id=despesa.id,
            farmacia_id=farmacia_id,
            ano=ano,
            mes=mes
        ).first()

        if existe:
            continue

        ultimo_dia = monthrange(ano, mes)[1]
        dia = despesa.dia_vencimento if despesa.dia_vencimento <= ultimo_dia else ultimo_dia

        lancamento = DespesaFixaLancamento(
            despesa_fixa_id=despesa.id,
            farmacia_id=farmacia_id,
            nome=despesa.nome,
            categoria=despesa.categoria,
            centro_custo=despesa.centro_custo,
            valor=despesa.valor_padrao,
            ano=ano,
            mes=mes,
            data_vencimento=date(ano, mes, dia),
            observacao=despesa.observacao
        )
        lancamento.preparar()
        db.session.add(lancamento)
        geradas += 1

    db.session.commit()

    flash(f"{geradas} despesa(s) fixa(s) gerada(s) com sucesso.", "success")
    return redirect(url_for("despesas_fixas.listar_lancamentos", farmacia_id=farmacia_id, ano=ano, mes=mes))


@despesas_fixas_bp.route("/pagar/<int:lancamento_id>", methods=["POST"])
@login_required
def pagar_lancamento(lancamento_id):
    lancamento = DespesaFixaLancamento.query.get_or_404(lancamento_id)

    if not usuario_tem_acesso_farmacia(current_user, lancamento.farmacia_id):
        flash("Você não tem acesso a esse lançamento.", "danger")
        return redirect(url_for("despesas_fixas.listar_lancamentos"))

    data_pagamento = request.form.get("data_pagamento")
    valor = request.form.get("valor", "").replace(",", ".").strip()

    if not data_pagamento:
        flash("Informe a data de pagamento.", "danger")
        return redirect(url_for("despesas_fixas.listar_lancamentos"))

    lancamento.data_pagamento = datetime.strptime(data_pagamento, "%Y-%m-%d").date()
    if valor:
        lancamento.valor = float(valor)

    lancamento.preparar()

    db.session.add(
        MovimentoCaixa(
            farmacia_id=lancamento.farmacia_id,
            tipo="saida",
            categoria=lancamento.categoria,
            descricao=f"Despesa fixa: {lancamento.nome}",
            valor=lancamento.valor,
            data_movimento=lancamento.data_pagamento,
            origem="despesa_fixa",
            observacao=lancamento.observacao
        )
    )

    db.session.commit()

    flash("Despesa fixa marcada como paga.", "success")
    return redirect(url_for("despesas_fixas.listar_lancamentos", farmacia_id=lancamento.farmacia_id, ano=lancamento.ano, mes=lancamento.mes))