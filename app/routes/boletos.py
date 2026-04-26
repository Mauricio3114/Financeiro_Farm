from datetime import datetime, date
from calendar import monthrange
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Farmacia, Boleto, UsuarioFarmacia

boletos_bp = Blueprint("boletos", __name__, url_prefix="/boletos")


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


def adicionar_mes(data_base, meses):
    mes = data_base.month - 1 + meses
    ano = data_base.year + mes // 12
    mes = mes % 12 + 1
    dia = min(data_base.day, monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def gerar_nome_parcela(nome_base, numero, total):
    if total <= 1:
        return nome_base
    return f"{nome_base} ({numero}/{total})"


@boletos_bp.route("/")
@login_required
def listar_boletos():
    farmacias = farmacias_do_usuario(current_user)
    farmacia_ids = [f.id for f in farmacias]

    filtro_farmacia_id = request.args.get("farmacia_id", type=int)
    filtro_status = request.args.get("status", "").strip()

    boletos = []

    if farmacia_ids:
        query = Boleto.query.filter(Boleto.farmacia_id.in_(farmacia_ids))

        if filtro_farmacia_id:
            query = query.filter(Boleto.farmacia_id == filtro_farmacia_id)

        boletos = query.order_by(Boleto.data_vencimento.asc()).all()

        for boleto in boletos:
            boleto.preparar()

        db.session.commit()

        if filtro_status:
            boletos = [b for b in boletos if b.status == filtro_status]

    return render_template(
        "boletos.html",
        boletos=boletos,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        filtro_status=filtro_status,
        hoje=date.today()
    )


@boletos_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo_boleto():
    farmacias = farmacias_do_usuario(current_user)

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        empresa_nome = request.form.get("empresa_nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        valor_original = request.form.get("valor_original", "0").replace(",", ".")
        data_vencimento = request.form.get("data_vencimento")
        data_pagamento = request.form.get("data_pagamento")
        valor_pago = request.form.get("valor_pago", "").replace(",", ".").strip()
        observacao = request.form.get("observacao", "").strip()

        parcelas = request.form.get("parcelas", type=int) or 1
        primeira_data_parcela = request.form.get("primeira_data_parcela", "").strip()

        if not farmacia_id or not empresa_nome or not data_vencimento:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("boleto_form.html", farmacias=farmacias, boleto=None)

        if parcelas < 1:
            parcelas = 1

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("boletos.listar_boletos"))

        valor_total_digitado = float(valor_original or 0)
        valor_parcela = round(valor_total_digitado / parcelas, 2)
        diferenca = round(valor_total_digitado - (valor_parcela * parcelas), 2)

        data_base = datetime.strptime(
            primeira_data_parcela if primeira_data_parcela else data_vencimento,
            "%Y-%m-%d"
        ).date()

        for i in range(parcelas):
            valor_atual = valor_parcela
            if i == parcelas - 1:
                valor_atual = round(valor_atual + diferenca, 2)

            boleto = Boleto(
                farmacia_id=farmacia_id,
                empresa_nome=gerar_nome_parcela(empresa_nome, i + 1, parcelas),
                descricao=descricao,
                valor_original=float(valor_atual),
                data_vencimento=adicionar_mes(data_base, i),
                observacao=observacao
            )

            if parcelas == 1 and data_pagamento:
                boleto.data_pagamento = datetime.strptime(data_pagamento, "%Y-%m-%d").date()

            if parcelas == 1 and valor_pago:
                boleto.valor_pago = float(valor_pago)

            boleto.preparar()

            if boleto.valor_pago is None and boleto.status == "pago":
                boleto.valor_pago = boleto.valor_total

            db.session.add(boleto)

        db.session.commit()

        if parcelas > 1:
            flash("Boletos parcelados cadastrados com sucesso.", "success")
        else:
            flash("Boleto cadastrado com sucesso.", "success")

        return redirect(url_for("boletos.listar_boletos"))

    return render_template("boleto_form.html", farmacias=farmacias, boleto=None)


@boletos_bp.route("/editar/<int:boleto_id>", methods=["GET", "POST"])
@login_required
def editar_boleto(boleto_id):
    boleto = Boleto.query.get_or_404(boleto_id)
    farmacias = farmacias_do_usuario(current_user)

    if not usuario_tem_acesso_farmacia(current_user, boleto.farmacia_id):
        flash("Você não tem acesso a esse boleto.", "danger")
        return redirect(url_for("boletos.listar_boletos"))

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        empresa_nome = request.form.get("empresa_nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        valor_original = request.form.get("valor_original", "0").replace(",", ".")
        data_vencimento = request.form.get("data_vencimento")
        data_pagamento = request.form.get("data_pagamento")
        valor_pago = request.form.get("valor_pago", "").replace(",", ".").strip()
        observacao = request.form.get("observacao", "").strip()

        if not farmacia_id or not empresa_nome or not data_vencimento:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("boleto_form.html", farmacias=farmacias, boleto=boleto)

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("boletos.listar_boletos"))

        boleto.farmacia_id = farmacia_id
        boleto.empresa_nome = empresa_nome
        boleto.descricao = descricao
        boleto.valor_original = float(valor_original or 0)
        boleto.data_vencimento = datetime.strptime(data_vencimento, "%Y-%m-%d").date()
        boleto.data_pagamento = datetime.strptime(data_pagamento, "%Y-%m-%d").date() if data_pagamento else None
        boleto.valor_pago = float(valor_pago) if valor_pago else None
        boleto.observacao = observacao

        boleto.preparar()

        if boleto.valor_pago is None and boleto.status == "pago":
            boleto.valor_pago = boleto.valor_total

        db.session.commit()

        flash("Boleto atualizado com sucesso.", "success")
        return redirect(url_for("boletos.listar_boletos"))

    return render_template("boleto_form.html", farmacias=farmacias, boleto=boleto)


@boletos_bp.route("/pagar/<int:boleto_id>", methods=["POST"])
@login_required
def pagar_boleto(boleto_id):
    boleto = Boleto.query.get_or_404(boleto_id)

    if not usuario_tem_acesso_farmacia(current_user, boleto.farmacia_id):
        flash("Você não tem acesso a esse boleto.", "danger")
        return redirect(url_for("boletos.listar_boletos"))

    data_pagamento = request.form.get("data_pagamento")
    valor_pago = request.form.get("valor_pago", "").replace(",", ".").strip()

    if not data_pagamento:
        flash("Informe a data de pagamento.", "danger")
        return redirect(url_for("boletos.listar_boletos"))

    boleto.data_pagamento = datetime.strptime(data_pagamento, "%Y-%m-%d").date()

    if valor_pago:
        boleto.valor_pago = float(valor_pago)
    else:
        boleto.valor_pago = float(boleto.valor_original or 0)

    boleto.preparar()

    db.session.commit()

    flash("Boleto marcado como pago com sucesso.", "success")
    return redirect(url_for("boletos.listar_boletos"))


@boletos_bp.route("/excluir/<int:boleto_id>", methods=["POST"])
@login_required
def excluir_boleto(boleto_id):
    boleto = Boleto.query.get_or_404(boleto_id)

    if not usuario_tem_acesso_farmacia(current_user, boleto.farmacia_id):
        flash("Você não tem acesso a esse boleto.", "danger")
        return redirect(url_for("boletos.listar_boletos"))

    db.session.delete(boleto)
    db.session.commit()

    flash("Boleto excluído com sucesso.", "success")
    return redirect(url_for("boletos.listar_boletos"))