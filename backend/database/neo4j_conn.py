import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            self.driver.verify_connectivity()
            print("Conexão ao Neo4j estabelecida com sucesso.")
        except Exception as e:
            print(f"Erro ao conectar ao Neo4j: {e}")

    def close(self):
        self.driver.close()

def get_neo4j_connection():
    return Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

if __name__ == "__main__":
    conn = get_neo4j_connection()
    conn.close()
