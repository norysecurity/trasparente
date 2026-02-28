import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Permissão para ler e escrever arquivos no Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveManager:
    def __init__(self):
        self.creds = None
        self.token_path = os.path.join(os.path.dirname(__file__), 'token.json')
        self.credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
        
        # Verifica se já temos o token salvo
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
        # Se não tem token ou é inválido, faz o login
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    print("⚠️ ATENÇÃO: Arquivo 'credentials.json' do Google Cloud não encontrado no backend.")
                    print("Baixe no Google Cloud Console e coloque na pasta backend/ para habilitar o Drive de 5TB.")
                    self.service = None
                    return
                # Removendo run_local_server para não travar o backend no servidor
                print("⚠️ ATENÇÃO: Autenticação via OAuth requer interação do usuário e arquivo credentials.json.")
                print("Por favor, execute script isolado para gerar token.json, o backend não suporta interrupção.")
                self.service = None
                return
            
            # Salva o token para a próxima vez
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
                
        self.service = build('drive', 'v3', credentials=self.creds)
        self.root_folder_id = self._get_or_create_folder("GovTech_Auditorias")

    def _get_or_create_folder(self, folder_name, parent_id=None):
        if not self.service: return None
        
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
        if not self.service: return None
        
        # 1. Cria a pasta com o nome do político dentro da pasta raiz
        pasta_politico_id = self._get_or_create_folder(nome_politico, self.root_folder_id)
        
        # 2. Faz o upload do JSON/Dossiê para a pasta dele
        nome_arquivo = os.path.basename(caminho_arquivo_local)
        
        # Verifica se o arquivo já existe para atualizar (opcional, aqui estamos criando novo)
        file_metadata = {'name': nome_arquivo, 'parents': [pasta_politico_id]}
        media = MediaFileUpload(caminho_arquivo_local, mimetype='application/json', resumable=True)
        
        file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"☁️ [GOOGLE DRIVE] Dossiê salvo na nuvem com sucesso! (Pasta: {nome_politico})")
        return file.get('id')
