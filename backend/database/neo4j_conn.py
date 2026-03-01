import os
import json
import logging
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "govtech_password")

logger = logging.getLogger("Neo4jMotor")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            self.driver.verify_connectivity()
            logger.info("🌐 [GRAFO] Conexão ao Neo4j estabelecida com sucesso.")
        except Exception as e:
            logger.error(f"❌ [ERRO GRAFO] Falha ao conectar ao Neo4j: {e}")

    def close(self):
        self.driver.close()

    def limpar_banco(self):
        """Limpa todo o banco de dados (útil para testes)"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("🧹 Banco de grafos limpo.")

    def criar_indice_unico(self):
        """Cria constraints para evitar duplicação de nós no grafo"""
        with self.driver.session() as session:
            try:
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Politico) REQUIRE p.cpf IS UNIQUE")
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Empresa) REQUIRE e.cnpj IS UNIQUE")
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Socio) REQUIRE s.nome IS UNIQUE")
            except Exception as e:
                logger.warning(f"Aviso ao criar índices (talvez já existam): {e}")

    def execute_query(self, query: str, parameters: dict = None):
        """Utilitário para rodar queries genéricas (usado pelo Worker do PNCP)"""
        with self.driver.session() as session:
            return session.run(query, parameters).data()

    # ---------------------------------------------------------
    # FASE 2: AS 3 FUNÇÕES OBRIGATÓRIAS DE INGESTÃO (Workers)
    # ---------------------------------------------------------

    def merge_politico(self, dados: dict):
        """Cria ou atualiza o nó (:Politico)"""
        query = """
        MERGE (p:Politico {cpf: $cpf})
        ON CREATE SET p.nome = $nome, p.cargo = $cargo, p.partido = $partido, p.cadastrado_em = date()
        ON MATCH SET p.nome = $nome, p.cargo = $cargo, p.partido = $partido
        """
        with self.driver.session() as session:
            session.run(query, cpf=dados.get("cpf", "00000000000"), nome=dados.get("nome", "Desconhecido"), 
                        cargo=dados.get("cargo", ""), partido=dados.get("partido", ""))

    def merge_empresa(self, dados: dict):
        """Cria ou atualiza o nó (:Empresa)"""
        query = """
        MERGE (e:Empresa {cnpj: $cnpj})
        ON CREATE SET e.nome = $nome, e.capital_social = $capital, e.uf = $uf
        ON MATCH SET e.nome = $nome
        """
        with self.driver.session() as session:
            session.run(query, cnpj=dados.get("cnpj", ""), nome=dados.get("nome", ""), 
                        capital=dados.get("capital_social", 0.0), uf=dados.get("uf", ""))

    def merge_relacao_financeira(self, cpf_politico: str, cnpj_empresa: str, valor: float, tipo: str):
        """
        Cria a aresta e.g [:PAGOU_A] ou [:DESTINOU_EMENDA]
        """
        query = f"""
        MATCH (p:Politico {{cpf: $cpf}})
        MATCH (e:Empresa {{cnpj: $cnpj}})
        MERGE (p)-[r:{tipo}]->(e)
        ON CREATE SET r.valor_total = $valor, r.atualizado_em = date()
        ON MATCH SET r.valor_total = r.valor_total + $valor, r.atualizado_em = date()
        """
        with self.driver.session() as session:
            session.run(query, cpf=cpf_politico, cnpj=cnpj_empresa, valor=valor)

    # ---------------------------------------------------------
    # A FUNÇÃO CRUCIAL PARA A IA (Extração de Subgrafo)
    # ---------------------------------------------------------
    def extrair_subgrafo_para_ia(self, cpf: str) -> dict:
        """
        Extrai o subgrafo de um político com até 3 graus de separação:
        Político -> Emendas -> Empresas -> Sócios
        Retorna em JSON limpo e estruturado para o Motor IA (Qwen).
        """
        query = """
        MATCH (p:Politico {cpf: $cpf})
        
        // 1º Grau: O que o político fez diretamente (Ex: Destinou Emenda para Empresa)
        OPTIONAL MATCH (p)-[rel_1]->(e:Empresa)
        
        // 2º Grau: O que essa Empresa tem de Sócios
        OPTIONAL MATCH (s:Socio)-[rel_2:E_SOCIO_DE]->(e)
        
        // 3º Grau: Esss Sócios tem outras empresas?
        OPTIONAL MATCH (s)-[rel_3:E_SOCIO_DE]->(e_outra:Empresa)
        
        RETURN 
            p.nome AS politico, 
            p.cpf AS cpf,
            collect(DISTINCT {
                empresa_nome: e.nome, 
                cnpj: e.cnpj, 
                relacao: type(rel_1), 
                valor_envolvido: rel_1.valor_total
            }) AS conexoes_diretas,
            collect(DISTINCT {
                socio: s.nome, 
                empresa_alvo: e.nome,
                outras_empresas: e_outra.nome
            }) AS rede_societaria
        """
        
        try:
            with self.driver.session() as session:
                resultado = session.run(query, cpf=cpf).single()
                
                if not resultado:
                    return {"erro": "Político não encontrado no grafo."}
                
                return {
                    "politico": resultado["politico"],
                    "cpf": resultado["cpf"],
                    "conexoes_diretas": [c for c in resultado["conexoes_diretas"] if c.get('empresa_nome')],
                    "rede_societaria": [s for s in resultado["rede_societaria"] if s.get('socio')]
                }
        except Exception as e:
            logger.error(f"Erro ao extrair subgrafo para IA: {e}")
            return {"erro": str(e)}

    # ---------------------------------------------------------
    # Função Antiga de Retrocompatibilidade (Chamada pelo pipeline)
    # ---------------------------------------------------------
    def registrar_dossie_no_grafo(self, dossie: dict):
        """
        Mantida para retrocompatibilidade com o agente_coletor_autonomo.py que passa
        um JSON massivo do dossiê. Aqui fazemos o parse e usamos as funções atômicas.
        """
        cpf = dossie.get("cpf_politico", "00000000000")
        if not cpf: cpf = "00000000000"
        
        nome = dossie.get("nome_politico", dossie.get("id_politico", "Desconhecido"))
        
        # 1. Cria Político
        self.merge_politico({"cpf": cpf, "nome": nome})

        # 2. Cria Empresas e Relações
        for emp in dossie.get("empresas", []):
            emp_cnpj = emp.get("cnpj", "")
            emp_nome = emp.get("nome", "Empresa Desconhecida")
            
            if not emp_cnpj: continue
                
            self.merge_empresa({"cnpj": emp_cnpj, "nome": emp_nome})
            
            # Se for proveniente de cartão corporativo ou nota fiscal
            tipo_rel = "CELEBROU_CONTRATO_COM"
            if "Emenda" in emp_nome:
                tipo_rel = "DESTINOU_EMENDA"
            elif "Cartão" in emp.get("cargo", ""):
                tipo_rel = "PAGOU_COM_CARTAO"
                
            valor_float = 0.0
            vl_str = str(emp.get("valor", "0")).replace("R$", "").replace(".", "").replace(",", ".").strip()
            try: valor_float = float(vl_str)
            except: pass

            self.merge_relacao_financeira(cpf, emp_cnpj, valor_float, tipo_rel)
            
            # Sócios
            for socio in emp.get("socios", []):
                with self.driver.session() as session:
                    session.run("""
                    MATCH (e:Empresa {cnpj: $cnpj})
                    MERGE (s:Socio {nome: $nome_socio})
                    MERGE (s)-[:E_SOCIO_DE]->(e)
                    """, cnpj=emp_cnpj, nome_socio=socio)
                    
        logger.info(f"🕸️ [GRAFO] Atualizada teia do dossiê CPF: {cpf}")

def get_neo4j_connection():
    conn = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    conn.criar_indice_unico()
    return conn
