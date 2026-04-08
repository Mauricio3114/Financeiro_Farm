from app import db


class DespesaMoto(db.Model):
    __tablename__ = "despesas_motos"

    id = db.Column(db.Integer, primary_key=True)
    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)
    entregador_id = db.Column(db.Integer, db.ForeignKey("entregadores.id"), nullable=True)
    moto_id = db.Column(db.Integer, db.ForeignKey("motos.id"), nullable=False)

    tipo_despesa = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Float, nullable=False, default=0.0)
    data_despesa = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.Text, nullable=True)

    farmacia = db.relationship("Farmacia", back_populates="despesas_motos")
    entregador = db.relationship("Entregador", back_populates="despesas_motos")
    moto = db.relationship("Moto", back_populates="despesas_motos")

    def __repr__(self):
        return f"<DespesaMoto {self.descricao}>"