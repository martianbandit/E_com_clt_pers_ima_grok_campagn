"""
Système de chargement progressif (pagination) pour les grandes listes
Améliore les performances en chargeant les données par chunks
"""

import math
from typing import Dict, List, Any, Optional
from flask import request, url_for
from sqlalchemy.orm import Query
from sqlalchemy import func

class ProgressiveLoader:
    """Gestionnaire du chargement progressif pour les grandes listes"""
    
    def __init__(self, items_per_page: int = 20, max_items_per_page: int = 100):
        self.items_per_page = items_per_page
        self.max_items_per_page = max_items_per_page
    
    def paginate_query(self, 
                      query: Query, 
                      page: int = 1, 
                      per_page: Optional[int] = None,
                      endpoint: str = None,
                      **url_params) -> Dict[str, Any]:
        """
        Pagine une requête SQLAlchemy
        
        Args:
            query: Requête SQLAlchemy à paginer
            page: Numéro de page (commence à 1)
            per_page: Nombre d'éléments par page
            endpoint: Endpoint Flask pour les liens de pagination
            **url_params: Paramètres supplémentaires pour les URLs
            
        Returns:
            Dict contenant les données paginées et métadonnées
        """
        if per_page is None:
            per_page = self.items_per_page
        
        # Limiter le nombre d'éléments par page
        per_page = min(per_page, self.max_items_per_page)
        
        # Calculer l'offset
        offset = (page - 1) * per_page
        
        # Compter le total d'éléments
        total_count = query.count()
        
        # Récupérer les éléments de la page courante
        items = query.offset(offset).limit(per_page).all()
        
        # Calculer les métadonnées de pagination
        total_pages = math.ceil(total_count / per_page) if per_page > 0 else 1
        has_prev = page > 1
        has_next = page < total_pages
        
        pagination_data = {
            'items': items,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_num': page - 1 if has_prev else None,
            'next_num': page + 1 if has_next else None
        }
        
        # Générer les URLs de navigation si endpoint fourni
        if endpoint:
            pagination_data.update(self._generate_navigation_urls(
                endpoint, page, total_pages, per_page, **url_params
            ))
        
        return pagination_data
    
    def _generate_navigation_urls(self, 
                                endpoint: str, 
                                current_page: int, 
                                total_pages: int,
                                per_page: int,
                                **url_params) -> Dict[str, Optional[str]]:
        """Génère les URLs de navigation pour la pagination"""
        urls = {
            'first_url': None,
            'prev_url': None,
            'next_url': None,
            'last_url': None
        }
        
        base_params = {**url_params, 'per_page': per_page}
        
        # URL première page
        if current_page > 1:
            urls['first_url'] = url_for(endpoint, page=1, **base_params)
        
        # URL page précédente
        if current_page > 1:
            urls['prev_url'] = url_for(endpoint, page=current_page - 1, **base_params)
        
        # URL page suivante
        if current_page < total_pages:
            urls['next_url'] = url_for(endpoint, page=current_page + 1, **base_params)
        
        # URL dernière page
        if current_page < total_pages:
            urls['last_url'] = url_for(endpoint, page=total_pages, **base_params)
        
        return urls
    
    def create_pagination_widget(self, pagination_data: Dict[str, Any], 
                                max_links: int = 7) -> str:
        """
        Génère le HTML du widget de pagination
        
        Args:
            pagination_data: Données de pagination
            max_links: Nombre maximum de liens à afficher
            
        Returns:
            HTML du widget de pagination
        """
        if pagination_data['pages'] <= 1:
            return ""
        
        current_page = pagination_data['page']
        total_pages = pagination_data['pages']
        
        # Calculer la plage de pages à afficher
        start_page = max(1, current_page - max_links // 2)
        end_page = min(total_pages, start_page + max_links - 1)
        
        # Ajuster si on est trop près de la fin
        if end_page - start_page < max_links - 1:
            start_page = max(1, end_page - max_links + 1)
        
        html_parts = ['<nav aria-label="Pagination">']
        html_parts.append('<ul class="pagination justify-content-center">')
        
        # Bouton Précédent
        prev_class = "disabled" if not pagination_data['has_prev'] else ""
        prev_url = pagination_data.get('prev_url', '#')
        html_parts.append(f'''
            <li class="page-item {prev_class}">
                <a class="page-link" href="{prev_url}" aria-label="Précédent">
                    <span aria-hidden="true">&laquo;</span>
                </a>
            </li>
        ''')
        
        # Liens vers les pages
        for page_num in range(start_page, end_page + 1):
            active_class = "active" if page_num == current_page else ""
            page_url = self._get_page_url(pagination_data, page_num)
            
            html_parts.append(f'''
                <li class="page-item {active_class}">
                    <a class="page-link" href="{page_url}">{page_num}</a>
                </li>
            ''')
        
        # Bouton Suivant
        next_class = "disabled" if not pagination_data['has_next'] else ""
        next_url = pagination_data.get('next_url', '#')
        html_parts.append(f'''
            <li class="page-item {next_class}">
                <a class="page-link" href="{next_url}" aria-label="Suivant">
                    <span aria-hidden="true">&raquo;</span>
                </a>
            </li>
        ''')
        
        html_parts.append('</ul>')
        html_parts.append('</nav>')
        
        return ''.join(html_parts)
    
    def _get_page_url(self, pagination_data: Dict[str, Any], page_num: int) -> str:
        """Génère l'URL pour une page spécifique"""
        # Récupérer les paramètres actuels de la requête
        args = request.args.copy()
        args['page'] = page_num
        
        # Construire l'URL
        return request.base_url + '?' + '&'.join([f"{k}={v}" for k, v in args.items()])
    
    def get_infinite_scroll_data(self, pagination_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prépare les données pour le scroll infini (AJAX)
        
        Returns:
            Données JSON pour le scroll infini côté client
        """
        return {
            'has_more': pagination_data['has_next'],
            'next_page': pagination_data['next_num'],
            'total_items': pagination_data['total'],
            'current_items': len(pagination_data['items']),
            'next_url': pagination_data.get('next_url'),
            'items_html': None  # À remplir avec le HTML rendu côté serveur
        }

class SearchFilterManager:
    """Gestionnaire pour les filtres et recherches avec pagination"""
    
    def __init__(self, progressive_loader: ProgressiveLoader):
        self.loader = progressive_loader
    
    def apply_filters(self, 
                     base_query: Query,
                     filters: Dict[str, Any],
                     search_term: Optional[str] = None,
                     search_fields: List[str] = None) -> Query:
        """
        Applique les filtres et recherche à une requête
        
        Args:
            base_query: Requête de base
            filters: Dictionnaire des filtres à appliquer
            search_term: Terme de recherche
            search_fields: Champs où chercher le terme
            
        Returns:
            Requête filtrée
        """
        filtered_query = base_query
        
        # Appliquer les filtres
        for field, value in filters.items():
            if value is not None and value != '':
                if hasattr(base_query.column_descriptions[0]['type'], field):
                    column = getattr(base_query.column_descriptions[0]['type'], field)
                    if isinstance(value, list):
                        filtered_query = filtered_query.filter(column.in_(value))
                    elif isinstance(value, str) and value.startswith('%'):
                        filtered_query = filtered_query.filter(column.like(value))
                    else:
                        filtered_query = filtered_query.filter(column == value)
        
        # Appliquer la recherche textuelle
        if search_term and search_fields:
            search_conditions = []
            for field in search_fields:
                if hasattr(base_query.column_descriptions[0]['type'], field):
                    column = getattr(base_query.column_descriptions[0]['type'], field)
                    search_conditions.append(column.ilike(f'%{search_term}%'))
            
            if search_conditions:
                from sqlalchemy import or_
                filtered_query = filtered_query.filter(or_(*search_conditions))
        
        return filtered_query
    
    def get_filter_options(self, query: Query, field: str) -> List[Dict[str, Any]]:
        """
        Récupère les options disponibles pour un filtre
        
        Args:
            query: Requête de base
            field: Nom du champ pour lequel récupérer les options
            
        Returns:
            Liste des options avec count
        """
        if not hasattr(query.column_descriptions[0]['type'], field):
            return []
        
        column = getattr(query.column_descriptions[0]['type'], field)
        
        # Compter les occurrences de chaque valeur
        result = query.with_entities(column, func.count(column))\
                     .group_by(column)\
                     .order_by(func.count(column).desc())\
                     .all()
        
        return [
            {'value': value, 'count': count, 'label': str(value)}
            for value, count in result if value is not None
        ]

# Instance globale
progressive_loader = ProgressiveLoader()
search_filter_manager = SearchFilterManager(progressive_loader)