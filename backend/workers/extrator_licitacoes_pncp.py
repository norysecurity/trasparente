import requests
import time
import os
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.neo4j_conn import get_neo4j_connection

PNCP_API = "https://pncp.gov.br/api/pncp/v1"

def extrair_licitacoes_milionarias():
    """
    Motor de Dinheiro Grosso (PNCP):
    1. Busca contratos homologados no portal nacional de contratações públicas
    2. Filtra aqueles que faturaram > R$ 1 Milhão no dia
    3. Alimenta a empresa e o contrato no Neo4j 
       (A IA no Dashboard vai cruzar isso ligando aos Políticos e Sócios Red Flag)
    """
    print("🔥 INICIANDO CAÇADOR DE LICITAÇÕES (PNCP) 🔥")
    neo4j_db = get_neo4j_connection()
    
    # Vamos buscar os contratos de hoje e ontem (Modo Diário de Inteligência)
    datas_busca = [datetime.now().strftime("%Y%m%d"), (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")]
    
    for data in datas_busca:
        print(f"🔎 Varrendo Diário Oficial / PNCP para a data: {data}")
        pagina = 1
        
        while True:
            try:
                # O PNCP permite buscar contratos por data de publicação
                url = f"{PNCP_API}/contratos?dataInicial={data}&dataFinal={data}&pagina={pagina}"
                res = requests.get(url, timeout=15)
                
                if res.status_code != 200:
                    print("⚠️ Limite de acesso PNCP. Aguardando 10s...")
                    time.sleep(10)
                    continue
                    
                dados = res.json()
                contratos = dados.get("data", [])
                
                if not contratos: 
                    break # Fim das páginas do dia
                
                for c in contratos:
                    valor = float(c.get("valorInicial", 0))
                    if valor >= 1_000_000: # SOMENTE DINHEIRO GROSSO (> 1 Milhão)
                        cnpj_fornecedor = str(c.get("fornecedorCnpjCpfIdGenerico", "")).strip()
                        nome_fornecedor = c.get("fornecedorNome", "DESCONHECIDO").upper()
                        orgao = c.get("orgaoEntidade", {}).get("razaoSocial", "GOVERNO").upper()
                        objeto = c.get("objetoContrato", "Sem Objeto")[:100]
                        data_pub = c.get("dataPublicacaoPncp", "")
                        
                        if len(cnpj_fornecedor) == 14: # Apenas Empresas, não PFs
                            print(f"🚨 ALERTA CONTRATO ({orgao}): {nome_fornecedor} faturou R$ {valor:,.2f}")
                            
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
                time.sleep(1) # Respeito à API Federal
                
            except Exception as e:
                print(f"❌ Erro lendo página PNCP {pagina}: {e}")
                break
                
    neo4j_db.close()
    print("🏁 CAÇA ÀS LICITAÇÕES (PNCP) CONCLUÍDA.")

if __name__ == "__main__":
    extrair_licitacoes_milionarias()
