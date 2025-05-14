# Documentation des Pages et Outils de MarkEasy

## Table des matières

1. [Introduction](#introduction)
2. [Pages principales](#pages-principales)
   - [Accueil](#accueil)
   - [Tableau de Bord](#tableau-de-bord)
   - [Profils Clients](#profils-clients)
   - [Campagnes](#campagnes)
   - [Fiches Produits](#fiches-produits)
   - [Métriques](#métriques)
3. [Outils spécialisés](#outils-spécialisés)
   - [Outils OSP](#outils-osp)
   - [Copy.ai](#copyai)
   - [Génération d'Images](#génération-dimages)
   - [Import de Produits](#import-de-produits)
4. [Pages utilisateur](#pages-utilisateur)
   - [Profil](#profil)
   - [Paramètres](#paramètres)
   - [Info Compte](#info-compte)
5. [Authentification](#authentification)
   - [Connexion standard](#connexion-standard)
   - [Google OAuth](#google-oauth)
   - [Replit Auth](#replit-auth)
6. [Pages légales](#pages-légales)
7. [Flux de données et interactions](#flux-de-données-et-interactions)

## Introduction

MarkEasy est une plateforme de marketing assistée par IA qui permet aux boutiques en ligne et aux entreprises de créer des campagnes marketing ciblées, de gérer des profils clients, et d'optimiser leur contenu produit. Cette documentation détaille chaque page et outil disponible dans l'application, ainsi que la façon dont ces éléments interagissent.

## Pages principales

### Accueil

**URL:** `/`

**Description:** Page d'accueil principale qui affiche un tableau de bord simplifié avec les statistiques importantes et les raccourcis vers les fonctionnalités principales.

**Fonctionnalités:**
- Vue d'ensemble des statistiques (nombre de clients, campagnes, etc.)
- Boutons d'accès rapide aux principales fonctionnalités
- Dernières activités et notifications
- Bannières promotionnelles rotatives

**Génération de contenu:** Cette page agrège des données des autres modules mais ne génère pas directement de contenu.

### Tableau de Bord

**URL:** `/dashboard`

**Description:** Tableau de bord analytique détaillé qui présente des métriques avancées sur les performances marketing de l'utilisateur.

**Fonctionnalités:**
- Graphiques de performance des campagnes
- Indicateurs clés de performance (KPI)
- Tendances des profils clients
- Analyse des conversions par segment
- État des boutiques et des niches de marché

**Génération de contenu:** Analyse les données collectées à partir des différentes campagnes, boutiques et clients pour présenter des insights actionnables.

### Profils Clients

**URL:** `/profiles`

**Description:** Page de gestion des profils clients qui permet de générer, visualiser et modifier des personas.

**Fonctionnalités:**
- Générateur automatique de profils clients basé sur l'IA
- Filtrage par niche de marché, démographie, etc.
- Visualisation détaillée des personas
- Options pour sauvegarder les profils dans la base de données
- Association des profils aux campagnes marketing

**Génération de contenu:** 
- Utilise l'API d'IA (Grok/OpenAI) pour générer des profils clients détaillés basés sur des paramètres comme:
  - Créneau de marché
  - Démographie cible (âge, localisation, niveau de revenu)
  - Intérêts et comportements d'achat
- Crée des descriptions riches incluant:
  - Points de douleur et besoins du client
  - Habitudes de consommation
  - Canaux de communication préférés
  - Styles de vie et valeurs

Les données générées alimentent ensuite les campagnes et permettent de cibler précisément le contenu marketing.

### Campagnes

**URL:** `/campaigns`

**Description:** Outil de création et gestion des campagnes marketing ciblées.

**Fonctionnalités:**
- Création de nouvelles campagnes
- Association à des profils clients spécifiques
- Génération automatique de contenu marketing adapté
- Options multilingues pour internationaliser les campagnes
- Outils de partage sur les réseaux sociaux
- Métriques de performance des campagnes

**Génération de contenu:**
- Utilise l'IA pour créer du contenu marketing adapté aux profils clients sélectionnés
- Génère différents types de contenu:
  - Accroches publicitaires
  - Descriptions de produits optimisées
  - Argumentaires de vente
  - Contenu pour réseaux sociaux
- Optimise le ton, le style et les points d'argumentation en fonction du persona cible
- Peut inclure des recommandations de produits similaires

### Fiches Produits

**URL:** `/products`

**Description:** Gestionnaire de fiches produits avec optimisation automatique par IA.

**Fonctionnalités:**
- Création et gestion de fiches produits
- Optimisation automatique des descriptions
- Génération de contenu SEO
- Import depuis des plateformes externes (comme AliExpress)
- Export vers des plateformes e-commerce (comme Shopify)

**Génération de contenu:**
- Utilise l'IA pour créer des descriptions optimisées pour:
  - La conversion (achat)
  - Le SEO (référencement)
  - L'engagement client
- Génère:
  - Titres optimisés
  - Descriptions détaillées
  - Balises meta pour SEO
  - FAQ produit
  - Spécifications techniques formatées
  - Variantes de produit

### Métriques

**URL:** `/metrics_dashboard`

**Description:** Page d'analyse avancée des métriques de performance marketing.

**Fonctionnalités:**
- Visualisation des données de performance
- Filtrage par date, type de métrique, etc.
- Graphiques et tableaux interactifs
- Exportation des données
- Recommandations d'optimisation basées sur les performances

**Génération de contenu:** Cette page analyse les données collectées mais ne génère pas directement de contenu via IA.

## Outils spécialisés

### Outils OSP

**URL:** `/osp-tools`

**Description:** Outils de Stratégie Personnalisée qui offrent des recommandations avancées basées sur l'analyse des données.

**Fonctionnalités:**
- Optimisation SEO
- Analyse des concurrents
- Recommandations de prix
- Optimisation des canaux de vente
- Analyse des tendances du marché

**Génération de contenu:**
- Utilise l'IA pour analyser les données commerciales et marketing
- Génère des recommandations actionnables et personnalisées
- Produit des rapports détaillés sur les opportunités d'optimisation
- Aide à identifier des niches de marché prometteuses

### Copy.ai

**URL:** `/copy_ai_tool`

**Description:** Intégration de l'outil Copy.ai pour générer du contenu marketing avancé via une interface externe.

**Fonctionnalités:**
- Interface embedée de Copy.ai
- Génération de contenu marketing divers
- Capacité à personnaliser les prompts pour des besoins spécifiques
- Transfert facile du contenu généré vers les campagnes MarkEasy

**Génération de contenu:**
- Utilise l'API Copy.ai pour générer divers types de contenu:
  - Emails marketing
  - Publications pour réseaux sociaux
  - Slogans et accroches publicitaires
  - Descriptions de produits
  - Articles de blog
- Le contenu généré peut être copié et utilisé dans les campagnes MarkEasy
- Permet une personnalisation avancée des prompts pour des résultats plus ciblés

### Génération d'Images

**URL:** `/image_generation`

**Description:** Outil de création d'images marketing optimisées via IA.

**Fonctionnalités:**
- Génération d'images pour les campagnes marketing
- Personnalisation basée sur les profils clients
- Différents styles artistiques disponibles
- Recherche automatique de produits similaires
- Intégration des images générées dans les campagnes

**Génération de contenu:**
- Utilise des modèles de génération d'images (Grok/DALL-E)
- Crée des visuels promotionnels basés sur:
  - Descriptions de produits
  - Profils clients cibles
  - Style artistique sélectionné
- Les images peuvent être directement associées aux campagnes marketing
- Option pour utiliser une image de référence comme base

### Import de Produits

**URL:** `/product_import`

**Description:** Outil d'importation et d'optimisation de produits depuis des plateformes externes comme AliExpress.

**Fonctionnalités:**
- Import automatisé depuis AliExpress
- Optimisation des descriptions et des prix
- Génération de contenu marketing
- Adaptation aux personas clients
- Options d'export vers Shopify et autres plateformes e-commerce

**Génération de contenu:**
- Extrait et transforme le contenu des produits importés
- Optimise les prix avec des stratégies psychologiques
- Génère des descriptions marketing améliorées
- Crée du contenu HTML formaté pour Shopify
- Adapte le contenu aux cibles démographiques spécifiques

## Pages utilisateur

### Profil

**URL:** `/user/profile`

**Description:** Page de gestion du profil utilisateur.

**Fonctionnalités:**
- Affichage et modification des informations personnelles
- Gestion des préférences
- Historique des activités
- Statistiques d'utilisation

### Paramètres

**URL:** `/user/settings`

**Description:** Configuration des paramètres de l'application.

**Fonctionnalités:**
- Paramètres de notification
- Préférences d'interface
- Options de confidentialité
- Gestion des intégrations

### Info Compte

**URL:** `/user-info`

**Description:** Informations détaillées sur le compte utilisateur.

**Fonctionnalités:**
- Détails d'abonnement
- Quotas d'utilisation
- Moyens de paiement
- Facturation

## Authentification

### Connexion standard

**URL:** `/login`

**Description:** Système d'authentification par email/mot de passe.

**Fonctionnalités:**
- Connexion par email et mot de passe
- Récupération de mot de passe
- Protection contre les attaques de force brute

### Google OAuth

**URL:** `/google_login`

**Description:** Authentification via compte Google.

**Fonctionnalités:**
- Connexion rapide avec Google
- Récupération des informations de profil
- Synchronisation des données utilisateur

### Replit Auth

**URL:** `/auth/replit_auth`

**Description:** Authentification via compte Replit (OpenID Connect).

**Fonctionnalités:**
- Connexion avec compte Replit
- Récupération des informations de profil
- Authentification robuste et sécurisée

## Pages légales

- **Politique de confidentialité:** `/privacy`
- **Conditions générales d'utilisation:** `/terms`
- **Politique des cookies:** `/cookies`
- **Mentions légales:** `/legal`
- **Politique de remboursement:** `/refund`

Ces pages fournissent les informations légales nécessaires pour la conformité réglementaire (RGPD, etc.).

## Flux de données et interactions

### Flux de génération de contenu

1. **Création de niches de marché**
   - L'utilisateur définit des niches de marché spécifiques
   - Ces niches servent de base pour la génération de personas clients

2. **Génération de personas clients**
   - L'IA génère des profils clients détaillés basés sur les niches
   - Ces profils incluent des informations démographiques, psychographiques, comportementales
   - Les personas peuvent être enregistrés dans la base de données pour une utilisation répétée

3. **Création de campagnes marketing**
   - Les campagnes sont créées en ciblant des personas spécifiques
   - L'IA génère du contenu marketing adapté aux caractéristiques des personas
   - Les campagnes peuvent inclure différents canaux et formats

4. **Optimisation de produits**
   - Les fiches produits sont optimisées pour les personas cibles
   - Le contenu est adapté pour maximiser la conversion et l'engagement
   - Des images marketing peuvent être générées pour compléter les descriptions

5. **Analyse et amélioration**
   - Les métriques de performance sont collectées et analysées
   - Les outils OSP fournissent des recommandations d'optimisation
   - Le contenu peut être régénéré ou affiné en fonction des performances

### Intégrations externes

1. **Copy.ai**
   - Génère du contenu marketing spécialisé via l'API Copy.ai
   - Le contenu peut être intégré aux campagnes MarkEasy
   - Permet une personnalisation avancée des prompts pour des résultats ciblés

2. **AliExpress**
   - Importe des données produits depuis AliExpress
   - Transforme et optimise ces données pour la vente
   - Adapte le contenu aux marchés et personas cibles

3. **Shopify**
   - Exporte les fiches produits optimisées vers Shopify
   - Formate le contenu HTML pour une intégration parfaite
   - Optimise les métadonnées SEO

4. **Réseaux sociaux**
   - Partage les campagnes sur différentes plateformes sociales
   - Adapte le format selon le réseau (Facebook, LinkedIn, Pinterest, Reddit)
   - Optimise les visuels et textes pour maximiser l'engagement

Ce système interconnecté permet aux utilisateurs de MarkEasy de créer une stratégie marketing cohérente, du développement des personas à la création de contenu, jusqu'à l'analyse et l'optimisation des performances.