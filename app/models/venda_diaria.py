from app import db


class VendaDiaria(db.Model):
    __tablename__ = "vendas_diarias"

    id = db.Column(db.Integer, primary_key=True)
    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)

    data_venda = db.Column(db.Date, nullable=False)

    valor_vista = db.Column(db.Float, default=0.0)
    valor_vulcabras = db.Column(db.Float, default=0.0)
    valor_debito = db.Column(db.Float, default=0.0)
    valor_credito = db.Column(db.Float, default=0.0)
    valor_pix = db.Column(db.Float, default=0.0)

    total_dia = db.Column(db.Float, default=0.0)
    observacao = db.Column(db.Text, nullable=True)

    farmacia = db.relationship("Farmacia", back_populates="vendas")

    def calcular_total(self):
        self.total_dia = float(
            (self.valor_vista or 0.0)
            + (self.valor_vulcabras or 0.0)
            + (self.valor_debito or 0.0)
            + (self.valor_credito or 0.0)
            + (self.valor_pix or 0.0)
        )

    def __repr__(self):
        return f"<VendaDiaria {self.data_venda}>"