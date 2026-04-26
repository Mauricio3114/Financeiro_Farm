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


def moeda(valor):
    return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def texto_data(valor):
    return valor.strftime("%d/%m/%Y") if valor else "-"


def build_pdf_detalhado(titulo, periodo, secoes, nome_arquivo):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=20,
        rightMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph(titulo, styles["Title"]))
    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph(periodo, styles["Normal"]))
    elementos.append(Spacer(1, 16))

    for secao in secoes:
        elementos.append(Paragraph(secao["titulo"], styles["Heading2"]))
        elementos.append(Spacer(1, 8))

        tabela_dados = [secao["cabecalho"]] + secao["linhas"]

        tabela = Table(tabela_dados, repeatRows=1)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))

        elementos.append(tabela)
        elementos.append(Spacer(1, 8))

        if secao.get("resumo"):
            resumo_tabela = Table(
                [["Resumo", "Valor"]] + secao["resumo"],
                colWidths=[220, 140]
            )
            resumo_tabela.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]))
            elementos.append(resumo_tabela)

        elementos.append(Spacer(1, 18))

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

    boletos = Boleto.query.filter(Boleto.farmacia_id.in_(farmacia_ids)).all()
    despesas = Despesa.query.filter(Despesa.farmacia_id.in_(farmacia_ids)).all()
    vendas = VendaDiaria.query.filter(VendaDiaria.farmacia_id.in_(farmacia_ids)).all()
    despesas_motos = DespesaMoto.query.filter(DespesaMoto.farmacia_id.in_(farmacia_ids)).all()

    boletos = aplicar_filtro_periodo_lista(boletos, "data_vencimento", data_inicio, data_fim)
    despesas = aplicar_filtro_periodo_lista(despesas, "data_despesa", data_inicio, data_fim)
    vendas = aplicar_filtro_periodo_lista(vendas, "data_venda", data_inicio, data_fim)
    despesas_motos = aplicar_filtro_periodo_lista(despesas_motos, "data_despesa", data_inicio, data_fim)

    for boleto in boletos:
        boleto.preparar()

    total_boletos_pagos = sum((b.valor_pago or 0) for b in boletos if b.status == "pago")
    total_boletos_abertos = sum((b.valor_total or 0) for b in boletos if b.status in ["a_vencer", "vencido"])
    total_despesas = sum(d.valor or 0 for d in despesas)
    total_despesas_motos = sum(d.valor or 0 for d in despesas_motos)
    total_vendas = sum(v.total_dia or 0 for v in vendas)
    resultado = total_vendas - (total_despesas + total_despesas_motos)

    linhas = [
        ["Boletos Pagos", moeda(total_boletos_pagos)],
        ["Boletos em Aberto", moeda(total_boletos_abertos)],
        ["Despesas Gerais", moeda(total_despesas)],
        ["Despesas das Motos", moeda(total_despesas_motos)],
        ["Vendas", moeda(total_vendas)],
        ["Resultado Financeiro", moeda(resultado)],
    ]

    return build_pdf_detalhado(
        "Relatório Financeiro - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        [{
            "titulo": "Resumo Geral",
            "cabecalho": ["Indicador", "Valor"],
            "linhas": linhas,
            "resumo": []
        }],
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

    boletos = Boleto.query.filter(Boleto.farmacia_id.in_(farmacia_ids)).all()
    despesas = Despesa.query.filter(Despesa.farmacia_id.in_(farmacia_ids)).all()
    vendas = VendaDiaria.query.filter(VendaDiaria.farmacia_id.in_(farmacia_ids)).all()
    despesas_motos = DespesaMoto.query.filter(DespesaMoto.farmacia_id.in_(farmacia_ids)).all()

    boletos = aplicar_filtro_periodo_lista(boletos, "data_vencimento", data_inicio, data_fim)
    despesas = aplicar_filtro_periodo_lista(despesas, "data_despesa", data_inicio, data_fim)
    vendas = aplicar_filtro_periodo_lista(vendas, "data_venda", data_inicio, data_fim)
    despesas_motos = aplicar_filtro_periodo_lista(despesas_motos, "data_despesa", data_inicio, data_fim)

    for boleto in boletos:
        boleto.preparar()

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo Financeiro"

    ws.append(["Indicador", "Valor"])
    ws.append(["Boletos Pagos", sum((b.valor_pago or 0) for b in boletos if b.status == "pago")])
    ws.append(["Boletos em Aberto", sum((b.valor_total or 0) for b in boletos if b.status in ["a_vencer", "vencido"])])
    ws.append(["Despesas Gerais", sum(d.valor or 0 for d in despesas)])
    ws.append(["Despesas das Motos", sum(d.valor or 0 for d in despesas_motos)])
    ws.append(["Vendas", sum(v.total_dia or 0 for v in vendas)])
    ws.append([
        "Resultado",
        sum(v.total_dia or 0 for v in vendas) - (sum(d.valor or 0 for d in despesas) + sum(d.valor or 0 for d in despesas_motos))
    ])

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
    farmacias, filtro_farmacia_id = get_farmacias_e_filtro()

    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    farmacia_ids_selecionadas = request.args.getlist("farmacia_ids")

    if farmacia_ids_selecionadas:
        farmacia_ids = [int(fid) for fid in farmacia_ids_selecionadas if fid.isdigit()]
    else:
        farmacia_ids = get_filtro_ids()

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

    for d in despesas_fixas:
        d.preparar()

    total_vendas = sum(v.total_dia or 0 for v in vendas)
    total_despesas = sum(d.valor or 0 for d in despesas)
    total_motos = sum(d.valor or 0 for d in despesas_motos)
    total_fixas = sum(d.valor or 0 for d in despesas_fixas)
    total_receber = sum(c.valor or 0 for c in contas if c.status != "recebido")
    total_recebido = sum((c.valor_recebido or c.valor or 0) for c in contas if c.status == "recebido")
    total_boletos_aberto = sum((b.valor_total or 0) for b in boletos if b.status in ["a_vencer", "vencido"])
    total_boletos_pagos = sum((b.valor_pago or 0) for b in boletos if b.status == "pago")
    total_despesas_geral = total_despesas + total_motos + total_fixas
    lucro = total_vendas - total_despesas_geral

    detalhes_vendas = []
    for v in vendas:
        detalhes_vendas.append({
            "data": texto_data(v.data_venda),
            "farmacia": v.farmacia.nome_fantasia if v.farmacia else "-",
            "vista": moeda(v.valor_vista),
            "vulcabras": moeda(v.valor_vulcabras),
            "debito": moeda(v.valor_debito),
            "credito": moeda(v.valor_credito),
            "pix": moeda(v.valor_pix),
            "total": moeda(v.total_dia),
            "observacao": v.observacao or "-"
        })

    detalhes_despesas = []
    for d in despesas:
        detalhes_despesas.append({
            "data": texto_data(d.data_despesa),
            "farmacia": d.farmacia.nome_fantasia if d.farmacia else "-",
            "categoria": d.categoria,
            "centro_custo": d.centro_custo or "-",
            "descricao": d.descricao,
            "forma_pagamento": d.forma_pagamento or "-",
            "valor": moeda(d.valor),
            "observacao": d.observacao or "-"
        })

    detalhes_motos = []
    for d in despesas_motos:
        detalhes_motos.append({
            "data": texto_data(d.data_despesa),
            "farmacia": d.farmacia.nome_fantasia if d.farmacia else "-",
            "moto": d.moto.modelo if d.moto else "-",
            "entregador": d.entregador.nome if d.entregador else "-",
            "tipo_despesa": d.tipo_despesa,
            "descricao": d.descricao,
            "valor": moeda(d.valor),
            "observacao": d.observacao or "-"
        })

    detalhes_fixas = []
    for d in despesas_fixas:
        detalhes_fixas.append({
            "vencimento": texto_data(d.data_vencimento),
            "pagamento": texto_data(d.data_pagamento),
            "farmacia": d.farmacia.nome_fantasia if d.farmacia else "-",
            "nome": d.nome,
            "categoria": d.categoria,
            "centro_custo": d.centro_custo or "-",
            "status": d.status,
            "valor": moeda(d.valor),
            "observacao": d.observacao or "-"
        })

    detalhes_boletos = []
    for b in boletos:
        detalhes_boletos.append({
            "empresa": b.empresa_nome,
            "descricao": b.descricao or "-",
            "farmacia": b.farmacia.nome_fantasia if b.farmacia else "-",
            "vencimento": texto_data(b.data_vencimento),
            "pagamento": texto_data(b.data_pagamento),
            "valor_original": moeda(b.valor_original),
            "juros": moeda(b.juros),
            "valor_total": moeda(b.valor_total),
            "valor_pago": moeda(b.valor_pago),
            "status": b.status,
            "observacao": b.observacao or "-"
        })

    detalhes_receber = []
    for c in contas:
        detalhes_receber.append({
            "cliente": c.cliente_nome,
            "descricao": c.descricao or "-",
            "farmacia": c.farmacia.nome_fantasia if c.farmacia else "-",
            "vencimento": texto_data(c.data_vencimento),
            "recebimento": texto_data(c.data_recebimento),
            "valor": moeda(c.valor),
            "valor_recebido": moeda(c.valor_recebido),
            "status": c.status,
            "observacao": c.observacao or "-"
        })

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
        farmacia_ids_selecionadas=farmacia_ids,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", ""),
        detalhes_vendas=detalhes_vendas,
        detalhes_despesas=detalhes_despesas,
        detalhes_motos=detalhes_motos,
        detalhes_fixas=detalhes_fixas,
        detalhes_boletos=detalhes_boletos,
        detalhes_receber=detalhes_receber
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

    for d in despesas_fixas:
        d.preparar()

    total_vendas = sum(v.total_dia or 0 for v in vendas)
    total_despesas = sum(d.valor or 0 for d in despesas)
    total_motos = sum(d.valor or 0 for d in despesas_motos)
    total_fixas = sum(d.valor or 0 for d in despesas_fixas)
    total_receber = sum(c.valor or 0 for c in contas if c.status != "recebido")
    total_recebido = sum((c.valor_recebido or c.valor) for c in contas if c.status == "recebido")
    total_boletos_aberto = sum((b.valor_total or 0) for b in boletos if b.status in ["a_vencer", "vencido"])
    total_boletos_pagos = sum((b.valor_pago or 0) for b in boletos if b.status == "pago")
    lucro = total_vendas - (total_despesas + total_motos + total_fixas)

    secoes = [
        {
            "titulo": "Vendas",
            "cabecalho": ["Data", "Farmácia", "À Vista", "Vulcabras", "Débito", "Crédito", "Pix", "Total"],
            "linhas": [
                [
                    texto_data(v.data_venda),
                    v.farmacia.nome_fantasia if v.farmacia else "-",
                    moeda(v.valor_vista),
                    moeda(v.valor_vulcabras),
                    moeda(v.valor_debito),
                    moeda(v.valor_credito),
                    moeda(v.valor_pix),
                    moeda(v.total_dia),
                ]
                for v in vendas
            ] or [["-", "-", "-", "-", "-", "-", "-", "-"]],
            "resumo": [["Total de Vendas", moeda(total_vendas)]],
        },
        {
            "titulo": "Despesas Gerais",
            "cabecalho": ["Data", "Farmácia", "Categoria", "Centro Custo", "Descrição", "Forma Pgto", "Valor"],
            "linhas": [
                [
                    texto_data(d.data_despesa),
                    d.farmacia.nome_fantasia if d.farmacia else "-",
                    d.categoria,
                    d.centro_custo or "-",
                    d.descricao,
                    d.forma_pagamento or "-",
                    moeda(d.valor),
                ]
                for d in despesas
            ] or [["-", "-", "-", "-", "-", "-", "-"]],
            "resumo": [["Total de Despesas Gerais", moeda(total_despesas)]],
        },
        {
            "titulo": "Despesas das Motos",
            "cabecalho": ["Data", "Farmácia", "Moto", "Entregador", "Tipo", "Descrição", "Valor"],
            "linhas": [
                [
                    texto_data(d.data_despesa),
                    d.farmacia.nome_fantasia if d.farmacia else "-",
                    d.moto.modelo if d.moto else "-",
                    d.entregador.nome if d.entregador else "-",
                    d.tipo_despesa,
                    d.descricao,
                    moeda(d.valor),
                ]
                for d in despesas_motos
            ] or [["-", "-", "-", "-", "-", "-", "-"]],
            "resumo": [["Total de Despesas das Motos", moeda(total_motos)]],
        },
        {
            "titulo": "Despesas Fixas",
            "cabecalho": ["Vencimento", "Pagamento", "Farmácia", "Nome", "Categoria", "Status", "Valor"],
            "linhas": [
                [
                    texto_data(d.data_vencimento),
                    texto_data(d.data_pagamento),
                    d.farmacia.nome_fantasia if d.farmacia else "-",
                    d.nome,
                    d.categoria,
                    d.status,
                    moeda(d.valor),
                ]
                for d in despesas_fixas
            ] or [["-", "-", "-", "-", "-", "-", "-"]],
            "resumo": [["Total de Despesas Fixas", moeda(total_fixas)]],
        },
        {
            "titulo": "Boletos a Pagar",
            "cabecalho": ["Empresa", "Farmácia", "Vencimento", "Pagamento", "Original", "Juros", "Total", "Status"],
            "linhas": [
                [
                    b.empresa_nome,
                    b.farmacia.nome_fantasia if b.farmacia else "-",
                    texto_data(b.data_vencimento),
                    texto_data(b.data_pagamento),
                    moeda(b.valor_original),
                    moeda(b.juros),
                    moeda(b.valor_total),
                    b.status,
                ]
                for b in boletos
            ] or [["-", "-", "-", "-", "-", "-", "-", "-"]],
            "resumo": [
                ["Boletos em Aberto", moeda(total_boletos_aberto)],
                ["Boletos Pagos", moeda(total_boletos_pagos)],
            ],
        },
        {
            "titulo": "Boletos a Receber",
            "cabecalho": ["Cliente", "Farmácia", "Vencimento", "Recebimento", "Valor", "Valor Recebido", "Status"],
            "linhas": [
                [
                    c.cliente_nome,
                    c.farmacia.nome_fantasia if c.farmacia else "-",
                    texto_data(c.data_vencimento),
                    texto_data(c.data_recebimento),
                    moeda(c.valor),
                    moeda(c.valor_recebido),
                    c.status,
                ]
                for c in contas
            ] or [["-", "-", "-", "-", "-", "-", "-"]],
            "resumo": [
                ["A Receber", moeda(total_receber)],
                ["Recebido", moeda(total_recebido)],
            ],
        },
        {
            "titulo": "Resultado Final",
            "cabecalho": ["Indicador", "Valor"],
            "linhas": [
                ["Vendas", moeda(total_vendas)],
                ["Despesas Gerais", moeda(total_despesas)],
                ["Despesas das Motos", moeda(total_motos)],
                ["Despesas Fixas", moeda(total_fixas)],
                ["Boletos em Aberto", moeda(total_boletos_aberto)],
                ["Boletos Pagos", moeda(total_boletos_pagos)],
                ["A Receber", moeda(total_receber)],
                ["Recebido", moeda(total_recebido)],
                ["Lucro / Resultado Final", moeda(lucro)],
            ],
            "resumo": [],
        },
    ]

    return build_pdf_detalhado(
        "Relatório Financeiro Completo - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        secoes,
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

    detalhes = []
    for v in vendas:
        detalhes.append({
            "Data": texto_data(v.data_venda),
            "Farmácia": v.farmacia.nome_fantasia if v.farmacia else "-",
            "À Vista": moeda(v.valor_vista),
            "Vulcabras": moeda(v.valor_vulcabras),
            "Débito": moeda(v.valor_debito),
            "Crédito": moeda(v.valor_credito),
            "Pix": moeda(v.valor_pix),
            "Total": moeda(v.total_dia),
            "Observação": v.observacao or "-"
        })

    return render_template(
        "relatorio_simples.html",
        titulo="Relatório de Vendas",
        subtitulo="Resumo detalhado de vendas do período",
        total=total,
        cor="blue",
        label_total="Total de Vendas",
        rota_pdf="relatorios.relatorio_vendas_pdf",
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", ""),
        detalhes=detalhes
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

    secoes = [{
        "titulo": "Detalhamento de Vendas",
        "cabecalho": ["Data", "Farmácia", "À Vista", "Vulcabras", "Débito", "Crédito", "Pix", "Total"],
        "linhas": [
            [
                texto_data(v.data_venda),
                v.farmacia.nome_fantasia if v.farmacia else "-",
                moeda(v.valor_vista),
                moeda(v.valor_vulcabras),
                moeda(v.valor_debito),
                moeda(v.valor_credito),
                moeda(v.valor_pix),
                moeda(v.total_dia),
            ]
            for v in vendas
        ] or [["-", "-", "-", "-", "-", "-", "-", "-"]],
        "resumo": [["Total de Vendas", moeda(total)]],
    }]

    return build_pdf_detalhado(
        "Relatório de Vendas - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        secoes,
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

    detalhes = []
    for d in despesas:
        detalhes.append({
            "Data": texto_data(d.data_despesa),
            "Farmácia": d.farmacia.nome_fantasia if d.farmacia else "-",
            "Categoria": d.categoria,
            "Centro Custo": d.centro_custo or "-",
            "Descrição": d.descricao,
            "Forma Pgto": d.forma_pagamento or "-",
            "Valor": moeda(d.valor),
            "Observação": d.observacao or "-"
        })

    return render_template(
        "relatorio_simples.html",
        titulo="Relatório de Despesas Gerais",
        subtitulo="Resumo detalhado de despesas gerais do período",
        total=total,
        cor="red",
        label_total="Total de Despesas Gerais",
        rota_pdf="relatorios.relatorio_despesas_pdf",
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", ""),
        detalhes=detalhes
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

    secoes = [{
        "titulo": "Detalhamento de Despesas Gerais",
        "cabecalho": ["Data", "Farmácia", "Categoria", "Centro Custo", "Descrição", "Forma Pgto", "Valor"],
        "linhas": [
            [
                texto_data(d.data_despesa),
                d.farmacia.nome_fantasia if d.farmacia else "-",
                d.categoria,
                d.centro_custo or "-",
                d.descricao,
                d.forma_pagamento or "-",
                moeda(d.valor),
            ]
            for d in despesas
        ] or [["-", "-", "-", "-", "-", "-", "-"]],
        "resumo": [["Total de Despesas Gerais", moeda(total)]],
    }]

    return build_pdf_detalhado(
        "Relatório de Despesas Gerais - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        secoes,
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

    detalhes = []
    for d in despesas_motos:
        detalhes.append({
            "Data": texto_data(d.data_despesa),
            "Farmácia": d.farmacia.nome_fantasia if d.farmacia else "-",
            "Moto": d.moto.modelo if d.moto else "-",
            "Entregador": d.entregador.nome if d.entregador else "-",
            "Tipo Despesa": d.tipo_despesa,
            "Descrição": d.descricao,
            "Valor": moeda(d.valor),
            "Observação": d.observacao or "-"
        })

    return render_template(
        "relatorio_simples.html",
        titulo="Relatório de Despesas das Motos",
        subtitulo="Resumo detalhado de despesas das motos do período",
        total=total,
        cor="orange",
        label_total="Total de Despesas das Motos",
        rota_pdf="relatorios.relatorio_despesas_motos_pdf",
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", ""),
        detalhes=detalhes
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

    secoes = [{
        "titulo": "Detalhamento de Despesas das Motos",
        "cabecalho": ["Data", "Farmácia", "Moto", "Entregador", "Tipo", "Descrição", "Valor"],
        "linhas": [
            [
                texto_data(d.data_despesa),
                d.farmacia.nome_fantasia if d.farmacia else "-",
                d.moto.modelo if d.moto else "-",
                d.entregador.nome if d.entregador else "-",
                d.tipo_despesa,
                d.descricao,
                moeda(d.valor),
            ]
            for d in despesas_motos
        ] or [["-", "-", "-", "-", "-", "-", "-"]],
        "resumo": [["Total de Despesas das Motos", moeda(total)]],
    }]

    return build_pdf_detalhado(
        "Relatório de Despesas das Motos - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        secoes,
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

    for d in despesas_fixas:
        d.preparar()

    total = sum(d.valor or 0 for d in despesas_fixas)

    detalhes = []
    for d in despesas_fixas:
        detalhes.append({
            "Vencimento": texto_data(d.data_vencimento),
            "Pagamento": texto_data(d.data_pagamento),
            "Farmácia": d.farmacia.nome_fantasia if d.farmacia else "-",
            "Nome": d.nome,
            "Categoria": d.categoria,
            "Centro Custo": d.centro_custo or "-",
            "Status": d.status,
            "Valor": moeda(d.valor),
            "Observação": d.observacao or "-"
        })

    return render_template(
        "relatorio_simples.html",
        titulo="Relatório de Despesas Fixas",
        subtitulo="Resumo detalhado de despesas fixas do período",
        total=total,
        cor="purple",
        label_total="Total de Despesas Fixas",
        rota_pdf="relatorios.relatorio_despesas_fixas_pdf",
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", ""),
        detalhes=detalhes
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

    for d in despesas_fixas:
        d.preparar()

    total = sum(d.valor or 0 for d in despesas_fixas)

    secoes = [{
        "titulo": "Detalhamento de Despesas Fixas",
        "cabecalho": ["Vencimento", "Pagamento", "Farmácia", "Nome", "Categoria", "Status", "Valor"],
        "linhas": [
            [
                texto_data(d.data_vencimento),
                texto_data(d.data_pagamento),
                d.farmacia.nome_fantasia if d.farmacia else "-",
                d.nome,
                d.categoria,
                d.status,
                moeda(d.valor),
            ]
            for d in despesas_fixas
        ] or [["-", "-", "-", "-", "-", "-", "-"]],
        "resumo": [["Total de Despesas Fixas", moeda(total)]],
    }]

    return build_pdf_detalhado(
        "Relatório de Despesas Fixas - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        secoes,
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

    detalhes_1 = []
    detalhes_2 = []

    for b in boletos:
        linha = {
            "Empresa": b.empresa_nome,
            "Descrição": b.descricao or "-",
            "Farmácia": b.farmacia.nome_fantasia if b.farmacia else "-",
            "Vencimento": texto_data(b.data_vencimento),
            "Pagamento": texto_data(b.data_pagamento),
            "Original": moeda(b.valor_original),
            "Juros": moeda(b.juros),
            "Total": moeda(b.valor_total),
            "Pago": moeda(b.valor_pago),
            "Status": b.status
        }

        if b.status == "pago":
            detalhes_2.append(linha)
        else:
            detalhes_1.append(linha)

    return render_template(
        "relatorio_duplo.html",
        titulo="Relatório de Boletos a Pagar",
        subtitulo="Resumo detalhado de boletos a pagar do período",
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
        data_fim=request.args.get("data_fim", ""),
        detalhes_1=detalhes_1,
        detalhes_2=detalhes_2
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

    secoes = [
        {
            "titulo": "Boletos em Aberto",
            "cabecalho": ["Empresa", "Farmácia", "Vencimento", "Original", "Juros", "Total", "Status"],
            "linhas": [
                [
                    b.empresa_nome,
                    b.farmacia.nome_fantasia if b.farmacia else "-",
                    texto_data(b.data_vencimento),
                    moeda(b.valor_original),
                    moeda(b.juros),
                    moeda(b.valor_total),
                    b.status,
                ]
                for b in boletos if b.status in ["a_vencer", "vencido"]
            ] or [["-", "-", "-", "-", "-", "-", "-"]],
            "resumo": [["Total em Aberto", moeda(total_aberto)]],
        },
        {
            "titulo": "Boletos Pagos",
            "cabecalho": ["Empresa", "Farmácia", "Vencimento", "Pagamento", "Total", "Pago", "Status"],
            "linhas": [
                [
                    b.empresa_nome,
                    b.farmacia.nome_fantasia if b.farmacia else "-",
                    texto_data(b.data_vencimento),
                    texto_data(b.data_pagamento),
                    moeda(b.valor_total),
                    moeda(b.valor_pago),
                    b.status,
                ]
                for b in boletos if b.status == "pago"
            ] or [["-", "-", "-", "-", "-", "-", "-"]],
            "resumo": [["Total Pago", moeda(total_pagos)]],
        },
    ]

    return build_pdf_detalhado(
        "Relatório de Boletos a Pagar - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        secoes,
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

    detalhes_1 = []
    detalhes_2 = []

    for c in contas:
        linha = {
            "Cliente": c.cliente_nome,
            "Descrição": c.descricao or "-",
            "Farmácia": c.farmacia.nome_fantasia if c.farmacia else "-",
            "Vencimento": texto_data(c.data_vencimento),
            "Recebimento": texto_data(c.data_recebimento),
            "Valor": moeda(c.valor),
            "Valor Recebido": moeda(c.valor_recebido),
            "Status": c.status
        }

        if c.status == "recebido":
            detalhes_2.append(linha)
        else:
            detalhes_1.append(linha)

    return render_template(
        "relatorio_duplo.html",
        titulo="Relatório de Boletos a Receber",
        subtitulo="Resumo detalhado de boletos a receber do período",
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
        data_fim=request.args.get("data_fim", ""),
        detalhes_1=detalhes_1,
        detalhes_2=detalhes_2
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

    secoes = [
        {
            "titulo": "Contas a Receber",
            "cabecalho": ["Cliente", "Farmácia", "Vencimento", "Valor", "Status"],
            "linhas": [
                [
                    c.cliente_nome,
                    c.farmacia.nome_fantasia if c.farmacia else "-",
                    texto_data(c.data_vencimento),
                    moeda(c.valor),
                    c.status,
                ]
                for c in contas if c.status != "recebido"
            ] or [["-", "-", "-", "-", "-"]],
            "resumo": [["Total a Receber", moeda(total_receber)]],
        },
        {
            "titulo": "Contas Recebidas",
            "cabecalho": ["Cliente", "Farmácia", "Vencimento", "Recebimento", "Valor Recebido", "Status"],
            "linhas": [
                [
                    c.cliente_nome,
                    c.farmacia.nome_fantasia if c.farmacia else "-",
                    texto_data(c.data_vencimento),
                    texto_data(c.data_recebimento),
                    moeda(c.valor_recebido or c.valor),
                    c.status,
                ]
                for c in contas if c.status == "recebido"
            ] or [["-", "-", "-", "-", "-", "-"]],
            "resumo": [["Total Recebido", moeda(total_recebido)]],
        },
    ]

    return build_pdf_detalhado(
        "Relatório de Boletos a Receber - Financeiro Farm",
        formatar_periodo(data_inicio, data_fim),
        secoes,
        "relatorio_boletos_receber.pdf"
    )


@relatorios_bp.route("/boletos-pagos")
@login_required
def relatorio_boletos_pagos():
    farmacias, filtro_farmacia_id = get_farmacias_e_filtro()

    farmacia_id = request.args.get("farmacia_id", type=int)
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if farmacia_id:
        farmacia_ids = [farmacia_id]
    else:
        farmacia_ids = get_filtro_ids()

    if not farmacia_ids:
        flash("Nenhuma farmácia encontrada.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    boletos = Boleto.query.filter(Boleto.farmacia_id.in_(farmacia_ids)).all()

    for b in boletos:
        b.preparar()

    boletos = [b for b in boletos if b.status == "pago"]

    boletos = aplicar_filtro_periodo_lista(
        boletos,
        "data_pagamento",
        data_inicio,
        data_fim
    )

    total_principal = sum(b.valor_original or 0 for b in boletos)
    total_juros = sum(b.juros or 0 for b in boletos)
    total_pago = sum(b.valor_pago or b.valor_total or 0 for b in boletos)

    detalhes_boletos = []
    for b in boletos:
        detalhes_boletos.append({
            "empresa": b.empresa_nome,
            "farmacia": b.farmacia.nome_fantasia if b.farmacia else "-",
            "descricao": b.descricao or "-",
            "vencimento": texto_data(b.data_vencimento),
            "pagamento": texto_data(b.data_pagamento),
            "valor_principal": moeda(b.valor_original),
            "juros_pago": moeda(b.juros),
            "valor_total_pago": moeda(b.valor_pago or b.valor_total),
            "observacao": b.observacao or "-"
        })

    return render_template(
        "relatorio_boletos_pagos.html",
        farmacias=farmacias,
        filtro_farmacia_id=farmacia_id,
        data_inicio=request.args.get("data_inicio", ""),
        data_fim=request.args.get("data_fim", ""),
        total_principal=total_principal,
        total_juros=total_juros,
        total_pago=total_pago,
        detalhes_boletos=detalhes_boletos
    )