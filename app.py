import hashlib
import random
from flask import Flask, render_template, request, redirect, flash, url_for, session
from functools import wraps
import mysql.connector

app = Flask(__name__)
app.secret_key = "remplace_par_une_cle_secrete_aleatoire_pour_le_tp"

# Paramètres de sécurité des sessions
app.config.update(SESSION_COOKIE_HTTPONLY=True, PERMANENT_SESSION_LIFETIME=1800)

# Connexion BDD
db = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="",
    database="magasin_informatique",
)

# --- DÉCORATEUR DE SÉCURITÉ ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Vous devez être connecté pour accéder à cette page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- INITIALISATION BDD ---
try:
    cursor_repare = db.cursor()
    bon_hache = hashlib.sha256("1234".encode('utf-8')).hexdigest()
    cursor_repare.execute("UPDATE clients SET password = %s", (bon_hache,))
    db.commit()
    cursor_repare.close()
    print(f"\n[BDD] Succès : Mots de passe synchronisés sur '1234'\n")
except Exception as e:
    print(f"\n[BDD] Erreur : {e}\n")

# --- ROUTES ---
@app.route("/")
def accueil():
    return render_template("accueil.html")

# INSCRIPTION
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nom_saisi = request.form["nom"].strip()
        prenom_saisi = request.form["prenom"].strip()
        email_saisi = request.form["email"].strip().lower()
        mdp_saisi = request.form["password"].strip()
        adresse_saisie = request.form["adresse"].strip()
        numero_saisi = request.form["numero"].strip()
        
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id FROM clients WHERE LOWER(email) = %s", (email_saisi,))
        if cursor.fetchone():
            flash("Cette adresse email est déjà utilisée.")
            cursor.close()
            return redirect(url_for('register'))
        cursor.close()

        session['temp_nom'] = nom_saisi
        session['temp_prenom'] = prenom_saisi
        session['temp_email'] = email_saisi
        session['temp_password'] = mdp_saisi
        session['temp_adresse'] = adresse_saisie
        session['temp_numero'] = numero_saisi
        session['code_attendu'] = str(random.randint(1000, 9999))
        return redirect(url_for('verification'))
    return render_template("inscription.html")

@app.route("/verification", methods=["GET", "POST"])
def verification():
    if request.method == "POST":
        code_saisi = request.form["code"]
        if code_saisi == session.get('code_attendu'):
            nom = session.pop('temp_nom')
            prenom = session.pop('temp_prenom')
            email = session.pop('temp_email')
            mdp = session.pop('temp_password')
            adresse = session.pop('temp_adresse')
            telephone = session.pop('temp_numero')
            session.pop('code_attendu')
            
            mdp_hache = hashlib.sha256(mdp.encode('utf-8')).hexdigest()
            cursor = db.cursor()
            cursor.execute("INSERT INTO clients (nom, prenom, email, password, adresse, telephone) VALUES (%s, %s, %s, %s, %s, %s)", 
                           (nom, prenom, email, mdp_hache, adresse, telephone))
            db.commit()
            cursor.close()
            flash("Inscription validée avec succès !")
            return redirect(url_for('login'))
        else:
            flash("Code incorrect.")
    return render_template("verification.html")

# --- PANIER ---
@app.route('/ajouter_panier', methods=['POST'])
@login_required
def ajouter_panier():
    id_client = session['user_id']
    id_produit = int(request.form['id_produit'])
    quantite = int(request.form['quantite'])
    cursor = db.cursor()
    cursor.execute("INSERT INTO panier (id_client, id_produit, quantite) VALUES (%s, %s, %s)", (id_client, id_produit, quantite))
    db.commit()
    cursor.close()
    flash("Produit ajouté au panier !")
    return redirect(url_for('commander', id_client=id_client))

