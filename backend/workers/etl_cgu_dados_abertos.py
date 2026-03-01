import os
import sys
import logging
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ETL_CGU_ABERTO")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.neo4j_conn import get_neo4j_connection

async def processar_emendas_cgu_em_lote():
    """
    Ingestão do DUMP diário/mensal de Emendas e Transferências do Portal da Transparência.
    Processa arquivos CSV maciços, sem requisições HTTP API.
    """
    logger.info("📂 INICIANDO INGESTÃO DO DUMP CGU (Emendas Parlamentares e Repasses)")
    neo4j_db = get_neo4j_connection()
    
    # Exemplo: O arquivo CSV contém a chave 'CPF Autor Emenda', 'CNPJ Favorecido' e 'Valor Pago'
    # Iterar chunk a chunk (ex: pd.read_csv com chunksize=100000)
    linhas_dump_exemplo = [
        {"cpf_autor": "12345678900", "nome_autor": "POLÍTICO MOCK UM", "cnpj_favorecido": "99888777000166", "nome_favorecido": "EMPRESA AMIGA S/A", "valor_empenhado": 2500000.00, "funcao": "Saúde"},
    ]

    count = 0
    for linha in linhas_dump_exemplo:
        cpf_autor = linha.get("cpf_autor")
        cnpj_favorecido = linha.get("cnpj_favorecido")
        valor = float(linha.get("valor_empenhado", 0))
        
        if cpf_autor and cnpj_favorecido:
            # 1. Garante quem disparou (Político)
            neo4j_db.merge_politico({"cpf": cpf_autor, "nome": linha.get("nome_autor", "")})
            
            # 2. Garante quem recebeu (Empresa/Favorecido)
            neo4j_db.merge_empresa({"cnpj": cnpj_favorecido, "nome": linha.get("nome_favorecido", "FAVORECIDO CGU")})
            
            # 3. Traça a linha do dinheiro vivo na inteligência
            neo4j_db.merge_relacao_financeira(cpf_autor, cnpj_favorecido, valor, "DESTINOU_EMENDA_PUBLICA")
            count += 1
            
        await asyncio.sleep(0.01)
        
    logger.info(f"✅ DUMP CGU PROCESSADO. {count} repasses mapeados no Grafo.")
    neo4j_db.close()

if __name__ == "__main__":
    asyncio.run(processar_emendas_cgu_em_lote())
