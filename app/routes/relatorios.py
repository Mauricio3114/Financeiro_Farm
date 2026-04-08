from io import BytesIO
from datetime import datetime
from flask import Blueprint, request, send_file, flash, redirect, url_for
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

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=25, rightMargin=25, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("Relatório Financeiro - Financeiro Farm", styles["Title"]))
    elementos.append(Spacer(1, 12))

    periodo = f"Período: {data_inicio.strftime('%d/%m/%Y') if data_inicio else 'Início'} até {data_fim.strftime('%d/%m/%Y') if data_fim else 'Hoje'}"
    elementos.append(Paragraph(periodo, styles["Normal"]))
    elementos.append(Spacer(1, 12))

    resumo = [
        ["Indicador", "Valor"],
        ["Total de Boletos Pagos", f"R$ {total_boletos_pagos:,.2f}"],
        ["Total de Boletos em Aberto", f"R$ {total_boletos_abertos:,.2f}"],
        ["Total de Despesas Gerais", f"R$ {total_despesas:,.2f}"],
        ["Total de Despesas das Motos", f"R$ {total_despesas_motos:,.2f}"],
        ["Total de Vendas", f"R$ {total_vendas:,.2f}"],
        ["Resultado Financeiro", f"R$ {resultado:,.2f}"],
    ]

    tabela = Table(resumo, colWidths=[300, 220])
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
        download_name="relatorio_financeiro.pdf",
        mimetype="application/pdf"
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