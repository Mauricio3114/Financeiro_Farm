from app import db


class DespesaFixa(db.Model):
    __tablename__ = "despesas_fixas"

    id = db.Column(db.Integer, primary_key=True)
    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)

    nome = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    centro_custo = db.Column(db.String(100), nullable=True)
    valor_padrao = db.Column(db.Float, nullable=False, default=0.0)
    dia_vencimento = db.Column(db.Integer, nullable=False)
    tipo_valor = db.Column(db.String(20), nullable=False, default="fixa")  # fixa / variavel
    observacao = db.Column(db.Text, nullable=True)
    ativa = db.Column(db.Boolean, default=True)

    farmacia = db.relationship("Farmacia")
    lancamentos = db.relationship(
        "DespesaFixaLancamento",
        back_populates="despesa_fixa",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<DespesaFixa {self.nome}>"