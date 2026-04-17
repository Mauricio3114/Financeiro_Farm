from app import create_app, db
from app.models import CategoriaDespesa

app = create_app()

CATEGORIAS_PADRAO = [
    ("Energia", "Operacional"),
    ("Água", "Operacional"),
    ("Internet", "Operacional"),
    ("Sistema", "Operacional"),
    ("Telefone", "Operacional"),
    ("Material de Escritório", "Operacional"),
    ("Limpeza", "Operacional"),
    ("Taxas Bancárias", "Operacional"),
    ("Contador", "Operacional"),
    ("Impostos", "Operacional"),
    ("Locução", "Operacional"),
    ("Impostos sobre Venda", "Operacional"),

    ("Combustível", "Entregas"),
    ("Manutenção Moto", "Entregas"),
    ("Troca de Óleo", "Entregas"),
    ("Pneus", "Entregas"),
    ("Peças", "Entregas"),
    ("Seguro Moto", "Entregas"),
    ("Documentação Moto", "Entregas"),
    ("Aluguel de Moto", "Entregas"),

    ("Salários", "Pessoal"),
    ("Folha de Pagamento", "Pessoal"),
    ("Vale Funcionário", "Pessoal"),
    ("Vale Família Lima", "Pessoal"),
    ("Comissão", "Pessoal"),
    ("Vale Transporte", "Pessoal"),
    ("Vale Alimentação", "Pessoal"),
    ("Encargos", "Pessoal"),
    ("INSS", "Pessoal"),
    ("FGTS", "Pessoal"),
    ("Férias", "Pessoal"),
    ("13º Salário", "Pessoal"),
    ("Treinamento", "Pessoal"),

    ("Aluguel", "Estrutura"),
    ("Reforma", "Estrutura"),
    ("Equipamentos", "Estrutura"),
    ("Móveis", "Estrutura"),
    ("Ar Condicionado", "Estrutura"),
    ("Manutenção Predial", "Estrutura"),
    ("Segurança", "Estrutura"),
    ("Câmeras / Monitoramento", "Estrutura"),
]

with app.app_context():
    inseridas = 0

    for nome, grupo in CATEGORIAS_PADRAO:
        existe = CategoriaDespesa.query.filter(
            db.func.lower(CategoriaDespesa.nome) == nome.lower()
        ).first()

        if not existe:
            db.session.add(CategoriaDespesa(nome=nome, grupo=grupo, ativa=True))
            inseridas += 1

    db.session.commit()

    print(f"✅ Categorias verificadas com sucesso. Novas inseridas: {inseridas}")