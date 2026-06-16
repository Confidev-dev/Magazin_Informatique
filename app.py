import hashlib
from flask import Flask, render_template, request, redirect
import mysql.connector

app = Flask(__name__)

# Connexion BDD
db = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="",
    database="magasin_informatique",
    ssl_disabled=True
)

# ------------------------------------------------------------------------
# FORCE LA RÉPARATION DE LA BASE DE DONNÉES AU DÉMARRAGE
# ------------------------------------------------------------------------
try:
    cursor_repare = db.cursor()
    # On calcule le hachage exact que Python va générer pour "1234"
    bon_hache = hashlib.sha256("1234".encode('utf-8')).hexdigest()
    
    # On force TOUS les clients de la base à avoir ce mot de passe haché
    cursor_repare.execute("UPDATE clients SET password = %s", (bon_hache,))
    db.commit()
    cursor_repare.close()
    print(f"\n[BDD] Succès : Tous les mots de passe ont été synchronisés sur '1234' (Hachage : {bon_hache})\n")
except Exception as e:
    print(f"\n[BDD] Erreur lors de la synchronisation automatique : {e}\n")
# ------------------------------------------------------------------------


# ACCUEIL
@app.route("/")
def accueil():
    return render_template("accueil.html")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email_saisi = request.form["email"].strip().lower()
        mdp_saisi = request.form["password"].strip()

        # --- FORCE BRUTE ADMIN ---
        if email_saisi == "admin" and mdp_saisi == "1234":
            return redirect("/admin")
        # --------------------------

        # Hachage du mot de passe tapé dans le formulaire
        mdp_hache = hashlib.sha256(mdp_saisi.encode('utf-8')).hexdigest()

        cursor = db.cursor(dictionary=True, buffered=True)

        # Requête SQL par paramètres (évite les bugs d'encodage et de guillemets)
        query = "SELECT id FROM clients WHERE LOWER(email) = %s AND password = %s"
        cursor.execute(query, (email_saisi, mdp_hache))
        
        client = cursor.fetchone()
        cursor.close()

        if client:
            return redirect(f"/client/{client['id']}")
        else:
            return "Erreur login", 200

    return render_template("login.html")


# PAGE CLIENT
@app.route("/client/<int:id_client>")
def client(id_client):
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


# PASSER UNE COMMANDE
@app.route('/client/<int:id_client>/commander', methods=['GET', 'POST'])
def commander(id_client):
    cursor = db.cursor(dictionary=True, buffered=True)

    if request.method == 'GET':
        cursor.execute("SELECT * FROM produits WHERE stock > 0")
        produits = cursor.fetchall()
        cursor.close()
        return render_template('commander.html', id_client=id_client, produits=produits)

    if request.method == 'POST':
        id_produit = int(request.form['id_produit'])
        quantite_demandee = int(request.form['quantite'])

        cursor.execute("SELECT * FROM produits WHERE id = %s", (id_produit,))
        produit = cursor.fetchone()

        if not produit or produit['stock'] < quantite_demandee:
            cursor.close()
            return "Stock insuffisant ou produit inexistant !", 400

        total_commande = produit['prix'] * quantite_demandee

        # Insertion commande globale
        cursor.execute(
            "INSERT INTO commandes (id_client, date_commande, total) VALUES (%s, NOW(), %s)",
            (id_client, total_commande)
        )
        id_commande = cursor.lastrowid

        # Insertion détails de la commande
        cursor.execute(
            "INSERT INTO details_commandes (id_commande, id_produit, quantite, prix_unitaire) VALUES (%s, %s, %s, %s)",
            (id_commande, id_produit, quantite_demandee, produit['prix'])
        )

        # Mise à jour des stocks
        cursor.execute(
            "UPDATE produits SET stock = stock - %s WHERE id = %s",
            (quantite_demandee, id_produit)
        )

        db.commit()
        cursor.close()
        return redirect(f'/client/{id_client}')


# PAGE ADMIN
@app.route("/admin")
def admin():
    cursor = db.cursor(dictionary=True, buffered=True)
    cursor.execute("SELECT * FROM produits")
    produits = cursor.fetchall()
    
    cursor.execute("SELECT * FROM clients")
    clients = cursor.fetchall()
    
    cursor.close()
    return render_template("admin.html", produits=produits, clients=clients)


# ROUTE SECRETE POUR LE TP
@app.route("/password")
def voir_les_mdp():
    cursor = db.cursor(dictionary=True, buffered=True)
    cursor.execute("SELECT email, password FROM clients")
    tous_les_clients = cursor.fetchall()
    cursor.close()
    
    html = "<h2>Liste des mots de passe des clients (Spécial TP) :</h2><ul>"
    for client in tous_les_clients:
        html += f"<li><strong>Email :</strong> {client['email']} | <strong>Mot de passe :</strong> {client['password']}</li>"
    html += "</ul>"
    
    return html


if __name__ == "__main__":
    app.run(debug=True)