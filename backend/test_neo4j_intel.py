from database.neo4j_conn import get_neo4j_connection
import json

def test_graph_intelligence():
    neo4j = get_neo4j_connection()
    
    # Busca uma empresa que acabou de ser injetada pelo PNCP
    query = """
    MATCH (s:Socio)-[:E_SOCIO_DE]->(e:Empresa)-[:GANHOU_LICITACAO]->(c:Contrato)
    RETURN s.nome as socio, e.nome as empresa, c.valor as valor, c.objeto as objeto
    LIMIT 5
    """
    
    with neo4j.driver.session() as session:
        results = session.run(query).data()
        print(json.dumps(results, indent=4, ensure_ascii=False))
    
    neo4j.close()

if __name__ == "__main__":
    test_graph_intelligence()
