from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Farmacia, UsuarioFarmacia, ContaReceber, MovimentoCaixa

contas_receber_bp = Blueprint("contas_receber", __name__, url_prefix="/contas-receber")


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


@contas_receber_bp.route("/")
@login_required
def listar_contas_receber():
    farmacias = farmacias_do_usuario(current_user)
    farmacia_ids = [f.id for f in farmacias]

    filtro_farmacia_id = request.args.get("farmacia_id", type=int)
    filtro_status = request.args.get("status", "").strip()

    contas = []

    if farmacia_ids:
        query = ContaReceber.query.filter(ContaReceber.farmacia_id.in_(farmacia_ids))

        if filtro_farmacia_id:
            query = query.filter(ContaReceber.farmacia_id == filtro_farmacia_id)

        contas = query.order_by(ContaReceber.data_vencimento.asc()).all()

        for conta in contas:
            conta.preparar()

        db.session.commit()

        if filtro_status:
            contas = [c for c in contas if c.status == filtro_status]

    return render_template(
        "contas_receber.html",
        contas=contas,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        filtro_status=filtro_status
    )


@contas_receber_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova_conta_receber():
    farmacias = farmacias_do_usuario(current_user)

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        cliente_nome = request.form.get("cliente_nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        valor = request.form.get("valor", "0").replace(",", ".")
        data_vencimento = request.form.get("data_vencimento")
        data_recebimento = request.form.get("data_recebimento")
        valor_recebido = request.form.get("valor_recebido", "").replace(",", ".").strip()
        observacao = request.form.get("observacao", "").strip()

        if not farmacia_id or not cliente_nome or not data_vencimento:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("conta_receber_form.html", farmacias=farmacias, conta=None)

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("contas_receber.listar_contas_receber"))

        conta = ContaReceber(
            farmacia_id=farmacia_id,
            cliente_nome=cliente_nome,
            descricao=descricao,
            valor=float(valor or 0),
            data_vencimento=datetime.strptime(data_vencimento, "%Y-%m-%d").date(),
            observacao=observacao
        )

        if data_recebimento:
            conta.data_recebimento = datetime.strptime(data_recebimento, "%Y-%m-%d").date()

        if valor_recebido:
            conta.valor_recebido = float(valor_recebido)

        conta.preparar()

        db.session.add(conta)
        db.session.flush()

        if conta.status == "recebido":
            db.session.add(
                MovimentoCaixa(
                    farmacia_id=conta.farmacia_id,
                    tipo="entrada",
                    categoria="Conta a Receber",
                    descricao=f"Recebimento: {conta.cliente_nome}",
                    valor=conta.valor_recebido if conta.valor_recebido is not None else conta.valor,
                    data_movimento=conta.data_recebimento,
                    origem="receber",
                    observacao=conta.descricao
                )
            )

        db.session.commit()

        flash("Conta a receber cadastrada com sucesso.", "success")
        return redirect(url_for("contas_receber.listar_contas_receber"))

    return render_template("conta_receber_form.html", farmacias=farmacias, conta=None)


@contas_receber_bp.route("/editar/<int:conta_id>", methods=["GET", "POST"])
@login_required
def editar_conta_receber(conta_id):
    conta = ContaReceber.query.get_or_404(conta_id)
    farmacias = farmacias_do_usuario(current_user)

    if not usuario_tem_acesso_farmacia(current_user, conta.farmacia_id):
        flash("Você não tem acesso a essa conta.", "danger")
        return redirect(url_for("contas_receber.listar_contas_receber"))

    if request.method == "POST":
        farmacia_id = request.form.get("farmacia_id", type=int)
        cliente_nome = request.form.get("cliente_nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        valor = request.form.get("valor", "0").replace(",", ".")
        data_vencimento = request.form.get("data_vencimento")
        data_recebimento = request.form.get("data_recebimento")
        valor_recebido = request.form.get("valor_recebido", "").replace(",", ".").strip()
        observacao = request.form.get("observacao", "").strip()

        if not farmacia_id or not cliente_nome or not data_vencimento:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("conta_receber_form.html", farmacias=farmacias, conta=conta)

        if not usuario_tem_acesso_farmacia(current_user, farmacia_id):
            flash("Você não tem acesso a essa farmácia.", "danger")
            return redirect(url_for("contas_receber.listar_contas_receber"))

        conta.farmacia_id = farmacia_id
        conta.cliente_nome = cliente_nome
        conta.descricao = descricao
        conta.valor = float(valor or 0)
        conta.data_vencimento = datetime.strptime(data_vencimento, "%Y-%m-%d").date()
        conta.data_recebimento = datetime.strptime(data_recebimento, "%Y-%m-%d").date() if data_recebimento else None
        conta.valor_recebido = float(valor_recebido) if valor_recebido else None
        conta.observacao = observacao
        conta.preparar()

        db.session.commit()

        flash("Conta a receber atualizada com sucesso.", "success")
        return redirect(url_for("contas_receber.listar_contas_receber"))

    return render_template("conta_receber_form.html", farmacias=farmacias, conta=conta)


@contas_receber_bp.route("/receber/<int:conta_id>", methods=["POST"])
@login_required
def receber_conta(conta_id):
    conta = ContaReceber.query.get_or_404(conta_id)

    if not usuario_tem_acesso_farmacia(current_user, conta.farmacia_id):
        flash("Você não tem acesso a essa conta.", "danger")
        return redirect(url_for("contas_receber.listar_contas_receber"))

    data_recebimento = request.form.get("data_recebimento")
    valor_recebido = request.form.get("valor_recebido", "").replace(",", ".").strip()

    if not data_recebimento:
        flash("Informe a data de recebimento.", "danger")
        return redirect(url_for("contas_receber.listar_contas_receber"))

    conta.data_recebimento = datetime.strptime(data_recebimento, "%Y-%m-%d").date()
    conta.valor_recebido = float(valor_recebido) if valor_recebido else conta.valor
    conta.preparar()

    db.session.add(
        MovimentoCaixa(
            farmacia_id=conta.farmacia_id,
            tipo="entrada",
            categoria="Conta a Receber",
            descricao=f"Recebimento: {conta.cliente_nome}",
            valor=conta.valor_recebido,
            data_movimento=conta.data_recebimento,
            origem="receber",
            observacao=conta.descricao
        )
    )

    db.session.commit()

    flash("Conta recebida com sucesso.", "success")
    return redirect(url_for("contas_receber.listar_contas_receber"))


@contas_receber_bp.route("/excluir/<int:conta_id>", methods=["POST"])
@login_required
def excluir_conta_receber(conta_id):
    conta = ContaReceber.query.get_or_404(conta_id)

    if not usuario_tem_acesso_farmacia(current_user, conta.farmacia_id):
        flash("Você não tem acesso a essa conta.", "danger")
        return redirect(url_for("contas_receber.listar_contas_receber"))

    db.session.delete(conta)
    db.session.commit()

    flash("Conta a receber excluída com sucesso.", "success")
    return redirect(url_for("contas_receber.listar_contas_receber"))