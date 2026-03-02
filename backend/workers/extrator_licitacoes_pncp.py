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

def buscar_qsa_brasilapi(cnpj: str):
    """
    Busca o Quadro de Sócios e Administradores (QSA) via BrasilAPI.
    """
    try:
        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            dados = res.json()
            return dados.get("qsa", [])
        return []
    except Exception as e:
        logger.error(f"Erro ao buscar QSA para CNPJ {cnpj}: {e}")
        return []

def extrair_licitacoes_recentes():
    """
    Motor PNCP Robusto: 
    1. Busca índices de contratos via /api/search/
    2. Detalha cada contrato via /api/pncp/v1/orgaos/... para pegar CNPJ
    3. Cruza com QSA (BrasilAPI)
    """
    logger.info("🔥 INICIANDO CAÇADOR DE LICITAÇÕES (SEARCH + DETAILS) 🔥")
    neo4j_db = get_neo4j_connection()
    
    pagina = 1
    while pagina <= 3: # Primeiras 3 páginas para evitar sobrecarga
        try:
            # Busca índices de contratos vigentes e recentes
            url_search = f"{PNCP_API_SEARCH}/?q=&tipos_documento=contrato&ordenacao=-data&status=vigente&pagina={pagina}"
            logger.info(f"🔎 Buscando Índices PNCP: {url_search}")
            res = requests.get(url_search, timeout=15)
            res.raise_for_status()
            items = res.json().get("items", [])
            
            if not items: break
            
            for item in items:
                try:
                    # Dados básicos para bater no endpoint de detalhes
                    orgao_cnpj = item.get("orgao_cnpj")
                    ano = item.get("ano")
                    sequencial = item.get("numero_sequencial")
                    
                    if not (orgao_cnpj and ano and sequencial): continue
                    
                    url_detail = f"{PNCP_API}/orgaos/{orgao_cnpj}/contratos/{ano}/{sequencial}"
                    logger.info(f"   📄 Detalhando contrato: {url_detail}")
                    res_det = requests.get(url_detail, timeout=10)
                    if res_det.status_code != 200: continue
                    
                    det = res_det.json()
                    id_controle = det.get("numeroControlePNCP")
                    cnpj_fornecedor = det.get("niFornecedor") # CNPJ DO GANHADOR
                    nome_fornecedor = det.get("nomeRazaoSocialFornecedor", "DESCONHECIDO").upper()
                    valor = float(det.get("valorGlobal", 0))
                    objeto = det.get("objetoContrato", "Sem Objeto")
                    orgao_nome = det.get("orgaoEntidade", {}).get("razaoSocial", "GOVERNO").upper()

                    if cnpj_fornecedor and len(str(cnpj_fornecedor)) >= 11:
                        logger.warning(f"   💰 CONTRATO DETECTADO: {nome_fornecedor} - R$ {valor:,.2f}")
                        
                        # Injeta no Neo4j
                        neo4j_db.execute_query('''
                            MERGE (e:Empresa {cnpj: $cnpj})
                            ON CREATE SET e.nome = $nome_empresa
                            MERGE (c:Contrato {id: $id})
                            ON CREATE SET 
                                c.valor = $valor, 
                                c.orgao = $orgao, 
                                c.objeto = $objeto,
                                c.data_cad = date()
                            MERGE (e)-[:GANHOU_LICITACAO]->(c)
                        ''', {
                            'cnpj': cnpj_fornecedor, 
                            'nome_empresa': nome_fornecedor,
                            'id': id_controle, 
                            'valor': valor, 
                            'orgao': orgao_nome, 
                            'objeto': objeto
                        })
                        
                        # Busca QSA (OSINT) e Injeta Sócios
                        socios = buscar_qsa_brasilapi(cnpj_fornecedor)
                        for s in socios:
                            nome_socio = s.get("nome_socio", "").upper()
                            if nome_socio:
                                neo4j_db.execute_query('''
                                    MATCH (e:Empresa {cnpj: $cnpj})
                                    MERGE (s:Socio {nome: $nome_socio})
                                    MERGE (s)-[:E_SOCIO_DE]->(e)
                                ''', {'cnpj': cnpj_fornecedor, 'nome_socio': nome_socio})
                                logger.info(f"      👥 Sócio detectado: {nome_socio}")
                    
                    time.sleep(1) # Intervalo entre contratos

                except Exception as ex:
                    logger.error(f"Erro ao detalhar contrato {item.get('id')}: {ex}")

            pagina += 1
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Erro na varredura PNCP: {e}")
            break
            
    neo4j_db.close()
    logger.info("🏁 CAÇA ÀS LICITAÇÕES E SÓCIOS CONCLUÍDA.")

if __name__ == "__main__":
    extrair_licitacoes_recentes()
