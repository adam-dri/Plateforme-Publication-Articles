from flask import (
    Flask, render_template, redirect, request, url_for, g, make_response
)
from . import base_de_donnees
import os
import hashlib
import uuid
from functools import wraps
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
SECRET = os.getenv("SECRET_KEY")
if not SECRET:
    raise RuntimeError("La variable SECRET_KEY n'est pas définie !")
app.secret_key = SECRET



def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        g._database = base_de_donnees.Database()
    return g._database


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.deconnecter()


@app.context_processor
def inject_user():
    id_session = request.cookies.get("id_session")
    username = get_db().get_session(id_session) if id_session else None
    return dict(logged_in=(username is not None), current_user=username)


@app.route("/")
def page_acceuil():
    cinq_articles = get_db().get_derniers_articles()
    return render_template("index.html", cinq_articles=cinq_articles)


@app.route("/recherche", methods=["GET", "POST"])
def rechercher():
    recherche = request.args.get('q', '')
    articles = []
    if recherche:
        articles = get_db().rechercher_article(recherche)
    return render_template("/recherche.html",
                           articles=articles, recherche=recherche)


@app.route("/article/<identifiant>")
def page_article(identifiant):
    article = get_db().get_article(identifiant)
    if article is None:
        return "Article non trouvé", 404
    # Récupérer info auteur
    auteur = get_db().get_info_utilisateurs(article["auteur"])
    return render_template("article.html", article=article, auteur=auteur)


# Page de connexion
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            message = "Le nom d'utilisateur ou le mot de passe est incorrect"
            return render_template("/admin.html",
                                   username=username, message=message)

        user = get_db().get_user_login_info(username)
        if user is None:
            message = "Le nom d'utilisateur ou le mot de passe est incorrect"
            return render_template("/admin.html",
                                   username=username, message=message)

        # Vérifier si le compte est actif
        salt, password_hash_db, etat = user[0], user[1], user[2]
        if etat != 1:
            message = "Votre compte est désactivé."
            return render_template("admin.html",
                                   username=username, message=message)

        password_hash = hashlib.sha512(
            str(password + salt).encode("utf-8")
        ).hexdigest()
        if password_hash == user[1]:
            id_session = uuid.uuid4().hex
            get_db().save_session(id_session, username)
            # cookie session
            response = make_response(redirect(url_for("page_articles")))
            response.set_cookie("id_session", id_session)
            return response
        else:
            message = "Le nom d'utilisateur ou le mot de passe est incorrect"
            return render_template("/admin.html",
                                   username=username, message=message)
    else:
        return render_template("admin.html", username="")


# Connexion nécessaire
def authentication_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        id_session = request.cookies.get("id_session")
        if not id_session or get_db().get_session(id_session) is None:
            # flash("Vous devez être connecté pour accéder à cette page.")
            return redirect(url_for("admin"))
        return f(*args, **kwargs)
    return decorated_function


# Connexion nécessaire
@app.route("/liste-articles")
@authentication_required
def page_articles():
    message = request.args.get("message")
    return render_template("/liste-articles.html",
                           articles=get_db().get_articles(), message=message)


# Modiifer un article
@app.route("/admin/modifier><identifiant>", methods=["GET", "POST"])
@authentication_required
def modifier_article(identifiant):
    article = get_db().get_article(identifiant)
    if article is None:
        message = "Article non trouvé."
        return redirect(url_for("Page_article", message=message))

    if request.method == "POST":
        nouveau_titre = request.form.get("titre")
        nouveau_identifiant = request.form.get("identifiant")
        nouveau_contenu = request.form.get("contenu")

        # Vérifier que les champs sont remplis
        if (not nouveau_contenu
                or not nouveau_identifiant
                or not nouveau_contenu):
            message = "Tous les champs doivent être remplis."
            return render_template("modifier_article.html",
                                   article=article, message=message)

        if nouveau_identifiant != identifiant:
            if not get_db().verifier_article_db((nouveau_identifiant)):
                message = """L'identifiant existe déjà,
                veuillez en choisir un autre."""
                return render_template("modifier_article.html",
                                       article=article, message=message)

        get_db().modifier_article(identifiant, nouveau_titre,
                                  nouveau_identifiant, nouveau_contenu)
        return redirect(url_for("page_articles"))

    return render_template("modifier_article.html", article=article)


