from app import db


class Moto(db.Model):
    __tablename__ = "motos"

    id = db.Column(db.Integer, primary_key=True)
    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)
    entregador_id = db.Column(db.Integer, db.ForeignKey("entregadores.id"), nullable=True)

    modelo = db.Column(db.String(120), nullable=False)
    placa = db.Column(db.String(20), nullable=True)
    ano = db.Column(db.String(10), nullable=True)
    cor = db.Column(db.String(50), nullable=True)
    km_atual = db.Column(db.Integer, nullable=True)
    km_ultima_revisao = db.Column(db.Integer, nullable=True)
    observacao = db.Column(db.Text, nullable=True)
    ativa = db.Column(db.Boolean, default=True)

    farmacia = db.relationship("Farmacia", back_populates="motos")
    entregador = db.relationship("Entregador", back_populates="motos")

    despesas_motos = db.relationship(
        "DespesaMoto",
        back_populates="moto",
        cascade="all, delete-orphan"
    )

    def identificacao(self):
        if self.placa:
            return f"{self.modelo} - {self.placa}"
        return self.modelo

    def km_desde_revisao(self):
        if self.km_atual is not None and self.km_ultima_revisao is not None:
            return self.km_atual - self.km_ultima_revisao
        return None

    def precisa_revisao(self, limite_km=3000):
        km = self.km_desde_revisao()
        if km is None:
            return False
        return km >= limite_km

    def __repr__(self):
        return f"<Moto {self.modelo}>"