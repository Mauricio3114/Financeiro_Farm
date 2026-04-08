from app import db


class UsuarioFarmacia(db.Model):
    __tablename__ = "usuario_farmacia"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    farmacia_id = db.Column(db.Integer, db.ForeignKey("farmacias.id"), nullable=False)

    usuario = db.relationship("Usuario", back_populates="vinculacoes")
    farmacia = db.relationship("Farmacia", back_populates="vinculacoes")

    __table_args__ = (
        db.UniqueConstraint("usuario_id", "farmacia_id", name="uq_usuario_farmacia"),
    )