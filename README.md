# Plateforme-Publication-Articles

## Installation et configuration

```bash
# 1. Cloner le dépôt
git clone https://github.com/adam-dri/adam-dri-Plateforme-Publication-Articles.git

# 2. Se placer dans le dossier du projet
cd Plateforme-Publication-Articles

# 3. Créer et activer l’environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# 4. Installer les dépendances
pip install -r requirements.txt

# 5. Créer le fichier .env avec votre clé secrète
echo 'SECRET_KEY=VOTRE_CLE_ICI' > .env

Étapes pour lancer le projet
- source bin/activate
- export FLASK_APP=app.py
- flask run

Comptes déjà créés
- username = prof
- mot de passe = secret1234

- username = adam
- mot de passe = secret1234

Installation:
- sudo pip3 install virtualenv

Activation:
- source bin/activate
- flask run
