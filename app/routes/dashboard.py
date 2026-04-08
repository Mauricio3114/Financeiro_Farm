from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import (
    Farmacia,
    Boleto,
    UsuarioFarmacia,
    Despesa,
    VendaDiaria,
    Entregador,
    Moto,
    DespesaMoto,
    ContaReceber,
    MovimentoCaixa,
    DespesaFixaLancamento,
)

dashboard_bp = Blueprint("dashboard", __name__)


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


def somar_vendas_periodo(farmacia_ids, inicio, fim):
    if not farmacia_ids:
        return 0.0

    vendas = VendaDiaria.query.filter(
        VendaDiaria.farmacia_id.in_(farmacia_ids),
        VendaDiaria.data_venda >= inicio,
        VendaDiaria.data_venda <= fim
    ).all()

    return float(sum(v.total_dia or 0 for v in vendas))


def somar_despesas_gerais_periodo(farmacia_ids, inicio, fim):
    if not farmacia_ids:
        return 0.0

    despesas = Despesa.query.filter(
        Despesa.farmacia_id.in_(farmacia_ids),
        Despesa.data_despesa >= inicio,
        Despesa.data_despesa <= fim
    ).all()

    return float(sum(d.valor or 0 for d in despesas))


def somar_despesas_motos_periodo(farmacia_ids, inicio, fim):
    if not farmacia_ids:
        return 0.0

    despesas = DespesaMoto.query.filter(
        DespesaMoto.farmacia_id.in_(farmacia_ids),
        DespesaMoto.data_despesa >= inicio,
        DespesaMoto.data_despesa <= fim
    ).all()

    return float(sum(d.valor or 0 for d in despesas))


