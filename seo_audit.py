
"""
Module d'audit SEO automatisé pour MarkEasy
Intègre Google Trends, Serper API et DataForSEO pour fournir des recommandations d'optimisation
spécifiques à la niche de la boutique.
"""
import os
import json
import logging
import datetime
import asyncio
import requests
from typing import Dict, List, Optional, Union
import base64
from pytrends.request import TrendReq
from app import db, log_metric
from models import Boutique, Campaign, Product, SEOAudit, SEOKeyword

# Configuration des APIs
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
DATAFORSEO_LOGIN = os.environ.get("DATAFORSEO_LOGIN", "")
DATAFORSEO_PASSWORD = os.environ.get("DATAFORSEO_PASSWORD", "")

# Initialisation des clients API
pytrends = TrendReq(hl='fr-FR', tz=360)

def get_dataforseo_auth_header():
    """Génère l'en-tête d'authentification pour DataForSEO"""
    credentials = f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    return {"Authorization": f"Basic {encoded_credentials}"}

class SEOAuditor:
    """Classe principale pour l'audit SEO"""
    
    def __init__(self, 
                boutique_id: Optional[int] = None, 
                campaign_id: Optional[int] = None,
                product_id: Optional[int] = None,
                locale: str = 'fr_FR',
                max_keywords: int = 20):
        """
        Initialise l'auditeur SEO
        
        Args:
            boutique_id: ID de la boutique à auditer (optionnel)
            campaign_id: ID de la campagne à auditer (optionnel)
            product_id: ID du produit à auditer (optionnel)
            locale: Code de langue et région (fr_FR par défaut)
            max_keywords: Nombre maximum de mots-clés à analyser
        """
        self.boutique_id = boutique_id
        self.campaign_id = campaign_id
        self.product_id = product_id
        self.locale = locale
        self.max_keywords = max_keywords
        
        # Déterminer la langue et le pays à partir du locale
        self.lang, self.country = self._parse_locale(locale)
        
        # Récupérer les données de l'objet à auditer
        self._load_audit_target()
    
    def _parse_locale(self, locale: str) -> tuple:
        """Extrait la langue et le pays du code locale"""
        parts = locale.split('_')
        if len(parts) == 2:
            return parts[0].lower(), parts[1].upper()
        return 'fr', 'FR'  # Valeurs par défaut
    
    def _load_audit_target(self):
        """Charge les données de l'objet à auditer"""
        self.boutique = None
        self.campaign = None
        self.product = None
        self.content = ""
        self.title = ""
        self.description = ""
        self.keywords = []
        self.niche = ""
        
        # Charger le contenu selon le type d'objet
        if self.boutique_id:
            self.boutique = Boutique.query.get(self.boutique_id)
            if self.boutique:
                self.title = self.boutique.name
                self.description = self.boutique.description
                self.niche = self.boutique.target_demographic
        
        elif self.campaign_id:
            self.campaign = Campaign.query.get(self.campaign_id)
            if self.campaign:
                self.title = self.campaign.title
                self.content = self.campaign.content
                self.description = self.campaign.content[:250] if self.campaign.content else ""
                self.keywords = self.campaign.image_keywords or []
                
                # Récupérer la boutique associée
                if self.campaign.boutique_id:
                    self.boutique = Boutique.query.get(self.campaign.boutique_id)
                    if self.boutique:
                        self.niche = self.boutique.target_demographic
        
        elif self.product_id:
            self.product = Product.query.get(self.product_id)
            if self.product:
                self.title = self.product.name
                self.description = self.product.base_description or self.product.generated_description or ""
                self.content = self.product.html_description or ""
                self.keywords = self.product.get_keywords_list() if hasattr(self.product, 'get_keywords_list') else []
                
                # Récupérer la boutique associée
                if self.product.boutique_id:
                    self.boutique = Boutique.query.get(self.product.boutique_id)
                    if self.boutique:
                        self.niche = self.boutique.target_demographic
    
    async def run_full_audit(self) -> Dict:
        """
        Exécute un audit SEO complet
        
        Returns:
            Dictionnaire contenant les résultats de l'audit
        """
        start_time = datetime.datetime.now()
        
        # Vérifier si nous avons un contenu à auditer
        if not (self.title or self.description or self.content):
            return {
                "success": False,
                "error": "Aucun contenu à auditer",
                "timestamp": start_time
            }
        
        # Extraire et analyser les mots-clés
        if not self.keywords:
            self.keywords = self._extract_keywords_from_content()
        
        # Créer des tâches asynchrones pour les différentes analyses
        tasks = [
            self._analyze_keyword_relevance(),
            self._analyze_keyword_trends(),
            self._analyze_keyword_competition(),
            self._analyze_serp_features(),
            self._analyze_content_quality(),
            self._analyze_dataforseo_metrics()
        ]
        
        # Exécuter toutes les tâches en parallèle
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Structurer les résultats
        audit_results = {
            "success": True,
            "timestamp": start_time,
            "title_analysis": self._analyze_title(),
            "description_analysis": self._analyze_description(),
            "keywords_analysis": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
            "trends_analysis": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
            "competition_analysis": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
            "serp_features": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
            "content_quality": results[4] if not isinstance(results[4], Exception) else {"error": str(results[4])},
            "technical_seo": results[5] if not isinstance(results[5], Exception) else {"error": str(results[5])},
            "recommendations": self._generate_recommendations()
        }
        
        # Calculer un score global
        audit_results["global_score"] = self._calculate_global_score(audit_results)
        
        # Sauvegarder l'audit dans la base de données
        self._save_audit_results(audit_results)
        
        # Journaliser la métrique
        self._log_audit_metric(audit_results)
        
        return audit_results
    
    def _extract_keywords_from_content(self) -> List[str]:
        """
        Extrait automatiquement les mots-clés pertinents du contenu
        
        Returns:
            Liste de mots-clés
        """
        # Combiner titre, description et contenu
        combined_text = f"{self.title} {self.description} {self.content}"
        
        # TODO: Implémenter une méthode plus sophistiquée d'extraction de mots-clés
        # Pour l'instant, retourner une liste vide
        extracted_keywords = []
        
        return extracted_keywords[:self.max_keywords]
    
    def _analyze_title(self) -> Dict:
        """
        Analyse le titre pour les bonnes pratiques SEO
        
        Returns:
            Dictionnaire avec l'analyse du titre
        """
        if not self.title:
            return {
                "score": 0,
                "length": 0,
                "is_optimal_length": False,
                "has_keywords": False,
                "recommendations": ["Aucun titre trouvé pour l'analyse"]
            }
        
        # Analyser la longueur du titre (idéalement entre 50-60 caractères)
        length = len(self.title)
        is_optimal_length = 40 <= length <= 60
        
        # Vérifier si le titre contient des mots-clés
        has_keywords = any(keyword.lower() in self.title.lower() for keyword in self.keywords)
        
        # Générer des recommandations
        recommendations = []
        if not is_optimal_length:
            if length < 40:
                recommendations.append(f"Le titre est trop court ({length} caractères). Visez 50-60 caractères pour un affichage optimal dans les résultats de recherche.")
            else:
                recommendations.append(f"Le titre est trop long ({length} caractères). Limitez-le à 60 caractères pour éviter la troncature dans les résultats de recherche.")
        
        if not has_keywords and self.keywords:
            recommendations.append("Incluez au moins un mot-clé principal dans le titre pour améliorer la pertinence SEO.")
        
        # Calculer un score simple
        score = 0
        if is_optimal_length:
            score += 50
        if has_keywords:
            score += 50
        
        return {
            "score": score,
            "title": self.title,
            "length": length,
            "is_optimal_length": is_optimal_length,
            "has_keywords": has_keywords,
            "recommendations": recommendations
        }
    
    def _analyze_description(self) -> Dict:
        """
        Analyse la description pour les bonnes pratiques SEO
        
        Returns:
            Dictionnaire avec l'analyse de la description
        """
        if not self.description:
            return {
                "score": 0,
                "length": 0,
                "is_optimal_length": False,
                "has_keywords": False,
                "keyword_density": 0,
                "recommendations": ["Aucune description trouvée pour l'analyse"]
            }
        
        # Analyser la longueur de la description (idéalement entre 120-158 caractères)
        length = len(self.description)
        is_optimal_length = 120 <= length <= 158
        
        # Vérifier si la description contient des mots-clés
        description_lower = self.description.lower()
        keyword_count = sum(1 for keyword in self.keywords if keyword.lower() in description_lower)
        has_keywords = keyword_count > 0
        
        # Calculer la densité de mots-clés
        word_count = len(self.description.split())
        keyword_density = (keyword_count / word_count) * 100 if word_count > 0 else 0
        
        # Générer des recommandations
        recommendations = []
        if not is_optimal_length:
            if length < 120:
                recommendations.append(f"La description est trop courte ({length} caractères). Visez 120-158 caractères pour un affichage optimal.")
            else:
                recommendations.append(f"La description est trop longue ({length} caractères). Limitez-la à 158 caractères pour éviter la troncature.")
        
        if not has_keywords and self.keywords:
            recommendations.append("Incluez au moins un mot-clé principal dans la description pour améliorer la pertinence SEO.")
        
        if keyword_density > 5:
            recommendations.append(f"La densité de mots-clés est trop élevée ({keyword_density:.1f}%). Visez 1-3% pour éviter le bourrage de mots-clés.")
        
        # Calculer un score simple
        score = 0
        if is_optimal_length:
            score += 40
        if has_keywords:
            score += 30
        if 1 <= keyword_density <= 3:
            score += 30
        
        return {
            "score": score,
            "description": self.description,
            "length": length,
            "is_optimal_length": is_optimal_length,
            "has_keywords": has_keywords,
            "keyword_density": keyword_density,
            "recommendations": recommendations
        }
    
    async def _analyze_keyword_relevance(self) -> Dict:
        """
        Analyse la pertinence des mots-clés par rapport à la niche
        
        Returns:
            Dictionnaire avec l'analyse de la pertinence des mots-clés
        """
        if not self.keywords:
            return {
                "score": 0,
                "relevant_keywords": [],
                "irrelevant_keywords": [],
                "niche_match_score": 0,
                "recommendations": ["Aucun mot-clé trouvé pour l'analyse"]
            }
        
        # Cette fonction devrait idéalement utiliser une API pour vérifier la pertinence des mots-clés
        # Pour l'instant, utilisons une logique simplifiée
        
        relevant_keywords = []
        irrelevant_keywords = []
        
        # Si nous avons des informations sur la niche, les utiliser pour évaluer la pertinence
        if self.niche:
            niche_terms = self.niche.lower().split()
            
            for keyword in self.keywords:
                keyword_lower = keyword.lower()
                # Un mot-clé est considéré comme pertinent s'il contient un terme de la niche
                if any(term in keyword_lower for term in niche_terms):
                    relevant_keywords.append(keyword)
                else:
                    irrelevant_keywords.append(keyword)
        else:
            # Sans information sur la niche, considérer tous les mots-clés comme pertinents
            relevant_keywords = self.keywords
        
        # Calculer un score de correspondance à la niche
        niche_match_score = (len(relevant_keywords) / len(self.keywords)) * 100 if self.keywords else 0
        
        # Générer des recommandations
        recommendations = []
        if niche_match_score < 50:
            recommendations.append(f"Seulement {niche_match_score:.1f}% de vos mots-clés sont pertinents pour votre niche. Ajoutez des mots-clés plus spécifiques à votre secteur.")
        
        if irrelevant_keywords:
            recommendations.append(f"Envisagez de remplacer les mots-clés non pertinents ({', '.join(irrelevant_keywords[:3])}) par des termes plus spécifiques à votre niche.")
        
        # Calculer un score global
        score = min(100, niche_match_score)
        
        return {
            "score": score,
            "relevant_keywords": relevant_keywords,
            "irrelevant_keywords": irrelevant_keywords,
            "niche_match_score": niche_match_score,
            "recommendations": recommendations
        }
    
    async def _analyze_keyword_trends(self) -> Dict:
        """
        Analyse les tendances des mots-clés avec Google Trends
        
        Returns:
            Dictionnaire avec l'analyse des tendances
        """
        if not self.keywords or len(self.keywords) == 0:
            return {
                "score": 0,
                "trends_data": {},
                "trending_keywords": [],
                "declining_keywords": [],
                "recommendations": ["Aucun mot-clé trouvé pour l'analyse des tendances"]
            }
        
        try:
            # Limiter à 5 mots-clés pour Google Trends
            top_keywords = self.keywords[:5]
            
            # Obtenir les tendances
            pytrends.build_payload(
                kw_list=top_keywords,
                cat=0,
                timeframe='today 12-m',  # Derniers 12 mois
                geo=self.country,
                gprop=''
            )
            
            interest_over_time = pytrends.interest_over_time()
            
            # Analyser les tendances
            trends_data = {}
            trending_keywords = []
            declining_keywords = []
            
            if not interest_over_time.empty:
                for keyword in top_keywords:
                    if keyword in interest_over_time.columns:
                        # Obtenir les données pour ce mot-clé
                        keyword_data = interest_over_time[keyword].tolist()
                        
                        if len(keyword_data) >= 2:
                            # Diviser en deux moitiés pour comparer
                            half_point = len(keyword_data) // 2
                            first_half_avg = sum(keyword_data[:half_point]) / half_point if half_point > 0 else 0
                            second_half_avg = sum(keyword_data[half_point:]) / (len(keyword_data) - half_point) if (len(keyword_data) - half_point) > 0 else 0
                            
                            # Calculer le changement en pourcentage
                            if first_half_avg > 0:
                                change_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100
                            else:
                                change_percent = 0 if second_half_avg == 0 else 100
                            
                            trends_data[keyword] = {
                                "data": keyword_data,
                                "change_percent": change_percent
                            }
                            
                            # Déterminer si le mot-clé est en tendance ou en déclin
                            if change_percent >= 10:
                                trending_keywords.append(keyword)
                            elif change_percent <= -10:
                                declining_keywords.append(keyword)
            
            # Générer des recommandations
            recommendations = []
            if trending_keywords:
                recommendations.append(f"Capitalisez sur les mots-clés en hausse: {', '.join(trending_keywords)}")
            
            if declining_keywords:
                recommendations.append(f"Reconsidérez l'utilisation des mots-clés en baisse: {', '.join(declining_keywords)}")
            
            if not trending_keywords and not declining_keywords:
                recommendations.append("Vos mots-clés ont une tendance stable. Envisagez d'explorer de nouveaux mots-clés émergents.")
            
            # Calculer un score simple
            score = min(100, 50 + (len(trending_keywords) * 10))
            
            return {
                "score": score,
                "trends_data": trends_data,
                "trending_keywords": trending_keywords,
                "declining_keywords": declining_keywords,
                "recommendations": recommendations
            }
        
        except Exception as e:
            logging.error(f"Erreur lors de l'analyse des tendances: {str(e)}")
            return {
                "score": 0,
                "error": str(e),
                "recommendations": ["Impossible d'analyser les tendances des mots-clés. Vérifiez votre connexion Internet."]
            }
    
    async def _analyze_keyword_competition(self) -> Dict:
        """
        Analyse la compétition des mots-clés avec Serper API
        
        Returns:
            Dictionnaire avec l'analyse de la compétition
        """
        if not self.keywords or not SERPER_API_KEY:
            return {
                "score": 0,
                "competition_data": {},
                "low_competition_keywords": [],
                "high_competition_keywords": [],
                "recommendations": ["Configuration de l'API Serper requise pour l'analyse de la compétition"]
            }
        
        try:
            competition_data = {}
            low_competition_keywords = []
            high_competition_keywords = []
            
            # Limiter à 5 mots-clés pour éviter trop de requêtes API
            top_keywords = self.keywords[:5]
            
            for keyword in top_keywords:
                # Appel à l'API Serper
                response = requests.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": SERPER_API_KEY,
                        "Content-Type": "application/json"
                    },
                    json={
                        "q": keyword,
                        "gl": self.country.lower(),
                        "hl": self.lang
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Analyser les résultats pour déterminer la compétition
                    organic_results = data.get("organic", [])
                    
                    # Vérifier le nombre de résultats organiques
                    result_count = len(organic_results)
                    
                    # Vérifier si des sites de grande autorité sont présents
                    has_authority_sites = any(
                        "wikipedia" in result.get("link", "").lower() or
                        ".gov" in result.get("link", "").lower() or
                        ".edu" in result.get("link", "").lower()
                        for result in organic_results
                    )
                    
                    # Vérifier si des résultats contiennent le mot-clé exact dans le titre
                    exact_match_count = sum(
                        1 for result in organic_results
                        if keyword.lower() in result.get("title", "").lower()
                    )
                    
                    # Calculer un score de compétition (échelle 0-100)
                    # Plus le score est élevé, plus la compétition est forte
                    competition_score = min(100, (
                        (result_count / 10) * 40 +  # Plus de résultats = plus de compétition
                        (exact_match_count / max(1, result_count)) * 30 +  # Plus de correspondances exactes = plus de compétition
                        (70 if has_authority_sites else 0)  # Présence de sites d'autorité = haute compétition
                    ))
                    
                    competition_data[keyword] = {
                        "score": competition_score,
                        "result_count": result_count,
                        "has_authority_sites": has_authority_sites,
                        "exact_match_count": exact_match_count
                    }
                    
                    # Classer le mot-clé selon son niveau de compétition
                    if competition_score < 50:
                        low_competition_keywords.append(keyword)
                    else:
                        high_competition_keywords.append(keyword)
            
            # Générer des recommandations
            recommendations = []
            if low_competition_keywords:
                recommendations.append(f"Concentrez-vous sur ces mots-clés à faible compétition: {', '.join(low_competition_keywords)}")
            
            if high_competition_keywords:
                recommendations.append(f"Utilisez des variantes longue traîne pour les mots-clés à forte compétition: {', '.join(high_competition_keywords)}")
            
            # Calculer un score global
            score = min(100, 100 - (len(high_competition_keywords) * 20))
            
            return {
                "score": score,
                "competition_data": competition_data,
                "low_competition_keywords": low_competition_keywords,
                "high_competition_keywords": high_competition_keywords,
                "recommendations": recommendations
            }
        
        except Exception as e:
            logging.error(f"Erreur lors de l'analyse de la compétition: {str(e)}")
            return {
                "score": 0,
                "error": str(e),
                "recommendations": ["Impossible d'analyser la compétition des mots-clés. Vérifiez votre clé API Serper."]
            }
    
    async def _analyze_serp_features(self) -> Dict:
        """
        Analyse les fonctionnalités SERP (featured snippets, etc.) avec Serper API
        
        Returns:
            Dictionnaire avec l'analyse des fonctionnalités SERP
        """
        if not self.keywords or not SERPER_API_KEY:
            return {
                "score": 0,
                "serp_features": {},
                "opportunity_keywords": [],
                "recommendations": ["Configuration de l'API Serper requise pour l'analyse SERP"]
            }
        
        try:
            serp_features = {}
            opportunity_keywords = []
            
            # Prendre seulement le mot-clé principal pour cette analyse
            main_keyword = self.keywords[0] if self.keywords else ""
            
            if main_keyword:
                # Appel à l'API Serper
                response = requests.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": SERPER_API_KEY,
                        "Content-Type": "application/json"
                    },
                    json={
                        "q": main_keyword,
                        "gl": self.country.lower(),
                        "hl": self.lang
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Analyser les fonctionnalités SERP
                    has_featured_snippet = "answerBox" in data
                    has_knowledge_graph = "knowledgeGraph" in data
                    has_related_questions = "relatedQuestions" in data
                    has_local_results = "local" in data
                    has_images = "images" in data
                    has_shopping = "shopping" in data
                    
                    serp_features = {
                        "featured_snippet": has_featured_snippet,
                        "knowledge_graph": has_knowledge_graph,
                        "related_questions": has_related_questions,
                        "local_results": has_local_results,
                        "images": has_images,
                        "shopping": has_shopping
                    }
                    
                    # Identifier les opportunités
                    if has_featured_snippet or has_related_questions:
                        opportunity_keywords.append(main_keyword)
                    
                    # Récupérer les questions associées
                    related_questions = []
                    if has_related_questions:
                        related_questions = [
                            q.get("question", "")
                            for q in data.get("relatedQuestions", [])
                            if "question" in q
                        ]
            
            # Générer des recommandations
            recommendations = []
            if serp_features.get("featured_snippet"):
                recommendations.append(f"Opportunité de featured snippet pour '{main_keyword}'. Structurez votre contenu en Q&A pour l'optimiser.")
            
            if serp_features.get("related_questions") and related_questions:
                recommendations.append(f"Répondez à ces questions dans votre contenu: {', '.join(related_questions[:3])}...")
            
            if serp_features.get("local_results"):
                recommendations.append("Optimisez votre présence locale (Google My Business) pour améliorer votre visibilité.")
            
            if serp_features.get("images"):
                recommendations.append("Les images apparaissent dans les résultats. Optimisez vos balises alt et noms de fichiers.")
            
            # Calculer un score simple
            score = 0
            if serp_features:
                score = sum(50 if feature else 0 for feature in [
                    serp_features.get("featured_snippet"),
                    serp_features.get("related_questions")
                ]) / 2
            
            return {
                "score": score,
                "serp_features": serp_features,
                "related_questions": related_questions,
                "opportunity_keywords": opportunity_keywords,
                "recommendations": recommendations
            }
        
        except Exception as e:
            logging.error(f"Erreur lors de l'analyse des fonctionnalités SERP: {str(e)}")
            return {
                "score": 0,
                "error": str(e),
                "recommendations": ["Impossible d'analyser les fonctionnalités SERP. Vérifiez votre clé API Serper."]
            }
    
    async def _analyze_content_quality(self) -> Dict:
        """
        Analyse la qualité du contenu pour les critères SEO
        
        Returns:
            Dictionnaire avec l'analyse de la qualité du contenu
        """
        if not self.content:
            return {
                "score": 0,
                "word_count": 0,
                "readability_score": 0,
                "has_headings": False,
                "has_images": False,
                "recommendations": ["Aucun contenu trouvé pour l'analyse"]
            }
        
        # Analyse du contenu
        word_count = len(self.content.split())
        
        # Détection basique des balises HTML (pour le contenu HTML)
        has_headings = "<h1" in self.content.lower() or "<h2" in self.content.lower() or "<h3" in self.content.lower()
        has_images = "<img" in self.content.lower()
        
        # Calcul simple de la lisibilité (nombre de mots par phrase)
        sentences = [s.strip() for s in self.content.replace(".", ".###").split("###") if s.strip()]
        avg_words_per_sentence = word_count / max(1, len(sentences))
        
        # Plus le nombre de mots par phrase est bas, plus le texte est lisible
        # On considère qu'une phrase de 15 mots ou moins est bien lisible
        readability_score = max(0, min(100, 100 - (avg_words_per_sentence - 15) * 3)) if avg_words_per_sentence > 0 else 0
        
        # Générer des recommandations
        recommendations = []
        if word_count < 300:
            recommendations.append(f"Le contenu est trop court ({word_count} mots). Visez au moins 300 mots pour un bon référencement.")
        
        if not has_headings:
            recommendations.append("Utilisez des titres (H1, H2, H3) pour structurer votre contenu et améliorer le référencement.")
        
        if not has_images:
            recommendations.append("Ajoutez des images avec des attributs alt pertinents pour améliorer l'engagement et le SEO.")
        
        if readability_score < 70:
            recommendations.append(f"La lisibilité du texte est faible. Utilisez des phrases plus courtes et un langage plus simple.")
        
        # Calculer un score global
        score = 0
        if word_count >= 300:
            score += 40
        if has_headings:
            score += 20
        if has_images:
            score += 10
        score += int(readability_score * 0.3)  # 30% du score total
        
        return {
            "score": score,
            "word_count": word_count,
            "readability_score": readability_score,
            "avg_words_per_sentence": avg_words_per_sentence,
            "has_headings": has_headings,
            "has_images": has_images,
            "recommendations": recommendations
        }
    
    async def _analyze_dataforseo_metrics(self) -> Dict:
        """
        Analyse les métriques techniques SEO avec DataForSEO
        
        Returns:
            Dictionnaire avec l'analyse technique SEO
        """
        if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD:
            return {
                "score": 0,
                "technical_issues": [],
                "recommendations": ["Configuration de DataForSEO requise pour l'analyse technique"]
            }
        
        # Pour cette démo, nous simulons une analyse technique
        # Dans un environnement réel, vous feriez un appel à l'API DataForSEO
        
        # Simuler quelques problèmes techniques courants
        technical_issues = []
        
        if not self.description:
            technical_issues.append({
                "type": "meta_description",
                "severity": "high",
                "message": "Meta description manquante"
            })
        
        if not self.keywords:
            technical_issues.append({
                "type": "keywords",
                "severity": "medium",
                "message": "Mots-clés non définis"
            })
        
        if self.content and self.content.lower().count("<img") > 0 and "alt=" not in self.content.lower():
            technical_issues.append({
                "type": "image_alt",
                "severity": "medium",
                "message": "Attributs ALT manquants sur certaines images"
            })
        
        # Générer des recommandations
        recommendations = []
        for issue in technical_issues:
            if issue["type"] == "meta_description":
                recommendations.append("Ajoutez une meta description de 120-158 caractères avec des mots-clés pertinents.")
            elif issue["type"] == "keywords":
                recommendations.append("Définissez des mots-clés ciblés pour optimiser votre contenu.")
            elif issue["type"] == "image_alt":
                recommendations.append("Ajoutez des attributs ALT descriptifs à toutes vos images.")
        
        # Calculer un score simple
        score = 100 - (len(technical_issues) * 20)
        
        return {
            "score": max(0, score),
            "technical_issues": technical_issues,
            "recommendations": recommendations
        }
    
    def _generate_recommendations(self) -> List[Dict]:
        """
        Génère une liste consolidée de recommandations d'optimisation
        
        Returns:
            Liste de recommandations avec priorité
        """
        # Cette fonction sera complétée après l'exécution de toutes les analyses
        # Pour l'instant, retourner une liste vide
        return []
    
    def _calculate_global_score(self, audit_results: Dict) -> int:
        """
        Calcule un score global d'optimisation SEO basé sur les différentes analyses
        
        Args:
            audit_results: Résultats complets de l'audit
            
        Returns:
            Score global sur 100
        """
        # Pondération des différentes analyses
        weights = {
            "title_analysis": 15,
            "description_analysis": 15,
            "keywords_analysis": 20,
            "trends_analysis": 10,
            "competition_analysis": 10,
            "serp_features": 5,
            "content_quality": 15,
            "technical_seo": 10
        }
        
        # Calculer la moyenne pondérée
        total_score = 0
        total_weight = 0
        
        for key, weight in weights.items():
            if key in audit_results and "score" in audit_results[key]:
                total_score += audit_results[key]["score"] * weight
                total_weight += weight
        
        # Calculer le score final
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 0
        
        return round(final_score)
    
    def _consolidate_recommendations(self, audit_results: Dict) -> List[Dict]:
        """
        Consolide toutes les recommandations des différentes analyses
        
        Args:
            audit_results: Résultats complets de l'audit
            
        Returns:
            Liste consolidée de recommandations avec priorités
        """
        all_recommendations = []
        
        # Collecter toutes les recommandations
        for section, data in audit_results.items():
            if isinstance(data, dict) and "recommendations" in data:
                for rec in data["recommendations"]:
                    # Déterminer la priorité en fonction de la section
                    priority = "high" if section in ["title_analysis", "description_analysis", "keywords_analysis"] else "medium"
                    
                    all_recommendations.append({
                        "section": section,
                        "text": rec,
                        "priority": priority
                    })
        
        # Trier par priorité
        return sorted(all_recommendations, key=lambda x: 0 if x["priority"] == "high" else 1)
    
    def _save_audit_results(self, audit_results: Dict):
        """
        Sauvegarde les résultats de l'audit dans la base de données
        
        Args:
            audit_results: Résultats complets de l'audit
        """
        try:
            # Créer un nouvel enregistrement d'audit
            audit = SEOAudit(
                boutique_id=self.boutique_id,
                campaign_id=self.campaign_id,
                product_id=self.product_id,
                audit_date=datetime.datetime.utcnow(),
                score=audit_results["global_score"],
                results=audit_results,
                locale=self.locale
            )
            
            db.session.add(audit)
            
            # Sauvegarder les mots-clés analysés
            for keyword in self.keywords:
                # Récupérer les données spécifiques à ce mot-clé
                competition_data = audit_results.get("competition_analysis", {}).get("competition_data", {}).get(keyword, {})
                trends_data = audit_results.get("trends_analysis", {}).get("trends_data", {}).get(keyword, {})
                
                competition_score = competition_data.get("score", 0) if competition_data else 0
                trend_change = trends_data.get("change_percent", 0) if trends_data else 0
                
                # Déterminer le statut du mot-clé
                if keyword in audit_results.get("competition_analysis", {}).get("low_competition_keywords", []):
                    status = "opportunity"
                elif keyword in audit_results.get("trends_analysis", {}).get("trending_keywords", []):
                    status = "trending"
                elif keyword in audit_results.get("trends_analysis", {}).get("declining_keywords", []):
                    status = "declining"
                else:
                    status = "neutral"
                
                # Créer ou mettre à jour l'enregistrement du mot-clé
                keyword_record = SEOKeyword.query.filter_by(
                    keyword=keyword,
                    locale=self.locale
                ).first()
                
                if not keyword_record:
                    keyword_record = SEOKeyword(
                        keyword=keyword,
                        locale=self.locale,
                        competition_score=competition_score,
                        trend_change=trend_change,
                        status=status,
                        last_updated=datetime.datetime.utcnow()
                    )
                    db.session.add(keyword_record)
                else:
                    # Mettre à jour les données existantes
                    keyword_record.competition_score = competition_score
                    keyword_record.trend_change = trend_change
                    keyword_record.status = status
                    keyword_record.last_updated = datetime.datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la sauvegarde des résultats d'audit: {str(e)}")
    
    def _log_audit_metric(self, audit_results: Dict):
        """
        Enregistre une métrique pour l'audit SEO
        
        Args:
            audit_results: Résultats complets de l'audit
        """
        try:
            log_metric(
                metric_name="seo_audit",
                data={
                    "boutique_id": self.boutique_id,
                    "campaign_id": self.campaign_id,
                    "product_id": self.product_id,
                    "score": audit_results["global_score"],
                    "keywords_count": len(self.keywords),
                    "trending_keywords_count": len(audit_results.get("trends_analysis", {}).get("trending_keywords", [])),
                    "opportunity_keywords_count": len(audit_results.get("competition_analysis", {}).get("low_competition_keywords", []))
                },
                category="seo",
                status="success",
                response_time=None
            )
        except Exception as e:
            logging.error(f"Erreur lors de l'enregistrement de la métrique d'audit: {str(e)}")


# Fonction pour exécuter un audit SEO à partir d'un identifiant
async def run_seo_audit(
    boutique_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    product_id: Optional[int] = None,
    locale: str = 'fr_FR'
) -> Dict:
    """
    Exécute un audit SEO complet
    
    Args:
        boutique_id: ID de la boutique (optionnel)
        campaign_id: ID de la campagne (optionnel)
        product_id: ID du produit (optionnel)
        locale: Code de langue et région
        
    Returns:
        Résultats de l'audit SEO
    """
    auditor = SEOAuditor(
        boutique_id=boutique_id,
        campaign_id=campaign_id,
        product_id=product_id,
        locale=locale
    )
    
    return await auditor.run_full_audit()


# Fonction pour obtenir les recommandations SEO pour un objet
def get_seo_recommendations(
    boutique_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    product_id: Optional[int] = None
) -> List[Dict]:
    """
    Récupère les dernières recommandations SEO pour un objet
    
    Args:
        boutique_id: ID de la boutique (optionnel)
        campaign_id: ID de la campagne (optionnel)
        product_id: ID du produit (optionnel)
        
    Returns:
        Liste de recommandations SEO
    """
    # Récupérer le dernier audit
    audit = None
    
    if boutique_id:
        audit = SEOAudit.query.filter_by(boutique_id=boutique_id).order_by(SEOAudit.audit_date.desc()).first()
    elif campaign_id:
        audit = SEOAudit.query.filter_by(campaign_id=campaign_id).order_by(SEOAudit.audit_date.desc()).first()
    elif product_id:
        audit = SEOAudit.query.filter_by(product_id=product_id).order_by(SEOAudit.audit_date.desc()).first()
    
    if not audit or not audit.results:
        return []
    
    # Extraire les recommandations
    recommendations = []
    for section, data in audit.results.items():
        if isinstance(data, dict) and "recommendations" in data:
            section_name = section.replace("_analysis", "").replace("_", " ").title()
            
            for rec in data["recommendations"]:
                recommendations.append({
                    "section": section_name,
                    "text": rec
                })
    
    return recommendations


# Fonction pour récupérer les mots-clés recommandés pour une niche
def get_recommended_keywords(niche_market_id: int, locale: str = 'fr_FR', limit: int = 10) -> List[Dict]:
    """
    Récupère les mots-clés recommandés pour une niche de marché
    
    Args:
        niche_market_id: ID de la niche de marché
        locale: Code de langue et région
        limit: Nombre maximum de mots-clés à retourner
        
    Returns:
        Liste de mots-clés recommandés avec leurs métriques
    """
    # Récupérer la niche
    from models import NicheMarket
    
    niche = NicheMarket.query.get(niche_market_id)
    if not niche:
        return []
    
    # Récupérer les boutiques dans cette niche
    boutiques = Boutique.query.filter_by(niche_market_id=niche_market_id).all()
    boutique_ids = [b.id for b in boutiques]
    
    # Récupérer les audits pour ces boutiques
    audits = SEOAudit.query.filter(
        SEOAudit.boutique_id.in_(boutique_ids),
        SEOAudit.locale == locale
    ).order_by(SEOAudit.audit_date.desc()).limit(10).all()
    
    # Extraire tous les mots-clés des audits
    all_keywords = {}
    
    for audit in audits:
        if not audit.results:
            continue
            
        # Extraire les mots-clés à faible compétition
        low_competition = audit.results.get("competition_analysis", {}).get("low_competition_keywords", [])
        for keyword in low_competition:
            if keyword not in all_keywords:
                all_keywords[keyword] = {"score": 3, "count": 1}
            else:
                all_keywords[keyword]["score"] += 3
                all_keywords[keyword]["count"] += 1
        
        # Extraire les mots-clés en tendance
        trending = audit.results.get("trends_analysis", {}).get("trending_keywords", [])
        for keyword in trending:
            if keyword not in all_keywords:
                all_keywords[keyword] = {"score": 2, "count": 1}
            else:
                all_keywords[keyword]["score"] += 2
                all_keywords[keyword]["count"] += 1
    
    # Récupérer les données des mots-clés depuis la base de données
    keywords_data = []
    
    for keyword, data in all_keywords.items():
        # Chercher le mot-clé dans la base de données
        keyword_record = SEOKeyword.query.filter_by(
            keyword=keyword,
            locale=locale
        ).first()
        
        if keyword_record:
            keywords_data.append({
                "keyword": keyword,
                "competition_score": keyword_record.competition_score,
                "trend_change": keyword_record.trend_change,
                "status": keyword_record.status,
                "relevance_score": data["score"] / data["count"]
            })
    
    # Trier par score de pertinence et limiter
    keywords_data.sort(key=lambda x: x["relevance_score"], reverse=True)
    return keywords_data[:limit]
