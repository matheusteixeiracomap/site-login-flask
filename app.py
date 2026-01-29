from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave_super_secreta")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    cur.execute("SELECT 1 FROM users WHERE username = %s", ('admin',))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (nome, username, senha, role) VALUES (%s, %s, %s, %s)",
            (
                'Administrador',
                'admin',
                generate_password_hash('admin123'),
                'admin'
            )
        )

    conn.commit()
    cur.close()
    conn.close()

# 🔥 EXECUTA NA SUBIDA DO APP
try:
    init_db()
except Exception as e:
    print("Erro ao iniciar banco:", e)

# ================= LOGIN =================
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

        return render_template('login.html', error="Usuário ou senha inválidos")

    return render_template('login.html')

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# ================= USUÁRIOS =================
@app.route('/usuarios', methods=['GET', 'POST'])
def usuarios():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    conn = get_db()
    cur = conn.cursor()

    # CADASTRAR USUÁRIO
    if request.method == 'POST':
        nome = request.form.get('nome')
        username = request.form.get('username')
        senha = request.form.get('senha')
        confirmar = request.form.get('confirmar_senha')
        role = request.form.get('role')

        if senha != confirmar:
            cur.execute("SELECT id, nome, username, role FROM users ORDER BY id")
            usuarios = cur.fetchall()
            cur.close()
            conn.close()
            return render_template(
                'usuarios.html',
                usuarios=usuarios,
                error="As senhas não conferem"
            )

        try:
            cur.execute(
                "INSERT INTO users (nome, username, senha, role) VALUES (%s, %s, %s, %s)",
                (nome, username, generate_password_hash(senha), role)
            )
            conn.commit()
            success = "Usuário cadastrado com sucesso!"
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            success = None
            error = "Usuário já existe"
        else:
            error = None

    else:
        success = None
        error = None

    # LISTAR USUÁRIOS
    cur.execute("SELECT id, nome, username, role FROM users ORDER BY id")
    usuarios = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'usuarios.html',
        usuarios=usuarios,
        success=success,
        error=error
    )


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
