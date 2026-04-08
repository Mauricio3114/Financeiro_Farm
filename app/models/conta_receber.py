from datetime import date
from app import db


class ContaReceber(db.Model):
    __tablename__ = "contas_receber"

    id = db.Column(db.Integer, primary_key=True)
    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)

    cliente_nome = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)

    valor = db.Column(db.Float, nullable=False, default=0.0)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_recebimento = db.Column(db.Date, nullable=True)

    valor_recebido = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(30), default="a_receber")
    observacao = db.Column(db.Text, nullable=True)

    farmacia = db.relationship("Farmacia")

    def atualizar_status(self):
        hoje = date.today()

        if self.data_recebimento:
            self.status = "recebido"
        else:
            if self.data_vencimento < hoje:
                self.status = "vencido"
            else:
                self.status = "a_receber"

    def preparar(self):
        self.atualizar_status()

    def __repr__(self):
        return f"<ContaReceber {self.cliente_nome}>"