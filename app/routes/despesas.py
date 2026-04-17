from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Farmacia, UsuarioFarmacia, Despesa, DespesaFixa

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
    filtro_tipo = request.args.get("tipo", "").strip()

    despesas_unificadas = []

    if farmacia_ids:
        despesas_normais_query = Despesa.query.filter(Despesa.farmacia_id.in_(farmacia_ids))
        despesas_fixas_query = DespesaFixa.query.filter(DespesaFixa.farmacia_id.in_(farmacia_ids))

        if filtro_farmacia_id:
            despesas_normais_query = despesas_normais_query.filter(Despesa.farmacia_id == filtro_farmacia_id)
            despesas_fixas_query = despesas_fixas_query.filter(DespesaFixa.farmacia_id == filtro_farmacia_id)

        if filtro_tipo in ["normal", "fixa"]:
            if filtro_tipo == "normal":
                despesas_fixas = []
                despesas_normais = despesas_normais_query.order_by(Despesa.data_despesa.desc()).all()
            else:
                despesas_normais = []
                despesas_fixas = despesas_fixas_query.order_by(DespesaFixa.nome.asc()).all()
        else:
            despesas_normais = despesas_normais_query.order_by(Despesa.data_despesa.desc()).all()
            despesas_fixas = despesas_fixas_query.order_by(DespesaFixa.nome.asc()).all()

        for d in despesas_normais:
            despesas_unificadas.append({
                "id": d.id,
                "tipo": "normal",
                "farmacia": d.farmacia.nome_fantasia if d.farmacia else "-",
                "categoria": d.categoria,
                "descricao": d.descricao,
                "valor": d.valor,
                "data_ref": d.data_despesa,
                "extra": d.forma_pagamento or "-",
                "status": "Lançada"
            })

        for d in despesas_fixas:
            despesas_unificadas.append({
                "id": d.id,
                "tipo": "fixa",
                "farmacia": d.farmacia.nome_fantasia if d.farmacia else "-",
                "categoria": d.categoria,
                "descricao": d.nome,
                "valor": d.valor_padrao,
                "data_ref": None,
                "extra": f"Vence dia {d.dia_vencimento}",
                "status": "Ativa" if d.ativa else "Inativa"
            })

        despesas_unificadas = sorted(
            despesas_unificadas,
            key=lambda x: (
                0 if x["data_ref"] else 1,
                x["data_ref"] or datetime.max.date()
            ),
            reverse=True
        )

    return render_template(
        "despesas.html",
        despesas=despesas_unificadas,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        filtro_tipo=filtro_tipo
    )


@despesas_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova_despesa():
    farmacias = farmacias_do_usuario(current_user)

    if request.method == "POST":
        tipo_despesa = request.form.get("tipo_despesa", "").strip()
        farmacia_id = request.form.get("farmacia_id", type=int)
        categoria = request.form.get("categoria", "").strip()
        descricao = request.form.get("descricao", "").strip()
        valor = request.form.get("valor", "0").replace(",", ".")
        observacao = request.form.get("observacao", "").strip()

        if not tipo_despesa or not farmacia_id or not categoria or not descricao:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("despesa_form.html", farmacias=farmacias, despesa=None)

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("despesas.listar_despesas"))

        if tipo_despesa == "normal":
            data_despesa = request.form.get("data_despesa")
            forma_pagamento = request.form.get("forma_pagamento", "").strip()

            if not data_despesa:
                flash("Informe a data da despesa.", "danger")
                return render_template("despesa_form.html", farmacias=farmacias, despesa=None)

            despesa = Despesa(
                farmacia_id=farmacia_id,
                categoria=categoria,
                descricao=descricao,
                valor=float(valor or 0),
                data_despesa=datetime.strptime(data_despesa, "%Y-%m-%d").date(),
                forma_pagamento=forma_pagamento,
                observacao=observacao
            )
            db.session.add(despesa)

        elif tipo_despesa == "fixa":
            dia_vencimento = request.form.get("dia_vencimento", type=int)
            tipo_valor = request.form.get("tipo_valor", "").strip()
            ativa = request.form.get("ativa") == "1"

            if not dia_vencimento or not tipo_valor:
                flash("Preencha os campos da despesa fixa.", "danger")
                return render_template("despesa_form.html", farmacias=farmacias, despesa=None)

            despesa_fixa = DespesaFixa(
                farmacia_id=farmacia_id,
                nome=descricao,
                categoria=categoria,
                valor_padrao=float(valor or 0),
                dia_vencimento=dia_vencimento,
                tipo_valor=tipo_valor,
                observacao=observacao,
                ativa=ativa
            )
            db.session.add(despesa_fixa)

        else:
            flash("Tipo de despesa inválido.", "danger")
            return render_template("despesa_form.html", farmacias=farmacias, despesa=None)

        db.session.commit()

        flash("Despesa salva com sucesso.", "success")
        return redirect(url_for("despesas.listar_despesas"))

    return render_template("despesa_form.html", farmacias=farmacias, despesa=None)


