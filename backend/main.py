from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

from database.neo4j_conn import get_neo4j_connection
from skills_coleta import gerar_dossie_completo
from motor_ia_qwen import MotorIAQwen
from gamificacao import gerar_relatorio_gamificado

motor_ia = MotorIAQwen()
neo4j_conn = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa conexão Neo4j no startup
    global neo4j_conn
    try:
        neo4j_conn = get_neo4j_connection()
        print("Backend conectado ao Neo4j localmente.")
    except Exception as e:
        print(f"Alerta: Neo4j indisponível na inicialização. {e}")
        
    yield
    
    # Fecha conexão no shutdown
    if neo4j_conn:
        neo4j_conn.close()

app = FastAPI(
    title="GovTech Transparência API",
    description="API gamificada de auditoria política com Grafos e LLM (Qwen)",
    version="1.0.0",
    lifespan=lifespan
)

# Configuração de CORS para permitir acesso do Frontend (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # URL do frontend em dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PoliticoRequest(BaseModel):
    nome: str
    cpf_cnpj: str

def salvar_analise_grafo(nome: str, cpf_cnpj: str, dossie: dict, score: float):
    """
    Persiste o político e suas redes no grafo Neo4j.
    Cria os nós: Politico, Empresa, Contrato.
    Cria as arestas: SOCIO_DE, VENCEU_CONTRATO, ENVOLVIDO_EM.
    """
    if not neo4j_conn:
        print("Neo4j inativo. Pulando a persistência no Grafo.")
        return

    query = """
    // 1. Cria ou Atualiza o Político
    MERGE (p:Politico {documento: $cpf_cnpj})
    ON CREATE SET p.nome = $nome, p.score_serasa = $score, p.criado_em = timestamp()
    ON MATCH SET p.score_serasa = $score, p.atualizado_em = timestamp()
    
    // 2. Cria as empresas ligadas ao candidato (do TSE)
    FOREACH (emp IN $empresas |
        MERGE (e:Empresa {nome: emp.nome})
        MERGE (p)-[:SOCIO_DE {participacao: emp.participacao}]->(e)
    )
    
    // 3. Cria os contratos públicos envolvendo essas empresas (do Portal)
    FOREACH (con IN $contratos |
        MERGE (c:Contrato {id_contrato: con.id_contrato})
        ON CREATE SET c.valor = con.valor, c.objeto = con.objeto
        
        // Relaciona a empresa que venceu o contrato
        MERGE (e2:Empresa {nome: con.empresa_vencedora})
        MERGE (e2)-[:VENCEU_CONTRATO]->(c)
        
        // Se a empresa vencedora é uma das que o político participa, cria a Red Flag!
        FOREACH (emp2 IN $empresas |
           FOREACH (_ IN CASE WHEN emp2.nome = con.empresa_vencedora THEN [1] ELSE [] END |
              MERGE (p)-[:ENVOLVIDO_EM_CONFLITO]->(c)
           )
        )
    )
    """
    
    empresas = dossie.get("dados_tse", {}).get("empresas_declaradas", [])
    contratos = dossie.get("dados_governamentais", {}).get("contratos_encontrados", [])
    
    try:
        with neo4j_conn.driver.session() as session:
            session.run(query, 
                nome=nome, 
                cpf_cnpj=cpf_cnpj, 
                score=score, 
                empresas=empresas, 
                contratos=contratos
            )
            print(f"Grafo para o político {nome} persistido com sucesso no Neo4j!")
    except Exception as e:
        print(f"Erro ao salvar grafo: {e}")


@app.get("/")
def read_root():
    return {"message": "Motor GovTech Transparência Operante!"}

@app.post("/auditoria/investigar", status_code=status.HTTP_200_OK)
async def iniciar_investigacao(politico: PoliticoRequest):
    """
    Rota principal do app. Processa o dossiê, aciona a LLM e pontua no Serasa do Político.
    """
    try:
        # 1. Coleta e consolida os dados de fontes públicas (Simuladas)
        print(f"Iniciando dossiê para: {politico.nome}")
        dossie = await gerar_dossie_completo(politico.nome, politico.cpf_cnpj)
        
        # 2. IA atua como Promotora/Auditora e analisa inconsistências no JSON
        analise_ia = await motor_ia.analisar_dossie(dossie)
        
        # 3. Gamefica a experiência (Score Serasa Político)
        resultado_game = gerar_relatorio_gamificado(analise_ia)
        
        # 4. Salva a árvore de corrupção ou legalidade como Grafo (Neo4j)
        score_final = resultado_game.get("score_auditoria", 1000.0)
        salvar_analise_grafo(politico.nome, politico.cpf_cnpj, dossie, score_final)
        
        # 5. Retorna o JSON amigável para o Frontend
        return {
            "dossie_enviado": dossie,
            "parecer_auditoria_ia": analise_ia,
            "resultado_gamificacao": resultado_game
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha no motor de inferência: {str(e)}"
        )
