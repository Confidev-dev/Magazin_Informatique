CREATE DATABASE IF NOT EXISTS magasin_informatique CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE magasin_informatique;

CREATE TABLE clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(50) NOT NULL,
    prenom VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    adresse VARCHAR(150),
    telephone VARCHAR(20)
);

CREATE TABLE produits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    description TEXT,
    prix DECIMAL(10,2) NOT NULL DEFAULT 0,
    stock INT NOT NULL DEFAULT 0,
    image VARCHAR(100)
);

CREATE TABLE commandes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_client INT NOT NULL,
    date_commande DATE NOT NULL,
    total DECIMAL(10,2) DEFAULT 0,
    statut VARCHAR(30) DEFAULT 'En attente',
    FOREIGN KEY (id_client) REFERENCES clients(id)
);

CREATE TABLE details_commandes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_commande INT NOT NULL,
    id_produit INT NOT NULL,
    quantite INT NOT NULL,
    prix_unitaire DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (id_commande) REFERENCES commandes(id),
    FOREIGN KEY (id_produit) REFERENCES produits(id)
);

INSERT INTO clients (nom, prenom, email, password) VALUES ('Dupont', 'Marie', 'marie@gmail.com', '1234');
INSERT INTO produits (nom, prix, stock) VALUES ('Ordinateur', 699.99, 10), ('Souris', 19.99, 50);
INSERT INTO commandes (id_client, date_commande) VALUES (1, '2026-06-01');
INSERT INTO details_commandes (id_commande, id_produit, quantite, prix_unitaire) VALUES (1, 1, 1, 699.99);
