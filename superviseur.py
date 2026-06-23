import socket
from datetime import datetime

# Configuration des services
services = {
    "Flask": 5000,
    "MySQL": 3306
}

# Chemin pour le fichier rapport à la racine
fichier_rapport = "rapport.txt"

def tester_service(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except:
        return False

# Exécution et écriture
with open(fichier_rapport, "a") as f:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f.write(f"--- Rapport du {timestamp} ---\n")
    
    for nom, port in services.items():
        statut = "ACTIF" if tester_service(port) else "INACTIF"
        ligne = f"{nom} (Port {port}) : {statut}"
        print(ligne)
        f.write(ligne + "\n")
    
    f.write("\n")