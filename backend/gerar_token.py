import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Permissão para ler e escrever arquivos no Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

print("Iniciando processo de autenticação com o Google Drive...")
print("Seu navegador deve abrir em instantes. Por favor, faça o login.")

try:
    token_path = 'token.json'
    credentials_path = 'credentials.json'
    
    if not os.path.exists(credentials_path):
        print(f"\n❌ Falha: Arquivo '{credentials_path}' não encontrado.")
        print("Obtenha no Google Cloud Console e coloque nesta pasta.")
        exit(1)
        
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    # Isso abre o navegador no PC do usuário e aguarda o login
    creds = flow.run_local_server(port=0)
    
    with open(token_path, 'w') as token:
        token.write(creds.to_json())
        
    print("\n✅ SUCESSO! Autenticação concluída.")
    print("O arquivo 'token.json' foi gerado na sua pasta backend.")
    print("Você já pode voltar a rodar o 'python main.py' normalmente.")

except Exception as e:
    print(f"\n❌ Erro durante a autenticação: {e}")
