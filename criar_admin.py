from app import create_app, db
from app.models import Usuario
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():

    email = "admin@financeirofarm.com"
    senha = "123456"

    usuario = Usuario.query.filter_by(email=email).first()

    if usuario:
        print("⚠️ Admin já existe!")
    else:
        novo_admin = Usuario(
            nome="Administrador",
            email=email,
            senha_hash=generate_password_hash(senha),  # 👈 corrigido
            perfil="admin",
            ativo=True
        )

        db.session.add(novo_admin)
        db.session.commit()

        print("✅ Admin criado com sucesso!")
        print(f"Email: {email}")
        print(f"Senha: {senha}")