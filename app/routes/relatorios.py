from io import BytesIO
from datetime import datetime
from flask import Blueprint, request, send_file, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl import Workbook

from app.models import (
    Farmacia,
    UsuarioFarmacia,
    Boleto,
    Despesa,
    VendaDiaria,
    DespesaMoto,
    ContaReceber,
    DespesaFixaLancamento,
)

relatorios_bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")


def farmacias_do_usuario(usuario):
    if usuario.is_admin():
        return Farmacia.query.order_by(Farmacia.nome_fantasia.asc()).all()

    vinculacoes = UsuarioFarmacia.query.filter_by(usuario_id=usuario.id).all()
    ids = [v.farmacia_id for v in vinculacoes]

    if not ids:
        return []

    return Farmacia.query.filter(Farmacia.id.in_(ids)).order_by(Farmacia.nome_fantasia.asc()).all()


def parse_date(value):
    try:
        if value:
            return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
    return None


def get_filtro_ids():
    farmacias = farmacias_do_usuario(current_user)
    farmacia_ids = [f.id for f in farmacias]
    filtro_farmacia_id = request.args.get("farmacia_id", type=int)

    if filtro_farmacia_id and filtro_farmacia_id in farmacia_ids:
        farmacia_ids = [filtro_farmacia_id]

    return farmacia_ids


def get_farmacias_e_filtro():
    farmacias = farmacias_do_usuario(current_user)
    filtro_farmacia_id = request.args.get("farmacia_id", type=int)
    return farmacias, filtro_farmacia_id


def formatar_periodo(data_inicio, data_fim):
    return f"Período: {data_inicio.strftime('%d/%m/%Y') if data_inicio else 'Início'} até {data_fim.strftime('%d/%m/%Y') if data_fim else 'Hoje'}"


def aplicar_filtro_periodo_lista(lista, campo_data, data_inicio=None, data_fim=None):
    resultado = lista

    if data_inicio:
        resultado = [item for item in resultado if getattr(item, campo_data) and getattr(item, campo_data) >= data_inicio]

    if data_fim:
        resultado = [item for item in resultado if getattr(item, campo_data) and getattr(item, campo_data) <= data_fim]

    return resultado


def build_pdf_resumo(titulo, periodo, resumo, nome_arquivo):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=25,
        rightMargin=25,
        topMargin=25,
        bottomMargin=25
    )

    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph(titulo, styles["Title"]))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(periodo, styles["Normal"]))
    elementos.append(Spacer(1, 12))

    tabela = Table(resumo, colWidths=[320, 220])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ]))

    elementos.append(tabela)
    doc.build(elementos)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=nome_arquivo,
        mimetype="application/pdf"
    )


@relatorios_bp.route("/financeiro-pdf")
@login_required
def relatorio_financeiro_pdf():
    farmacia_ids = get_filtro_ids()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada para gerar relatório.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    boletos_query = Boleto.query.filter(Boleto.farmacia_id.in_(farmacia_ids))
    despesas_query = Despesa.query.filter(Despesa.farmacia_id.in_(farmacia_ids))
    vendas_query = VendaDiaria.query.filter(VendaDiaria.farmacia_id.in_(farmacia_ids))
    despesas_motos_query = DespesaMoto.query.filter(DespesaMoto.farmacia_id.in_(farmacia_ids))

    if data_inicio:
        boletos_query = boletos_query.filter(Boleto.data_vencimento >= data_inicio)
        despesas_query = despesas_query.filter(Despesa.data_despesa >= data_inicio)
        vendas_query = vendas_query.filter(VendaDiaria.data_venda >= data_inicio)
        despesas_motos_query = despesas_motos_query.filter(DespesaMoto.data_despesa >= data_inicio)

    if data_fim:
        boletos_query = boletos_query.filter(Boleto.data_vencimento <= data_fim)
        despesas_query = despesas_query.filter(Despesa.data_despesa <= data_fim)
        vendas_query = vendas_query.filter(VendaDiaria.data_venda <= data_fim)
        despesas_motos_query = despesas_motos_query.filter(DespesaMoto.data_despesa <= data_fim)

    boletos = boletos_query.all()
    despesas = despesas_query.all()
    vendas = vendas_query.all()
    despesas_motos = despesas_motos_query.all()

    for boleto in boletos:
        boleto.preparar()

    total_boletos_pagos = sum((b.valor_pago or 0) for b in boletos if b.status == "pago")
    total_boletos_abertos = sum((b.valor_total or 0) for b in boletos if b.status in ["a_vencer", "vencido"])
    total_despesas = sum(d.valor for d in despesas)
    total_despesas_motos = sum(d.valor for d in despesas_motos)
    total_vendas = sum(v.total_dia for v in vendas)
    resultado = total_vendas - (total_despesas + total_despesas_motos)

    periodo = formatar_periodo(data_inicio, data_fim)

    resumo = [
        ["Indicador", "Valor"],
        ["Total de Boletos Pagos", f"R$ {total_boletos_pagos:,.2f}"],
        ["Total de Boletos em Aberto", f"R$ {total_boletos_abertos:,.2f}"],
        ["Total de Despesas Gerais", f"R$ {total_despesas:,.2f}"],
        ["Total de Despesas das Motos", f"R$ {total_despesas_motos:,.2f}"],
        ["Total de Vendas", f"R$ {total_vendas:,.2f}"],
        ["Resultado Financeiro", f"R$ {resultado:,.2f}"],
    ]

    return build_pdf_resumo(
        "Relatório Financeiro - Financeiro Farm",
        periodo,
        resumo,
        "relatorio_financeiro.pdf"
    )


