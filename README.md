# Authentication Microservice — MSOA E-commerce

## Description

Microservice REST d'authentification développé avec Python et FastAPI dans le cadre du TP d'Architecture Orientée Microservices (MSOA).

Il permet l'inscription, la connexion, la récupération du profil et la déconnexion des utilisateurs.

## Technologies

- Python / FastAPI
- SQLite
- JWT (JSON Web Token)
- Argon2 (hachage des mots de passe)
- Uvicorn

## Installation

Créer un environnement virtuel :

```bash
python -m venv .venv
```

Installer les dépendances (Git Bash sur Windows) :

```bash
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Créer un fichier `.env` à partir de `.env.example` et remplacer la valeur de `AUTH_JWT_SECRET` par une clé secrète générée de manière sécurisée.

Lancer le serveur :

```bash
./.venv/Scripts/python.exe -m uvicorn main:app --reload --port 8081
```

Documentation API : http://localhost:8081/docs

## Endpoints REST

| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Inscription |
| POST | `/api/auth/login` | Connexion et génération JWT |
| GET | `/api/auth/me` | Profil de l'utilisateur connecté |
| POST | `/api/auth/logout` | Révocation du JWT |

## Communication avec React

Le frontend React est configuré avec `AUTH: "rest"` dans `src/config/backend.js` et communique avec le microservice sur le port 8081.

Le frontend utilise les API REST pour les opérations d'authentification et transmet le JWT dans l'en-tête Authorization pour les requêtes protégées.

## Sécurité

- Mots de passe hachés avec Argon2
- Tokens JWT signés et expirables
- Révocation des tokens lors de la déconnexion
- Configuration CORS pour le frontend React
- Secrets exclus du dépôt Git

## Tests

Les scénarios à vérifier sont l'inscription, la connexion, la récupération du profil, la déconnexion, le refus des identifiants incorrects et le refus des emails déjà enregistrés.