def somar_despesas_fixas_periodo(farmacia_ids, inicio, fim):
    if not farmacia_ids:
        return 0.0

    despesas = DespesaFixaLancamento.query.filter(
        DespesaFixaLancamento.farmacia_id.in_(farmacia_ids),
        DespesaFixaLancamento.data_vencimento >= inicio,
        DespesaFixaLancamento.data_vencimento <= fim
    ).all()

    for item in despesas:
        item.preparar()

    db.session.commit()
    return float(sum(d.valor or 0 for d in despesas))


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    hoje = date.today()

    farmacias = farmacias_do_usuario(current_user)
    farmacia_ids = [f.id for f in farmacias]

    filtro_farmacia_id = request.args.get("farmacia_id", type=int)
    data_inicio = parse_date(request.args.get("data_inicio"))
    data_fim = parse_date(request.args.get("data_fim"))

    if filtro_farmacia_id and filtro_farmacia_id in farmacia_ids:
        farmacia_ids_filtrados = [filtro_farmacia_id]
    else:
        farmacia_ids_filtrados = farmacia_ids

    if not data_inicio:
        data_inicio = hoje.replace(day=1)

    if not data_fim:
        data_fim = hoje

    total_farmacias = len(farmacias)

    total_boletos = 0
    total_pagos = 0
    total_vencidos = 0
    soma_a_pagar = 0
    soma_pagos = 0
    total_despesas = 0
    total_despesas_motos = 0
    total_despesas_fixas = 0
    total_vendas = 0
    total_entregadores = 0
    total_motos = 0
    total_receber = 0
    total_recebido = 0
    total_entradas_caixa = 0
    total_saidas_caixa = 0

    motos_revisao = []
    top_categorias = []
    top_motos = []
    top_entregadores = []
    top_centros = []
    boletos_proximos = []

    resumo_pagamentos = {
        "vista": 0,
        "vulcabras": 0,
        "debito": 0,
        "credito": 0,
        "pix": 0,
    }

    if farmacia_ids_filtrados:
        boletos_query = Boleto.query.filter(Boleto.farmacia_id.in_(farmacia_ids_filtrados))
        boletos_query = boletos_query.filter(Boleto.data_vencimento >= data_inicio, Boleto.data_vencimento <= data_fim)
        boletos = boletos_query.order_by(Boleto.data_vencimento.asc()).all()

        for boleto in boletos:
            boleto.preparar()

        db.session.commit()

        total_boletos = len(boletos)
        total_pagos = len([b for b in boletos if b.status == "pago"])
        total_vencidos = len([b for b in boletos if b.status == "vencido"])
        soma_a_pagar = sum((b.valor_total or 0) for b in boletos if b.status in ["a_vencer", "vencido"])
        soma_pagos = sum((b.valor_pago or 0) for b in boletos if b.status == "pago")

        boletos_alerta = Boleto.query.filter(Boleto.farmacia_id.in_(farmacia_ids_filtrados)).order_by(Boleto.data_vencimento.asc()).all()
        for boleto in boletos_alerta:
            boleto.preparar()
            if boleto.status != "pago":
                dias = (boleto.data_vencimento - hoje).days
                if 0 <= dias <= 2:
                    boletos_proximos.append((boleto, dias))

        despesas_query = Despesa.query.filter(
            Despesa.farmacia_id.in_(farmacia_ids_filtrados),
            Despesa.data_despesa >= data_inicio,
            Despesa.data_despesa <= data_fim
        )
        despesas = despesas_query.all()
        total_despesas = sum(d.valor or 0 for d in despesas)

        despesas_motos_query = DespesaMoto.query.filter(
            DespesaMoto.farmacia_id.in_(farmacia_ids_filtrados),
            DespesaMoto.data_despesa >= data_inicio,
            DespesaMoto.data_despesa <= data_fim
        )
        despesas_motos = despesas_motos_query.all()
        total_despesas_motos = sum(d.valor or 0 for d in despesas_motos)

        despesas_fixas_query = DespesaFixaLancamento.query.filter(
            DespesaFixaLancamento.farmacia_id.in_(farmacia_ids_filtrados),
            DespesaFixaLancamento.data_vencimento >= data_inicio,
            DespesaFixaLancamento.data_vencimento <= data_fim
        )
        despesas_fixas = despesas_fixas_query.all()
        for item in despesas_fixas:
            item.preparar()
        db.session.commit()
        total_despesas_fixas = sum(item.valor or 0 for item in despesas_fixas)

        vendas_query = VendaDiaria.query.filter(
            VendaDiaria.farmacia_id.in_(farmacia_ids_filtrados),
            VendaDiaria.data_venda >= data_inicio,
            VendaDiaria.data_venda <= data_fim
        )
        vendas = vendas_query.all()

        total_vendas = sum(v.total_dia or 0 for v in vendas)
        resumo_pagamentos["vista"] = sum(v.valor_vista or 0 for v in vendas)
        resumo_pagamentos["vulcabras"] = sum(v.valor_vulcabras or 0 for v in vendas)
        resumo_pagamentos["debito"] = sum(v.valor_debito or 0 for v in vendas)
        resumo_pagamentos["credito"] = sum(v.valor_credito or 0 for v in vendas)
        resumo_pagamentos["pix"] = sum(v.valor_pix or 0 for v in vendas)

        contas_receber_query = ContaReceber.query.filter(
            ContaReceber.farmacia_id.in_(farmacia_ids_filtrados),
            ContaReceber.data_vencimento >= data_inicio,
            ContaReceber.data_vencimento <= data_fim
        )
        contas_receber = contas_receber_query.all()
        for conta in contas_receber:
            conta.preparar()
        db.session.commit()

        total_receber = sum((c.valor or 0) for c in contas_receber if c.status in ["a_receber", "vencido"])
        total_recebido = sum((c.valor_recebido or c.valor or 0) for c in contas_receber if c.status == "recebido")

        caixa_query = MovimentoCaixa.query.filter(
            MovimentoCaixa.farmacia_id.in_(farmacia_ids_filtrados),
            MovimentoCaixa.data_movimento >= data_inicio,
            MovimentoCaixa.data_movimento <= data_fim
        )
        movimentos = caixa_query.all()
        total_entradas_caixa = sum(m.valor or 0 for m in movimentos if m.tipo == "entrada")
        total_saidas_caixa = sum(m.valor or 0 for m in movimentos if m.tipo == "saida")

        total_entregadores = Entregador.query.filter(
            Entregador.farmacia_id.in_(farmacia_ids_filtrados),
            Entregador.ativo == True
        ).count()

        motos = Moto.query.filter(
            Moto.farmacia_id.in_(farmacia_ids_filtrados),
            Moto.ativa == True
        ).all()
        total_motos = len(motos)
        motos_revisao = [m for m in motos if m.precisa_revisao()]

        top_categorias_db = db.session.query(
            Despesa.categoria,
            func.sum(Despesa.valor)
        ).filter(
            Despesa.farmacia_id.in_(farmacia_ids_filtrados),
            Despesa.data_despesa >= data_inicio,
            Despesa.data_despesa <= data_fim
        ).group_by(Despesa.categoria).order_by(func.sum(Despesa.valor).desc()).limit(5).all()
        top_categorias = top_categorias_db

        top_motos_db = db.session.query(
            Moto.modelo,
            Moto.placa,
            func.sum(DespesaMoto.valor)
        ).join(DespesaMoto, DespesaMoto.moto_id == Moto.id).filter(
            DespesaMoto.farmacia_id.in_(farmacia_ids_filtrados),
            DespesaMoto.data_despesa >= data_inicio,
            DespesaMoto.data_despesa <= data_fim
        ).group_by(Moto.id, Moto.modelo, Moto.placa).order_by(func.sum(DespesaMoto.valor).desc()).limit(5).all()
        top_motos = top_motos_db

        top_entregadores_db = db.session.query(
            Entregador.nome,
            func.sum(DespesaMoto.valor)
        ).join(DespesaMoto, DespesaMoto.entregador_id == Entregador.id).filter(
            DespesaMoto.farmacia_id.in_(farmacia_ids_filtrados),
            DespesaMoto.data_despesa >= data_inicio,
            DespesaMoto.data_despesa <= data_fim
        ).group_by(Entregador.id, Entregador.nome).order_by(func.sum(DespesaMoto.valor).desc()).limit(5).all()
        top_entregadores = top_entregadores_db

        centros = defaultdict(float)

        for item in despesas:
            chave = item.centro_custo or "Não definido"
            centros[chave] += float(item.valor or 0)

        for item in despesas_fixas:
            chave = item.centro_custo or "Não definido"
            centros[chave] += float(item.valor or 0)

        top_centros = sorted(centros.items(), key=lambda x: x[1], reverse=True)[:5]

    receita_bruta = float(total_vendas)
    despesas_operacionais = float(total_despesas + total_despesas_motos + total_despesas_fixas)
    lucro_liquido = float(receita_bruta - despesas_operacionais)
    resultado = lucro_liquido
    saldo_caixa = float(total_entradas_caixa - total_saidas_caixa)

    margem_lucro = 0.0
    if receita_bruta > 0:
        margem_lucro = (lucro_liquido / receita_bruta) * 100

    inicio_mes_atual = hoje.replace(day=1)
    fim_mes_atual = date(hoje.year, hoje.month, monthrange(hoje.year, hoje.month)[1])

    ultimo_dia_mes_anterior = inicio_mes_atual - timedelta(days=1)
    inicio_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
    fim_mes_anterior = ultimo_dia_mes_anterior

    if farmacia_ids_filtrados:
        vendas_mes_atual = somar_vendas_periodo(farmacia_ids_filtrados, inicio_mes_atual, min(hoje, fim_mes_atual))
        despesas_mes_atual = (
            somar_despesas_gerais_periodo(farmacia_ids_filtrados, inicio_mes_atual, min(hoje, fim_mes_atual))
            + somar_despesas_motos_periodo(farmacia_ids_filtrados, inicio_mes_atual, min(hoje, fim_mes_atual))
            + somar_despesas_fixas_periodo(farmacia_ids_filtrados, inicio_mes_atual, min(hoje, fim_mes_atual))
        )
        lucro_mes_atual = vendas_mes_atual - despesas_mes_atual

        vendas_mes_anterior = somar_vendas_periodo(farmacia_ids_filtrados, inicio_mes_anterior, fim_mes_anterior)
        despesas_mes_anterior = (
            somar_despesas_gerais_periodo(farmacia_ids_filtrados, inicio_mes_anterior, fim_mes_anterior)
            + somar_despesas_motos_periodo(farmacia_ids_filtrados, inicio_mes_anterior, fim_mes_anterior)
            + somar_despesas_fixas_periodo(farmacia_ids_filtrados, inicio_mes_anterior, fim_mes_anterior)
        )
        lucro_mes_anterior = vendas_mes_anterior - despesas_mes_anterior
    else:
        vendas_mes_atual = 0
        despesas_mes_atual = 0
        lucro_mes_atual = 0
        vendas_mes_anterior = 0
        despesas_mes_anterior = 0
        lucro_mes_anterior = 0

    dias_decorridos = hoje.day
    dias_no_mes = monthrange(hoje.year, hoje.month)[1]

    previsao_receita = receita_bruta
    previsao_despesas = despesas_operacionais
    previsao_lucro = lucro_liquido

    if dias_decorridos > 0 and data_inicio == inicio_mes_atual and data_fim == hoje:
        media_vendas_dia = receita_bruta / dias_decorridos if dias_decorridos else 0
        media_despesas_dia = (total_despesas + total_despesas_motos) / dias_decorridos if dias_decorridos else 0

        previsao_receita = media_vendas_dia * dias_no_mes
        previsao_despesas = (media_despesas_dia * dias_no_mes) + total_despesas_fixas
        previsao_lucro = previsao_receita - previsao_despesas

    return render_template(
        "dashboard.html",
        total_farmacias=total_farmacias,
        total_boletos=total_boletos,
        total_pagos=total_pagos,
        total_vencidos=total_vencidos,
        soma_a_pagar=soma_a_pagar,
        soma_pagos=soma_pagos,
        total_despesas=total_despesas,
        total_despesas_motos=total_despesas_motos,
        total_despesas_fixas=total_despesas_fixas,
        total_despesas_geral=despesas_operacionais,
        total_vendas=total_vendas,
        total_entregadores=total_entregadores,
        total_motos=total_motos,
        total_receber=total_receber,
        total_recebido=total_recebido,
        total_entradas_caixa=total_entradas_caixa,
        total_saidas_caixa=total_saidas_caixa,
        saldo_caixa=saldo_caixa,
        resultado=resultado,
        receita_bruta=receita_bruta,
        despesas_operacionais=despesas_operacionais,
        lucro_liquido=lucro_liquido,
        margem_lucro=margem_lucro,
        hoje=hoje,
        farmacias=farmacias,
        filtro_farmacia_id=filtro_farmacia_id,
        data_inicio=data_inicio.strftime("%Y-%m-%d") if data_inicio else "",
        data_fim=data_fim.strftime("%Y-%m-%d") if data_fim else "",
        motos_revisao=motos_revisao,
        top_categorias=top_categorias,
        top_motos=top_motos,
        top_entregadores=top_entregadores,
        top_centros=top_centros,
        boletos_proximos=boletos_proximos,
        resumo_pagamentos=resumo_pagamentos,
        vendas_mes_atual=vendas_mes_atual,
        despesas_mes_atual=despesas_mes_atual,
        lucro_mes_atual=lucro_mes_atual,
        vendas_mes_anterior=vendas_mes_anterior,
        despesas_mes_anterior=despesas_mes_anterior,
        lucro_mes_anterior=lucro_mes_anterior,
        previsao_receita=previsao_receita,
        previsao_despesas=previsao_despesas,
        previsao_lucro=previsao_lucro
    )