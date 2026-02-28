import asyncio
import os
import re
import requests
import fitz  # PyMuPDF
import json
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from duckduckgo_search import DDGS

load_dotenv()

# Credenciais e Endpoints
CGU_API_KEY = os.getenv("CGU_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "govtech_password")

def get_neo4j_driver():
    try:
        from neo4j import GraphDatabase
        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except ImportError:
        print("Neo4j driver não instalado ou inacessível no Worker.")
        return None
    except Exception as e:
        print(f"Erro ao conectar ao Neo4j: {e}")
        return None

async def buscar_socios_receita(cnpj: str) -> list:
    print(f"🔍 Buscando Quadro de Sócios e Administradores (QSA) para o CNPJ: {cnpj}")
    cnpj_limpo = re.sub(r'[^0-9]', '', cnpj)
    
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
    try:
        resposta = await asyncio.to_thread(requests.get, url, timeout=10)
        if resposta.status_code == 200:
            dados = resposta.json()
            qsa = dados.get("qsa", [])
            socios = [{"nome": s.get("nome_socio"), "cargo": s.get("qualificacao_socio")} for s in qsa]
            print(f"  ✅ Encontrados {len(socios)} sócios.")
            return socios
        else:
            print(f"  ❌ Erro ao buscar QSA (Status: {resposta.status_code})")
            return []
    except Exception as e:
        print(f"  ⚠️ Falha na API da Receita: {e}")
        return []

async def buscar_contratos_portal_transparencia(cnpj: str) -> list:
    print(f"💰 Verificando Recebimento de Verbas Públicas para o CNPJ: {cnpj}")
    if not CGU_API_KEY:
        print("  ⚠️ CGU_API_KEY não configurada. Simulação ativada.")
        return []
        
    url = "https://api.portaldatransparencia.gov.br/api-de-dados/contratos"
    headers = {"chave-api-dados": CGU_API_KEY}
    params = {"cnpjContratada": re.sub(r'[^0-9]', '', cnpj), "pagina": 1}
    
    try:
        resposta = await asyncio.to_thread(requests.get, url, headers=headers, params=params, timeout=10)
        if resposta.status_code == 200:
            contratos = resposta.json()
            resultados = []
            for c in contratos:
                resultados.append({
                    "orgao": c.get("orgaoSuperior", {}).get("nomeOrgao"),
                    "valor": c.get("valorInicial"),
                    "data": c.get("dataAssinatura")
                })
            print(f"  ✅ Encontrados {len(resultados)} contratos públicos.")
            return resultados
        return []
    except Exception as e:
        print(f"  ⚠️ Falha ao buscar contratos: {e}")
        return []

async def buscar_cpf_e_bens_tse(nome_politico: str) -> list:
    """
    Busca declarações de bens no TSE via DuckDuckGo para encontrar CNPJs Reais.
    """
    print(f"🕵️‍♂️ Buscando declarações no TSE para: {nome_politico}")
    query = f'site:divulgacandcontas.tse.jus.br "{nome_politico}" bens declarados'
    cnpjs_encontrados = set()
    try:
        def fetch_ddgs():
            with DDGS() as ddgs:
                return list(ddgs.text(query, region='br-pt', safesearch='off', max_results=10))
        
        resultados = await asyncio.to_thread(fetch_ddgs)
        for r in resultados:
            texto = r.get('body', '') + " " + r.get('title', '')
            # Regex para formato de CNPJ padrão XX.XXX.XXX/XXXX-XX ou XXXXXXXXXXXXXX
            cnpjs = re.findall(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b', texto)
            for c in cnpjs:
                cnpjs_encontrados.add(re.sub(r'[^0-9]', '', c))
                
        print(f"  ✅ Encontrados {len(cnpjs_encontrados)} CNPJs nas declarações do TSE.")
        return list(cnpjs_encontrados)
    except Exception as e:
        print(f"  ❌ Erro na busca do TSE: {e}")
        return []

async def pesquisar_historico_criminal_web(nome_politico: str):
    """
    Pesquisa em tempo real o histórico do político na Web (DDG) focando na PF e STF.
    """
    print(f"🌐 Iniciando OSINT na Web Aberta (DuckDuckGo STF/PF) para: {nome_politico}")
    query = f'"{nome_politico}" (STF OR "Polícia Federal" OR "Ministério Público" OR corrupção OR inquérito OR "Lava Jato" OR indiciado)'
    resultados = []
    try:
        def fetch_ddgs():
            with DDGS() as ddgs:
                return list(ddgs.text(query, region='br-pt', safesearch='off', max_results=5))
        
        resultados = await asyncio.to_thread(fetch_ddgs)
    except Exception as e:
        print(f"  ❌ Erro na busca web: {e}")
    return resultados

def avaliar_red_flags_ia(nome_politico: str, resultados_web: list):
    """
    Processa NLP/Regex nos resultados. Subtrai até 200 pontos de SCORE SERASA por cada caso letal.
    """
    red_flags = []
    pontos_perdidos = 0
    palavras_chave = ["lava jato", "propina", "inquérito", "denunciado", "indiciado", "jbs", "stf", "polícia federal", "desvio", "corrupção", "condenado", "lavagem", "réu"]
    
    for r in resultados_web:
        texto = str(r.get('title', '') + " " + r.get('body', '')).lower()
        title = r.get('title', 'Notícia Investigativa')
        url = r.get('href', '')
        
        encontrado = [p for p in palavras_chave if p in texto]
        if encontrado:
            motivo = f"Palavras-chave detectadas na reportagem: {', '.join(encontrado)}."
            red_flags.append({
                "data": datetime.now().strftime("%d/%m/%Y"),
                "titulo": title,
                "desc": motivo,
                "fonte": url
            })
            pontos_perdidos += 150
            print(f"  🚨 ALERTA CRIMINAL: {title}")
            
    return red_flags, pontos_perdidos

def salvar_malha_fina_neo4j(grafos_dados: dict):
    driver = get_neo4j_driver()
    if not driver:
        print("📛 Neo4j Offline. Os relacionamentos não serão salvaguardados.")
        return

    query = """
    MERGE (p:Politico {nome: $politico_nome})
    ON CREATE SET p.cpf = $politico_cpf, p.auditado_em = timestamp()
    
    FOREACH (emp IN $empresas |
        MERGE (e:Empresa {cnpj: emp.cnpj})
        ON CREATE SET e.nome = emp.nome
        MERGE (p)-[:DECLARA_SER_DONO_DE]->(e)
    )
    
    FOREACH (socio IN $socios |
        MERGE (s:Pessoa {nome: socio.nome})
        MERGE (p)-[:TEM_ASSOCIACAO_COM {cargo: socio.cargo}]->(s)
        MERGE (s)-[:OPERA_NA_EMPRESA]->(e) 
    )
    
    FOREACH (flag IN $red_flags |
        MERGE (r:RedFlag {url: flag.fonte})
        ON CREATE SET r.titulo = flag.titulo, r.data = flag.data
        MERGE (p)-[:ALVO_EM]->(r)
    )
    """
    try:
        with driver.session() as session:
            session.run(query, **grafos_dados)
            print(f"🕸️ Teia Neo4j atualizada com Sucesso para {grafos_dados['politico_nome']}!")
    except Exception as e:
        print(f"Erro ao salvar grafos: {e}")
    finally:
        driver.close()

async def auditar_malha_fina(id_politico: int, nome_politico: str, cpf_politico: str, cnpjs_reais: list = None):
    print(f"\n=======================================================")
    print(f"🕵️  WORKER INICIANDO AUDITORIA: {nome_politico.upper()}")
    print(f"=======================================================")
    
    # 1. Search criminal history Web openly
    resultados_web = await pesquisar_historico_criminal_web(nome_politico)
    red_flags_encontradas, pontos_perdidos = avaliar_red_flags_ia(nome_politico, resultados_web)
    
    # 2. Search TSE Assets if no CNPJs provided
    cnpjs_reais_encontrados = set(cnpjs_reais) if cnpjs_reais and cnpjs_reais != [""] else set()
    cnpjs_tse = await buscar_cpf_e_bens_tse(nome_politico)
    cnpjs_reais_encontrados.update(cnpjs_tse)
    
    lista_cnpjs_finais = list(cnpjs_reais_encontrados)

    if not lista_cnpjs_finais:
        print("📋 Sem CNPJs na lista. Avançando para consolidação...")
        
    empresas_do_politico = [{"nome": f"Empresa Vinculada {cnpj}", "cnpj": cnpj} for cnpj in lista_cnpjs_finais]
    todos_socios = []
    todos_contratos = []
    
    for empresa in empresas_do_politico:
        socios = await buscar_socios_receita(empresa["cnpj"])
        todos_socios.extend(socios)
        contratos = await buscar_contratos_portal_transparencia(empresa["cnpj"])
        todos_contratos.extend(contratos)
        
    dados_grafo = {
        "politico_nome": nome_politico,
        "politico_cpf": cpf_politico,
        "empresas": empresas_do_politico,
        "socios": todos_socios,
        "contratos": todos_contratos,
        "red_flags": red_flags_encontradas
    }
    
    salvar_malha_fina_neo4j(dados_grafo)
    
    # Criar e salvar dossie num ficheiro json local para o main.py consumir
    os.makedirs("dossies", exist_ok=True)
    dossie = {
        "id_politico": id_politico,
        "redFlags": red_flags_encontradas,
        "pontos_perdidos": pontos_perdidos,
        "data_auditoria": datetime.now().isoformat()
    }
    
    caminho_arquivo = f"dossies/dossie_{id_politico}.json"
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(dossie, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Dossiê JSON salvo com sucesso em {caminho_arquivo}")
    print(f"✅ Auditoria Concluída: {nome_politico}\n")

async def worker_noturno():
    print("🌙 Inicializando Worker Autônomo de Varredura Noturna OSINT...")
    alvos = [
        {"id": 900001, "nome": "Luiz Inácio Lula da Silva", "cpf": "000.000.000-01"},
        {"id": 900002, "nome": "Tarcísio de Freitas", "cpf": "111.111.111-02"},
    ]
    
    for alvo in alvos:
        await auditar_malha_fina(alvo["id"], alvo["nome"], alvo["cpf"], [])
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(worker_noturno())
