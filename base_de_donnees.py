import sqlite3
import os
import hashlib
import base64
import uuid

CHEMIN_BD = f"{os.path.dirname(os.path.abspath(__file__))}/database.db"


def creer_bd():
    """
    Cette méthode permet de créer la base de données.
    De plus, elle crée aussi les tables articles, utilisateurs et sessions
    si elles n'existent pas déjà.

    Returns:
        str: Le chemin absolu de la base de données.
    """
    try:
        connexion = sqlite3.connect(CHEMIN_BD)
        curseur = connexion.cursor()

        table_articles = """
            CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT NOT NULL,
            identifiant TEXT UNIQUE NOT NULL CHECK(
                identifiant GLOB '[A-Za-z0-9_ éèàçôù-][A-Za-z0-9_ éèàçôù-]*'
                AND TRIM(identifiant) != ''
                AND LENGTH(TRIM(identifiant)) >= 2
            ),
            auteur TEXT NOT NULL,
            date_publication DATE NOT NULL,
            contenu TEXT NOT NULL,
            FOREIGN KEY (auteur) REFERENCES utilisateurs(username)
            );
            """

        table_utilisateurs = """
            CREATE TABLE IF NOT EXISTS utilisateurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt varchar(32),
                nom TEXT NOT NULL,
                prenom TEXT NOT NULL,
                photo_profil BLOB,
                etat INTEGER NOT NULL DEFAULT 1
            );
        """

        table_sessions = """
            CREATE TABLE IF NOT EXISTS sessions(
                id_session TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL
            );
            """

        curseur.execute(table_articles)
        connexion.commit()

        curseur.execute(table_utilisateurs)
        connexion.commit()

        curseur.execute(table_sessions)
        connexion.commit()

    except sqlite3.Error as e:
        print("Erreur lors de la création de la table:", e)
    finally:
        curseur.close()
        connexion.close()


