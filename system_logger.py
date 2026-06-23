"""
Module de logging système pour EduGestion IA
Réservé exclusivement au développeur (super_users)

Fonctionnalités :
- Logs des connexions utilisateurs
- Logs des erreurs système
- Logs des actions critiques (CRUD)
- Statistiques d'utilisation
- Monitoring des performances
"""

import os
import json
import sqlite3
import logging
import functools
from datetime import datetime, timedelta
from pathlib import Path
from flask import request, session, current_app


# Configuration du répertoire de logs
LOGS_DIR = Path(__file__).parent / 'logs'
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Fichier de base de données pour les logs structurés
LOGS_DB = LOGS_DIR / 'system_logs.db'


class SystemLogger:
    """
    Gestionnaire centralisé des logs système
    """
    
    def __init__(self):
        self._init_logs_db()
        self._setup_file_logging()
        
    def _init_logs_db(self):
        """Initialise la base de données des logs"""
        conn = sqlite3.connect(str(LOGS_DB))
        cursor = conn.cursor()
        
        # Table des logs d'activité
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                user_id INTEGER,
                username TEXT,
                ip_address TEXT,
                action TEXT NOT NULL,
                description TEXT,
                details TEXT,
                endpoint TEXT,
                method TEXT,
                user_agent TEXT,
                session_id TEXT
            )
        ''')
        
        # Table des logs de connexion
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                username TEXT NOT NULL,
                ip_address TEXT,
                success BOOLEAN NOT NULL,
                failure_reason TEXT,
                user_agent TEXT,
                session_id TEXT
            )
        ''')
        
        # Table des erreurs système
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                error_type TEXT,
                message TEXT NOT NULL,
                traceback TEXT,
                endpoint TEXT,
                user_id INTEGER,
                ip_address TEXT
            )
        ''')
        
        # Créer des index pour optimiser les requêtes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_logs(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_category ON activity_logs(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_logs(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_login_timestamp ON login_logs(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_login_username ON login_logs(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_error_timestamp ON error_logs(timestamp)')
        
        conn.commit()
        conn.close()
        
    def _setup_file_logging(self):
        """Configure les logs dans des fichiers"""
        # Logger pour les erreurs
        error_handler = logging.FileHandler(LOGS_DIR / 'errors.log')
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        error_handler.setFormatter(error_formatter)
        
        # Logger pour l'activité
        activity_handler = logging.FileHandler(LOGS_DIR / 'activity.log')
        activity_handler.setLevel(logging.INFO)
        activity_formatter = logging.Formatter(
            '%(asctime)s - %(message)s'
        )
        activity_handler.setFormatter(activity_formatter)
        
        # Configurer le logger root
        self.logger = logging.getLogger('EduGestion')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(activity_handler)
        
    def log_activity(self, level, category, action, description=None, details=None, user=None):
        """
        Enregistre une activité dans les logs
        
        Args:
            level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            category: Catégorie de l'action (auth, crud, system, admin, etc.)
            action: Nom de l'action effectuée
            description: Description détaillée (optionnel)
            details: Détails techniques en JSON (optionnel)
            user: Objet utilisateur Flask-Login (optionnel)
        """
        try:
            timestamp = datetime.now().isoformat()
            
            # Récupérer les infos de la requête si disponible
            ip_address = None
            endpoint = None
            method = None
            user_agent = None
            session_id = None
            
            try:
                from flask import request
                if request:
                    ip_address = request.remote_addr
                    endpoint = request.endpoint
                    method = request.method
                    user_agent = request.headers.get('User-Agent', '')[:255]
            except:
                pass
                
            # Infos utilisateur
            user_id = None
            username = None
            if user and hasattr(user, 'id'):
                user_id = user.id
                username = getattr(user, 'username', None)
                
            # Enregistrer dans la base SQLite
            conn = sqlite3.connect(str(LOGS_DB))
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO activity_logs 
                (timestamp, level, category, user_id, username, ip_address, action, 
                 description, details, endpoint, method, user_agent, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, level, category, user_id, username, ip_address, action,
                  description, json.dumps(details) if details else None, endpoint, method, 
                  user_agent, session_id))
            conn.commit()
            conn.close()
            
            # Écrire aussi dans le fichier de log
            log_message = f"[{category}] {action}"
            if username:
                log_message += f" par {username}"
            if description:
                log_message += f" - {description}"
                
            level_method = getattr(self.logger, level.lower(), self.logger.info)
            level_method(log_message)
            
        except Exception as e:
            # Ne pas bloquer l'application si le logging échoue
            self.logger.error(f"Erreur lors du log d'activité: {str(e)}")
            
    def log_login(self, username, success, failure_reason=None):
        """
        Enregistre une tentative de connexion
        
        Args:
            username: Nom d'utilisateur
            success: True si connexion réussie, False sinon
            failure_reason: Raison de l'échec (optionnel)
        """
        try:
            timestamp = datetime.now().isoformat()
            
            # Récupérer les infos de la requête
            ip_address = None
            user_agent = None
            session_id = None
            
            try:
                from flask import request
                if request:
                    ip_address = request.remote_addr
                    user_agent = request.headers.get('User-Agent', '')[:255]
            except:
                pass
                
            # Enregistrer dans la base
            conn = sqlite3.connect(str(LOGS_DB))
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO login_logs 
                (timestamp, username, ip_address, success, failure_reason, user_agent, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, username, ip_address, success, failure_reason, user_agent, session_id))
            conn.commit()
            conn.close()
            
            # Log dans le fichier
            status = "RÉUSSIE" if success else "ÉCHOUÉE"
            self.logger.info(f"Connexion {status} pour '{username}' depuis {ip_address or 'inconnu'}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du log de connexion: {str(e)}")
            
    def log_error(self, error, endpoint=None, user=None):
        """
        Enregistre une erreur système
        
        Args:
            error: Exception ou message d'erreur
            endpoint: Endpoint où l'erreur s'est produite
            user: Utilisateur connecté (optionnel)
        """
        try:
            import traceback
            
            timestamp = datetime.now().isoformat()
            
            # Extraire les informations de l'erreur
            if isinstance(error, Exception):
                error_type = type(error).__name__
                message = str(error)
                tb = traceback.format_exc()
            else:
                error_type = "Unknown"
                message = str(error)
                tb = None
                
            # Infos utilisateur et IP
            user_id = None
            ip_address = None
            
            if user and hasattr(user, 'id'):
                user_id = user.id
                
            try:
                from flask import request
                if request:
                    ip_address = request.remote_addr
                    if not endpoint:
                        endpoint = request.endpoint
            except:
                pass
                
            # Enregistrer dans la base
            conn = sqlite3.connect(str(LOGS_DB))
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO error_logs 
                (timestamp, level, error_type, message, traceback, endpoint, user_id, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, 'ERROR', error_type, message, tb, endpoint, user_id, ip_address))
            conn.commit()
            conn.close()
            
            # Log dans le fichier
            self.logger.error(f"ERREUR [{error_type}] dans {endpoint or 'inconnu'}: {message}")
            
        except Exception as e:
            # Dernier recours si tout échoue
            print(f"ERREUR CRITIQUE - Impossible de logger: {str(e)}")
            
    def get_stats(self, days=7):
        """
        Retourne des statistiques d'utilisation
        
        Args:
            days: Nombre de jours pour les statistiques
            
        Returns:
            dict: Statistiques
        """
        try:
            since = (datetime.now() - timedelta(days=days)).isoformat()
            
            conn = sqlite3.connect(str(LOGS_DB))
            cursor = conn.cursor()
            
            # Nombre total d'actions
            cursor.execute('''
                SELECT COUNT(*) FROM activity_logs WHERE timestamp > ?
            ''', (since,))
            total_actions = cursor.fetchone()[0]
            
            # Connexions réussies/échouées
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
                FROM login_logs WHERE timestamp > ?
            ''', (since,))
            row = cursor.fetchone()
            logins_success = row[0] or 0
            logins_failed = row[1] or 0
            
            # Erreurs
            cursor.execute('''
                SELECT COUNT(*) FROM error_logs WHERE timestamp > ?
            ''', (since,))
            total_errors = cursor.fetchone()[0]
            
            # Top utilisateurs actifs
            cursor.execute('''
                SELECT username, COUNT(*) as count 
                FROM activity_logs 
                WHERE timestamp > ? AND username IS NOT NULL
                GROUP BY username 
                ORDER BY count DESC 
                LIMIT 5
            ''', (since,))
            top_users = cursor.fetchall()
            
            # Actions par catégorie
            cursor.execute('''
                SELECT category, COUNT(*) as count 
                FROM activity_logs 
                WHERE timestamp > ?
                GROUP BY category 
                ORDER BY count DESC
            ''', (since,))
            categories = cursor.fetchall()
            
            conn.close()
            
            return {
                'period_days': days,
                'total_actions': total_actions,
                'logins_success': logins_success,
                'logins_failed': logins_failed,
                'total_errors': total_errors,
                'top_users': top_users,
                'categories': categories
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'period_days': days,
                'total_actions': 0,
                'logins_success': 0,
                'logins_failed': 0,
                'total_errors': 0,
                'top_users': [],
                'categories': []
            }


# Instance globale
system_logger = SystemLogger()


# Décorateur pour logger automatiquement les actions
def log_action(category, action_description):
    """
    Décorateur pour logger automatiquement une action
    
    Usage:
        @log_action('crud', 'Création élève')
        def create_eleve():
            ...
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Récupérer l'utilisateur courant si disponible
            user = None
            try:
                from flask_login import current_user
                if current_user and current_user.is_authenticated:
                    user = current_user
            except:
                pass
                
            # Exécuter la fonction
            try:
                result = f(*args, **kwargs)
                success = True
                error_msg = None
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                # Logger l'action
                description = action_description
                if not success:
                    description += f" (ÉCHEC: {error_msg})"
                    
                system_logger.log_activity(
                    level='INFO' if success else 'ERROR',
                    category=category,
                    action=action_description,
                    description=description,
                    user=user
                )
                
            return result
        return decorated_function
    return decorator
