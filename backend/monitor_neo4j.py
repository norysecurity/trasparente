import os
import sys
import time
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, TransientError, DriverError

# Carrega as variáveis de ambiente
sys.path.insert(0, '.')
load_dotenv()
load_dotenv('../.env')

def monitor_neo4j_indexes():
    uri  = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    pwd  = os.getenv('NEO4J_PASSWORD', 'password')

    print("Iniciando monitoramento de índices do Neo4j...")

    # Connection timeout estendido para dar chance ao banco de responder
    try:
        with GraphDatabase.driver(uri, auth=(user, pwd), connection_timeout=30) as driver:
            while True:
                try:
                    with driver.session() as session:
                        # Busca os índices e a porcentagem de progresso
                        result = session.run("SHOW INDEXES YIELD name, state, populationPercent").data()

                        populating = [idx for idx in result if idx.get('state') == 'POPULATING']
                        online     = [idx for idx in result if idx.get('state') == 'ONLINE']

                        print("\n--- Status Atual ---")
                        print(f"Índices ONLINE: {len(online)}")

                        if not populating:
                            print("Nenhum índice sendo criado no momento. O banco está livre!")
                            break

                        for idx in populating:
                            name = idx.get('name', 'Desconhecido')
                            pct  = idx.get('populationPercent', 0.0)
                            # Trata casos onde populationPercent vem como None
                            pct_display = f"{pct:.2f}" if pct is not None else "0.00"
                            print(f" - Criando índice '{name}': {pct_display}% concluído")

                except (ServiceUnavailable, TransientError, DriverError) as e:
                    print(f"\n[Aviso] Neo4j ocupado ou travado. Aguardando liberação...")
                    print(f"Detalhe técnico: {e}")

                # Aguarda 15 segundos antes de tentar novamente para não sobrecarregar
                time.sleep(15)

    except Exception as e:
        print(f"Erro fatal ao tentar inicializar o driver do Neo4j: {e}")

if __name__ == "__main__":
    monitor_neo4j_indexes()
