from datetime import date
from app import db


class AgendaEvento(db.Model):
    __tablename__ = "agenda_eventos"

    id = db.Column(db.Integer, primary_key=True)

    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=True)

    tipo = db.Column(db.String(50), nullable=False, default="aviso_geral")
    prioridade = db.Column(db.String(20), nullable=False, default="normal")
    repeticao = db.Column(db.String(20), nullable=False, default="nenhuma")

    data_evento = db.Column(db.Date, nullable=False)
    hora_evento = db.Column(db.String(10), nullable=True)

    status = db.Column(db.String(20), nullable=False, default="pendente")
    observacao = db.Column(db.Text, nullable=True)

    def dias_para_evento(self):
        hoje = date.today()

        if self.repeticao == "anual":
            try:
                proxima_data = self.data_evento.replace(year=hoje.year)
            except ValueError:
                proxima_data = self.data_evento.replace(year=hoje.year, day=28)

            if proxima_data < hoje:
                try:
                    proxima_data = self.data_evento.replace(year=hoje.year + 1)
                except ValueError:
                    proxima_data = self.data_evento.replace(year=hoje.year + 1, day=28)

            return (proxima_data - hoje).days

        if self.repeticao == "mensal":
            ano = hoje.year
            mes = hoje.month
            dia = self.data_evento.day

            try:
                proxima_data = date(ano, mes, dia)
            except ValueError:
                proxima_data = date(ano, mes, 28)

            if proxima_data < hoje:
                if mes == 12:
                    ano += 1
                    mes = 1
                else:
                    mes += 1

                try:
                    proxima_data = date(ano, mes, dia)
                except ValueError:
                    proxima_data = date(ano, mes, 28)

            return (proxima_data - hoje).days

        return (self.data_evento - hoje).days

    def data_exibicao(self):
        hoje = date.today()

        if self.repeticao == "anual":
            try:
                proxima_data = self.data_evento.replace(year=hoje.year)
            except ValueError:
                proxima_data = self.data_evento.replace(year=hoje.year, day=28)

            if proxima_data < hoje:
                try:
                    proxima_data = self.data_evento.replace(year=hoje.year + 1)
                except ValueError:
                    proxima_data = self.data_evento.replace(year=hoje.year + 1, day=28)

            return proxima_data

        if self.repeticao == "mensal":
            ano = hoje.year
            mes = hoje.month
            dia = self.data_evento.day

            try:
                proxima_data = date(ano, mes, dia)
            except ValueError:
                proxima_data = date(ano, mes, 28)

            if proxima_data < hoje:
                if mes == 12:
                    ano += 1
                    mes = 1
                else:
                    mes += 1

                try:
                    proxima_data = date(ano, mes, dia)
                except ValueError:
                    proxima_data = date(ano, mes, 28)

            return proxima_data

        return self.data_evento

    def esta_proximo(self):
        dias = self.dias_para_evento()
        return 0 <= dias <= 7 and self.status == "pendente"

    def nivel_alerta(self):
        dias = self.dias_para_evento()

        if self.status != "pendente":
            return "normal"

        if dias < 0:
            return "atrasado"
        if dias == 0:
            return "hoje"
        if dias <= 3:
            return "urgente"
        if dias <= 7:
            return "proximo"
        return "normal"

    def __repr__(self):
        return f"<AgendaEvento {self.titulo}>"