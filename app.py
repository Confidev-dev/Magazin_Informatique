import os
import re
import bcrypt
import uuid
from flask import Flask, render_template, request, redirect, url_for
from mysql.connector import pooling
from flask_mail import Mail, Message

app = Flask(__name__)

# Config BDD
db_config = {
    "host": os.getenv("DB_HOST", "db"),
    "user": "root",
    "password": "ton_mot_de_passe",
    "database": "magasin_informatique"
}

# Config Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'False') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'True') == 'True'
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))

mail = Mail(app)

db_pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **db_config)

def get_db():
    return db_pool.get_connection()

# ACCUEIL
@app.route("/")
def accueil():
    return render_template("accueil.html")

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        # Bypass admin (à retirer en prod)
        if email == "admin" and password == "1234":
            return redirect("/admin")

        conn = get_db()
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT id, password, is_verified FROM clients WHERE email=%s", (email,))
        client = cursor.fetchone()
        cursor.close()
        conn.close()

        if client:
            if not client['is_verified']:
                return "Veuillez vérifier votre email avant de vous connecter."
            
            if bcrypt.checkpw(password.encode('utf-8'), client['password'].encode('utf-8')):
                return redirect(f"/client/{client['id']}")
            
        return "Erreur login : identifiants incorrects"
        
    return render_template("login.html")

# PAGE CLIENT
@app.route("/client/<int:id_client>")
def client(id_client):
    conn = get_db()
    cursor = conn.cursor(dictionary=True, buffered=True)
    cursor.execute("""
        SELECT p.nom, p.prix, dc.quantite
        FROM details_commandes dc
        JOIN commandes c ON dc.id_commande = c.id
        JOIN produits p ON dc.id_produit = p.id
        WHERE c.id_client = %s
    """, (id_client,))
    produits = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("client.html", produits=produits, id_client=id_client)

# PAGE ADMIN
@app.route("/admin")
def admin():
    conn = get_db()
    cursor = conn.cursor(dictionary=True, buffered=True)
    cursor.execute("SELECT * FROM produits")
    p = cursor.fetchall()
    cursor.execute("SELECT * FROM clients")
    c = cursor.fetchall()
    cursor.execute("SELECT * FROM commandes")
    cmd = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin.html", produits=p, clients=c, commandes=cmd)

# PAGE COMMANDER
@app.route("/client/<int:id_client>/commander", methods=["GET", "POST"])
def commander(id_client):
    conn = get_db()
    if request.method == "POST":
        id_prod = request.form["id_produit"]
        qte = int(request.form["quantite"])
        cursor = conn.cursor()
        
        cursor.execute("SELECT stock, prix FROM produits WHERE id=%s", (id_prod,))
        prod = cursor.fetchone()
        
        if prod and prod[0] >= qte:
            cursor.execute("INSERT INTO commandes (id_client, date_commande) VALUES (%s, CURDATE())", (id_client,))
            id_cmd = cursor.lastrowid
            cursor.execute("INSERT INTO details_commandes (id_commande, id_produit, quantite, prix_unitaire) VALUES (%s, %s, %s, %s)",
                           (id_cmd, id_prod, qte, prod[1]))
            cursor.execute("UPDATE produits SET stock = stock - %s WHERE id=%s", (qte, id_prod))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(f"/client/{id_client}")
        
        cursor.close()
        conn.close()
        return render_template("erreur_stock.html", id_client=id_client)

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nom, prix FROM produits WHERE stock > 0")
    produits = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("commander.html", produits=produits, id_client=id_client)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        nom = request.form["nom"]
        prenom = request.form["prenom"]
        email = request.form["email"]
        adresse = request.form.get("adresse")
        telephone = request.form.get("telephone")
        password = request.form["password"]

        # --- VALIDATION MOT DE PASSE ---
        # 1. Longueur min 8
        # 2. Au moins une majuscule, une minuscule et un chiffre (optionnel mais conseillé)
        if len(password) < 8:
            return "Le mot de passe doit faire au moins 8 caractères."
        if not re.search(r"[A-Z]", password) or not re.search(r"[0-9]", password):
            return "Le mot de passe doit contenir au moins une majuscule et un chiffre."
        # -------------------------------

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        token = str(uuid.uuid4())

        conn = get_db()
        cursor = conn.cursor(buffered=True)
        
        try:
            cursor.execute("SELECT id FROM clients WHERE email = %s", (email,))
            if cursor.fetchone():
                return "Cet email est déjà utilisé."

            sql = """INSERT INTO clients (nom, prenom, email, adresse, telephone, password, verification_token) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (nom, prenom, email, adresse, telephone, hashed_pw.decode('utf-8'), token))
            
            # Envoi du mail de vérification
            msg = Message("Vérification de votre compte", recipients=[email])
            link = url_for('verify', token=token, _external=True)
            msg.body = f"Bonjour {prenom}, veuillez cliquer sur ce lien pour vérifier votre compte : {link}"
            mail.send(msg)

            conn.commit()
            return "Un email de vérification a été envoyé. Veuillez vérifier votre boîte de réception."
            
        except Exception as e:
            return f"Erreur critique : {e}"
        finally:
            cursor.close()
            conn.close()
            
    return render_template("signup.html")

@app.route("/verify/<token>")
def verify(token):
    conn = get_db()
    cursor = conn.cursor(buffered=True)
    try:
        cursor.execute("SELECT id FROM clients WHERE verification_token = %s", (token,))
        client = cursor.fetchone()
        if client:
            cursor.execute("UPDATE clients SET is_verified = TRUE, verification_token = NULL WHERE id = %s", (client[0],))
            conn.commit()
            return "Votre compte a été vérifié avec succès ! Vous pouvez maintenant vous <a href='/login'>connecter</a>."
        else:
            return "Lien de vérification invalide ou expiré."
    except Exception as e:
        return f"Erreur : {e}"
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)