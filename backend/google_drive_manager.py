import os
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Permissão para ler e escrever arquivos no Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

logger = logging.getLogger("GoogleDriveManager")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class DriveCredentialsError(Exception):
    """Exceção levantada quando credenciais ou tokens oauth estão ausentes."""
    pass

class GoogleDriveManager:
    """
    Data Lake Frio Governamental
    Responsável por armazenar arquivos JSON consolidados na nuvem (Google Drive 5TB)
    para consulta offline da transparência.
    """
    def __init__(self):
        self.creds = None
        self.token_path = os.path.join(os.path.dirname(__file__), 'token.json')
        self.credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
        self.service = None
        self.root_folder_id = None
        
        self.init_service()

    def init_service(self):
        """Inicializa e valida o Auth0 sem silenciar as exceções cruciais de ambiente"""
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("♻️ Atualizando token de acesso expirado do Google Drive...")
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    msg = " Arquivo 'credentials.json' (GCP) não encontrado no backend. O Data Lake Google Drive exige credencial."
                    logger.error(f"❌ {msg}")
                    raise DriveCredentialsError(msg)
                    
                msg = " Autenticação Oauth2 pendente. O arquivo token.json não está presente/válido. Autentique manualmente sua conta para o App Console."
                logger.error(f"❌ {msg}")
                raise DriveCredentialsError(msg)

            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
                
        self.service = build('drive', 'v3', credentials=self.creds)
        self.root_folder_id = self._get_or_create_folder("GovTech_Auditorias")
        logger.info("☁️ [DRIVE] Data Lake Storage Manager ativo.")

    def _get_or_create_folder(self, folder_name, parent_id=None):
        if not self.service: 
            raise DriveCredentialsError("Service do Google Drive não instanciado.")
        
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
            
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if items:
            return items[0]['id']
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')

    def salvar_dossie_no_drive(self, nome_politico, caminho_arquivo_local):
        if not self.service: 
            logger.warning(f"⚠️ Ignorando upload de {nome_politico}, o serviço Drive está offline/invalido.")
            return None
            
        pasta_politico_id = self._get_or_create_folder(nome_politico, self.root_folder_id)
        nome_arquivo = os.path.basename(caminho_arquivo_local)
        
        file_metadata = {'name': nome_arquivo, 'parents': [pasta_politico_id]}
        media = MediaFileUpload(caminho_arquivo_local, mimetype='application/json', resumable=True)
        
        try:
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            logger.info(f"📤 [DRIVE_LAKE] JSON Dossiê gravado na nuvem! (Entidade: {nome_politico}) | ID: {file.get('id')}")
            return file.get('id')
        except Exception as e:
            logger.error(f"❌ Erro ao performar upload para Google Drive: {e}")
            raise