@relatorios_bp.route("/financeiro-excel")
@login_required
def relatorio_financeiro_excel():
    farmacia_ids = get_filtro_ids()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada para gerar relatório.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    boletos_query = Boleto.query.filter(Boleto.farmacia_id.in_(farmacia_ids))
    despesas_query = Despesa.query.filter(Despesa.farmacia_id.in_(farmacia_ids))
    vendas_query = VendaDiaria.query.filter(VendaDiaria.farmacia_id.in_(farmacia_ids))
    despesas_motos_query = DespesaMoto.query.filter(DespesaMoto.farmacia_id.in_(farmacia_ids))

    if data_inicio:
        boletos_query = boletos_query.filter(Boleto.data_vencimento >= data_inicio)
        despesas_query = despesas_query.filter(Despesa.data_despesa >= data_inicio)
        vendas_query = vendas_query.filter(VendaDiaria.data_venda >= data_inicio)
        despesas_motos_query = despesas_motos_query.filter(DespesaMoto.data_despesa >= data_inicio)

    if data_fim:
        boletos_query = boletos_query.filter(Boleto.data_vencimento <= data_fim)
        despesas_query = despesas_query.filter(Despesa.data_despesa <= data_fim)
        vendas_query = vendas_query.filter(VendaDiaria.data_venda <= data_fim)
        despesas_motos_query = despesas_motos_query.filter(DespesaMoto.data_despesa <= data_fim)

    boletos = boletos_query.all()
    despesas = despesas_query.all()
    vendas = vendas_query.all()
    despesas_motos = despesas_motos_query.all()

    for boleto in boletos:
        boleto.preparar()

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo Financeiro"

    ws.append(["Indicador", "Valor"])
    ws.append(["Boletos Pagos", sum((b.valor_pago or 0) for b in boletos if b.status == "pago")])
    ws.append(["Boletos em Aberto", sum((b.valor_total or 0) for b in boletos if b.status in ["a_vencer", "vencido"])])
    ws.append(["Despesas Gerais", sum(d.valor for d in despesas)])
    ws.append(["Despesas das Motos", sum(d.valor for d in despesas_motos)])
    ws.append(["Vendas", sum(v.total_dia for v in vendas)])
    ws.append(["Resultado", sum(v.total_dia for v in vendas) - (sum(d.valor for d in despesas) + sum(d.valor for d in despesas_motos))])

    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 20

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="relatorio_financeiro.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@relatorios_bp.route("/financeiro-completo")
@login_required
def relatorio_financeiro_completo():
    farmacia_ids = get_filtro_ids()
    farmacias, filtro_farmacia_id = get_farmacias_e_filtro()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    boletos = Boleto.query.filter(Boleto.farmacia_id.in_(farmacia_ids)).all()
    despesas = Despesa.query.filter(Despesa.farmacia_id.in_(farmacia_ids)).all()
    vendas = VendaDiaria.query.filter(VendaDiaria.farmacia_id.in_(farmacia_ids)).all()
    despesas_motos = DespesaMoto.query.filter(DespesaMoto.farmacia_id.in_(farmacia_ids)).all()
    contas = ContaReceber.query.filter(ContaReceber.farmacia_id.in_(farmacia_ids)).all()
    despesas_fixas = DespesaFixaLancamento.query.filter(DespesaFixaLancamento.farmacia_id.in_(farmacia_ids)).all()

    boletos = aplicar_filtro_periodo_lista(boletos, "data_vencimento", data_inicio, data_fim)
    despesas = aplicar_filtro_periodo_lista(despesas, "data_despesa", data_inicio, data_fim)
    vendas = aplicar_filtro_periodo_lista(vendas, "data_venda", data_inicio, data_fim)
    despesas_motos = aplicar_filtro_periodo_lista(despesas_motos, "data_despesa", data_inicio, data_fim)
    contas = aplicar_filtro_periodo_lista(contas, "data_vencimento", data_inicio, data_fim)
    despesas_fixas = aplicar_filtro_periodo_lista(despesas_fixas, "data_vencimento", data_inicio, data_fim)

    for b in boletos:
        b.preparar()

    for c in contas:
        c.preparar()

    total_vendas = sum(v.total_dia for v in vendas)
    total_despesas = sum(d.valor for d in despesas)
    total_motos = sum(d.valor for d in despesas_motos)
    total_fixas = sum(d.valor for d in despesas_fixas)

    total_receber = sum(c.valor for c in contas if c.status != "recebido")
    total_recebido = sum((c.valor_recebido or c.valor) for c in contas if c.status == "recebido")

    total_boletos_aberto = sum((b.valor_total or 0) for b in boletos if b.status in ["a_vencer", "vencido"])
    total_boletos_pagos = sum((b.valor_pago or 0) for b in boletos if b.status == "pago")

    total_despesas_geral = total_despesas + total_motos + total_fixas
    lucro = total_vendas - total_despesas_geral

    return render_template(
        "relatorio_completo.html",
        vendas=total_vendas,
        despesas=total_despesas,
        motos=total_motos,
        fixas=total_fixas,
        receber=total_receber,
        recebido=total_recebido,
        boletos_aberto=total_boletos_aberto,
        boletos_pagos=total_boletos_pagos,
        lucro=lucro,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", "")
    )


