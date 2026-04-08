from app import db


class MovimentoCaixa(db.Model):
    __tablename__ = "movimentos_caixa"

    id = db.Column(db.Integer, primary_key=True)
    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)

    tipo = db.Column(db.String(20), nullable=False)  # entrada / saida
    categoria = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Float, nullable=False, default=0.0)
    data_movimento = db.Column(db.Date, nullable=False)
    origem = db.Column(db.String(50), nullable=True)  # venda, despesa, boleto, receber, manual
    observacao = db.Column(db.Text, nullable=True)

    farmacia = db.relationship("Farmacia")

    def __repr__(self):
        return f"<MovimentoCaixa {self.tipo} {self.valor}>"