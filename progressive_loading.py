"""
Système de progressive loading pour optimiser l'affichage 
des grandes listes avec pagination et lazy loading
"""

import math
import logging
from flask import request, jsonify, render_template
from sqlalchemy import func

logger = logging.getLogger(__name__)

class ProgressiveLoader:
    """Gestionnaire de chargement progressif pour les grandes listes"""
    
    def __init__(self, app=None):
        self.app = app
        self.default_page_size = 20
        self.max_page_size = 100
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le progressive loader avec l'application Flask"""
        self.app = app
        
        # Configuration depuis l'environnement
        import os
        self.default_page_size = int(os.environ.get('DEFAULT_PAGE_SIZE', '20'))
        self.max_page_size = int(os.environ.get('MAX_PAGE_SIZE', '100'))
        
        logger.info(f"Progressive loading initialisé - Page size: {self.default_page_size}")
        
        # Injection des fonctions dans les templates
        @app.context_processor
        def inject_progressive_functions():
            return {
                'paginate_query': self.paginate_query,
                'render_pagination': self.render_pagination_controls
            }
    
    def paginate_query(self, query, page=None, per_page=None, error_out=False):
        """
        Pagine une requête SQLAlchemy avec optimisations
        
        Args:
            query: Requête SQLAlchemy
            page: Numéro de page (commence à 1)
            per_page: Nombre d'éléments par page
            error_out: Lever une erreur si la page n'existe pas
            
        Returns:
            dict: Résultats paginés avec métadonnées
        """
        # Récupération des paramètres depuis la requête HTTP
        if page is None:
            page = request.args.get('page', 1, type=int)
        if per_page is None:
            per_page = request.args.get('per_page', self.default_page_size, type=int)
        
        # Limitation de la taille de page
        per_page = min(per_page, self.max_page_size)
        
        # Calcul de l'offset
        offset = (page - 1) * per_page
        
        try:
            # Comptage total optimisé
            total_count = query.count()
            
            # Récupération des éléments avec limite et offset
            items = query.offset(offset).limit(per_page).all()
            
            # Calcul des métadonnées de pagination
            total_pages = math.ceil(total_count / per_page) if per_page > 0 else 1
            
            has_prev = page > 1
            has_next = page < total_pages
            
            prev_num = page - 1 if has_prev else None
            next_num = page + 1 if has_next else None
            
            pagination_data = {
                'items': items,
                'total': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'has_prev': has_prev,
                'has_next': has_next,
                'prev_num': prev_num,
                'next_num': next_num,
                'iter_pages': self._iter_pages(page, total_pages)
            }
            
            return pagination_data
            
        except Exception as e:
            logger.error(f"Erreur pagination: {e}")
            if error_out:
                raise
            return {
                'items': [],
                'total': 0,
                'page': 1,
                'per_page': per_page,
                'total_pages': 0,
                'has_prev': False,
                'has_next': False,
                'prev_num': None,
                'next_num': None,
                'iter_pages': []
            }
    
    def lazy_load_endpoint(self, query_builder, template_partial, **template_kwargs):
        """
        Endpoint générique pour le lazy loading AJAX
        
        Args:
            query_builder: Fonction qui retourne la requête SQLAlchemy
            template_partial: Template partiel à rendre
            **template_kwargs: Variables supplémentaires pour le template
            
        Returns:
            Response JSON avec HTML et métadonnées
        """
        try:
            # Construction de la requête
            query = query_builder()
            
            # Pagination
            pagination = self.paginate_query(query)
            
            # Rendu du template partiel
            html_content = render_template(
                template_partial,
                items=pagination['items'],
                pagination=pagination,
                **template_kwargs
            )
            
            return jsonify({
                'success': True,
                'html': html_content,
                'pagination': {
                    'page': pagination['page'],
                    'total_pages': pagination['total_pages'],
                    'has_next': pagination['has_next'],
                    'has_prev': pagination['has_prev'],
                    'total': pagination['total']
                }
            })
            
        except Exception as e:
            logger.error(f"Erreur lazy loading: {e}")
            return jsonify({
                'success': False,
                'error': 'Erreur lors du chargement des données'
            }), 500
    
    def infinite_scroll_data(self, query, serializer_func=None):
        """
        Retourne des données formatées pour l'infinite scroll
        
        Args:
            query: Requête SQLAlchemy
            serializer_func: Fonction pour sérialiser les objets
            
        Returns:
            dict: Données JSON pour infinite scroll
        """
        pagination = self.paginate_query(query)
        
        # Sérialisation des éléments
        if serializer_func:
            items_data = [serializer_func(item) for item in pagination['items']]
        else:
            # Sérialisation basique par défaut
            items_data = []
            for item in pagination['items']:
                if hasattr(item, 'to_dict'):
                    items_data.append(item.to_dict())
                else:
                    items_data.append(str(item))
        
        return {
            'items': items_data,
            'pagination': {
                'current_page': pagination['page'],
                'total_pages': pagination['total_pages'],
                'has_next': pagination['has_next'],
                'next_page': pagination['next_num'],
                'total_items': pagination['total']
            }
        }
    
    def render_pagination_controls(self, pagination, endpoint, **kwargs):
        """
        Génère les contrôles de pagination HTML
        
        Args:
            pagination: Données de pagination
            endpoint: Endpoint de la route
            **kwargs: Paramètres supplémentaires pour l'URL
            
        Returns:
            str: HTML des contrôles de pagination
        """
        from flask import url_for
        
        if pagination['total_pages'] <= 1:
            return ""
        
        html_parts = ['<nav aria-label="Pagination"><ul class="pagination justify-content-center">']
        
        # Bouton précédent
        if pagination['has_prev']:
            prev_url = url_for(endpoint, page=pagination['prev_num'], **kwargs)
            html_parts.append(f'<li class="page-item"><a class="page-link" href="{prev_url}">Précédent</a></li>')
        else:
            html_parts.append('<li class="page-item disabled"><span class="page-link">Précédent</span></li>')
        
        # Numéros de page
        for page_num in pagination['iter_pages']:
            if page_num is None:
                html_parts.append('<li class="page-item disabled"><span class="page-link">…</span></li>')
            elif page_num == pagination['page']:
                html_parts.append(f'<li class="page-item active"><span class="page-link">{page_num}</span></li>')
            else:
                page_url = url_for(endpoint, page=page_num, **kwargs)
                html_parts.append(f'<li class="page-item"><a class="page-link" href="{page_url}">{page_num}</a></li>')
        
        # Bouton suivant
        if pagination['has_next']:
            next_url = url_for(endpoint, page=pagination['next_num'], **kwargs)
            html_parts.append(f'<li class="page-item"><a class="page-link" href="{next_url}">Suivant</a></li>')
        else:
            html_parts.append('<li class="page-item disabled"><span class="page-link">Suivant</span></li>')
        
        html_parts.append('</ul></nav>')
        
        return ''.join(html_parts)
    
    def _iter_pages(self, page, total_pages, left_edge=2, left_current=2, right_current=3, right_edge=2):
        """
        Génère les numéros de page à afficher dans la pagination
        """
        last = total_pages
        
        for num in range(1, min(left_edge + 1, last + 1)):
            yield num
        
        if left_edge + 1 < page - left_current:
            yield None
        
        for num in range(max(left_edge + 1, page - left_current), 
                        min(page + right_current + 1, last + 1)):
            yield num
        
        if page + right_current < last - right_edge:
            yield None
        
        for num in range(max(page + right_current + 1, last - right_edge + 1), last + 1):
            yield num
    
    def get_performance_stats(self):
        """Retourne les statistiques de performance du progressive loading"""
        return {
            'default_page_size': self.default_page_size,
            'max_page_size': self.max_page_size,
            'pagination_enabled': True,
            'lazy_loading_enabled': True
        }

# Instance globale
progressive_loader = ProgressiveLoader()

def init_progressive_loading(app):
    """Initialise le progressive loading pour l'application"""
    progressive_loader.init_app(app)
    return progressive_loader