import os
import json
import asyncio
import logging
from datetime import datetime
from motor_ia_qwen import AuditorGovernamentalIA
from database.neo4j_conn import Neo4jConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AuditorEmMassa")

# Configurações
BATCH_SIZE = 50  # Processar em lotes para não estourar a API

async def processar_politico(auditor, neo4j, p):
    """Gera o dossiê completo para um político e salva na estrutura hierárquica."""
    # Acesso seguro às propriedades do nó Neo4j
    id_politico = p.get("id_tse") or p.get("id") or p.get("cpf")
    nome = p.get("nome", "Desconhecido")
    uf = (p.get("uf") or "BR").upper()
    cidade = (p.get("municipio") or p.get("cidade") or "OUTROS").upper()
    
    if not id_politico:
        logger.warning(f"Político {nome} sem ID válido. Pulando.")
        return

    logger.info(f"Auditando: {nome} (ID: {id_politico}) - {cidade}/{uf}")
    
    # Busca teia no Neo4j
    teia = neo4j.extrair_subgrafo_para_ia(id_politico)
    if not teia:
        logger.warning(f"Sem teia para {nome}, gerando dossiê básico.")
        teia = {"politico": p, "empresas": [], "socios": []}

    # Analisa com Auditoria Sênior (Qwen-Max)
    laudo = await auditor.analisar_teia_financeira(teia)
    
    # Monta o dossiê final
    dossie = {
        "id": id_politico,
        "nome_politico": nome,
        "uf": uf,
        "cidade": cidade,
        "partido": p.get("partido"),
        "cargo": p.get("cargo"),
        "ia_analise": laudo,
        "empresas": teia.get("empresas", []),
        "socios_detectados": teia.get("socios", []),
        "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }
    
    # Salva na pasta organizada
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pasta_destino = os.path.join(base_dir, "dossies", uf, cidade)
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)
        
    filename = f"dossie_{id_politico}.json"
    filepath = os.path.join(pasta_destino, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(dossie, f, ensure_ascii=False, indent=4)
        
    logger.info(f"✅ Dossiê salvo: {uf}/{cidade}/{filename}")

async def main():
    logger.info("🚀 Iniciando Grande Auditoria Nacional...")
    auditor = AuditorGovernamentalIA()
    from database.neo4j_conn import get_neo4j_connection
    neo4j = get_neo4j_connection()
    
    # 1. Busca todos os políticos do Neo4j (Injetados)
    # Aqui vamos usar uma query que retorna todos os nós de políticos
    query = "MATCH (p:Politico) RETURN p LIMIT 500" # Limite inicial para teste massivo
    with neo4j.driver.session() as session:
        result = session.run(query)
        # Converte cada nó em um dicionário Python real para evitar problemas de acesso
        politicos = [dict(record["p"]) for record in result]
    
    logger.info(f"Encontrados {len(politicos)} políticos para auditoria.")
    
    # 2. Processamento em paralelo (com limite de concorrência restrito)
    semaphore = asyncio.Semaphore(2) # 2 por vez para evitar bloqueio da API internacional
    
    async def sem_process(p):
        async with semaphore:
            try:
                await processar_politico(auditor, neo4j, p)
            except Exception as e:
                logger.error(f"Falha ao auditar {p.get('nome')}: {e}")

    await asyncio.gather(*(sem_process(p) for p in politicos))
    logger.info("🏁 Auditoria em Massa Concluída!")

if __name__ == "__main__":
    asyncio.run(main())
