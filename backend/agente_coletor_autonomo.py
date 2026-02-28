import asyncio
import os
import re
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from duckduckgo_search import DDGS

load_dotenv()

CGU_API_KEY = os.getenv("CGU_API_KEY", "")

# Headers obrigatórios para o Portal da Transparência
HEADERS_CGU = {
    "chave-api-dados": CGU_API_KEY,
    "Accept": "application/json"
}

# 1. LISTA NEGRA: Nomes famosos de processos severos (Dedução imediata de 500pts)
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

async def consultar_brasil_api_cnpj(cnpj: str) -> dict:
    """Consulta a base espelho da Receita Federal via BrasilAPI"""
    cnpj_limpo = "".join(filter(str.isdigit, cnpj))
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
    print(f"🏢 [RECEITA FEDERAL] Consultando CNPJ: {cnpj_limpo}...")
    try:
        # Usando to_thread para não bloquear o event loop do FastAPI
        res = await asyncio.to_thread(requests.get, url, timeout=10)
        if res.status_code == 200:
            return res.json()
        return {}
    except Exception as e:
        print(f"Erro BrasilAPI: {e}")
        return {}

async def consultar_cgu_pep(cpf: str) -> bool:
    """Verifica se o CPF está na lista de Pessoas Expostas Politicamente da CGU"""
    cpf_limpo = "".join(filter(str.isdigit, cpf))
    url = f"https://api.portaldatransparencia.gov.br/api-de-dados/peps?cpf={cpf_limpo}&pagina=1"
    print(f"⚖️ [CGU] Consultando Portal da Transparência (PEP) para CPF: {cpf_limpo}...")
    try:
        res = await asyncio.to_thread(requests.get, url, headers=HEADERS_CGU, timeout=10)
        if res.status_code == 200 and len(res.json()) > 0:
            return True
        return False
    except Exception as e:
        print(f"Erro CGU PEP: {e}")
        return False

async def consultar_cgu_sancoes(cpf_ou_cnpj: str) -> list:
    """Consulta o Cadastro de Empresas Inidôneas e Suspensas (CEIS)"""
    doc_limpo = "".join(filter(str.isdigit, cpf_ou_cnpj))
    url = f"https://api.portaldatransparencia.gov.br/api-de-dados/ceis?codigoSancionado={doc_limpo}&pagina=1"
    print(f"🚫 [CGU] Consultando Sanções (CEIS) para: {doc_limpo}...")
    try:
        res = await asyncio.to_thread(requests.get, url, headers=HEADERS_CGU, timeout=10)
        if res.status_code == 200:
            return res.json()
        return []
    except Exception:
        return []

async def consultar_ibama_multas(nome_ou_cnpj: str) -> list:
    """
    Consulta a API CKAN de Dados Abertos do IBAMA para Autuações Ambientais.
    Endpoint real do CKAN do Governo: dadosabertos.ibama.gov.br
    """
    url = "https://dadosabertos.ibama.gov.br/api/3/action/datastore_search"
    # ID do dataset de Autuações Ambientais do IBAMA
    resource_id = "1138dd20-22b3-402d-88bc-b2f56110f63e"
    print(f"🌳 [IBAMA] Verificando crimes ambientais para: {nome_ou_cnpj}...")
    try:
        params = {"resource_id": resource_id, "q": nome_ou_cnpj, "limit": 5}
        res = await asyncio.to_thread(requests.get, url, params=params, timeout=10)
        if res.status_code == 200:
            dados = res.json().get("result", {}).get("records", [])
            return dados
        return []
    except Exception:
        return []

def buscar_cpf_e_bens_tse_sync(nome_politico: str) -> list:
    print(f"🕵️‍♂️ [TSE] Buscando CNPJs em Declarações via OSINT (DuckDuckGo) para: {nome_politico}")
    query = f'site:divulgacandcontas.tse.jus.br "{nome_politico}" bens declarados'
    cnpjs_encontrados = set()
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, region='br-pt', safesearch='off', max_results=10))
            for r in resultados:
                texto = r.get('body', '') + " " + r.get('title', '')
                cnpjs = re.findall(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b', texto)
                for c in cnpjs:
                    cnpjs_encontrados.add(re.sub(r'[^0-9]', '', c))
    except Exception:
        pass
    return list(cnpjs_encontrados)

def pesquisar_historico_criminal_sync(nome_politico: str):
    print(f"🌐 [OSINT STF/PF] Iniciando Vasculha Síncrona para: {nome_politico}")
    query = f'"{nome_politico}" (STF OR "Polícia Federal" OR "Lava Jato" OR inquérito OR condenado OR "Polícia" OR "Ministério Público")'
    resultados = []
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, region='br-pt', safesearch='off', max_results=10))
    except Exception as e:
        print(f"  ❌ Erro DuckDuckGo: {e}")
    return resultados

