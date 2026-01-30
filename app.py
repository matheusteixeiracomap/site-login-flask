from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import psycopg2
import psycopg2.extras
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave_super_secreta")

DATABASE_URL = os.environ.get("DATABASE_URL")

# ================= UPLOAD =================
UPLOAD_FOLDER = "static/notas_fiscais"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ================= BANCO =================
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Cria tabela users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Cria tabela estoque
    cur.execute("""
        CREATE TABLE IF NOT EXISTS estoque (
            id SERIAL PRIMARY KEY,
            produto TEXT NOT NULL,
            categoria TEXT,
            quantidade INTEGER DEFAULT 0,
            minimo INTEGER DEFAULT 0,
            valor NUMERIC(10,2) DEFAULT 0,
            fornecedor TEXT,
            nota_fiscal TEXT
        )
    """)

    # Cria tabela funcionarios
    cur.execute("""
        CREATE TABLE IF NOT EXISTS funcionarios (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            matricula TEXT UNIQUE,
            cargo TEXT,
            setor TEXT,
            data_admissao DATE,
            ativo BOOLEAN DEFAULT TRUE
        )
    """)

    # Cria admin se não existir
    cur.execute("SELECT 1 FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (nome, username, senha, role) VALUES (%s,%s,%s,%s)",
            ("Administrador", "admin", generate_password_hash("admin123"), "admin")
        )

    conn.commit()
    cur.close()
    conn.close()


init_db()

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        senha = request.form["senha"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, nome, senha, role FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user[2], senha):
            session["user_id"] = user[0]
            session["nome"] = user[1]
            session["role"] = user[3]
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Usuário ou senha inválidos")

    return render_template("login.html")

@app.route("/usuarios")
def usuarios():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nome, username, role FROM users ORDER BY nome")
    usuarios = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("usuarios.html", usuarios=usuarios)




# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

# ================= ESTOQUE =================
@app.route("/estoque", methods=["GET", "POST"])
def estoque():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == "POST":
        produto = request.form["produto"]
        categoria = request.form["categoria"]
        quantidade = int(request.form["quantidade"])
        minimo = int(request.form["minimo"])
        valor = request.form["valor"] or 0
        fornecedor = request.form["fornecedor"]

        arquivo = request.files.get("nota_fiscal")
        nome_arquivo = None

        if arquivo and arquivo.filename:
            nome_arquivo = secure_filename(arquivo.filename)
            arquivo.save(os.path.join(app.config["UPLOAD_FOLDER"], nome_arquivo))

        cur.execute("""
            INSERT INTO estoque
            (produto, categoria, quantidade, minimo, valor, fornecedor, nota_fiscal)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (produto, categoria, quantidade, minimo, valor, fornecedor, nome_arquivo))

        conn.commit()

    cur.execute("SELECT * FROM estoque ORDER BY produto")
    itens = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("estoque.html", itens=itens)

# ================= FUNCIONÁRIOS =================
@app.route("/funcionarios", methods=["GET", "POST"])
def funcionarios():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    error = success = None

    if request.method == "POST":
        try:
            cur.execute("""
                INSERT INTO funcionarios (nome, matricula, cargo, setor, data_admissao)
                VALUES (%s,%s,%s,%s,%s)
            """, (
                request.form["nome"],
                request.form["matricula"],
                request.form["cargo"],
                request.form["setor"],
                request.form["data_admissao"]
            ))
            conn.commit()
            success = "Funcionário cadastrado com sucesso!"
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            error = "Matrícula já cadastrada"

    cur.execute("SELECT * FROM funcionarios ORDER BY nome")
    funcionarios = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("funcionarios.html", funcionarios=funcionarios, error=error, success=success)

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
