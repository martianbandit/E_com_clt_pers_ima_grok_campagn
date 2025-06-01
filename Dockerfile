# Dockerfile pour NinjaLead.ai
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Création de l'utilisateur non-root pour la sécurité
RUN groupadd -r ninjalead && useradd -r -g ninjalead ninjalead

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Définition du répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances
COPY pyproject.toml ./

# Installation des dépendances Python
RUN pip install -e .

# Copie du code source
COPY . .

# Changement du propriétaire des fichiers
RUN chown -R ninjalead:ninjalead /app

# Basculer vers l'utilisateur non-root
USER ninjalead

# Port d'exposition
EXPOSE 5000

# Commande de démarrage
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--keep-alive", "2", "--max-requests", "1000", "--max-requests-jitter", "100", "main:app"]