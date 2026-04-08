from app import db


class Entregador(db.Model):
    __tablename__ = "entregadores"

    id = db.Column(db.Integer, primary_key=True)
    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)

    nome = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(30), nullable=True)
    cpf = db.Column(db.String(20), nullable=True)
    observacao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    farmacia = db.relationship("Farmacia", back_populates="entregadores")

    motos = db.relationship(
        "Moto",
        back_populates="entregador",
        cascade="all, delete-orphan"
    )

    despesas_motos = db.relationship(
        "DespesaMoto",
        back_populates="entregador"
    )

    def __repr__(self):
        return f"<Entregador {self.nome}>"