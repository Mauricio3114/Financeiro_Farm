from app import db


class Farmacia(db.Model):
    __tablename__ = "farmacias"

    id = db.Column(db.Integer, primary_key=True)
    nome_fantasia = db.Column(db.String(150), nullable=False)
    razao_social = db.Column(db.String(150), nullable=True)
    cnpj = db.Column(db.String(30), nullable=True)
    telefone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    endereco = db.Column(db.String(255), nullable=True)
    responsavel = db.Column(db.String(120), nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    vinculacoes = db.relationship(
        "UsuarioFarmacia",
        back_populates="farmacia",
        cascade="all, delete-orphan"
    )

    boletos = db.relationship(
        "Boleto",
        back_populates="farmacia",
        cascade="all, delete-orphan"
    )

    despesas = db.relationship(
        "Despesa",
        back_populates="farmacia",
        cascade="all, delete-orphan"
    )

    vendas = db.relationship(
        "VendaDiaria",
        back_populates="farmacia",
        cascade="all, delete-orphan"
    )

    entregadores = db.relationship(
        "Entregador",
        back_populates="farmacia",
        cascade="all, delete-orphan"
    )

    motos = db.relationship(
        "Moto",
        back_populates="farmacia",
        cascade="all, delete-orphan"
    )

    despesas_motos = db.relationship(
        "DespesaMoto",
        back_populates="farmacia",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Farmacia {self.nome_fantasia}>"