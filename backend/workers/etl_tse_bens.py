import os
import sys
import json
import logging
import asyncio

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ETL_TSE_BENS")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.neo4j_conn import get_neo4j_connection

async def processar_bens_tse_em_lote():
    """
    Simula o comportamento de ingerir o DUMP de bens de candidatos (TSE).
    Na prática, deve baixar o ZIP de 'Repositório de Dados Eleitorais', descompactar e ler o CSV gigante.
    Aqui usamos mock-estrutural para inserção limpa em Neo4j.
    """
    logger.info("📂 INICIANDO INGESTÃO DO DUMP TSE (Modo Offline-First)")
    neo4j_db = get_neo4j_connection()
    
    # Exemplo: O Dump do TSE contém Político X declarou Quotas da Empresa Y (CNPJ).
    # Como não temos o CSV na mão de 1GB agora, o Worker cria o padrão que lerá as linhas do chunk CSV:
    linhas_dump_exemplo = [
        {"cpf_candidato": "12345678900", "nome": "POLÍTICO MOCK UM", "tipo_bem": "Quotas ou quinhões de capital", "descricao": "90% das quotas da EMPRESA MOCK LTDA", "cnpj_relacionado": "11222333000144", "valor": 500000.00},
        {"cpf_candidato": "09876543211", "nome": "POLÍTICO MOCK DOIS", "tipo_bem": "Terreno", "descricao": "TERRENO NA CIDADE X", "cnpj_relacionado": "", "valor": 1200000.00}
    ]

    count = 0
    for linha in linhas_dump_exemplo:
        cpf = linha.get("cpf_candidato")
        nome = linha.get("nome")
        cnpj = linha.get("cnpj_relacionado")
        descricao = linha.get("descricao", "")
        valor = float(linha.get("valor", 0))

        if cpf:
            # Garante o Político
            neo4j_db.merge_politico({"cpf": cpf, "nome": nome, "cargo": "Candidato"})
            
            # Se for bem atrelado a empresa (CNPJ)
            if cnpj and len(cnpj) >= 11:
                nome_empresa = descricao.split("da ")[-1] if "da " in descricao else "Empresa Declarada TSE"
                neo4j_db.merge_empresa({"cnpj": cnpj, "nome": nome_empresa.upper()})
                # O Cérebro: O Político declarou posse da Empresa X (Logo, na prática é dono ou sócio dela)
                neo4j_db.merge_relacao_financeira(cpf, cnpj, valor, "E_DONO_PARCIAL_OU_TOTAL_DE")
                count += 1
                
        # Simulando leitura de lote para evitar out-of-memory
        await asyncio.sleep(0.01)
        
    logger.info(f"✅ DUMP TSE PROCESSADO. {count} conexões societárias diretas anexadas ao Grafo.")
    neo4j_db.close()

if __name__ == "__main__":
    asyncio.run(processar_bens_tse_em_lote())