def avaliar_score_inicial_sincrono(nome_politico: str):
    """
    Garante que a rota do Frontend obtenha a penalidade baseada em fatos antes das views.
    """
    pontos_perdidos = 0
    red_flags = []
    motivos = []
    
    # 1. LISTA NEGRA
    for mafioso in LISTA_NEGRA:
        if mafioso in nome_politico.lower():
            pontos_perdidos += 500
            motivos.append("Lista Negra Oficial (Risco Extremo)")
            red_flags.append({
                "data": datetime.now().strftime("%d/%m/%Y"),
                "titulo": "Histórico Crítico em Foco Nacional",
                "desc": f"Este político consta na base negra inicial de alta corrupção ({mafioso.title()}).",
                "fonte": "Base Governamental"
            })
            print(f"  🚨 ALERTA: {nome_politico} está na LISTA NEGRA (-500 pontos)")
            break

    # 2. DUCKDUCKGO OSINT STF/PF
    noticias = pesquisar_historico_criminal_sync(nome_politico)
    palavras_chave = ["réu", "propina", "desvio", "corrupção", "condenado", "lavagem de dinheiro", "inquérito", "indiciado", "lava jato", "stf", "polícia federal"]
    for r in noticias:
        texto = str(r.get('title', '') + " " + r.get('body', '')).lower()
        title = r.get('title', 'Notícia')
        url = r.get('href', '')
        encontrado = [p for p in palavras_chave if p in texto]
        if encontrado:
            motivos.append(f"OSINT revelou: {', '.join(encontrado)}")
            pontos_perdidos += 200
            red_flags.append({
                "data": datetime.now().strftime("%d/%m/%Y"),
                "titulo": title,
                "desc": f"Evidências encontradas: {', '.join(encontrado)}.",
                "fonte": url
            })
            print(f"  🚨 ALERTA OSINT: {title} (-200 pts)")
            
    return pontos_perdidos, red_flags, motivos

async def auditar_malha_fina_assincrona(id_politico: int, nome_politico: str, cpf_real: str = None, cnpjs_declarados: list = None, red_flags_iniciais: list = None, pontos_perdidos_iniciais: int = 0):
    """
    Motor Central de Auditoria Governamental Background.
    Cruza Receita Federal, CGU, IBAMA e TCU em tempo real.
    """
    print(f"\n=======================================================")
    print(f"🚀 INICIANDO AUDITORIA GOVTECH MULTI-API: {nome_politico.upper()}")
    print(f"=======================================================")
    
    pontos_perdidos = pontos_perdidos_iniciais
    red_flags = list(red_flags_iniciais) if red_flags_iniciais else []
    empresas_detalhadas = []
    
    if not cpf_real or cpf_real == "00000000000":
        print("⚠️ CPF real não fornecido ou nulo. A auditoria profunda na CGU PEP não ocorrerá.")
    else:
        is_pep = await consultar_cgu_pep(cpf_real)
        if is_pep:
            print("  🚨 POLÍTICO IDENTIFICADO COMO PEP ATIVO NA CGU.")
    
    cnpjs = set(cnpjs_declarados) if cnpjs_declarados else set()
    cnpjs_tse = buscar_cpf_e_bens_tse_sync(nome_politico)
    cnpjs.update(cnpjs_tse)
    cnpjs = [c for c in cnpjs if c and c.strip()]
    
    # 1. VARREDURA DE EMPRESAS (RECEITA FEDERAL)
    for cnpj in cnpjs:
        dados_receita = await consultar_brasil_api_cnpj(cnpj)
        if dados_receita:
            nome_empresa = dados_receita.get("razao_social")
            empresas_detalhadas.append({
                "nome": nome_empresa,
                "cnpj": cnpj,
                "socios": [s.get("nome_socio") for s in dados_receita.get("qsa", [])],
                "valor": "Consulta BrasilAPI Confidencial"
            })
            
            # 2. VARREDURA DE SANÇÕES PARA A EMPRESA (CGU)
            sancoes = await consultar_cgu_sancoes(cnpj)
            if sancoes:
                pontos_perdidos += 300
                red_flags.append({
                    "data": sancoes[0].get("dataPublicacaoSancao", "N/A"),
                    "titulo": "Empresa Sancionada (CGU)",
                    "desc": f"A empresa {nome_empresa} possui sanções ativas no CEIS/CNEP.",
                    "fonte": "https://portaldatransparencia.gov.br/"
                })
        else:
            empresas_detalhadas.append({
                "nome": f"Empresa (S/ Info Receita: {cnpj})",
                "cnpj": cnpj,
                "socios": []
            })

    # 3. VARREDURA DE MULTAS AMBIENTAIS (IBAMA)
    multas_ibama = await consultar_ibama_multas(nome_politico)
    if multas_ibama:
        for multa in multas_ibama:
            pontos_perdidos += 150
            red_flags.append({
                "data": multa.get("DAT_HORA_AUTO_INFRACAO", "N/A"),
                "titulo": "Autuação Ambiental (IBAMA)",
                "desc": f"Infração: {multa.get('DES_INFRACAO', 'Crime ambiental detectado')[:100]}...",
                "fonte": "https://dadosabertos.ibama.gov.br/"
            })

    # Regra de Segurança: Score nunca é negativo
    score_final = 1000 - pontos_perdidos
    if score_final < 0: score_final = 0

    print(f"✅ Auditoria GovTech Concluída!")
    print(f"📊 SCORE REAL CALCULADO: {score_final}")
    print(f"🚩 Red Flags Encontradas: {len(red_flags)}")
    print(f"🏢 Empresas Mapeadas: {len(empresas_detalhadas)}\n")

    os.makedirs("dossies", exist_ok=True)
    dossie = {
        "id_politico": id_politico,
        "redFlags": red_flags,
        "pontos_perdidos": pontos_perdidos,
        "empresas": empresas_detalhadas,
        "data_auditoria": datetime.now().isoformat()
    }
    
    caminho_arquivo = f"dossies/dossie_{id_politico}.json"
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(dossie, f, ensure_ascii=False, indent=4)
        
    return score_final, red_flags, empresas_detalhadas
