"""
Intégration Google Analytics 4 pour tracking avancé
Suivi des conversions et analyses de performance
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    Dimension,
    Metric,
    DateRange,
    Filter,
    FilterExpression
)
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

class GoogleAnalyticsManager:
    """Gestionnaire Google Analytics 4"""
    
    def __init__(self):
        self.property_id = os.environ.get('GA4_PROPERTY_ID')
        self.service_account_key = os.environ.get('GA4_SERVICE_ACCOUNT_KEY')
        self.credentials_path = os.environ.get('GA4_CREDENTIALS_PATH')
        
        self.client = None
        
        if self.property_id and (self.service_account_key or self.credentials_path):
            try:
                if self.credentials_path:
                    credentials = Credentials.from_service_account_file(self.credentials_path)
                elif self.service_account_key:
                    import json
                    credentials_info = json.loads(self.service_account_key)
                    credentials = Credentials.from_service_account_info(credentials_info)
                
                self.client = BetaAnalyticsDataClient(credentials=credentials)
                self.enabled = True
                logger.info("Google Analytics 4 initialized")
            except Exception as e:
                logger.error(f"Erreur initialisation GA4: {str(e)}")
                self.enabled = False
        else:
            self.enabled = False
            logger.warning("Google Analytics 4 non configuré")
    
    def get_basic_metrics(self, 
                         start_date: str = "30daysAgo",
                         end_date: str = "today") -> Optional[Dict]:
        """Récupérer les métriques de base"""
        if not self.enabled:
            return None
        
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[
                    Dimension(name="date"),
                ],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="totalUsers"),
                    Metric(name="pageviews"),
                    Metric(name="bounceRate"),
                    Metric(name="sessionDuration")
                ],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            )
            
            response = self.client.run_report(request)
            
            # Traiter la réponse
            metrics_data = []
            for row in response.rows:
                date_value = row.dimension_values[0].value
                metric_values = [mv.value for mv in row.metric_values]
                
                metrics_data.append({
                    'date': date_value,
                    'sessions': int(metric_values[0]),
                    'users': int(metric_values[1]),
                    'pageviews': int(metric_values[2]),
                    'bounce_rate': float(metric_values[3]),
                    'avg_session_duration': float(metric_values[4])
                })
            
            # Calculer les totaux
            totals = {
                'total_sessions': sum(day['sessions'] for day in metrics_data),
                'total_users': sum(day['users'] for day in metrics_data),
                'total_pageviews': sum(day['pageviews'] for day in metrics_data),
                'avg_bounce_rate': sum(day['bounce_rate'] for day in metrics_data) / len(metrics_data) if metrics_data else 0,
                'avg_session_duration': sum(day['avg_session_duration'] for day in metrics_data) / len(metrics_data) if metrics_data else 0
            }
            
            return {
                'daily_data': metrics_data,
                'totals': totals,
                'period': f"{start_date} to {end_date}"
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération métriques GA4: {str(e)}")
            return None
    
    def get_conversion_metrics(self, 
                              start_date: str = "30daysAgo",
                              end_date: str = "today") -> Optional[Dict]:
        """Récupérer les métriques de conversion"""
        if not self.enabled:
            return None
        
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[
                    Dimension(name="eventName"),
                ],
                metrics=[
                    Metric(name="eventCount"),
                    Metric(name="conversions"),
                    Metric(name="totalRevenue")
                ],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimension_filter=FilterExpression(
                    filter=Filter(
                        field_name="eventName",
                        string_filter=Filter.StringFilter(
                            match_type=Filter.StringFilter.MatchType.CONTAINS,
                            value="conversion"
                        )
                    )
                )
            )
            
            response = self.client.run_report(request)
            
            conversions_data = []
            for row in response.rows:
                event_name = row.dimension_values[0].value
                metric_values = [mv.value for mv in row.metric_values]
                
                conversions_data.append({
                    'event_name': event_name,
                    'event_count': int(metric_values[0]),
                    'conversions': int(metric_values[1]),
                    'revenue': float(metric_values[2]) if metric_values[2] else 0.0
                })
            
            return {
                'conversions': conversions_data,
                'total_conversions': sum(conv['conversions'] for conv in conversions_data),
                'total_revenue': sum(conv['revenue'] for conv in conversions_data)
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération conversions GA4: {str(e)}")
            return None
    
    def get_traffic_sources(self, 
                           start_date: str = "30daysAgo",
                           end_date: str = "today") -> Optional[Dict]:
        """Récupérer les sources de trafic"""
        if not self.enabled:
            return None
        
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[
                    Dimension(name="sessionDefaultChannelGroup"),
                    Dimension(name="sessionSource"),
                ],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="totalUsers"),
                    Metric(name="conversions")
                ],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            )
            
            response = self.client.run_report(request)
            
            traffic_data = []
            for row in response.rows:
                channel = row.dimension_values[0].value
                source = row.dimension_values[1].value
                metric_values = [mv.value for mv in row.metric_values]
                
                traffic_data.append({
                    'channel': channel,
                    'source': source,
                    'sessions': int(metric_values[0]),
                    'users': int(metric_values[1]),
                    'conversions': int(metric_values[2])
                })
            
            # Grouper par canal
            channels_summary = {}
            for item in traffic_data:
                channel = item['channel']
                if channel not in channels_summary:
                    channels_summary[channel] = {
                        'sessions': 0,
                        'users': 0,
                        'conversions': 0
                    }
                
                channels_summary[channel]['sessions'] += item['sessions']
                channels_summary[channel]['users'] += item['users']
                channels_summary[channel]['conversions'] += item['conversions']
            
            return {
                'detailed_sources': traffic_data,
                'channels_summary': channels_summary
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération sources trafic GA4: {str(e)}")
            return None
    
    def get_page_analytics(self, 
                          start_date: str = "30daysAgo",
                          end_date: str = "today") -> Optional[Dict]:
        """Récupérer les analytics par page"""
        if not self.enabled:
            return None
        
        try:
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[
                    Dimension(name="pagePath"),
                    Dimension(name="pageTitle"),
                ],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="uniquePageViews"),
                    Metric(name="averageTimeOnPage"),
                    Metric(name="exitRate")
                ],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                order_bys=[
                    {
                        'metric': {'metric_name': 'screenPageViews'},
                        'desc': True
                    }
                ],
                limit=50
            )
            
            response = self.client.run_report(request)
            
            pages_data = []
            for row in response.rows:
                page_path = row.dimension_values[0].value
                page_title = row.dimension_values[1].value
                metric_values = [mv.value for mv in row.metric_values]
                
                pages_data.append({
                    'path': page_path,
                    'title': page_title,
                    'pageviews': int(metric_values[0]),
                    'unique_pageviews': int(metric_values[1]),
                    'avg_time_on_page': float(metric_values[2]),
                    'exit_rate': float(metric_values[3])
                })
            
            return {
                'top_pages': pages_data[:10],
                'all_pages': pages_data
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération analytics pages GA4: {str(e)}")
            return None
    
    def track_custom_event(self, 
                          event_name: str,
                          parameters: Dict[str, Any] = None) -> bool:
        """Envoyer un événement personnalisé (via Measurement Protocol)"""
        if not self.enabled:
            return False
        
        try:
            import requests
            
            # URL Measurement Protocol GA4
            url = "https://www.google-analytics.com/mp/collect"
            
            # Paramètres requis
            params = {
                'measurement_id': self.property_id,
                'api_secret': os.environ.get('GA4_API_SECRET', '')
            }
            
            # Corps de la requête
            payload = {
                'client_id': 'ninjalead_server',
                'events': [{
                    'name': event_name,
                    'parameters': parameters or {}
                }]
            }
            
            response = requests.post(url, params=params, json=payload)
            
            if response.status_code == 204:
                logger.info(f"Événement GA4 envoyé: {event_name}")
                return True
            else:
                logger.error(f"Erreur envoi événement GA4: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Exception envoi événement GA4: {str(e)}")
            return False
    
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Générer un résumé pour le tableau de bord"""
        if not self.enabled:
            return {'enabled': False, 'error': 'Google Analytics non configuré'}
        
        try:
            # Récupérer les données des 30 derniers jours
            basic_metrics = self.get_basic_metrics()
            conversions = self.get_conversion_metrics()
            traffic_sources = self.get_traffic_sources()
            top_pages = self.get_page_analytics()
            
            # Comparer avec la période précédente pour les tendances
            previous_metrics = self.get_basic_metrics("60daysAgo", "30daysAgo")
            
            trends = {}
            if basic_metrics and previous_metrics:
                current_totals = basic_metrics['totals']
                previous_totals = previous_metrics['totals']
                
                for metric in current_totals:
                    if metric in previous_totals and previous_totals[metric] > 0:
                        change = ((current_totals[metric] - previous_totals[metric]) / previous_totals[metric]) * 100
                        trends[metric] = round(change, 2)
            
            return {
                'enabled': True,
                'basic_metrics': basic_metrics,
                'conversions': conversions,
                'traffic_sources': traffic_sources,
                'top_pages': top_pages,
                'trends': trends,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur génération dashboard GA4: {str(e)}")
            return {'enabled': False, 'error': str(e)}

# Instance globale
analytics_manager = GoogleAnalyticsManager()

# Événements personnalisés prédéfinis
CUSTOM_EVENTS = {
    'campaign_created': {
        'name': 'campaign_created',
        'description': 'Nouvelle campagne créée'
    },
    'customer_generated': {
        'name': 'customer_generated',
        'description': 'Nouveau client généré par IA'
    },
    'product_analyzed': {
        'name': 'product_analyzed',
        'description': 'Produit analysé avec OSP'
    },
    'subscription_started': {
        'name': 'subscription_started',
        'description': 'Abonnement démarré'
    },
    'feature_used': {
        'name': 'feature_used',
        'description': 'Fonctionnalité utilisée'
    }
}