@relatorios_bp.route("/financeiro-completo-pdf")
@login_required
def relatorio_financeiro_completo_pdf():
    farmacia_ids = get_filtro_ids()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    boletos = Boleto.query.filter(Boleto.farmacia_id.in_(farmacia_ids)).all()
    despesas = Despesa.query.filter(Despesa.farmacia_id.in_(farmacia_ids)).all()
    vendas = VendaDiaria.query.filter(VendaDiaria.farmacia_id.in_(farmacia_ids)).all()
    despesas_motos = DespesaMoto.query.filter(DespesaMoto.farmacia_id.in_(farmacia_ids)).all()
    contas = ContaReceber.query.filter(ContaReceber.farmacia_id.in_(farmacia_ids)).all()
    despesas_fixas = DespesaFixaLancamento.query.filter(DespesaFixaLancamento.farmacia_id.in_(farmacia_ids)).all()

    boletos = aplicar_filtro_periodo_lista(boletos, "data_vencimento", data_inicio, data_fim)
    despesas = aplicar_filtro_periodo_lista(despesas, "data_despesa", data_inicio, data_fim)
    vendas = aplicar_filtro_periodo_lista(vendas, "data_venda", data_inicio, data_fim)
    despesas_motos = aplicar_filtro_periodo_lista(despesas_motos, "data_despesa", data_inicio, data_fim)
    contas = aplicar_filtro_periodo_lista(contas, "data_vencimento", data_inicio, data_fim)
    despesas_fixas = aplicar_filtro_periodo_lista(despesas_fixas, "data_vencimento", data_inicio, data_fim)

    for b in boletos:
        b.preparar()

    for c in contas:
        c.preparar()

    total_vendas = sum(v.total_dia for v in vendas)
    total_despesas = sum(d.valor for d in despesas)
    total_motos = sum(d.valor for d in despesas_motos)
    total_fixas = sum(d.valor for d in despesas_fixas)
    total_receber = sum(c.valor for c in contas if c.status != "recebido")
    total_recebido = sum((c.valor_recebido or c.valor) for c in contas if c.status == "recebido")
    total_boletos_aberto = sum((b.valor_total or 0) for b in boletos if b.status in ["a_vencer", "vencido"])
    total_boletos_pagos = sum((b.valor_pago or 0) for b in boletos if b.status == "pago")
    total_despesas_geral = total_despesas + total_motos + total_fixas
    lucro = total_vendas - total_despesas_geral

    periodo = formatar_periodo(data_inicio, data_fim)

    resumo = [
        ["Indicador", "Valor"],
        ["Vendas", f"R$ {total_vendas:,.2f}"],
        ["Despesas Gerais", f"R$ {total_despesas:,.2f}"],
        ["Despesas das Motos", f"R$ {total_motos:,.2f}"],
        ["Despesas Fixas", f"R$ {total_fixas:,.2f}"],
        ["Boletos em Aberto", f"R$ {total_boletos_aberto:,.2f}"],
        ["Boletos Pagos", f"R$ {total_boletos_pagos:,.2f}"],
        ["A Receber", f"R$ {total_receber:,.2f}"],
        ["Recebido", f"R$ {total_recebido:,.2f}"],
        ["Resultado Final", f"R$ {lucro:,.2f}"],
    ]

    return build_pdf_resumo(
        "Relatório Financeiro Completo - Financeiro Farm",
        periodo,
        resumo,
        "relatorio_financeiro_completo.pdf"
    )