class Database:
    def __init__(self):
        self.connexion = None

    def get_connexion(self):
        connexion = sqlite3.connect(CHEMIN_BD)
        connexion.row_factory = sqlite3.Row
        return connexion

    def deconnecter(self):
        if self.connexion is not None:
            self.connexion.close()

    def verifier_username_db(self, username):
        """
        Cette méthode vérifie si un utilisateur existe dans la base de données.

        Args:
            username (str): Le username de l'utilisateur
        Returns:
            Bool:
                - True => l'utilisateur existe
                - False => l'utilisateur inexistant
        """
        connexion = self.get_connexion()
        curseur = connexion.cursor()

        curseur.execute("SELECT username FROM utilisateurs WHERE username=?",
                        (username,))

        if curseur.fetchone() is not None:
            # username existe déjà
            return False
        else:
            # username inexistant
            return True

    def verifier_info_connexion(self, username, password_entre):
        """
        Cette méthode vérifie si les informations entrées
        sont existantes dans la base de données.

        Args:
            username (str): Le username de entrée.
            password_entre (str): Le mot de passe entrée.
        Returns:
            Bool:
                - True => l'utilisateur est validé.
                - False => l'utilisateur est inexistant ou
                le mot de passe est incorrect.
        """
        curseur = self.get_connexion().cursor()

        if not self.verifier_username_db(username):
            # Si le username n'existe pas, return False
            return False

        salt = curseur.execute("""SELECT salt FROM utilisateurs
        WHERE username=?""", (username, ))
        password_bd = curseur.execute("""SELECT password_hash FROM utilisateurs
        WHERE username=?""", (username, ))

        if (
                hashlib.sha512(
                    str(password_entre + salt).encode("utf-8")
                ).hexdigest() == password_bd
        ):
            return True
        else:
            return False

    def verifier_article_db(self, identifiant):
        """
        Cette méthode vérifie si un article existe dans la base de donnée.

        Args:
            identifiant (str): L'identifiant de l'article

        Returns:
            Bool:
                - True => Article inexistant
                - False => Article existant
        """
        connexion = self.get_connexion()
        curseur = connexion.cursor()

        curseur.execute("""SELECT identifiant FROM articles
        WHERE identifiant = ?""", (identifiant,))

        if curseur.fetchone() is not None:
            # Article éxiste déjà
            return False
        else:
            # Article inexistant
            return True

    def creer_utilisateur(self, username, password_hash,
                          salt, nom, prenom, photo_profil):
        """
        Cette méthode créer un utilisateur dans la base de donnée.

        Returns:
            Bool:
                - True => l'utilisateur existe
                - False => l'utilisateur inexistant
        """
        connexion = self.get_connexion()

        connexion.execute("""insert into utilisateurs(username, password_hash,
        salt, nom, prenom, photo_profil)
            values(?, ?, ?, ?, ?, ?)""", (username, password_hash,
                                          salt, nom, prenom, photo_profil))

        connexion.commit()

    def ajout_article(self, titre, identifiant, auteur,
                      date_publication, contenu):
        """
        Cette méthode ajoute un article à la base de données.
        """
        connexion = self.get_connexion()

        connexion.execute("""INSERT INTO articles(titre, identifiant,
         auteur, date_publication, contenu)
            VALUES(?, ?, ?, ?, ?)""", (titre, identifiant,
                                       auteur, date_publication, contenu))

        connexion.commit()

    def get_user_login_info(self, username):
        """
        Cette fonction retourne le salt, le password_hash et
        l'état de l'utilisateur s'il existe dans la bd.
        Returns:
            Tuple: (salt, password_hash, etat) ou
            None si l'utilisateur n'existe pas.
        """
        curseur = self.get_connexion().cursor()
        curseur.execute("""SELECT salt, password_hash, etat FROM utilisateurs
         WHERE username=?""", (username, ))
        user = curseur.fetchone()
        if user is None:
            return None
        else:
            return user[0], user[1], user[2]

    def save_session(self, id_session, username):
        connexion = self.get_connexion()
        connexion.execute(("""INSERT INTO sessions(id_session, username)
         VALUES (?, ?)"""), (id_session, username))
        connexion.commit()

    def delete_session(self, id_session):
        connexion = self.get_connexion()
        connexion.execute(("""DELETE FROM sessions WHERE id_session=?"""),
                          (id_session,))
        connexion.commit()

    def get_session(self, id_session):
        curseur = self.get_connexion().cursor()
        curseur.execute(("""SELECT username FROM sessions
         WHERE id_session=?"""), (id_session,))
        data = curseur.fetchone()
        if data is None:
            return None
        else:
            return data[0]

    def get_articles(self):
        """
        Cette méthode retourne la liste des articles en ordre de sortie.
        """
        articles = []
        curseur = self.get_connexion().cursor()

        curseur.execute("""SELECT * FROM articles
         ORDER BY date_publication DESC""")

        for i in curseur.fetchall():
            article = {
                "titre": i["titre"],
                "identifiant": i["identifiant"],
                "auteur": i["auteur"],
                "date_publication": i["date_publication"],
                "contenu": i["contenu"]
            }
            articles.append(article)

        return articles

    def get_utilisateurs(self):
        """
        Cette méthode retourne les utilisateurs inscrits.
        """
        utilisateurs = []
        connexion = self.get_connexion()
        connexion.row_factory = sqlite3.Row
        curseur = connexion.cursor()

        curseur.execute("SELECT * FROM utilisateurs")

        for i in curseur.fetchall():
            utilisateur = {
                "username": i["username"],
                "password_hash": i["password_hash"],
                "salt": i["salt"],
                "nom": i["nom"],
                "prenom": i["prenom"],
                "photo_profil":
                    base64.b64encode(i["photo_profil"]).decode("utf-8"),
                "etat": i["etat"]
            }
            utilisateurs.append(utilisateur)

        return utilisateurs

    def get_info_utilisateurs(self, username):
        """
        Cette méthode retourne les informations d'un utilisateurs.

        Args:
            username (str): Le username
        Returns:
            dictionnaire avec les informations
        """
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        curseur.execute("""SELECT * FROM utilisateurs
         WHERE username=?""", (username,))
        user = curseur.fetchone()
        if user is None:
            return None
        else:
            return {
                "username": user["username"],
                "nom": user["nom"],
                "prenom": user["prenom"],
                "photo_profil":
                    base64.b64encode(user["photo_profil"]).decode("utf-8")
                    if user["photo_profil"] else None,
                "etat": user["etat"]
            }

    def get_derniers_articles(self):
        """
        Cette méthode retournes les 5 derniers articles en date du jour.
        """
        articles = []
        curseur = self.get_connexion().cursor()

        curseur.execute("""SELECT id, titre, identifiant, auteur,
         date_publication, contenu FROM articles WHERE date_publication
          <= DATE('now')
          ORDER BY date_publication DESC LIMIT 5;""")

        for i in curseur.fetchall():
            article = {
                "id": i["id"],
                "titre": i["titre"],
                "identifiant": i["identifiant"],
                "auteur": i["auteur"],
                "date_publicaiton": i["date_publication"],
                "contenu": i["contenu"]
            }
            articles.append(article)

        return articles

    def get_article(self, identifiant_article):
        """
        Cette méthode retourne les informations sur un article.
        """
        curseur = self.get_connexion().cursor()

        curseur.execute("""SELECT * FROM articles
         WHERE identifiant=?""", (identifiant_article,))
        article = curseur.fetchone()

        if article is None:
            return None
        else:
            return {
                "titre": article["titre"],
                "identifiant": article["identifiant"],
                "auteur": article["auteur"],
                "date_publication": article["date_publication"],
                "contenu": article["contenu"]
            }

    def rechercher_article(self, recherche):
        """
        Cette méthode retourne tous les articles qui répondent à la recherche.
        """
        articles = []

        curseur = self.get_connexion().cursor()

        recherche = f"%{recherche.lower()}%"

        curseur.execute("""SELECT * FROM articles
             WHERE LOWER(titre) LIKE ?
                OR LOWER(auteur) LIKE ?
                OR LOWER(contenu) LIKE ?
                ORDER BY date_publication DESC
                """, (recherche, recherche, recherche))

        for article in curseur.fetchall():
            article = {
                "titre": article["titre"],
                "identifiant": article["identifiant"],
                "auteur": article["auteur"],
                "date_publication": article["date_publication"],
                "contenu": article["contenu"]
            }
            articles.append(article)

        return articles

    def modifier_article(self, identifiant_courant, nouveau_titre,
                         nouveau_identifiant, nouveau_contenu):
        """
        Cette méthode permet de modifier le contenu d'un article.
        """
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        curseur.execute("""UPDATE articles SET titre=?, identifiant=?,
         contenu=? WHERE identifiant=?""",
                        (nouveau_titre, nouveau_identifiant,
                         nouveau_contenu, identifiant_courant))
        connexion.commit()

    def changer_etat_utilisateur(self, username, nouvel_etat):
        """
        Cette méthode permet de changer le statut d'un utilisateur.
        1 = activé
        0 = désactivé
        """
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        curseur.execute("""UPDATE utilisateurs SET etat = ?
         WHERE username = ?""", (nouvel_etat, username))
        connexion.commit()

    def supprimer_article(self, identifiant):
        """
        Cette méthode permet de supprimer un article de la bd.
        """
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        curseur.execute("""DELETE FROM articles
         WHERE identifiant = ?""", (identifiant,))
        connexion.commit()
