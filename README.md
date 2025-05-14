# MarkEasy - Plateforme de Marketing IA pour Boutiques

<div align="center">
  <img src="static/img/markeasy-ninja-new.png" alt="MarkEasy Logo" width="200">
  <h3>Le marketing, c'est facile... quand on a un ninja dans sa poche.</h3>
</div>

## Table des matières
- [Vue d'ensemble](#vue-densemble)
- [Fonctionnalités clés](#fonctionnalités-clés)
- [Architecture technique](#architecture-technique)
- [Prérequis système](#prérequis-système)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Authentification](#authentification)
- [Sécurité et isolation multi-utilisateurs](#sécurité-et-isolation-multi-utilisateurs)
- [Internationalisation](#internationalisation)
- [API et intégrations](#api-et-intégrations)
- [Déploiement](#déploiement)
- [Licence](#licence)

## Vue d'ensemble

MarkEasy est une plateforme de marketing alimentée par l'IA, conçue pour aider les boutiques en ligne et les entreprises de niche à optimiser leurs campagnes marketing, à comprendre leurs clients et à améliorer leurs performances commerciales. Développée avec Python et Flask, cette application web offre une suite complète d'outils pour la génération de contenu, l'analyse de données clients et la gestion de campagnes marketing.

La plateforme est conçue avec une architecture multi-tenant permettant à chaque utilisateur de travailler dans son propre environnement isolé avec ses propres données de boutiques, campagnes et clients.

## Fonctionnalités clés

### 1. Gestion de boutiques
- Création et gestion de multiples boutiques
- Paramètres linguistiques et personnalisation par boutique
- Statistiques et métriques par boutique

### 2. Gestion des clients
- Création et importation de profils clients
- Segmentation et analyse de la clientèle
- Génération de personas clients avec IA
- Visualisation des données clients

### 3. Campagnes marketing
- Création de campagnes ciblées
- Suivi des performances des campagnes
- Suggestions de contenu optimisé par IA
- Support multilingue pour les campagnes internationales

### 4. Gestion des produits
- Importation de produits depuis diverses sources (dont AliExpress)
- Optimisation des descriptions et du positionnement produit
- Génération de fiches produits optimisées pour le SEO
- Export vers Shopify et autres plateformes e-commerce

### 5. Outils OSP (Outils de Stratégie Personnalisée)
- Analyse de contenu
- Cartographie de valeur
- Optimisation SEO
- Recommandations stratégiques personnalisées

### 6. Tableau de bord analytique
- Vue d'ensemble des performances
- Métriques clés et KPIs
- Tendances et prévisions
- Rapports personnalisables

### 7. Génération d'images IA
- Création d'avatars pour les personas clients
- Génération d'images pour les campagnes marketing
- Personnalisation du style visuel

## Architecture technique

MarkEasy est construit sur une pile technologique moderne et robuste :

### Backend
- **Langage** : Python 3.11
- **Framework** : Flask
- **Base de données** : PostgreSQL
- **ORM** : SQLAlchemy
- **Authentification** : Flask-Login, OAuth (Google, GitHub, Replit Auth)
- **Internationalisation** : Flask-Babel

### IA et Machine Learning
- **Génération de texte** : OpenAI GPT, Grok (xAI)
- **Génération d'images** : OpenAI DALL-E, Grok (xAI)
- **Analyse de données** : Modèles personnalisés

### Frontend
- **Framework CSS** : Bootstrap 5
- **JavaScript** : Vanilla JS avec composants interactifs
- **Thème** : Support des modes clair/sombre
- **Responsive design** : Compatible mobile, tablette et desktop

### Infrastructure
- **Déploiement** : Compatible avec Replit
- **Base de données** : PostgreSQL
- **Stockage** : Système de fichiers local ou cloud

### Sécurité
- **Architecture multi-tenant** : Isolation complète des données entre utilisateurs
- **Authentification** : Support multi-fournisseurs (email/mot de passe, OAuth)
- **Protection CSRF** : Jetons de sécurité sur tous les formulaires
- **Chiffrement** : Hachage sécurisé des mots de passe

## Prérequis système

- Python 3.11+
- PostgreSQL 14+
- pip (gestionnaire de paquets Python)
- Connexion Internet (pour les API d'IA)
- Navigateur web moderne

## Installation

### Installation locale

1. Cloner le dépôt :
```bash
git clone https://github.com/your-username/markeasy.git
cd markeasy
```

2. Créer un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Configurer les variables d'environnement :
```bash
cp .env.example .env
# Éditer le fichier .env avec vos propres variables
```

5. Initialiser la base de données :
```bash
flask db init
flask db migrate
flask db upgrade
```

6. Lancer l'application :
```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

### Installation sur Replit

1. Créer un nouveau Repl et importer depuis GitHub
2. Configurer les secrets d'environnement dans l'interface Replit
3. Exécuter l'application avec le bouton Run

## Configuration

### Variables d'environnement

MarkEasy utilise plusieurs variables d'environnement pour sa configuration :

| Variable | Description | Obligatoire |
|----------|-------------|------------|
| `DATABASE_URL` | URL de connexion à la base de données PostgreSQL | Oui |
| `SESSION_SECRET` | Clé secrète pour les sessions Flask | Oui |
| `OPENAI_API_KEY` | Clé API OpenAI pour la génération de contenu | Non |
| `XAI_API_KEY` | Clé API xAI (Grok) pour la génération de contenu | Non |
| `GITHUB_CLIENT_ID` | ID client OAuth GitHub | Non |
| `GITHUB_CLIENT_SECRET` | Secret client OAuth GitHub | Non |
| `GOOGLE_OAUTH_CLIENT_ID` | ID client OAuth Google | Non |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Secret client OAuth Google | Non |

### Configuration de l'authentification OAuth

#### Google OAuth

1. Accéder à [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Créer un nouveau projet
3. Configurer l'écran de consentement OAuth
4. Créer des identifiants OAuth 2.0
5. Ajouter l'URI de redirection : `https://your-domain.com/google_login/callback`
6. Copier l'ID client et le secret dans les variables d'environnement

#### GitHub OAuth

1. Accéder à [GitHub Developer Settings](https://github.com/settings/developers)
2. Créer une nouvelle application OAuth
3. Configurer l'URL de rappel : `https://your-domain.com/github/authorized`
4. Copier l'ID client et le secret dans les variables d'environnement

## Utilisation

### Démarrage rapide

1. **Créer un compte** : Inscrivez-vous avec votre email ou connectez-vous via Google/GitHub/Replit
2. **Créer une boutique** : Configurez votre première boutique avec ses informations de base
3. **Importer des clients** : Ajoutez manuellement vos clients ou importez-les depuis un fichier
4. **Générer des personas** : Utilisez l'IA pour créer des personas détaillés basés sur vos clients
5. **Créer une campagne** : Configurez une campagne marketing ciblée
6. **Gérer les produits** : Ajoutez, importez ou optimisez vos fiches produits
7. **Analyser les performances** : Consultez votre tableau de bord pour suivre les résultats

### Fonctionnalités détaillées

#### Gestion des boutiques

- **Création de boutique** : Définissez le nom, la niche, la description et les paramètres de votre boutique
- **Configuration linguistique** : Définissez les langues principales et secondaires de votre boutique
- **Statistiques de boutique** : Visualisez les performances globales de votre boutique

#### Gestion des clients

- **Création de profils** : Ajoutez des informations démographiques, comportementales et de préférence
- **Segmentation** : Groupez vos clients par caractéristiques similaires
- **Personas générés par IA** : Créez des représentations détaillées de vos segments de clientèle
- **Avatars personnalisés** : Générez des avatars visuels pour vos personas

#### Campagnes marketing

- **Définition de cible** : Sélectionnez les segments clients à cibler
- **Création de contenu** : Générez des textes, slogans et descriptions avec l'IA
- **Planification** : Définissez le calendrier et les canaux de diffusion
- **Suivi des performances** : Mesurez l'impact et les résultats de vos campagnes

#### Outils OSP

- **Analyse de contenu** : Évaluez l'efficacité de votre copie marketing
- **Cartographie de valeur** : Identifiez les propositions de valeur les plus pertinentes
- **Optimisation SEO** : Améliorez le référencement de vos contenus

## Authentification

MarkEasy prend en charge plusieurs méthodes d'authentification :

### 1. Email/Mot de passe
- Inscription traditionnelle avec validation d'email
- Connexion sécurisée avec hachage des mots de passe

### 2. Google OAuth
- Connexion rapide via compte Google
- Synchronisation du profil (nom, email, photo)

### 3. GitHub OAuth
- Connexion pour les utilisateurs GitHub
- Récupération automatique des informations de profil

### 4. Replit Auth
- Authentification via le système Replit (utile pour le déploiement sur Replit)

## Sécurité et isolation multi-utilisateurs

MarkEasy implémente une architecture multi-tenant sécurisée :

- **Isolation des données** : Chaque utilisateur ne peut voir et manipuler que ses propres données
- **Filtrage par owner_id** : Toutes les requêtes de base de données sont filtrées par l'ID du propriétaire
- **Vérification d'autorisation** : Contrôles stricts pour empêcher l'accès non autorisé
- **Protection CSRF** : Jetons de sécurité sur tous les formulaires
- **Hachage des mots de passe** : Stockage sécurisé des informations d'identification

## Internationalisation

MarkEasy est entièrement internationalisé :

- **Interface multilingue** : L'interface utilisateur est disponible en plusieurs langues
- **Contenu marketing multilingue** : Génération de contenu dans différentes langues
- **Gestion des préférences linguistiques** : Chaque utilisateur peut choisir sa langue préférée
- **Campagnes internationales** : Support pour cibler différentes régions linguistiques

## API et intégrations

### API internes
- API pour la génération de contenu
- API pour l'analyse de données
- API pour la gestion des boutiques et campagnes

### Intégrations externes
- OpenAI GPT pour la génération de texte
- Grok (xAI) comme alternative de génération
- DALL-E et autres services pour la génération d'images
- Possibilité d'intégration avec Shopify et autres plateformes e-commerce

## Déploiement

### Sur Replit
1. Forker le projet sur Replit
2. Configurer les secrets d'environnement
3. Exécuter l'application

### Sur VPS ou serveur dédié
1. Installer les prérequis système
2. Cloner le dépôt
3. Configurer les variables d'environnement
4. Configurer un serveur WSGI (Gunicorn)
5. Configurer un serveur proxy (Nginx)
6. Configurer SSL avec Let's Encrypt

### Sur services cloud (AWS, Google Cloud, etc.)
Des instructions spécifiques sont disponibles pour chaque fournisseur de services cloud.

## Licence

MarkEasy est un logiciel propriétaire développé exclusivement pour l'utilisation par les clients autorisés.

---

<div align="center">
  <p>MarkEasy © 2025 - Tous droits réservés</p>
  <p>Développé avec ❤️ par l'équipe MarkEasy</p>
</div>