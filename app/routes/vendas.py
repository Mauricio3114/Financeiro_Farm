from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Farmacia, UsuarioFarmacia, VendaDiaria

vendas_bp = Blueprint("vendas", __name__, url_prefix="/vendas")


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


@vendas_bp.route("/")
@login_required
def listar_vendas():
    farmacias = farmacias_do_usuario(current_user)
    farmacia_ids = [f.id for f in farmacias]

    filtro_farmacia_id = request.args.get("farmacia_id", type=int)

    vendas = []
    if farmacia_ids:
        query = VendaDiaria.query.filter(VendaDiaria.farmacia_id.in_(farmacia_ids))
        if filtro_farmacia_id:
            query = query.filter(VendaDiaria.farmacia_id == filtro_farmacia_id)
        vendas = query.order_by(VendaDiaria.data_venda.desc()).all()

    return render_template(
        "vendas.html",
        vendas=vendas,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id
    )


@vendas_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova_venda():
    farmacias = farmacias_do_usuario(current_user)

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        data_venda = request.form.get("data_venda")
        valor_vista = request.form.get("valor_vista", "0").replace(",", ".")
        valor_vulcabras = request.form.get("valor_vulcabras", "0").replace(",", ".")
        valor_debito = request.form.get("valor_debito", "0").replace(",", ".")
        valor_credito = request.form.get("valor_credito", "0").replace(",", ".")
        valor_pix = request.form.get("valor_pix", "0").replace(",", ".")
        observacao = request.form.get("observacao", "").strip()

        if not farmacia_id or not data_venda:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("venda_form.html", farmacias=farmacias, venda=None)

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("vendas.listar_vendas"))

        venda = VendaDiaria(
            farmacia_id=farmacia_id,
            data_venda=datetime.strptime(data_venda, "%Y-%m-%d").date(),
            valor_vista=float(valor_vista or 0),
            valor_vulcabras=float(valor_vulcabras or 0),
            valor_debito=float(valor_debito or 0),
            valor_credito=float(valor_credito or 0),
            valor_pix=float(valor_pix or 0),
            observacao=observacao
        )
        venda.calcular_total()

        db.session.add(venda)
        db.session.commit()

        flash("Venda do dia cadastrada com sucesso.", "success")
        return redirect(url_for("vendas.listar_vendas"))

    return render_template("venda_form.html", farmacias=farmacias, venda=None)


@vendas_bp.route("/editar/<int:venda_id>", methods=["GET", "POST"])
@login_required
def editar_venda(venda_id):
    venda = VendaDiaria.query.get_or_404(venda_id)
    farmacias = farmacias_do_usuario(current_user)

    if not usuario_tem_acesso_farmacia(current_user, venda.farmacia_id):
        flash("Você não tem acesso a essa venda.", "danger")
        return redirect(url_for("vendas.listar_vendas"))

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        data_venda = request.form.get("data_venda")
        valor_vista = request.form.get("valor_vista", "0").replace(",", ".")
        valor_vulcabras = request.form.get("valor_vulcabras", "0").replace(",", ".")
        valor_debito = request.form.get("valor_debito", "0").replace(",", ".")
        valor_credito = request.form.get("valor_credito", "0").replace(",", ".")
        valor_pix = request.form.get("valor_pix", "0").replace(",", ".")
        observacao = request.form.get("observacao", "").strip()

        if not farmacia_id or not data_venda:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("venda_form.html", farmacias=farmacias, venda=venda)

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("vendas.listar_vendas"))

        venda.farmacia_id = farmacia_id
        venda.data_venda = datetime.strptime(data_venda, "%Y-%m-%d").date()
        venda.valor_vista = float(valor_vista or 0)
        venda.valor_vulcabras = float(valor_vulcabras or 0)
        venda.valor_debito = float(valor_debito or 0)
        venda.valor_credito = float(valor_credito or 0)
        venda.valor_pix = float(valor_pix or 0)
        venda.observacao = observacao
        venda.calcular_total()

        db.session.commit()

        flash("Venda atualizada com sucesso.", "success")
        return redirect(url_for("vendas.listar_vendas"))

    return render_template("venda_form.html", farmacias=farmacias, venda=venda)


@vendas_bp.route("/excluir/<int:venda_id>", methods=["POST"])
@login_required
def excluir_venda(venda_id):
    venda = VendaDiaria.query.get_or_404(venda_id)

    if not usuario_tem_acesso_farmacia(current_user, venda.farmacia_id):
        flash("Você não tem acesso a essa venda.", "danger")
        return redirect(url_for("vendas.listar_vendas"))

    db.session.delete(venda)
    db.session.commit()

    flash("Venda excluída com sucesso.", "success")
    return redirect(url_for("vendas.listar_vendas"))