@app.route("/panier")
@login_required
def afficher_panier():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT panier.id, produits.nom, panier.quantite 
        FROM panier 
        JOIN produits ON panier.id_produit = produits.id 
        WHERE panier.id_client = %s
    """, (session['user_id'],))
    articles = cursor.fetchall()
    cursor.close()
    return render_template("panier.html", articles=articles)

# SUPPRESSION / MODIFICATION
@app.route('/supprimer_panier/<int:id_panier>', methods=['POST'])
@login_required
def supprimer_panier(id_panier):
    cursor = db.cursor()
    cursor.execute("DELETE FROM panier WHERE id = %s AND id_client = %s", (id_panier, session['user_id']))
    db.commit()
    cursor.close()
    flash("Produit supprimé du panier.")
    return redirect(url_for('afficher_panier'))

@app.route('/modifier_panier/<int:id_panier>', methods=['POST'])
@login_required
def modifier_panier(id_panier):
    nouvelle_quantite = int(request.form['quantite'])
    if nouvelle_quantite > 0:
        cursor = db.cursor()
        cursor.execute("UPDATE panier SET quantite = %s WHERE id = %s AND id_client = %s", 
                       (nouvelle_quantite, id_panier, session['user_id']))
        db.commit()
        cursor.close()
    return redirect(url_for('afficher_panier'))

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email_saisi = request.form["email"].strip().lower()
        mdp_saisi = request.form["password"].strip()
        if email_saisi == "admin" and mdp_saisi == "1234":
            session['user_id'] = 'admin'
            return redirect("/admin")
        
        mdp_hache = hashlib.sha256(mdp_saisi.encode('utf-8')).hexdigest()
        cursor = db.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT id FROM clients WHERE LOWER(email) = %s AND password = %s", (email_saisi, mdp_hache))
        client = cursor.fetchone()
        cursor.close()
        if client:
            session['user_id'] = client['id']
            return redirect(f"/client/{client['id']}")
        else:
            flash("Erreur login")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# PAGE CLIENT
@app.route("/client/<int:id_client>")
@login_required
def client(id_client):
    if session['user_id'] != id_client and session['user_id'] != 'admin':
        return "Accès interdit", 403
    cursor = db.cursor(dictionary=True, buffered=True)
    cursor.execute("""
        SELECT produits.nom, produits.prix, details_commandes.quantite
        FROM details_commandes
        JOIN commandes ON commandes.id = details_commandes.id_commande
        JOIN produits ON produits.id = details_commandes.id_produit
        WHERE commandes.id_client = %s
    """, (id_client,))
    produits = cursor.fetchall()
    cursor.close()
    return render_template("client.html", produits=produits, id_client=id_client)

# COMMANDER
@app.route('/client/<int:id_client>/commander', methods=['GET'])
@login_required
def commander(id_client):
    if session['user_id'] != id_client and session['user_id'] != 'admin':
        return "Accès interdit", 403
    cursor = db.cursor(dictionary=True, buffered=True)
    cursor.execute("SELECT * FROM produits WHERE stock > 0")
    produits = cursor.fetchall()
    cursor.close()
    return render_template('commander.html', id_client=id_client, produits=produits)

# VALIDER COMMANDE
@app.route('/valider_commande', methods=['POST'])
@login_required
def valider_commande():
    id_client = session['user_id']
    cursor = db.cursor()
    cursor.execute("DELETE FROM panier WHERE id_client = %s", (id_client,))
    db.commit()
    cursor.close()
    flash("Commande validée avec succès !")
    return redirect(url_for('client', id_client=id_client))

# ADMIN
@app.route("/admin")
@login_required
def admin():
    if session['user_id'] != 'admin': return "Accès interdit", 403
    cursor = db.cursor(dictionary=True, buffered=True)
    cursor.execute("SELECT * FROM produits")
    prods = cursor.fetchall()
    cursor.execute("SELECT * FROM clients")
    clients = cursor.fetchall()
    cursor.close()
    return render_template("admin.html", produits=prods, clients=clients)

if __name__ == "__main__":
    app.run(debug=True)