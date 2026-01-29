from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
from flask import Flask, render_template, request, redirect, session, flash


app = Flask(__name__)
app.secret_key = "chave_super_secreta"

# ===============================
# CONEXÃO COM O BANCO
# ===============================
def get_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# ===============================
# CRIAR TABELA AUTOMATICAMENTE
# ===============================
def criar_tabela():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    db.commit()
    cursor.close()
    db.close()

# Executa na inicialização do app
criar_tabela()

# ===============================
# LOGIN
# ===============================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        senha = request.form["password"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (user,)
        )
        usuario = cursor.fetchone()

        cursor.close()
        db.close()

        if usuario and check_password_hash(usuario[2], senha):
            session["user"] = user
            return redirect("/dashboard")
        else:
            flash("Usuário ou senha inválidos", "error")

    return render_template("login.html")


# ===============================
# CADASTRO
# ===============================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form["username"]
        senha = generate_password_hash(request.form["password"])

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (user, senha)
        )
        db.commit()

        cursor.close()
        db.close()

        return redirect("/")

    return render_template("register.html")

# ===============================
# DASHBOARD (PROTEGIDO)
# ===============================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html")

# ===============================
# LOGOUT
# ===============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ===============================
# START
# ===============================
if __name__ == "__main__":
    app.run()
