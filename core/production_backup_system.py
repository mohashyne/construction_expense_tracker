"""
Enhanced production backup system with multiple storage destinations
Supports local, Google Drive, and database backup options
"""

import os
import json
import csv
import zipfile
import tempfile
import subprocess
import shutil
from datetime import datetime, timedelta
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from django.core.files.storage import default_storage
import logging

from .backup_system import BackupManager
from .models import Company, CompanyMembership, UserProfile

logger = logging.getLogger(__name__)


class BackupDestination:
    """Base class for backup destinations"""
    
    def __init__(self, name, config=None):
        self.name = name
        self.config = config or {}
    
    def upload(self, local_path, remote_name):
        """Upload backup to destination"""
        raise NotImplementedError
    
    def list_backups(self):
        """List available backups at destination"""
        raise NotImplementedError
    
    def download(self, remote_name, local_path):
        """Download backup from destination"""
        raise NotImplementedError
    
    def delete(self, remote_name):
        """Delete backup from destination"""
        raise NotImplementedError
    
    def test_connection(self):
        """Test connection to backup destination"""
        raise NotImplementedError


class LocalBackupDestination(BackupDestination):
    """Local filesystem backup destination"""
    
    def __init__(self, config=None):
        super().__init__("Local Storage", config)
        self.backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def upload(self, local_path, remote_name):
        """Move/copy file to backup directory"""
        destination_path = os.path.join(self.backup_dir, remote_name)
        if local_path != destination_path:
            shutil.copy2(local_path, destination_path)
        return destination_path
    
    def list_backups(self):
        """List local backup files"""
        backups = []
        if os.path.exists(self.backup_dir):
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.zip'):
                    file_path = os.path.join(self.backup_dir, filename)
                    stat = os.stat(file_path)
                    backups.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_mtime),
                        'destination': 'local'
                    })
        return backups
    
    def download(self, remote_name, local_path):
        """Copy from backup directory to local path"""
        source_path = os.path.join(self.backup_dir, remote_name)
        if os.path.exists(source_path):
            shutil.copy2(source_path, local_path)
            return True
        return False
    
    def delete(self, remote_name):
        """Delete local backup file"""
        file_path = os.path.join(self.backup_dir, remote_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    
    def test_connection(self):
        """Test local storage access"""
        try:
            test_file = os.path.join(self.backup_dir, 'test_connection.tmp')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return True
        except Exception as e:
            logger.error(f"Local backup destination test failed: {e}")
            return False


class GoogleDriveBackupDestination(BackupDestination):
    """Google Drive backup destination"""
    
    def __init__(self, config=None):
        super().__init__("Google Drive", config)
        self.service = None
        self.folder_id = config.get('folder_id') if config else None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive API service"""
        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account
            
            # Load service account credentials
            credentials_path = getattr(settings, 'GOOGLE_DRIVE_CREDENTIALS_PATH', None)
            if not credentials_path or not os.path.exists(credentials_path):
                logger.warning("Google Drive credentials not found")
                return False
            
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            
            self.service = build('drive', 'v3', credentials=credentials)
            return True
            
        except ImportError:
            logger.warning("Google API client library not installed. Run: pip install google-api-python-client google-auth")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            return False
    
    def upload(self, local_path, remote_name):
        """Upload backup to Google Drive"""
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        try:
            from googleapiclient.http import MediaFileUpload
            
            file_metadata = {
                'name': remote_name,
                'description': f'Construction Tracker backup created on {datetime.now().isoformat()}'
            }
            
            if self.folder_id:
                file_metadata['parents'] = [self.folder_id]
            
            media = MediaFileUpload(local_path, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            return file.get('id')
            
        except Exception as e:
            logger.error(f"Google Drive upload failed: {e}")
            raise
    
    def list_backups(self):
        """List backups in Google Drive"""
        if not self.service:
            return []
        
        try:
            query = "name contains 'backup' and trashed=false"
            if self.folder_id:
                query += f" and '{self.folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, size, createdTime, modifiedTime)"
            ).execute()
            
            backups = []
            for file in results.get('files', []):
                backups.append({
                    'filename': file['name'],
                    'size': int(file.get('size', 0)),
                    'created_at': datetime.fromisoformat(file['createdTime'].replace('Z', '+00:00')),
                    'destination': 'google_drive',
                    'file_id': file['id']
                })
            
            return backups
            
        except Exception as e:
            logger.error(f"Google Drive list failed: {e}")
            return []
    
    def download(self, remote_name, local_path):
        """Download backup from Google Drive"""
        if not self.service:
            return False
        
        try:
            # Find file by name
            query = f"name='{remote_name}' and trashed=false"
            results = self.service.files().list(q=query).execute()
            files = results.get('files', [])
            
            if not files:
                return False
            
            file_id = files[0]['id']
            request = self.service.files().get_media(fileId=file_id)
            
            with open(local_path, 'wb') as f:
                downloader = request.execute()
                f.write(downloader)
            
            return True
            
        except Exception as e:
            logger.error(f"Google Drive download failed: {e}")
            return False
    
    def delete(self, remote_name):
        """Delete backup from Google Drive"""
        if not self.service:
            return False
        
        try:
            # Find file by name
            query = f"name='{remote_name}' and trashed=false"
            results = self.service.files().list(q=query).execute()
            files = results.get('files', [])
            
            if not files:
                return False
            
            file_id = files[0]['id']
            self.service.files().delete(fileId=file_id).execute()
            return True
            
        except Exception as e:
            logger.error(f"Google Drive delete failed: {e}")
            return False
    
    def test_connection(self):
        """Test Google Drive connection"""
        if not self.service:
            return False
        
        try:
            # Try to list files to test connection
            self.service.files().list(pageSize=1).execute()
            return True
        except Exception as e:
            logger.error(f"Google Drive connection test failed: {e}")
            return False


class DatabaseBackupDestination(BackupDestination):
    """Database backup destination - creates database dumps"""
    
    def __init__(self, config=None):
        super().__init__("Database Backup", config)
        self.backup_dir = os.path.join(settings.MEDIA_ROOT, 'db_backups')
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def upload(self, local_path, remote_name):
        """This destination creates its own backups"""
        return self.create_database_backup(remote_name)
    
    def create_database_backup(self, backup_name):
        """Create database backup using Django management command"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Use Django's dumpdata command for database backup
            with open(backup_path, 'w') as backup_file:
                call_command('dumpdata', stdout=backup_file, format='json', indent=2)
            
            # Create compressed version
            import gzip
            compressed_path = backup_path + '.gz'
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed version
            os.remove(backup_path)
            
            return compressed_path
            
        except Exception as e:
            logger.error(f"Database backup creation failed: {e}")
            raise
    
    def create_sql_backup(self, backup_name):
        """Create raw SQL backup (for PostgreSQL/MySQL)"""
        try:
            db_config = settings.DATABASES['default']
            engine = db_config['ENGINE']
            
            backup_path = os.path.join(self.backup_dir, backup_name.replace('.json.gz', '.sql'))
            
            if 'postgresql' in engine:
                # PostgreSQL backup
                cmd = [
                    'pg_dump',
                    f"--host={db_config.get('HOST', 'localhost')}",
                    f"--port={db_config.get('PORT', 5432)}",
                    f"--username={db_config['USER']}",
                    f"--dbname={db_config['NAME']}",
                    f"--file={backup_path}",
                    '--verbose'
                ]
                
                env = os.environ.copy()
                env['PGPASSWORD'] = db_config['PASSWORD']
                
                subprocess.run(cmd, env=env, check=True)
                
            elif 'mysql' in engine:
                # MySQL backup
                cmd = [
                    'mysqldump',
                    f"--host={db_config.get('HOST', 'localhost')}",
                    f"--port={db_config.get('PORT', 3306)}",
                    f"--user={db_config['USER']}",
                    f"--password={db_config['PASSWORD']}",
                    db_config['NAME']
                ]
                
                with open(backup_path, 'w') as backup_file:
                    subprocess.run(cmd, stdout=backup_file, check=True)
            
            else:
                logger.warning(f"SQL backup not supported for {engine}")
                return None
            
            # Compress SQL backup
            import gzip
            compressed_path = backup_path + '.gz'
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            os.remove(backup_path)
            return compressed_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"SQL backup command failed: {e}")
            return None
        except Exception as e:
            logger.error(f"SQL backup creation failed: {e}")
            return None
    
    def list_backups(self):
        """List database backup files"""
        backups = []
        if os.path.exists(self.backup_dir):
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.gz'):
                    file_path = os.path.join(self.backup_dir, filename)
                    stat = os.stat(file_path)
                    backups.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_mtime),
                        'destination': 'database'
                    })
        return backups
    
    def download(self, remote_name, local_path):
        """Copy database backup to local path"""
        source_path = os.path.join(self.backup_dir, remote_name)
        if os.path.exists(source_path):
            shutil.copy2(source_path, local_path)
            return True
        return False
    
    def delete(self, remote_name):
        """Delete database backup file"""
        file_path = os.path.join(self.backup_dir, remote_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    
    def test_connection(self):
        """Test database backup capability"""
        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False


class ProductionBackupManager:
    """Enhanced backup manager with multiple destination support"""
    
    def __init__(self, user):
        self.user = user
        self.destinations = self._initialize_destinations()
    
    def _initialize_destinations(self):
        """Initialize available backup destinations"""
        destinations = {}
        
        # Always include local backup
        destinations['local'] = LocalBackupDestination()
        
        # Add Google Drive if configured
        if hasattr(settings, 'GOOGLE_DRIVE_CREDENTIALS_PATH'):
            google_drive_config = {
                'folder_id': getattr(settings, 'GOOGLE_DRIVE_BACKUP_FOLDER_ID', None)
            }
            destinations['google_drive'] = GoogleDriveBackupDestination(google_drive_config)
        
        # Add database backup
        destinations['database'] = DatabaseBackupDestination()
        
        return destinations
    
    def get_available_destinations(self):
        """Get list of available and working destinations"""
        available = []
        for name, destination in self.destinations.items():
            status = destination.test_connection()
            available.append({
                'name': name,
                'display_name': destination.name,
                'available': status,
                'type': 'cloud' if name == 'google_drive' else 'local'
            })
        return available
    
    def create_backup(self, backup_type='full', destinations=None):
        """Create backup and store in specified destinations"""
        if destinations is None:
            destinations = ['local']  # Default to local storage
        
        results = []
        
        # Create base backup using existing system
        base_backup_manager = BackupManager(self.user, backup_type)
        backup_result = base_backup_manager.create_backup()
        
        if not backup_result['success']:
            return backup_result
        
        local_backup_path = backup_result['backup_path']
        backup_filename = backup_result['backup_file']
        
        # Upload to each specified destination
        for dest_name in destinations:
            if dest_name not in self.destinations:
                results.append({
                    'destination': dest_name,
                    'success': False,
                    'error': 'Destination not available'
                })
                continue
            
            try:
                destination = self.destinations[dest_name]
                
                if dest_name == 'database':
                    # Create database-specific backup
                    db_backup_name = backup_filename.replace('.zip', '_db.json.gz')
                    result_path = destination.create_database_backup(db_backup_name)
                    
                    # Also create SQL backup if possible
                    sql_backup_name = backup_filename.replace('.zip', '_sql.sql.gz')
                    sql_path = destination.create_sql_backup(sql_backup_name)
                    
                    results.append({
                        'destination': dest_name,
                        'success': True,
                        'backup_file': db_backup_name,
                        'sql_backup': sql_path is not None
                    })
                else:
                    # Upload data backup
                    uploaded_path = destination.upload(local_backup_path, backup_filename)
                    
                    results.append({
                        'destination': dest_name,
                        'success': True,
                        'backup_file': backup_filename,
                        'path': uploaded_path if dest_name == 'local' else None
                    })
            
            except Exception as e:
                logger.error(f"Backup to {dest_name} failed: {e}")
                results.append({
                    'destination': dest_name,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'backup_file': backup_filename,
            'size': backup_result['size'],
            'created_at': backup_result['created_at'],
            'destinations': results
        }
    
    def list_all_backups(self):
        """List backups from all destinations"""
        all_backups = {}
        
        for dest_name, destination in self.destinations.items():
            try:
                backups = destination.list_backups()
                all_backups[dest_name] = {
                    'name': destination.name,
                    'backups': backups,
                    'available': destination.test_connection()
                }
            except Exception as e:
                logger.error(f"Failed to list backups from {dest_name}: {e}")
                all_backups[dest_name] = {
                    'name': destination.name,
                    'backups': [],
                    'available': False,
                    'error': str(e)
                }
        
        return all_backups
    
    def download_backup(self, destination_name, backup_filename, local_path=None):
        """Download backup from specific destination"""
        if destination_name not in self.destinations:
            return {'success': False, 'error': 'Destination not found'}
        
        if local_path is None:
            local_path = os.path.join(tempfile.gettempdir(), backup_filename)
        
        try:
            destination = self.destinations[destination_name]
            success = destination.download(backup_filename, local_path)
            
            if success:
                return {
                    'success': True,
                    'local_path': local_path,
                    'size': os.path.getsize(local_path)
                }
            else:
                return {'success': False, 'error': 'Download failed'}
                
        except Exception as e:
            logger.error(f"Download from {destination_name} failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def delete_backup(self, destination_name, backup_filename):
        """Delete backup from specific destination"""
        if destination_name not in self.destinations:
            return {'success': False, 'error': 'Destination not found'}
        
        try:
            destination = self.destinations[destination_name]
            success = destination.delete(backup_filename)
            
            return {'success': success}
            
        except Exception as e:
            logger.error(f"Delete from {destination_name} failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def sync_backup_to_cloud(self, backup_filename, cloud_destinations=None):
        """Sync existing local backup to cloud destinations"""
        if cloud_destinations is None:
            cloud_destinations = ['google_drive']
        
        local_destination = self.destinations.get('local')
        if not local_destination:
            return {'success': False, 'error': 'Local destination not available'}
        
        # Find local backup
        local_backups = local_destination.list_backups()
        local_backup = next((b for b in local_backups if b['filename'] == backup_filename), None)
        
        if not local_backup:
            return {'success': False, 'error': 'Local backup not found'}
        
        local_path = os.path.join(local_destination.backup_dir, backup_filename)
        
        results = []
        for dest_name in cloud_destinations:
            if dest_name not in self.destinations:
                continue
                
            try:
                destination = self.destinations[dest_name]
                uploaded_path = destination.upload(local_path, backup_filename)
                
                results.append({
                    'destination': dest_name,
                    'success': True,
                    'backup_file': backup_filename
                })
                
            except Exception as e:
                logger.error(f"Sync to {dest_name} failed: {e}")
                results.append({
                    'destination': dest_name,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'backup_file': backup_filename,
            'sync_results': results
        }


def get_backup_schedule_status():
    """Get status of scheduled backups"""
    # This would integrate with celery/cron for scheduled backups
    return {
        'scheduled_backups': [],
        'last_auto_backup': None,
        'next_scheduled': None,
        'schedule_enabled': False
    }


def configure_backup_destinations(config_data):
    """Configure backup destinations"""
    # This would save configuration to database or settings
    return {'success': True, 'message': 'Backup destinations configured'}


def test_all_backup_destinations():
    """Test all backup destinations"""
    manager = ProductionBackupManager(None)
    return manager.get_available_destinations()
