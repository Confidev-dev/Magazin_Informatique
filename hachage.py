import hashlib
import mysql.connector

# Connexion à ta base de données
db = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="",
    database="magasin_informatique",
    ssl_disabled=True
)

cursor = db.cursor(dictionary=True)

# On désactive la sécurité Safe Update pour pouvoir modifier les lignes
cursor.execute("SET SQL_SAFE_UPDATES = 0;")

# On récupère tous les clients de la base
cursor.execute("SELECT id, email, password FROM clients")
clients = cursor.fetchall()

print("--- DEBUT DU HACHAGE ---")

for client in clients:
    id_client = client['id']
    email_client = client['email']
    mdp_clair = client['password'].strip()
    
    # Si le mot de passe fait déjà 64 caractères, il est déjà haché
    if len(mdp_clair) == 64:
        print(f"[Info] {email_client} est déjà haché.")
        continue
        
    # Calcul du hachage SHA-256 exact pour "1234"
    mdp_hache = hashlib.sha256(mdp_clair.encode('utf-8')).hexdigest()
    
    # On écrase le texte en clair par la version hachée dans MySQL
    cursor.execute(
        "UPDATE clients SET password = %s WHERE id = %s",
        (mdp_hache, id_client)
    )
    print(f"[Succès] {email_client} haché -> {mdp_hache[:10]}...")

# On valide les changements définitivement
db.commit()

cursor.close()
db.close()
print("--- FIN DU HACHAGE : TOUT EST OK ---")