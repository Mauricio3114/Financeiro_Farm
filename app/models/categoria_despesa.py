from datetime import datetime
from app import db


class CategoriaDespesa(db.Model):
    __tablename__ = "categorias_despesa"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    grupo = db.Column(db.String(80), nullable=False, default="Outros")
    ativa = db.Column(db.Boolean, default=True)
    criada_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CategoriaDespesa {self.nome}>"