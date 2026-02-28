import requests
import time
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.neo4j_conn import get_neo4j_connection

CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2"

def extrair_todos_deputados_com_despesas():
    """
    Motor ETL de Background:
    1. Lista TODOS os deputados ativos
    2. Registra o nó [Politico] no Neo4j
    3. Puxa TODAS as despesas paginando do 1 ao fim
    4. Cria ou Conecta o Nó [Empresa] ao [Politico] com relação [PAGOU_A]
    """
    print("🔥 INICIANDO ASPIRADOR DE DADOS: CÂMARA DOS DEPUTADOS 🔥")
    neo4j_db = get_neo4j_connection()
    
    try:
        res_dep = requests.get(f"{CAMARA_API}/deputados", params={"itens": 1000})
        deputados = res_dep.json().get("dados", [])
        print(f"📥 {len(deputados)} Deputados Ativos Encontrados. Iniciando Ingestão Infinita...")
    except Exception as e:
        print(f"❌ Falha ao contatar API da Câmara: {e}")
        return

    for dep in deputados:
        id_dep = dep.get("id")
        nome = dep.get("nome")
        siglaUf = dep.get("siglaUf")
        siglaPartido = dep.get("siglaPartido")
        
        print(f"⏳ Processando: {nome} ({siglaPartido}-{siglaUf})")
        
        # 1. Registra o Politico Base
        neo4j_db.execute_query('''
            MERGE (p:Politico {id_camara: $id_camara})
            SET p.nome = $nome, p.estado = $uf, p.partido = $partido, p.cargo = "Deputado Federal"
        ''', {'id_camara': id_dep, 'nome': nome, 'uf': siglaUf, 'partido': siglaPartido})
        
        # 2. Inicia Paginação Infinita de Despesas
        pagina = 1
        total_despesas = 0
        while True:
            try:
                res_desp = requests.get(f"{CAMARA_API}/deputados/{id_dep}/despesas", params={
                    "itens": 100, "pagina": pagina, "ordem": "DESC", "ordenarPor": "dataDocumento"
                })
                
                if res_desp.status_code != 200: 
                    print(f"  ⚠️ Limite de Taxa ou Erro. Resfriando por 5s...")
                    time.sleep(5)
                    continue
                    
                dados_pagina = res_desp.json().get("dados", [])
                if not dados_pagina: 
                    break # Fim das despesas deste deputado
                
                for d in dados_pagina:
                    cnpj_raw = str(d.get("cnpjCpfFornecedor", "")).replace(".", "").replace("-", "").replace("/", "").strip()
                    if not cnpj_raw or len(cnpj_raw) != 14: continue # Pula CPFs ou inválidos
                    
                    valor = float(d.get("valorDocumento", 0))
                    nome_fornecedor = d.get("nomeFornecedor", "Desconhecido").upper()
                    
                    # 3. Cria Relação Neo4j (Politico -> PAGOU_A -> Empresa)
                    neo4j_db.execute_query('''
                        MATCH (p:Politico {id_camara: $id_camara})
                        MERGE (e:Empresa {cnpj: $cnpj})
                        ON CREATE SET e.nome = $nome_empresa
                        MERGE (p)-[r:PAGOU_A]->(e)
                        ON CREATE SET r.valor_total = $valor, r.qtd_transacoes = 1
                        ON MATCH SET r.valor_total = r.valor_total + $valor, r.qtd_transacoes = r.qtd_transacoes + 1
                    ''', {
                        'id_camara': id_dep, 
                        'cnpj': cnpj_raw, 
                        'nome_empresa': nome_fornecedor, 
                        'valor': valor
                    })
                    total_despesas += 1
                
                print(f"  👉 {total_despesas} despesas registradas no Grafo...")
                pagina += 1
                time.sleep(0.5) # Respeito à API Cidadã
                
            except Exception as e:
                print(f"  ❌ Erro processando página {pagina} de {nome}: {e}")
                break
                
        print(f"✅ {nome} finalizado. Total Inserido: {total_despesas} transações.")
        time.sleep(1) # Intervalo entre políticos

    neo4j_db.close()
    print("🏁 EXTRAÇÃO TOTAL DA CÂMARA CONCLUÍDA.")

if __name__ == "__main__":
    extrair_todos_deputados_com_despesas()
