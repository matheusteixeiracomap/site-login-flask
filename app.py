from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
from datetime import date

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave_super_secreta")

DATABASE_URL = os.environ.get("DATABASE_URL")

# ===============================
# CONEXÃO COM BANCO
# ===============================
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # USUÁRIOS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # ESTOQUE (ATUALIZADO)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS estoque (
            id SERIAL PRIMARY KEY,
            produto TEXT NOT NULL,
            categoria TEXT,
            quantidade INTEGER DEFAULT 0,
            minimo INTEGER DEFAULT 0,
            valor NUMERIC(10,2),
            data_entrada DATE,
            fornecedor TEXT,
            nota_fiscal TEXT
        )
    """)

    # ADMIN PADRÃO
    cur.execute("SELECT 1 FROM users WHERE username = %s", ('admin',))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users (nome, username, senha, role)
            VALUES (%s, %s, %s, %s)
        """, (
            'Administrador',
            'admin',
            generate_password_hash('admin123'),
            'admin'
        ))

    conn.commit()
    cur.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print("Erro ao iniciar banco:", e)

# ================= USUÁRIOS =================
@app.route('/usuarios')
def usuarios():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nome, username, role FROM users ORDER BY nome")
    usuarios = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('usuarios.html', usuarios=usuarios)


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

# ================= ESTOQUE (MENU) =================
@app.route('/estoque')
def estoque():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('estoque.html')

# ================= CADASTRO DE PRODUTO =================
@app.route('/estoque/cadastro', methods=['GET', 'POST'])
def cadastro_produto():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        produto = request.form.get('produto')
        categoria = request.form.get('categoria')
        quantidade = int(request.form.get('quantidade'))
        minimo = int(request.form.get('minimo') or 0)
        valor = request.form.get('valor')
        data_entrada = request.form.get('data_entrada') or date.today()
        fornecedor = request.form.get('fornecedor')
        nota_fiscal = request.form.get('nota_fiscal')

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO estoque
            (produto, categoria, quantidade, minimo, valor, data_entrada, fornecedor, nota_fiscal)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            produto,
            categoria,
            quantidade,
            minimo,
            valor,
            data_entrada,
            fornecedor,
            nota_fiscal
        ))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('estoque'))

    return render_template('cadastro_produto.html')

# ================= ENTRADA DE ESTOQUE =================
@app.route('/estoque/entrada', methods=['GET', 'POST'])
def entrada_estoque():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        produto_id = request.form.get('produto_id')
        quantidade = int(request.form.get('quantidade'))

        cur.execute("""
            UPDATE estoque
            SET quantidade = quantidade + %s
            WHERE id = %s
        """, (quantidade, produto_id))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('estoque'))

    cur.execute("""
        SELECT id, produto, quantidade
        FROM estoque
        ORDER BY produto
    """)
    produtos = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('entrada_estoque.html', produtos=produtos)

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