@despesas_bp.route("/editar/<string:tipo>/<int:despesa_id>", methods=["GET", "POST"])
@login_required
def editar_despesa(tipo, despesa_id):
    farmacias = farmacias_do_usuario(current_user)

    if tipo == "normal":
        despesa = Despesa.query.get_or_404(despesa_id)

        if not usuario_tem_acesso_farmacia(current_user, despesa.farmacia_id):
            flash("Você não tem acesso a essa despesa.", "danger")
            return redirect(url_for("despesas.listar_despesas"))

        if request.method == "POST":
            farmacia_id = request.form.get("farmacia_id", type=int)
            categoria = request.form.get("categoria", "").strip()
            descricao = request.form.get("descricao", "").strip()
            valor = request.form.get("valor", "0").replace(",", ".")
            data_despesa = request.form.get("data_despesa")
            forma_pagamento = request.form.get("forma_pagamento", "").strip()
            observacao = request.form.get("observacao", "").strip()

            if not farmacia_id or not categoria or not descricao or not data_despesa:
                flash("Preencha os campos obrigatórios.", "danger")
                return render_template("despesa_form.html", farmacias=farmacias, despesa=despesa, tipo_edicao="normal")

            despesa.farmacia_id = farmacia_id
            despesa.categoria = categoria
            despesa.descricao = descricao
            despesa.valor = float(valor or 0)
            despesa.data_despesa = datetime.strptime(data_despesa, "%Y-%m-%d").date()
            despesa.forma_pagamento = forma_pagamento
            despesa.observacao = observacao

            db.session.commit()
            flash("Despesa atualizada com sucesso.", "success")
            return redirect(url_for("despesas.listar_despesas"))

        return render_template("despesa_form.html", farmacias=farmacias, despesa=despesa, tipo_edicao="normal")

    elif tipo == "fixa":
        despesa = DespesaFixa.query.get_or_404(despesa_id)

        if not usuario_tem_acesso_farmacia(current_user, despesa.farmacia_id):
            flash("Você não tem acesso a essa despesa fixa.", "danger")
            return redirect(url_for("despesas.listar_despesas"))

        if request.method == "POST":
            farmacia_id = request.form.get("farmacia_id", type=int)
            categoria = request.form.get("categoria", "").strip()
            descricao = request.form.get("descricao", "").strip()
            valor = request.form.get("valor", "0").replace(",", ".")
            dia_vencimento = request.form.get("dia_vencimento", type=int)
            tipo_valor = request.form.get("tipo_valor", "").strip()
            ativa = request.form.get("ativa") == "1"
            observacao = request.form.get("observacao", "").strip()

            if not farmacia_id or not categoria or not descricao or not dia_vencimento or not tipo_valor:
                flash("Preencha os campos obrigatórios.", "danger")
                return render_template("despesa_form.html", farmacias=farmacias, despesa=despesa, tipo_edicao="fixa")

            despesa.farmacia_id = farmacia_id
            despesa.categoria = categoria
            despesa.nome = descricao
            despesa.valor_padrao = float(valor or 0)
            despesa.dia_vencimento = dia_vencimento
            despesa.tipo_valor = tipo_valor
            despesa.ativa = ativa
            despesa.observacao = observacao

            db.session.commit()
            flash("Despesa fixa atualizada com sucesso.", "success")
            return redirect(url_for("despesas.listar_despesas"))

        return render_template("despesa_form.html", farmacias=farmacias, despesa=despesa, tipo_edicao="fixa")

    flash("Tipo inválido.", "danger")
    return redirect(url_for("despesas.listar_despesas"))


@despesas_bp.route("/excluir/<string:tipo>/<int:despesa_id>", methods=["POST"])
@login_required
def excluir_despesa(tipo, despesa_id):
    if tipo == "normal":
        despesa = Despesa.query.get_or_404(despesa_id)

        if not usuario_tem_acesso_farmacia(current_user, despesa.farmacia_id):
            flash("Você não tem acesso a essa despesa.", "danger")
            return redirect(url_for("despesas.listar_despesas"))

        db.session.delete(despesa)
        db.session.commit()
        flash("Despesa excluída com sucesso.", "success")
        return redirect(url_for("despesas.listar_despesas"))

    elif tipo == "fixa":
        despesa = DespesaFixa.query.get_or_404(despesa_id)

        if not usuario_tem_acesso_farmacia(current_user, despesa.farmacia_id):
            flash("Você não tem acesso a essa despesa fixa.", "danger")
            return redirect(url_for("despesas.listar_despesas"))

        db.session.delete(despesa)
        db.session.commit()
        flash("Despesa fixa excluída com sucesso.", "success")
        return redirect(url_for("despesas.listar_despesas"))

    flash("Tipo inválido.", "danger")
    return redirect(url_for("despesas.listar_despesas"))