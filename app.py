from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'chave_super_secreta_123'

DB_NAME = 'database.db'


# =========================
#  BANCO DE DADOS
# =========================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    admin = conn.execute(
        "SELECT * FROM users WHERE username = 'admin'"
    ).fetchone()

    if not admin:
        senha_admin = generate_password_hash('admin123')
        conn.execute(
            "INSERT INTO users (nome, username, senha, role) VALUES (?, ?, ?, ?)",
            ('Administrador', 'admin', senha_admin, 'admin')
        )

    conn.commit()
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

        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?',
            (username,)
        ).fetchone()

        if user and check_password_hash(user['senha'], senha):
            session['user_id'] = user['id']
            session['nome'] = user['nome']
            session['role'] = user['role']
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
        email = request.form['email']
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
            db = get_db()
            db.execute(
                'INSERT INTO users (nome, email, senha, role) VALUES (?, ?, ?, ?)',
                (nome, email, senha_hash, role)
            )
            db.commit()
            return render_template(
                'register_user.html',
                success='Usuário cadastrado com sucesso!'
            )
        except sqlite3.IntegrityError:
            return render_template(
                'register_user.html',
                error='E-mail já cadastrado'
            )

    return render_template('register_user.html')


# =========================
#  LOGOUT
# =========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# =========================
#  START
# =========================
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
