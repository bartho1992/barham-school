"""
Module de gestion des sauvegardes pour EduGestion IA
Réservé exclusivement au développeur (super_users)
"""

import os
import shutil
import sqlite3
import json
from datetime import datetime
from pathlib import Path


class BackupManager:
    """Gestionnaire de sauvegardes de la base de données SQLite"""
    
    def __init__(self, db_path=None, backup_dir=None):
        """
        Initialise le gestionnaire de backups
        
        Args:
            db_path: Chemin vers le fichier .db (défaut: school.db dans le répertoire courant)
            backup_dir: Répertoire de stockage des backups (défaut: backups/)
        """
        if db_path is None:
            self.db_path = Path(__file__).parent / 'school.db'
        else:
            self.db_path = Path(db_path)
            
        if backup_dir is None:
            self.backup_dir = Path(__file__).parent / 'backups'
        else:
            self.backup_dir = Path(backup_dir)
            
        # Créer le répertoire de backups s'il n'existe pas
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_backup(self, commentaire=''):
        """
        Crée une sauvegarde de la base de données
        
        Args:
            commentaire: Description optionnelle de la sauvegarde
            
        Returns:
            dict: Informations sur la sauvegarde créée
        """
        if not self.db_path.exists():
            raise FileNotFoundError(f"Base de données non trouvée: {self.db_path}")
            
        # Générer un nom de fichier unique avec timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{timestamp}.db"
        backup_path = self.backup_dir / backup_filename
        
        # Créer la sauvegarde en copiant le fichier
        shutil.copy2(self.db_path, backup_path)
        
        # Créer un fichier de métadonnées JSON
        metadata = {
            'filename': backup_filename,
            'created_at': datetime.now().isoformat(),
            'db_size': self.db_path.stat().st_size,
            'db_modified': datetime.fromtimestamp(self.db_path.stat().st_mtime).isoformat(),
            'commentaire': commentaire,
            'created_by': 'developpeur'  # Sera remplacé par l'utilisateur connecté
        }
        
        metadata_path = self.backup_dir / f"backup_{timestamp}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
        return {
            'success': True,
            'filename': backup_filename,
            'path': str(backup_path),
            'size': metadata['db_size'],
            'created_at': metadata['created_at'],
            'commentaire': commentaire
        }
        
    def list_backups(self):
        """
        Liste toutes les sauvegardes disponibles
        
        Returns:
            list: Liste des sauvegardes triées par date (plus récente d'abord)
        """
        backups = []
        
        # Parcourir tous les fichiers de métadonnées JSON
        for metadata_file in sorted(self.backup_dir.glob('backup_*.json'), reverse=True):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    
                # Vérifier que le fichier .db existe toujours
                db_file = self.backup_dir / metadata['filename']
                if db_file.exists():
                    backups.append({
                        'filename': metadata['filename'],
                        'created_at': metadata['created_at'],
                        'size': metadata['db_size'],
                        'commentaire': metadata.get('commentaire', ''),
                        'created_by': metadata.get('created_by', 'inconnu'),
                        'db_modified': metadata.get('db_modified', '')
                    })
            except Exception as e:
                # Ignorer les fichiers corrompus
                continue
                
        return backups
        
    def restore_backup(self, filename):
        """
        Restaure une sauvegarde
        
        Args:
            filename: Nom du fichier de sauvegarde à restaurer
            
        Returns:
            dict: Résultat de l'opération
        """
        backup_path = self.backup_dir / filename
        
        if not backup_path.exists():
            return {
                'success': False,
                'error': f"Sauvegarde non trouvée: {filename}"
            }
            
        # Créer une sauvegarde de sécurité avant restauration
        safety_backup = None
        if self.db_path.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safety_name = f"auto_before_restore_{timestamp}.db"
            safety_path = self.backup_dir / safety_name
            shutil.copy2(self.db_path, safety_path)
            safety_backup = safety_name
            
        try:
            # Vérifier l'intégrité du fichier de backup
            conn = sqlite3.connect(str(backup_path))
            conn.execute("PRAGMA integrity_check")
            conn.close()
            
            # Restaurer en copiant le fichier
            shutil.copy2(backup_path, self.db_path)
            
            return {
                'success': True,
                'message': f"Restauration réussie: {filename}",
                'safety_backup': safety_backup
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Erreur lors de la restauration: {str(e)}"
            }
            
    def delete_backup(self, filename):
        """
        Supprime une sauvegarde
        
        Args:
            filename: Nom du fichier à supprimer
            
        Returns:
            dict: Résultat de l'opération
        """
        backup_path = self.backup_dir / filename
        metadata_file = self.backup_dir / filename.replace('.db', '.json')
        
        try:
            if backup_path.exists():
                backup_path.unlink()
            if metadata_file.exists():
                metadata_file.unlink()
            return {
                'success': True,
                'message': f"Sauvegarde supprimée: {filename}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Erreur lors de la suppression: {str(e)}"
            }
            
    def get_db_info(self):
        """
        Retourne des informations sur la base de données actuelle
        
        Returns:
            dict: Informations sur la base de données
        """
        if not self.db_path.exists():
            return {
                'exists': False,
                'path': str(self.db_path),
                'size': 0,
                'modified': None
            }
            
        stat = self.db_path.stat()
        
        # Compter les tables
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Compter les enregistrements par table principales
            counts = {}
            for table in ['eleve', 'classe', 'user', 'note', 'paiement']:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
            conn.close()
        except:
            tables = []
            counts = {}
            
        return {
            'exists': True,
            'path': str(self.db_path),
            'size': stat.st_size,
            'size_human': self._format_size(stat.st_size),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'tables': tables,
            'record_counts': counts
        }
        
    def _format_size(self, size_bytes):
        """Formate une taille en bytes en format lisible"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"


# Instance globale du gestionnaire de backups
backup_manager = BackupManager()
