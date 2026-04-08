from datetime import date
from app import db


class Boleto(db.Model):
    __tablename__ = "boletos"

    id = db.Column(db.Integer, primary_key=True)

    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)

    empresa_nome = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)

    valor_original = db.Column(db.Float, nullable=False, default=0.0)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date, nullable=True)

    valor_pago = db.Column(db.Float, nullable=True)
    juros = db.Column(db.Float, default=0.0)
    valor_total = db.Column(db.Float, default=0.0)

    status = db.Column(db.String(30), default="a_vencer")
    observacao = db.Column(db.Text, nullable=True)

    farmacia = db.relationship("Farmacia", back_populates="boletos")

    def calcular_juros(self, valor_juros_dia=2.0):
        if self.data_pagamento and self.data_pagamento > self.data_vencimento:
            dias_atraso = (self.data_pagamento - self.data_vencimento).days
            self.juros = float(dias_atraso * valor_juros_dia)
        else:
            self.juros = 0.0

        self.valor_total = float(self.valor_original + self.juros)

    def atualizar_status(self):
        hoje = date.today()

        if self.data_pagamento:
            self.status = "pago"
        else:
            if self.data_vencimento < hoje:
                self.status = "vencido"
            else:
                self.status = "a_vencer"

    def preparar(self):
        self.calcular_juros()
        self.atualizar_status()

    def __repr__(self):
        return f"<Boleto {self.empresa_nome}>"