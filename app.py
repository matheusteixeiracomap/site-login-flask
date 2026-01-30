from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_key")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # USERS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # ESTOQUE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS estoque (
            id SERIAL PRIMARY KEY,
            produto TEXT NOT NULL,
            categoria TEXT,
            quantidade INTEGER NOT NULL DEFAULT 0,
            minimo INTEGER NOT NULL DEFAULT 0
        )
    """)

    # MOVIMENTAÇÃO
    cur.execute("""
        CREATE TABLE IF NOT EXISTS estoque_mov (
            id SERIAL PRIMARY KEY,
            estoque_id INTEGER REFERENCES estoque(id) ON DELETE CASCADE,
            tipo TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ADMIN PADRÃO
    cur.execute("SELECT 1 FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users (nome, username, senha, role)
            VALUES (%s, %s, %s, %s)
        """, ('Administrador', 'admin', generate_password_hash('admin123'), 'admin'))

    conn.commit()
    cur.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print("Erro DB:", e)

# ================= LOGIN =================
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        senha = request.form['senha']

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, nome, senha, role FROM users WHERE username=%s", (username,))
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
    error = success = None

    if request.args.get('delete'):
        uid = request.args.get('delete')
        cur.execute("SELECT role FROM users WHERE id=%s", (uid,))
        if cur.fetchone()[0] == 'admin':
            error = "Não pode excluir o admin"
        else:
            cur.execute("DELETE FROM users WHERE id=%s", (uid,))
            conn.commit()
            success = "Usuário excluído"

    if request.method == 'POST':
        if request.form['senha'] != request.form['confirmar']:
            error = "Senhas não conferem"
        else:
            try:
                cur.execute("""
                    INSERT INTO users (nome, username, senha, role)
                    VALUES (%s,%s,%s,%s)
                """, (
                    request.form['nome'],
                    request.form['username'],
                    generate_password_hash(request.form['senha']),
                    request.form['role']
                ))
                conn.commit()
                success = "Usuário cadastrado"
            except:
                conn.rollback()
                error = "Usuário já existe"

    cur.execute("SELECT id, nome, username, role FROM users ORDER BY id")
    usuarios = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('usuarios.html', usuarios=usuarios, error=error, success=success)

# ================= ESTOQUE =================
@app.route('/estoque', methods=['GET', 'POST'])
def estoque():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        cur.execute("""
            INSERT INTO estoque (produto, categoria, quantidade, minimo)
            VALUES (%s,%s,%s,%s)
        """, (
            request.form['produto'],
            request.form['categoria'],
            request.form['quantidade'],
            request.form['minimo']
        ))
        conn.commit()

    cur.execute("SELECT * FROM estoque ORDER BY produto")
    itens = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('estoque.html', itens=itens)

@app.route('/estoque/editar/<int:id>', methods=['GET', 'POST'])
def editar_produto(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        cur.execute("SELECT quantidade FROM estoque WHERE id=%s", (id,))
        old = cur.fetchone()[0]

        qtd = int(request.form['quantidade'])
        cur.execute("""
            UPDATE estoque SET produto=%s, categoria=%s, quantidade=%s, minimo=%s
            WHERE id=%s
        """, (
            request.form['produto'],
            request.form['categoria'],
            qtd,
            request.form['minimo'],
            id
        ))

        diff = qtd - old
        if diff != 0:
            cur.execute("""
                INSERT INTO estoque_mov (estoque_id, tipo, quantidade)
                VALUES (%s,'ajuste',%s)
            """, (id, diff))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('estoque'))

    cur.execute("SELECT * FROM estoque WHERE id=%s", (id,))
    item = cur.fetchone()

    cur.close()
    conn.close()
    return render_template('editar_estoque.html', item=item)

@app.route('/estoque/excluir/<int:id>')
def excluir_produto(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM estoque WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('estoque'))

@app.route('/estoque/historico/<int:id>')
def historico_estoque(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT tipo, quantidade, data
        FROM estoque_mov
        WHERE estoque_id=%s
        ORDER BY data DESC
    """, (id,))
    hist = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('historico_estoque.html', historico=hist)

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
