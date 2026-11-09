import os
import secrets
from datetime import datetime
from functools import wraps
from flask import (Flask, request, redirect, url_for,
                   render_template_string, session)
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Chave usada para assinar a sessão do login
app.secret_key = os.environ.get("SECRET_KEY", "troque-essa-chave-em-producao")

# Senha de acesso: defina APP_SENHA nas variáveis de ambiente
APP_SENHA = os.environ.get("APP_SENHA", "tarot@123#2026")

APP_USUARIO = os.environ.get("APP_USUARIO", "suzana")

# Em produção usa o Neon (DATABASE_URL). Localmente usa um arquivo SQLite.
db_url = os.environ.get("DATABASE_URL", "sqlite:///atendimentos.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
db = SQLAlchemy(app)


class Atendimento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(120), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False, default=datetime.now)
    tema = db.Column(db.String(200))
    valor = db.Column(db.Numeric(10, 2), default=0)
    pago = db.Column(db.Boolean, default=False)
    observacoes = db.Column(db.Text)


with app.app_context():
    db.create_all()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logado"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


BASE = """
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Atendimentos</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; background: #faf7f2; color: #333; }
  h1 { color: #5b3e8a; }
  a.btn, button, input[type=submit] { background: #5b3e8a; color: #fff; border: 0; padding: .5rem 1rem; border-radius: 6px; text-decoration: none; cursor: pointer; font-size: .95rem; }
  button.sec { background: #888; }
  button.danger { background: #b03a3a; }
  table { width: 100%; border-collapse: collapse; background: #fff; }
  th, td { padding: .6rem; border-bottom: 1px solid #eee; text-align: left; font-size: .95rem; }
  .pago { color: #2e7d32; font-weight: bold; }
  .nao { color: #b03a3a; font-weight: bold; }
  .card { background: #fff; padding: 1rem 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px #0001; }
  label { display: block; margin-top: .8rem; font-weight: 600; }
  input, textarea, select { width: 100%; padding: .5rem; margin-top: .3rem; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 1rem; }
  .resumo { display: flex; gap: 1rem; margin: 1rem 0; }
  .resumo div { flex: 1; background: #fff; padding: 1rem; border-radius: 8px; box-shadow: 0 1px 3px #0001; }
  .resumo strong { font-size: 1.4rem; color: #5b3e8a; }
  form.inline { display: inline; }
  .topo { display: flex; justify-content: space-between; align-items: center; }
</style>
</head>
<body>
{{ conteudo|safe }}
</body>
</html>
"""

LOGIN = """
<h1>🔮 Entrar</h1>
<div class="card" style="max-width:360px">
<form method="post">
  <label>Usuário
    <input name="usuario" required autofocus>
  </label>
  <label>Senha
    <input type="password" name="senha" required>
  </label>
  {% if erro %}<p class="nao">{{ erro }}</p>{% endif %}
  <p><input type="submit" value="Entrar"></p>
</form>
</div>
"""


LISTA = """
<div class="topo">
  <h1>🔮 Atendimentos</h1>
  <a class="btn sec" href="{{ url_for('logout') }}">Sair</a>
</div>
<a class="btn" href="{{ url_for('novo') }}">+ Novo atendimento</a>

<div class="resumo">
  <div>Atendimentos<br><strong>{{ total }}</strong></div>
  <div>Recebido<br><strong>R$ {{ '%.2f'|format(recebido) }}</strong></div>
  <div>A receber<br><strong>R$ {{ '%.2f'|format(a_receber) }}</strong></div>
</div>

<table>
  <tr><th>Data</th><th>Cliente</th><th>Tema</th><th>Valor</th><th>Pago?</th><th></th></tr>
  {% for a in atendimentos %}
  <tr>
    <td>{{ a.data_hora.strftime('%d/%m/%Y %H:%M') }}</td>
    <td>{{ a.cliente }}</td>
    <td>{{ a.tema or '' }}</td>
    <td>R$ {{ '%.2f'|format(a.valor or 0) }}</td>
    <td>
      <form class="inline" method="post" action="{{ url_for('alternar_pago', id=a.id) }}">
        <button class="sec" type="submit">{% if a.pago %}<span class="pago">Sim</span>{% else %}<span class="nao">Não</span>{% endif %}</button>
      </form>
    </td>
        <td>
      <a class="btn sec" href="{{ url_for('editar', id=a.id) }}">Editar</a>
      <form class="inline" method="post" action="{{ url_for('excluir', id=a.id) }}" onsubmit="return confirm('Excluir este atendimento?')">
        <button class="danger" type="submit">Excluir</button>
      </form>
    </td>

  </tr>
  {% else %}
  <tr><td colspan="6">Nenhum atendimento registrado ainda.</td></tr>
  {% endfor %}
</table>
"""

