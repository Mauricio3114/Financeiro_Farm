from datetime import date
from app import db


class DespesaFixaLancamento(db.Model):
    __tablename__ = "despesas_fixas_lancamentos"

    id = db.Column(db.Integer, primary_key=True)
    despesa_fixa_id = db.Column(db.Integer, db.ForeignKey("despesas_fixas.id"), nullable=False)
    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)

    nome = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    centro_custo = db.Column(db.String(100), nullable=True)
    valor = db.Column(db.Float, nullable=False, default=0.0)

    ano = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date, nullable=True)

    status = db.Column(db.String(30), default="pendente")  # pendente / pago / vencido
    observacao = db.Column(db.Text, nullable=True)

    despesa_fixa = db.relationship("DespesaFixa", back_populates="lancamentos")
    farmacia = db.relationship("Farmacia")

    def atualizar_status(self):
        hoje = date.today()
        if self.data_pagamento:
            self.status = "pago"
        else:
            if self.data_vencimento < hoje:
                self.status = "vencido"
            else:
                self.status = "pendente"

    def preparar(self):
        self.atualizar_status()

    def __repr__(self):
        return f"<DespesaFixaLancamento {self.nome} {self.mes}/{self.ano}>"