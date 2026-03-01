import os
import sys
import logging
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ETL_RFB_QSA")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.neo4j_conn import get_neo4j_connection

async def processar_qsa_rfb_em_lote():
    """
    Ingestão do Quadro Societário (QSA) via banco da Receita Federal do Brasil (RFB).
    Este é o script mais colossal no projeto do Bruno (Gigabytes de CSV).
    Ele vincula PESSOAS FÍSICAS às EMPRESAS.
    """
    logger.info("📂 INICIANDO INGESTÃO DO DUMP RECEITA FEDERAL (Sócios e Empresas)")
    neo4j_db = get_neo4j_connection()
    
    # Lê as tuplas: CNPJ <-> Nome do Sócio
    linhas_dump_exemplo = [
        {"cnpj": "11222333000144", "razao_social": "EMPRESA MOCK LTDA", "nome_socio": "ESPOSA DO POLITICO MOCK UM"},
        {"cnpj": "99888777000166", "razao_social": "EMPRESA AMIGA S/A", "nome_socio": "AMIGO DO POLITICO MOCK UM"}
    ]

    count = 0
    for linha in linhas_dump_exemplo:
        cnpj = linha.get("cnpj")
        socio = linha.get("nome_socio")
        razao = linha.get("razao_social")
        
        if cnpj and socio:
            neo4j_db.merge_empresa({"cnpj": cnpj, "nome": razao})
            
            # Aqui é Cypher puro para fazer o vínculo
            neo4j_db.execute_query("""
                MATCH (e:Empresa {cnpj: $cnpj})
                MERGE (s:Socio {nome: $nome_socio})
                MERGE (s)-[:E_SOCIO_DE]->(e)
            """, {"cnpj": cnpj, "nome_socio": socio.upper()})
            count += 1
            
        await asyncio.sleep(0.01)
        
    logger.info(f"✅ DUMP RECEITA QSA PROCESSADO. {count} relações societárias atreladas.")
    neo4j_db.close()

if __name__ == "__main__":
    asyncio.run(processar_qsa_rfb_em_lote())
