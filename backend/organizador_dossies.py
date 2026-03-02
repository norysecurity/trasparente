import os
import json
import shutil
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OrganizadorDossies")

def organizar():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dossies_dir = os.path.join(base_dir, "dossies")
    
    if not os.path.exists(dossies_dir):
        logger.error("Pasta 'dossies' não encontrada.")
        return

    arquivos = [f for f in os.listdir(dossies_dir) if f.endswith(".json")]
    
    for arq in arquivos:
        caminho_antigo = os.path.join(dossies_dir, arq)
        try:
            with open(caminho_antigo, "r", encoding="utf-8") as f:
                dados = json.load(f)
            
            uf = (dados.get("uf") or "BR").upper().strip()
            cidade = (dados.get("cidade") or "OUTROS").upper().strip()
            
            # Sanitizar nomes de pastas
            cidade = cidade.replace("/", "-").replace("\\", "-")
            
            nova_pasta = os.path.join(dossies_dir, uf, cidade)
            if not os.path.exists(nova_pasta):
                os.makedirs(nova_pasta)
            
            caminho_novo = os.path.join(nova_pasta, arq)
            shutil.move(caminho_antigo, caminho_novo)
            logger.info(f"Movido: {arq} -> {uf}/{cidade}/")
        except Exception as e:
            logger.error(f"Erro ao organizar {arq}: {e}")

if __name__ == "__main__":
    organizar()