# Nouvel article
@app.route("/admin-nouveau", methods=["GET", "POST"])
@authentication_required
def page_ajout_admin():
    if request.method == "POST":
        titre = request.form.get("titre")
        identifiant = request.form.get("identifiant")
        date_publicaiton = request.form.get("date_publication")
        contenu = request.form.get("contenu")

        # Vérifier les champs
        if not titre or not identifiant or not date_publicaiton or not contenu:
            message = "Tous les champs sont obligatoies."
            return render_template("admin-nouveau.html",
                                   titre=titre,
                                   identifiant=identifiant,
                                   date_publicaiton=date_publicaiton,
                                   contenu=contenu,
                                   message=message)

        # Vérifier que l'identifiant n'existe pas
        if not get_db().verifier_article_db(identifiant):
            message = "L'identifiant existe déjà!"
            return render_template("admin-nouveau.html",
                                   titre=titre,
                                   identifiant=identifiant,
                                   date_publicaiton=date_publicaiton,
                                   contenu=contenu,
                                   message=message)

        # Auteur selon session
        id_session = request.cookies.get("id_session")
        auteur = get_db().get_session(id_session)

        # Ajouter l'article
        get_db().ajout_article(titre, identifiant, auteur,
                               date_publicaiton, contenu)
        message = "Article créé avec succès."
        return redirect(url_for("page_article",
                                identifiant=identifiant, message=message))
    # GET
    return render_template("admin-nouveau.html")


# Supprimer un article
@app.route("/supprimer_article/<identifiant>", methods=["POST"])
@authentication_required
def supprimer_article(identifiant):
    get_db().supprimer_article(identifiant)
    # Rediriger vers la liste des articles avec éventuellement un message
    return redirect(url_for("page_articles"))


@app.route("/utilisateurs")
@authentication_required
def page_utilisateurs():
    utilisateurs = get_db().get_utilisateurs()
    return render_template("utilisateurs.html", utilisateurs=utilisateurs)


@app.route("/changer_etat_utilisateur/<username>", methods=["POST"])
@authentication_required
def changer_etat_utilisateur(username):
    nouvel_etat = request.form.get("etat")
    try:
        nouvel_etat = int(nouvel_etat)
    except (ValueError, TypeError):
        nouvel_etat = 1
    get_db().changer_etat_utilisateur(username, nouvel_etat)
    return redirect(url_for("page_utilisateurs"))


@app.route("/form-utilisateurs", methods=["GET", "POST"])
@authentication_required
def page_ajout_utilisateur():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        prenom = request.form.get("prenom").title()
        nom = request.form.get("nom").title()
        photo_fichier = request.files.get("photo_profil")
        # Gérer photo
        if photo_fichier and photo_fichier.filename != "":
            photo_profil = photo_fichier.read()
        else:
            photo_par_defaut = f"""{os.path.dirname(os.path.abspath(__file__))}
            /static/robot.jpeg"""
            with open(photo_par_defaut, "rb") as fichier_photo:
                photo_profil = fichier_photo.read()

        # Gérer mot de passe
        salt = uuid.uuid4().hex
        password_hash = hashlib.sha512(
            str(password + salt).encode("utf-8")
        ).hexdigest()

        get_db().creer_utilisateur(username, password_hash,
                                   salt, nom, prenom, photo_profil)

        return redirect(url_for("page_utilisateurs"))

    # GET
    return render_template("form-utilisateurs.html")


@app.route("/logout")
def logout():
    # Récupérer l'identifiant de session depuis le cookie
    id_session = request.cookies.get("id_session")
    if id_session:
        get_db().delete_session(id_session)
    # Créer une réponse de redirection
    response = make_response(redirect("/"))
    # Supprimer le cookie "id_session"
    response.delete_cookie("id_session")
    return response


if __name__ == '__main__':
    app.run(debug=True)
