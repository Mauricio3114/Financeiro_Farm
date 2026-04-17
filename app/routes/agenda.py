from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models import AgendaEvento

agenda_bp = Blueprint("agenda", __name__, url_prefix="/agenda")


@agenda_bp.route("/")
@login_required
def listar_agenda():
    filtro_status = request.args.get("status", "").strip()

    query = AgendaEvento.query

    if filtro_status:
        query = query.filter(AgendaEvento.status == filtro_status)

    eventos = query.order_by(AgendaEvento.data_evento.asc()).all()
    eventos = sorted(eventos, key=lambda e: (e.data_exibicao(), e.hora_evento or ""))

    return render_template(
        "agenda.html",
        eventos=eventos,
        filtro_status=filtro_status
    )


@agenda_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo_evento():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        tipo = request.form.get("tipo", "").strip()
        prioridade = request.form.get("prioridade", "").strip()
        repeticao = request.form.get("repeticao", "").strip()
        data_evento = request.form.get("data_evento")
        hora_evento = request.form.get("hora_evento", "").strip()
        status = request.form.get("status", "").strip()
        observacao = request.form.get("observacao", "").strip()

        if not titulo or not tipo or not prioridade or not repeticao or not data_evento or not status:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("agenda_form.html", evento=None)

        evento = AgendaEvento(
            titulo=titulo,
            descricao=descricao,
            tipo=tipo,
            prioridade=prioridade,
            repeticao=repeticao,
            data_evento=datetime.strptime(data_evento, "%Y-%m-%d").date(),
            hora_evento=hora_evento or None,
            status=status,
            observacao=observacao
        )

        db.session.add(evento)
        db.session.commit()

        flash("Evento da agenda cadastrado com sucesso.", "success")
        return redirect(url_for("agenda.listar_agenda"))

    return render_template("agenda_form.html", evento=None)


@agenda_bp.route("/editar/<int:evento_id>", methods=["GET", "POST"])
@login_required
def editar_evento(evento_id):
    evento = AgendaEvento.query.get_or_404(evento_id)

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        tipo = request.form.get("tipo", "").strip()
        prioridade = request.form.get("prioridade", "").strip()
        repeticao = request.form.get("repeticao", "").strip()
        data_evento = request.form.get("data_evento")
        hora_evento = request.form.get("hora_evento", "").strip()
        status = request.form.get("status", "").strip()
        observacao = request.form.get("observacao", "").strip()

        if not titulo or not tipo or not prioridade or not repeticao or not data_evento or not status:
            flash("Preencha os campos obrigatórios.", "danger")
            return render_template("agenda_form.html", evento=evento)

        evento.titulo = titulo
        evento.descricao = descricao
        evento.tipo = tipo
        evento.prioridade = prioridade
        evento.repeticao = repeticao
        evento.data_evento = datetime.strptime(data_evento, "%Y-%m-%d").date()
        evento.hora_evento = hora_evento or None
        evento.status = status
        evento.observacao = observacao

        db.session.commit()

        flash("Evento atualizado com sucesso.", "success")
        return redirect(url_for("agenda.listar_agenda"))

    return render_template("agenda_form.html", evento=evento)


@agenda_bp.route("/concluir/<int:evento_id>", methods=["POST"])
@login_required
def concluir_evento(evento_id):
    evento = AgendaEvento.query.get_or_404(evento_id)

    evento.status = "concluido"
    db.session.commit()

    flash("Evento concluído com sucesso.", "success")
    return redirect(url_for("agenda.listar_agenda"))


@agenda_bp.route("/reabrir/<int:evento_id>", methods=["POST"])
@login_required
def reabrir_evento(evento_id):
    evento = AgendaEvento.query.get_or_404(evento_id)

    evento.status = "pendente"
    db.session.commit()

    flash("Evento reaberto com sucesso.", "success")
    return redirect(url_for("agenda.listar_agenda"))


@agenda_bp.route("/excluir/<int:evento_id>", methods=["POST"])
@login_required
def excluir_evento(evento_id):
    evento = AgendaEvento.query.get_or_404(evento_id)

    db.session.delete(evento)
    db.session.commit()

    flash("Evento excluído com sucesso.", "success")
    return redirect(url_for("agenda.listar_agenda"))