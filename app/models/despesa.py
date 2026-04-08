from app import db


class Despesa(db.Model):
    __tablename__ = "despesas"

    id = db.Column(db.Integer, primary_key=True)
    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)

    categoria = db.Column(db.String(100), nullable=False)
    centro_custo = db.Column(db.String(100), nullable=True)
    descricao = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Float, nullable=False, default=0.0)
    data_despesa = db.Column(db.Date, nullable=False)
    forma_pagamento = db.Column(db.String(50), nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    farmacia = db.relationship("Farmacia", back_populates="despesas")

    def __repr__(self):
        return f"<Despesa {self.descricao}>"