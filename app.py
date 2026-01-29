from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave_super_secreta")

# =========================
#  BANCO DE DADOS (POSTGRES)
# =========================
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # TABELA DE USUÁRIOS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # ADMIN PADRÃO
    cur.execute(
        "SELECT 1 FROM users WHERE username = %s",
        ('admin',)
    )

    if not cur.fetchone():
        senha_admin = generate_password_hash('admin123')
        cur.execute(
            "INSERT INTO users (nome, username, senha, role) VALUES (%s, %s, %s, %s)",
            ('Administrador', 'admin', senha_admin, 'admin')
        )

    conn.commit()
    cur.close()
    conn.close()


# =========================
#  LOGIN
# =========================
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        senha = request.form['senha']

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, nome, senha, role FROM users WHERE username = %s",
            (username,)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user[2], senha):
            session['user_id'] = user[0]
            session['nome'] = user[1]
            session['role'] = user[3]
            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Usuário ou senha inválidos')

    return render_template('login.html')


# =========================
#  DASHBOARD
# =========================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('dashboard.html')


# =========================
#  CADASTRAR USUÁRIO (ADMIN)
# =========================
@app.route('/usuarios', methods=['GET', 'POST'])
def register_user():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        nome = request.form['nome']
        username = request.form['username']
        senha = request.form['senha']
        confirmar = request.form['confirmar_senha']
        role = request.form['role']

        if senha != confirmar:
            return render_template(
                'register_user.html',
                error='As senhas não conferem'
            )

        senha_hash = generate_password_hash(senha)

        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (nome, username, senha, role) VALUES (%s, %s, %s, %s)",
                (nome, username, senha_hash, role)
            )
            conn.commit()
            cur.close()
            conn.close()

            return render_template(
                'register_user.html',
                success='Usuário cadastrado com sucesso!'
            )

        except psycopg2.errors.UniqueViolation:
            return render_template(
                'register_user.html',
                error='Usuário já existe'
            )

    return render_template('register_user.html')


# =========================
#  LOGOUT
# =========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.before_first_request
def setup_database():
    init_db()
    
