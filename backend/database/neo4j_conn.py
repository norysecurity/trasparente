import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "govtech_password")

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            self.driver.verify_connectivity()
            print("🌐 [GRAFO] Conexão ao Neo4j estabelecida com sucesso.")
        except Exception as e:
            print(f"❌ [ERRO GRAFO] Erro ao conectar ao Neo4j: {e}")

    def close(self):
        self.driver.close()

    def limpar_banco(self):
        """Limpa todo o banco de dados (útil para testes)"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("🧹 Banco de grafos limpo.")

    def criar_indice_unico(self):
        """Cria constraints para evitar duplicação de nós no grafo"""
        with self.driver.session() as session:
            try:
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Politico) REQUIRE p.id_governo IS UNIQUE")
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Empresa) REQUIRE e.cnpj IS UNIQUE")
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Socio) REQUIRE s.nome IS UNIQUE")
            except Exception as e:
                print(f"⚠️ Aviso ao criar índices: {e}")

    def registrar_dossie_no_grafo(self, dossie: dict):
        """
        Esta é a função mágica que transforma o JSON do Agente em uma teia de conexões.
        Deve ser chamada logo após a IA gerar o JSON no main.py ou agente_coletor_autonomo.py.
        """
        id_politico = dossie.get("id_politico")
        nome_politico = dossie.get("nome_politico", f"Político {id_politico}") # Ajuste caso o nome venha no dict
        empresas = dossie.get("empresas", [])

        with self.driver.session() as session:
            # 1. Cria o nó do Político
            session.execute_write(self._criar_no_politico, id_politico, nome_politico)

            # 2. Itera sobre as empresas e cria os nós e relações
            for emp in empresas:
                nome_emp = emp.get("nome", "Empresa Desconhecida")
                cnpj = emp.get("cnpj", "")
                socios = emp.get("socios", [])

                if cnpj:
                    # Cria a Empresa e liga ao Político (Relação: FORNECEU_PARA ou VINCULADO_A)
                    session.execute_write(self._criar_no_empresa_e_relacionar, id_politico, nome_emp, cnpj)

                    # 3. Itera sobre os sócios da empresa para achar possíveis laranjas/nepotismo
                    for socio in socios:
                        session.execute_write(self._criar_no_socio_e_relacionar, socio, cnpj)

            print(f"🕸️ [GRAFO] Teia de conexões populada no Neo4j para o político ID: {id_politico}")

    @staticmethod
    def _criar_no_politico(tx, id_politico, nome_politico):
        query = """
        MERGE (p:Politico {id_governo: $id_politico})
        ON CREATE SET p.nome = $nome_politico, p.risco_analisado = true
        ON MATCH SET p.nome = $nome_politico
        RETURN p
        """
        tx.run(query, id_politico=str(id_politico), nome_politico=nome_politico)

    @staticmethod
    def _criar_no_empresa_e_relacionar(tx, id_politico, nome_empresa, cnpj):
        query = """
        MATCH (p:Politico {id_governo: $id_politico})
        MERGE (e:Empresa {cnpj: $cnpj})
        ON CREATE SET e.razao_social = $nome_empresa
        MERGE (e)-[r:RECEBEU_REPASSE_DE]->(p)
        RETURN e, r
        """
        tx.run(query, id_politico=str(id_politico), nome_empresa=nome_empresa, cnpj=cnpj)

    @staticmethod
    def _criar_no_socio_e_relacionar(tx, nome_socio, cnpj):
        query = """
        MATCH (e:Empresa {cnpj: $cnpj})
        MERGE (s:Socio {nome: $nome_socio})
        MERGE (s)-[r:E_SOCIO_DE]->(e)
        RETURN s, r
        """
        tx.run(query, nome_socio=nome_socio, cnpj=cnpj)

def get_neo4j_connection():
    conn = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    conn.criar_indice_unico()
    return conn

if __name__ == "__main__":
    # Teste de conexão e inserção simulada
    conn = get_neo4j_connection()
    
    # Simulação do dicionário que seu motor IA já gera
    mock_dossie = {
        "id_politico": 900001,
        "nome_politico": "Luiz Inácio Lula da Silva",
        "empresas": [
            {
                "nome": "EMPRESA DE TESTE GOVTECH LTDA",
                "cnpj": "12345678000199",
                "socios": ["JOAO DA SILVA", "MARIA DA SILVA"]
            }
        ]
    }
    
    conn.registrar_dossie_no_grafo(mock_dossie)
    conn.close()
