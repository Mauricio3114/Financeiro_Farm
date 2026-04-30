from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import (
    Farmacia,
    Usuario,
    UsuarioFarmacia,
    Boleto,
    Despesa,
    VendaDiaria,
    Entregador,
    Moto,
    DespesaMoto,
    ContaReceber,
    MovimentoCaixa,
    DespesaFixaLancamento,
)

farmacias_bp = Blueprint("farmacias", __name__, url_prefix="/farmacias")


def admin_required():
    return current_user.is_authenticated and current_user.is_admin()


@farmacias_bp.route("/")
@login_required
def listar_farmacias():
    if current_user.is_admin():
        farmacias = Farmacia.query.order_by(Farmacia.nome_fantasia.asc()).all()
    else:
        vinculacoes = UsuarioFarmacia.query.filter_by(usuario_id=current_user.id).all()
        ids = [v.farmacia_id for v in vinculacoes]
        farmacias = Farmacia.query.filter(Farmacia.id.in_(ids)).order_by(Farmacia.nome_fantasia.asc()).all() if ids else []

    return render_template("farmacias.html", farmacias=farmacias)


@farmacias_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova_farmacia():
    if not admin_required():
        flash("Apenas admin pode cadastrar farmácias.", "danger")
        return redirect(url_for("farmacias.listar_farmacias"))

    usuarios = Usuario.query.filter_by(ativo=True).order_by(Usuario.nome.asc()).all()

    if request.method == "POST":
        nome_fantasia = request.form.get("nome_fantasia", "").strip()
        razao_social = request.form.get("razao_social", "").strip()
        cnpj = request.form.get("cnpj", "").strip()
        telefone = request.form.get("telefone", "").strip()
        email = request.form.get("email", "").strip()
        endereco = request.form.get("endereco", "").strip()
        responsavel = request.form.get("responsavel", "").strip()
        usuario_ids = request.form.getlist("usuarios")

        if not nome_fantasia:
            flash("Informe o nome fantasia.", "danger")
            return render_template("farmacia_form.html", usuarios=usuarios, farmacia=None, vinculados=[])

        farmacia = Farmacia(
            nome_fantasia=nome_fantasia,
            razao_social=razao_social,
            cnpj=cnpj,
            telefone=telefone,
            email=email,
            endereco=endereco,
            responsavel=responsavel,
            ativo=True
        )
        db.session.add(farmacia)
        db.session.flush()

        for usuario_id in usuario_ids:
            db.session.add(
                UsuarioFarmacia(usuario_id=int(usuario_id), farmacia_id=farmacia.id)
            )

        db.session.commit()
        flash("Farmácia cadastrada com sucesso.", "success")
        return redirect(url_for("farmacias.listar_farmacias"))

    return render_template("farmacia_form.html", usuarios=usuarios, farmacia=None, vinculados=[])


@farmacias_bp.route("/editar/<int:farmacia_id>", methods=["GET", "POST"])
@login_required
def editar_farmacia(farmacia_id):
    if not admin_required():
        flash("Apenas admin pode editar farmácias.", "danger")
        return redirect(url_for("farmacias.listar_farmacias"))

    farmacia = Farmacia.query.get_or_404(farmacia_id)
    usuarios = Usuario.query.filter_by(ativo=True).order_by(Usuario.nome.asc()).all()
    vinculados = [v.usuario_id for v in farmacia.vinculacoes]

    if request.method == "POST":
        farmacia.nome_fantasia = request.form.get("nome_fantasia", "").strip()
        farmacia.razao_social = request.form.get("razao_social", "").strip()
        farmacia.cnpj = request.form.get("cnpj", "").strip()
        farmacia.telefone = request.form.get("telefone", "").strip()
        farmacia.email = request.form.get("email", "").strip()
        farmacia.endereco = request.form.get("endereco", "").strip()
        farmacia.responsavel = request.form.get("responsavel", "").strip()
        farmacia.ativo = request.form.get("ativo") == "1"

        usuario_ids = [int(uid) for uid in request.form.getlist("usuarios")]

        UsuarioFarmacia.query.filter_by(farmacia_id=farmacia.id).delete()

        for usuario_id in usuario_ids:
            db.session.add(
                UsuarioFarmacia(usuario_id=usuario_id, farmacia_id=farmacia.id)
            )

        db.session.commit()
        flash("Farmácia atualizada com sucesso.", "success")
        return redirect(url_for("farmacias.listar_farmacias"))

    return render_template(
        "farmacia_form.html",
        usuarios=usuarios,
        farmacia=farmacia,
        vinculados=vinculados
    )


@farmacias_bp.route("/deletar/<int:farmacia_id>", methods=["POST"])
@login_required
def deletar_farmacia(farmacia_id):
    if not admin_required():
        flash("Apenas admin pode deletar farmácias.", "danger")
        return redirect(url_for("farmacias.listar_farmacias"))

    farmacia = Farmacia.query.get_or_404(farmacia_id)

    try:
        UsuarioFarmacia.query.filter_by(farmacia_id=farmacia.id).delete()
        DespesaMoto.query.filter_by(farmacia_id=farmacia.id).delete()
        MovimentoCaixa.query.filter_by(farmacia_id=farmacia.id).delete()
        ContaReceber.query.filter_by(farmacia_id=farmacia.id).delete()
        DespesaFixaLancamento.query.filter_by(farmacia_id=farmacia.id).delete()
        Boleto.query.filter_by(farmacia_id=farmacia.id).delete()
        Despesa.query.filter_by(farmacia_id=farmacia.id).delete()
        VendaDiaria.query.filter_by(farmacia_id=farmacia.id).delete()
        Entregador.query.filter_by(farmacia_id=farmacia.id).delete()
        Moto.query.filter_by(farmacia_id=farmacia.id).delete()

        db.session.delete(farmacia)
        db.session.commit()

        flash("Farmácia e todos os dados vinculados foram deletados com sucesso.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao deletar farmácia: {str(e)}", "danger")

    return redirect(url_for("farmacias.listar_farmacias"))