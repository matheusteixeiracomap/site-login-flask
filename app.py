from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "chave_super_secreta"

# ===============================
# CONEXÃO COM O BANCO
# ===============================
def get_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# ===============================
# CRIAR TABELA
# ===============================
def criar_tabela():
    try:
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
    except Exception as e:
        print("Erro ao criar tabela:", e)

criar_tabela()

# ===============================
# LOGIN
# ===============================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        senha = request.form.get("password")

        try:
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
                return redirect(url_for("dashboard"))
            else:
                flash("Usuário ou senha inválidos", "error")

        except Exception as e:
            flash("Erro interno no servidor", "error")
            print(e)

    return render_template("login.html")

# ===============================
# CADASTRO
# ===============================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form.get("username")
        senha = generate_password_hash(request.form.get("password"))

        try:
            db = get_db()
            cursor = db.cursor()

            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (user, senha)
            )
            db.commit()

            cursor.close()
            db.close()

            flash("Usuário cadastrado com sucesso!", "success")
            return redirect(url_for("login"))

        except psycopg2.errors.UniqueViolation:
            flash("Usuário já existe", "error")
        except Exception as e:
            flash("Erro ao cadastrar usuário", "error")
            print(e)

    return render_template("register.html")

# ===============================
# DASHBOARD
# ===============================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("dashboard.html", usuario=session["user"])



from flask import session, redirect, url_for

@app.route('/register-user', methods=['GET', 'POST'])
def register_user():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        confirmar = request.form['confirmar_senha']

        if senha != confirmar:
            return render_template(
                'register_user.html',
                error='As senhas não conferem'
            )

        return render_template(
            'register_user.html',
            success='Usuário cadastrado com sucesso!'
        )

    return render_template('register_user.html')


# ===============================
# LOGOUT
# ===============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ===============================
# START
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