@relatorios_bp.route("/vendas")
@login_required
def relatorio_vendas():
    farmacia_ids = get_filtro_ids()
    farmacias, filtro_farmacia_id = get_farmacias_e_filtro()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    vendas = VendaDiaria.query.filter(VendaDiaria.farmacia_id.in_(farmacia_ids)).all()
    vendas = aplicar_filtro_periodo_lista(vendas, "data_venda", data_inicio, data_fim)

    total = sum(v.total_dia or 0 for v in vendas)

    return render_template(
        "relatorio_simples.html",
        titulo="Relatório de Vendas",
        subtitulo="Resumo de vendas do período",
        total=total,
        cor="blue",
        label_total="Total de Vendas",
        rota_pdf="relatorios.relatorio_vendas_pdf",
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", "")
    )


@relatorios_bp.route("/vendas-pdf")
@login_required
def relatorio_vendas_pdf():
    farmacia_ids = get_filtro_ids()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    vendas = VendaDiaria.query.filter(VendaDiaria.farmacia_id.in_(farmacia_ids)).all()
    vendas = aplicar_filtro_periodo_lista(vendas, "data_venda", data_inicio, data_fim)
    total = sum(v.total_dia or 0 for v in vendas)

    resumo = [
        ["Indicador", "Valor"],
        ["Total de Vendas", f"R$ {total:,.2f}"],
    ]

    return build_pdf_resumo(
        "Relatório de Vendas - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        resumo,
        "relatorio_vendas.pdf"
    )


@relatorios_bp.route("/despesas")
@login_required
def relatorio_despesas():
    farmacia_ids = get_filtro_ids()
    farmacias, filtro_farmacia_id = get_farmacias_e_filtro()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    despesas = Despesa.query.filter(Despesa.farmacia_id.in_(farmacia_ids)).all()
    despesas = aplicar_filtro_periodo_lista(despesas, "data_despesa", data_inicio, data_fim)

    total = sum(d.valor or 0 for d in despesas)

    return render_template(
        "relatorio_simples.html",
        titulo="Relatório de Despesas Gerais",
        subtitulo="Resumo de despesas gerais do período",
        total=total,
        cor="red",
        label_total="Total de Despesas Gerais",
        rota_pdf="relatorios.relatorio_despesas_pdf",
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", "")
    )


