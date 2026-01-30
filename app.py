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
        CREATE TABLE IF NOT EXISTS estoque (
            id SERIAL PRIMARY KEY,
            produto TEXT NOT NULL,
            categoria TEXT,
            quantidade INTEGER NOT NULL,
            minimo INTEGER NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS estoque_mov (
            id SERIAL PRIMARY KEY,
            estoque_id INTEGER REFERENCES estoque(id) ON DELETE CASCADE,
            tipo TEXT NOT NULL, -- entrada / saida / ajuste
            quantidade INTEGER NOT NULL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    error = None
    success = None

    # 🔎 BUSCA
    search = request.args.get('search', '')

    # 🗑️ EXCLUIR
    if request.args.get('delete'):
        user_id = request.args.get('delete')

        cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        role = cur.fetchone()

        if role and role[0] == 'admin':
            error = "Não é permitido excluir o administrador"
        else:
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            success = "Usuário excluído com sucesso!"

    # ➕ CADASTRAR
    if request.method == 'POST':
        nome = request.form.get('nome')
        username = request.form.get('username')
        senha = request.form.get('senha')
        confirmar = request.form.get('confirmar_senha')
        role = request.form.get('role')

        if senha != confirmar:
            error = "As senhas não conferem"
        else:
            try:
                cur.execute(
                    "INSERT INTO users (nome, username, senha, role) VALUES (%s, %s, %s, %s)",
                    (nome, username, generate_password_hash(senha), role)
                )
                conn.commit()
                success = "Usuário cadastrado com sucesso!"
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                error = "Usuário já existe"

    # 📋 LISTAR
    if search:
        cur.execute(
            "SELECT id, nome, username, role FROM users WHERE nome ILIKE %s OR username ILIKE %s ORDER BY id",
            (f"%{search}%", f"%{search}%")
        )
    else:
        cur.execute("SELECT id, nome, username, role FROM users ORDER BY id")

    usuarios = cur.fetchall()

    # 📊 CONTADOR
    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template(
        'usuarios.html',
        usuarios=usuarios,
        total=total,
        error=error,
        success=success,
        search=search
    )

@app.route('/estoque/editar/<int:id>', methods=['GET', 'POST'])
def editar_produto(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        produto = request.form.get('produto')
        categoria = request.form.get('categoria')
        quantidade = int(request.form.get('quantidade'))
        minimo = int(request.form.get('minimo'))

        # quantidade anterior
        cur.execute("SELECT quantidade FROM estoque WHERE id = %s", (id,))
        qtd_antiga = cur.fetchone()[0]

        cur.execute("""
            UPDATE estoque
            SET produto=%s, categoria=%s, quantidade=%s, minimo=%s
            WHERE id=%s
        """, (produto, categoria, quantidade, minimo, id))

        # histórico (ajuste)
        diff = quantidade - qtd_antiga
        if diff != 0:
            cur.execute("""
                INSERT INTO estoque_mov (estoque_id, tipo, quantidade)
                VALUES (%s, %s, %s)
            """, (id, 'ajuste', diff))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('estoque'))

    cur.execute("SELECT * FROM estoque WHERE id = %s", (id,))
    item = cur.fetchone()

    cur.close()
    conn.close()
    return render_template('editar_estoque.html', item=item)

@app.route('/estoque/excluir/<int:id>')
def excluir_produto(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM estoque WHERE id = %s", (id,))
    conn.commit()

    cur.close()
    conn.close()
    return redirect(url_for('estoque'))

@app.route('/estoque/historico/<int:id>')
def historico_estoque(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT e.produto, m.tipo, m.quantidade, m.data
        FROM estoque_mov m
        JOIN estoque e ON e.id = m.estoque_id
        WHERE e.id = %s
        ORDER BY m.data DESC
    """, (id,))
    historico = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('historico_estoque.html', historico=historico)



# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