FORM = """
<h1>{{ titulo }}</h1>
<div class="card">
<form method="post" action="{{ action }}">
  <label>Cliente
    <input name="cliente" required value="{{ a.cliente if a else '' }}">
  </label>
  <label>Data e hora
    <input type="datetime-local" name="data_hora" required
           value="{{ a.data_hora.strftime('%Y-%m-%dT%H:%M') if a else agora }}">
  </label>
  <label>Tema / pergunta
    <input name="tema" value="{{ a.tema or '' if a else '' }}">
  </label>
  <label>Valor (R$)
    <input type="number" step="0.01" name="valor" value="{{ '%.2f'|format(a.valor or 0) if a else '0' }}">
  </label>
  <label>
    <input type="checkbox" name="pago" style="width:auto" {% if a and a.pago %}checked{% endif %}> Já foi pago
  </label>
  <label>Observações
    <textarea name="observacoes" rows="4">{{ a.observacoes or '' if a else '' }}</textarea>
  </label>
  <p><input type="submit" value="Salvar"> <a class="btn" style="background:#888" href="{{ url_for('index') }}">Cancelar</a></p>
</form>
</div>
"""



@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        senha = request.form.get("senha", "")
        usuario_ok = secrets.compare_digest(usuario, APP_USUARIO)
        senha_ok = secrets.compare_digest(senha, APP_SENHA)
        if usuario_ok and senha_ok:
            session["logado"] = True
            return redirect(url_for("index"))
        erro = "Usuário ou senha incorretos."
    conteudo = render_template_string(LOGIN, erro=erro)
    return render_template_string(BASE, conteudo=conteudo)



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    atendimentos = Atendimento.query.order_by(Atendimento.data_hora.desc()).all()
    total = len(atendimentos)
    recebido = sum(float(a.valor or 0) for a in atendimentos if a.pago)
    a_receber = sum(float(a.valor or 0) for a in atendimentos if not a.pago)
    conteudo = render_template_string(LISTA, atendimentos=atendimentos,
                                      total=total, recebido=recebido, a_receber=a_receber)
    return render_template_string(BASE, conteudo=conteudo)


def preencher(a, form):
    a.cliente = form["cliente"].strip()
    a.data_hora = datetime.fromisoformat(form["data_hora"])
    a.tema = form.get("tema", "").strip()
    a.valor = form.get("valor") or 0
    a.pago = form.get("pago") == "on"
    a.observacoes = form.get("observacoes", "").strip()


@app.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if request.method == "POST":
        a = Atendimento()
        preencher(a, request.form)
        db.session.add(a)
        db.session.commit()
        return redirect(url_for("index"))

    agora = datetime.now().strftime("%Y-%m-%dT%H:%M")
    conteudo = render_template_string(FORM, a=None, agora=agora,
                                      titulo="Novo atendimento", action=url_for("novo"))
    return render_template_string(BASE, conteudo=conteudo)


@app.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    a = db.get_or_404(Atendimento, id)
    if request.method == "POST":
        preencher(a, request.form)
        db.session.commit()
        return redirect(url_for("index"))

    conteudo = render_template_string(FORM, a=a, agora=None,
                                      titulo="Editar atendimento", action=url_for("editar", id=a.id))
    return render_template_string(BASE, conteudo=conteudo)


@app.route("/pago/<int:id>", methods=["POST"])
@login_required
def alternar_pago(id):
    a = db.get_or_404(Atendimento, id)
    a.pago = not a.pago
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/excluir/<int:id>", methods=["POST"])
@login_required
def excluir(id):
    a = db.get_or_404(Atendimento, id)
    db.session.delete(a)
    db.session.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
