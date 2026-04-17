from app import create_app, db
from app.models import CategoriaDespesa

app = create_app()

with app.app_context():
    categorias = CategoriaDespesa.query.order_by(
        CategoriaDespesa.nome.asc(),
        CategoriaDespesa.id.asc()
    ).all()

    vistos = {}
    removidas = 0

    for categoria in categorias:
        chave = categoria.nome.strip().lower()

        if chave not in vistos:
            vistos[chave] = categoria
        else:
            db.session.delete(categoria)
            removidas += 1

    db.session.commit()

    print(f"✅ Categorias duplicadas removidas: {removidas}")