@relatorios_bp.route("/despesas-pdf")
@login_required
def relatorio_despesas_pdf():
    farmacia_ids = get_filtro_ids()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    despesas = Despesa.query.filter(Despesa.farmacia_id.in_(farmacia_ids)).all()
    despesas = aplicar_filtro_periodo_lista(despesas, "data_despesa", data_inicio, data_fim)
    total = sum(d.valor or 0 for d in despesas)

    resumo = [
        ["Indicador", "Valor"],
        ["Total de Despesas Gerais", f"R$ {total:,.2f}"],
    ]

    return build_pdf_resumo(
        "Relatório de Despesas Gerais - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        resumo,
        "relatorio_despesas_gerais.pdf"
    )


@relatorios_bp.route("/despesas-motos")
@login_required
def relatorio_despesas_motos():
    farmacia_ids = get_filtro_ids()
    farmacias, filtro_farmacia_id = get_farmacias_e_filtro()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    despesas_motos = DespesaMoto.query.filter(DespesaMoto.farmacia_id.in_(farmacia_ids)).all()
    despesas_motos = aplicar_filtro_periodo_lista(despesas_motos, "data_despesa", data_inicio, data_fim)

    total = sum(d.valor or 0 for d in despesas_motos)

    return render_template(
        "relatorio_simples.html",
        titulo="Relatório de Despesas das Motos",
        subtitulo="Resumo de despesas das motos do período",
        total=total,
        cor="orange",
        label_total="Total de Despesas das Motos",
        rota_pdf="relatorios.relatorio_despesas_motos_pdf",
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", "")
    )


@relatorios_bp.route("/despesas-motos-pdf")
@login_required
def relatorio_despesas_motos_pdf():
    farmacia_ids = get_filtro_ids()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    despesas_motos = DespesaMoto.query.filter(DespesaMoto.farmacia_id.in_(farmacia_ids)).all()
    despesas_motos = aplicar_filtro_periodo_lista(despesas_motos, "data_despesa", data_inicio, data_fim)
    total = sum(d.valor or 0 for d in despesas_motos)

    resumo = [
        ["Indicador", "Valor"],
        ["Total de Despesas das Motos", f"R$ {total:,.2f}"],
    ]

    return build_pdf_resumo(
        "Relatório de Despesas das Motos - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        resumo,
        "relatorio_despesas_motos.pdf"
    )


@relatorios_bp.route("/despesas-fixas")
@login_required
def relatorio_despesas_fixas():
    farmacia_ids = get_filtro_ids()
    farmacias, filtro_farmacia_id = get_farmacias_e_filtro()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    despesas_fixas = DespesaFixaLancamento.query.filter(DespesaFixaLancamento.farmacia_id.in_(farmacia_ids)).all()
    despesas_fixas = aplicar_filtro_periodo_lista(despesas_fixas, "data_vencimento", data_inicio, data_fim)

    total = sum(d.valor or 0 for d in despesas_fixas)

    return render_template(
        "relatorio_simples.html",
        titulo="Relatório de Despesas Fixas",
        subtitulo="Resumo de despesas fixas do período",
        total=total,
        cor="purple",
        label_total="Total de Despesas Fixas",
        rota_pdf="relatorios.relatorio_despesas_fixas_pdf",
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", "")
    )


@relatorios_bp.route("/despesas-fixas-pdf")
@login_required
def relatorio_despesas_fixas_pdf():
    farmacia_ids = get_filtro_ids()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    despesas_fixas = DespesaFixaLancamento.query.filter(DespesaFixaLancamento.farmacia_id.in_(farmacia_ids)).all()
    despesas_fixas = aplicar_filtro_periodo_lista(despesas_fixas, "data_vencimento", data_inicio, data_fim)
    total = sum(d.valor or 0 for d in despesas_fixas)

    resumo = [
        ["Indicador", "Valor"],
        ["Total de Despesas Fixas", f"R$ {total:,.2f}"],
    ]

    return build_pdf_resumo(
        "Relatório de Despesas Fixas - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        resumo,
        "relatorio_despesas_fixas.pdf"
    )


