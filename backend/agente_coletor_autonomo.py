import asyncio
import os
import re
import requests
import json
from datetime import datetime
from duckduckgo_search import DDGS

# Credenciais e Endpoints
CGU_API_KEY = os.getenv("CGU_API_KEY", "")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "govtech_password")

# 1. LISTA NEGRA: Nomes famosos de processos severos que perdem pontuação automática.
LISTA_NEGRA = [
    "aécio neves", 
    "eduardo cunha", 
    "geddel", 
    "sergio cabral", 
    "fernando collor", 
    "bolsonaro", 
    "lula",
    "arthur lira"
]

def get_neo4j_driver():
    try:
        from neo4j import GraphDatabase
        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except ImportError:
        return None
    except Exception as e:
        return None

async def buscar_socios_receita(cnpj: str) -> list:
    print(f"CONECTANDO AO BRASILAPI... Buscando Quadro Societário para CNPJ: {cnpj}")
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
            print(f"  ❌ Erro ao buscar QSA na BrasilAPI (Status: {resposta.status_code})")
            return []
    except Exception as e:
        print(f"  ⚠️ Falha na BrasilAPI: {e}")
        return []

async def buscar_contratos_portal_transparencia(cnpj: str) -> list:
    print(f"BUSCANDO NO PORTAL DA TRANSPARÊNCIA... Verificando Verbas Públicas para CNPJ: {cnpj}")
    if not CGU_API_KEY:
        print("  ⚠️ Header chave-api-dados não preenchido. As requisições tentarão sem token.")
        
    url = "https://api.portaldatransparencia.gov.br/api-de-dados/contratos"
    headers = {"chave-api-dados": CGU_API_KEY} if CGU_API_KEY else {}
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
            print(f"  ✅ Encontrados {len(resultados)} contratos públicos no CNPJ.")
            return resultados
        return []
    except Exception as e:
        print(f"  ⚠️ Falha ao buscar contratos: {e}")
        return []

async def buscar_cpf_e_bens_tse(nome_politico: str) -> list:
    print(f"🕵️‍♂️ Buscando declarações TSE (DuckDuckGo Search) para: {nome_politico}")
    query = f'site:divulgacandcontas.tse.jus.br "{nome_politico}" bens declarados'
    cnpjs_encontrados = set()
    try:
        def fetch_ddgs():
            with DDGS() as ddgs:
                return list(ddgs.text(query, region='br-pt', safesearch='off', max_results=10))
        
        resultados = await asyncio.to_thread(fetch_ddgs)
        for r in resultados:
            texto = r.get('body', '') + " " + r.get('title', '')
            cnpjs = re.findall(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b', texto)
            for c in cnpjs:
                cnpjs_encontrados.add(re.sub(r'[^0-9]', '', c))
                
        print(f"  ✅ Encontrados {len(cnpjs_encontrados)} CNPJs nas declarações TSE.")
        return list(cnpjs_encontrados)
    except Exception:
        return []

def pesquisar_historico_criminal_sync(nome_politico: str):
    print(f"🌐 Iniciando OSINT Síncrono (DuckDuckGo Processos Ferozes) para: {nome_politico}")
    query = f'"{nome_politico}" (STF OR "Polícia Federal" OR "Ministério Público" OR corrupção OR inquérito OR "Lava Jato" OR condenado OR réu)'
    resultados = []
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, region='br-pt', safesearch='off', max_results=5))
    except Exception as e:
        print(f"  ❌ Erro na busca web síncrona: {e}")
    return resultados

def avaliar_red_flags_ia(nome_politico: str, resultados_web: list):
    red_flags = []
    pontos_perdidos = 0
    motivos_detalhados = []
    
    # Check Lista Negra OBRIGATÓRIA
    if any(nome.lower() in nome_politico.lower() for nome in LISTA_NEGRA):
        motivos_detalhados.append("Cadastro na Lista Negra Inicial")
        pontos_perdidos += 500
        print(f"  🚨 ALERTA GERAL: {nome_politico} na LISTA NEGRA. Dedução imediata de 500 pontos.")
        red_flags.append({
            "data": datetime.now().strftime("%d/%m/%Y"),
            "titulo": "Histórico Crítico em Foco Nacional",
            "desc": "Este político está na database pública de alto risco ou envolvimento severo.",
            "fonte": "Base Transparência"
        })

    # Regras punitivas do OSINT (Títulos Notícias com palavras críveis)
    palavras_chave = ["réu", "propina", "desvio", "corrupção", "condenado", "lavagem de dinheiro", "inquérito", "indiciado", "lava jato", "stf", "polícia federal"]
    for r in resultados_web:
        texto = str(r.get('title', '') + " " + r.get('body', '')).lower()
        title = r.get('title', 'Notícia Investigativa')
        url = r.get('href', '')
        
        encontrado = [p for p in palavras_chave if p in texto]
        if encontrado:
            motivo = f"Ações ilegais detectadas: {', '.join(encontrado)}."
            red_flags.append({
                "data": datetime.now().strftime("%d/%m/%Y"),
                "titulo": title,
                "desc": motivo,
                "fonte": url
            })
            pontos_perdidos += 200
            motivos_detalhados.append(f"OSINT revelou fatos graves (-200 pts)")
            print(f"  🚨 ALERTA CRIMINAL: {title} | Dedução: -200pts | Evidências: {motivo}")
            
    return red_flags, pontos_perdidos, motivos_detalhados

def salvar_malha_fina_neo4j(grafos_dados: dict):
    driver = get_neo4j_driver()
    if not driver:
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
    except Exception:
        pass
    finally:
        driver.close()

async def auditar_malha_fina_assincrona(id_politico: int, nome_politico: str, cpf_politico: str, cnpjs_reais: list, red_flags_iniciais: list, pontos_perdidos_iniciais: int):
    print(f"\n=======================================================")
    print(f"🕵️  WORKER BACKGROUND INICIANDO VARREDURA PROFUNDA: {nome_politico.upper()}")
    print(f"=======================================================")
    
    cnpjs_reais_encontrados = set(cnpjs_reais) if cnpjs_reais and cnpjs_reais != [""] else set()
    cnpjs_tse = await buscar_cpf_e_bens_tse(nome_politico)
    cnpjs_reais_encontrados.update(cnpjs_tse)
    
    lista_cnpjs_finais = list(cnpjs_reais_encontrados)

    empresas_do_politico = []
    
    # Mocking removido - se vazio, a api retornará array limpo para as bases
    for cnpj in lista_cnpjs_finais:
        empresa_dado = {"nome": f"Empresa Avaliada {cnpj}", "cnpj": cnpj}
        empresas_do_politico.append(empresa_dado)
        
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
        "red_flags": red_flags_iniciais
    }
    
    salvar_malha_fina_neo4j(dados_grafo)
    
    os.makedirs("dossies", exist_ok=True)
    dossie = {
        "id_politico": id_politico,
        "redFlags": red_flags_iniciais,
        "pontos_perdidos": pontos_perdidos_iniciais,
        "empresas": empresas_do_politico,
        "data_auditoria": datetime.now().isoformat()
    }
    
    caminho_arquivo = f"dossies/dossie_{id_politico}.json"
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(dossie, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Dossiê JSON PROFUNDO salvo com sucesso para {nome_politico}\n")
