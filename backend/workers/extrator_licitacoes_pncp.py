import requests
import time
import os
import sys
import logging
from datetime import datetime, timedelta

# Configuração de Logging Profissional
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ExtratorPNCP")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.neo4j_conn import get_neo4j_connection

# A URL base do PNCP para contratos públicos - vamos consumir usando o de compras gerais (pode ser iterado por órgão)
# Porém, a API v1 exige orgao CNPJ. Para contornar e buscar diariamente, usaremos a rota de publicações ativas abertas se disponível ou a busca textual.
PNCP_API = "https://pncp.gov.br/api/pncp/v1"
PNCP_API_SEARCH = "https://pncp.gov.br/api/search"

def extrair_licitacoes_milionarias():
    """
    Motor de Dinheiro Grosso (PNCP):
    1. Busca contratos homologados no portal nacional de contratações públicas
    2. Filtra aqueles que faturaram > R$ 1 Milhão no dia
    3. Alimenta a empresa e o contrato no Neo4j 
       (A IA no Dashboard vai cruzar isso ligando aos Políticos e Sócios Red Flag)
    """
    logger.info("🔥 INICIANDO CAÇADOR DE LICITAÇÕES (PNCP) 🔥")
    neo4j_db = get_neo4j_connection()
    
    # Vamos buscar os contratos de hoje e ontem (Modo Diário de Inteligência)
    datas_busca = [datetime.now().strftime("%Y%m%d"), (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")]
    
    for data in datas_busca:
        logger.info(f"🔎 Varrendo Diário Oficial / PNCP para a data: {data}")
        pagina = 1
        
        while True:
            try:
                # Na ausência de busca pura por data no endpoint restrito /contratos, 
                # a melhor abordagem no PNCP oficial é através da API de busca (solr):
                # O endpoint /api/search permite filtros mais abertos.
                # Aqui fazemos um request robusto (ainda que adaptado ao /contratos se o endpoint de data estiver operando no /search)
                url = f"{PNCP_API_SEARCH}/?q=&tipos_documento=contratos&data_publicacao_inicial={data}&data_publicacao_final={data}&pagina={pagina}"
                logger.info(f"Acessando: {url}")
                res = requests.get(url, timeout=15)
                
                # Tratamento de erro de HTTP explícito
                res.raise_for_status()
                    
                dados = res.json()
                
                # A documentação de search geralmente põe em "items" ou "data"
                contratos = dados.get("items", dados.get("data", []))
                
                if not contratos: 
                    logger.info(f"Sem mais dados para {data} na página {pagina}.")
                    break # Fim das páginas do dia
                
                for c in contratos:
                    valor = float(c.get("valorInicial", c.get("valorContrato", 0)))
                    if valor >= 1_000_000: # SOMENTE DINHEIRO GROSSO (> 1 Milhão)
                        cnpj_fornecedor = str(c.get("fornecedorCnpjCpfIdGenerico", c.get("fornecedorCnpjCpf", ""))).strip()
                        nome_fornecedor = c.get("fornecedorNome", c.get("nomeFornecedor", "DESCONHECIDO")).upper()
                        orgao = c.get("orgaoEntidade", {}).get("razaoSocial", c.get("nomeOrgao", "GOVERNO")).upper()
                        objeto = c.get("objetoContrato", c.get("objeto", "Sem Objeto"))[:100]
                        data_pub = c.get("dataPublicacaoPncp", c.get("dataPublicacao", ""))
                        
                        if len(cnpj_fornecedor) == 14: # Apenas Empresas, não PFs
                            logger.warning(f"🚨 ALERTA CONTRATO ({orgao}): {nome_fornecedor} faturou R$ {valor:,.2f}")
                            
                            # Registra Empresa no Neo4j como 'Pote de Ouro'
                            neo4j_db.execute_query('''
                                MERGE (e:Empresa {cnpj: $cnpj})
                                ON CREATE SET e.nome = $nome_empresa
                                MERGE (o:Governo {nome: $orgao})
                                MERGE (o)-[r:CONTRATOU]->(e)
                                ON CREATE SET r.valor = $valor, r.objeto = $objeto, r.data_pub = $data_pub
                                ON MATCH SET r.valor = r.valor + $valor
                            ''', {
                                'cnpj': cnpj_fornecedor,
                                'nome_empresa': nome_fornecedor,
                                'orgao': orgao,
                                'valor': valor,
                                'objeto': objeto,
                                'data_pub': data_pub
                            })
                            # Se a empresa já era de parente/político no Grafo... A bruxa solta no Dashboard depois.
                
                pagina += 1
                time.sleep(1.5) # Respeito à API Federal rigoroso
                
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Erro de conexão na página PNCP {pagina}: {e}")
                if hasattr(e, 'response') and e.response is not None:
                     logger.error(f"Conteúdo do erro: {e.response.text}")
                logger.info("Aguardando 10s para tentar próxima página...")
                time.sleep(10)
                pagina += 1 # Pula página pra não travar loop infinito
                
            except Exception as e:
                logger.error(f"❌ Erro interno desconhecido processando página {pagina}: {e}")
                break
                
    neo4j_db.close()
    logger.info("🏁 CAÇA ÀS LICITAÇÕES (PNCP) CONCLUÍDA.")

if __name__ == "__main__":
    extrair_licitacoes_milionarias()