@relatorios_bp.route("/boletos-pagar")
@login_required
def relatorio_boletos_pagar():
    farmacia_ids = get_filtro_ids()
    farmacias, filtro_farmacia_id = get_farmacias_e_filtro()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    boletos = Boleto.query.filter(Boleto.farmacia_id.in_(farmacia_ids)).all()
    boletos = aplicar_filtro_periodo_lista(boletos, "data_vencimento", data_inicio, data_fim)

    for b in boletos:
        b.preparar()

    total = sum((b.valor_total or 0) for b in boletos if b.status in ["a_vencer", "vencido"])
    total_pagos = sum((b.valor_pago or 0) for b in boletos if b.status == "pago")

    return render_template(
        "relatorio_duplo.html",
        titulo="Relatório de Boletos a Pagar",
        subtitulo="Resumo de boletos a pagar do período",
        total_1=total,
        total_2=total_pagos,
        label_1="Boletos em Aberto",
        label_2="Boletos Pagos",
        cor_1="yellow",
        cor_2="green",
        rota_pdf="relatorios.relatorio_boletos_pagar_pdf",
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", "")
    )


@relatorios_bp.route("/boletos-pagar-pdf")
@login_required
def relatorio_boletos_pagar_pdf():
    farmacia_ids = get_filtro_ids()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    boletos = Boleto.query.filter(Boleto.farmacia_id.in_(farmacia_ids)).all()
    boletos = aplicar_filtro_periodo_lista(boletos, "data_vencimento", data_inicio, data_fim)

    for b in boletos:
        b.preparar()

    total_aberto = sum((b.valor_total or 0) for b in boletos if b.status in ["a_vencer", "vencido"])
    total_pagos = sum((b.valor_pago or 0) for b in boletos if b.status == "pago")

    resumo = [
        ["Indicador", "Valor"],
        ["Boletos em Aberto", f"R$ {total_aberto:,.2f}"],
        ["Boletos Pagos", f"R$ {total_pagos:,.2f}"],
    ]

    return build_pdf_resumo(
        "Relatório de Boletos a Pagar - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        resumo,
        "relatorio_boletos_pagar.pdf"
    )


@relatorios_bp.route("/boletos-receber")
@login_required
def relatorio_boletos_receber():
    farmacia_ids = get_filtro_ids()
    farmacias, filtro_farmacia_id = get_farmacias_e_filtro()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    contas = ContaReceber.query.filter(ContaReceber.farmacia_id.in_(farmacia_ids)).all()
    contas = aplicar_filtro_periodo_lista(contas, "data_vencimento", data_inicio, data_fim)

    for c in contas:
        c.preparar()

    total_receber = sum(c.valor or 0 for c in contas if c.status != "recebido")
    total_recebido = sum((c.valor_recebido or c.valor or 0) for c in contas if c.status == "recebido")

    return render_template(
        "relatorio_duplo.html",
        titulo="Relatório de Boletos a Receber",
        subtitulo="Resumo de boletos a receber do período",
        total_1=total_receber,
        total_2=total_recebido,
        label_1="A Receber",
        label_2="Recebido",
        cor_1="teal",
        cor_2="green",
        rota_pdf="relatorios.relatorio_boletos_receber_pdf",
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", "")
    )


@relatorios_bp.route("/boletos-receber-pdf")
@login_required
def relatorio_boletos_receber_pdf():
    farmacia_ids = get_filtro_ids()
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    contas = ContaReceber.query.filter(ContaReceber.farmacia_id.in_(farmacia_ids)).all()
    contas = aplicar_filtro_periodo_lista(contas, "data_vencimento", data_inicio, data_fim)

    for c in contas:
        c.preparar()

    total_receber = sum(c.valor or 0 for c in contas if c.status != "recebido")
    total_recebido = sum((c.valor_recebido or c.valor or 0) for c in contas if c.status == "recebido")

    resumo = [
        ["Indicador", "Valor"],
        ["A Receber", f"R$ {total_receber:,.2f}"],
        ["Recebido", f"R$ {total_recebido:,.2f}"],
    ]

    return build_pdf_resumo(
        "Relatório de Boletos a Receber - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        resumo,
        "relatorio_boletos_receber.pdf"
    )