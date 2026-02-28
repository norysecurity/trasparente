import asyncio
import os
import re
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from motor_ia_qwen import MotorIAQwen

# Forçar leitura do .env na raiz do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path)

CGU_API_KEY = os.getenv("CGU_API_KEY", "")

# Headers obrigatórios para o Portal da Transparência
HEADERS_CGU = {
    "chave-api-dados": CGU_API_KEY,
    "Accept": "application/json"
}

async def consultar_brasil_api_cnpj(cnpj: str) -> dict:
    """Consulta a base espelho da Receita Federal via BrasilAPI"""
    cnpj_limpo = "".join(filter(str.isdigit, cnpj))
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
    print(f"🏢 [RECEITA FEDERAL] Consultando CNPJ: {cnpj_limpo}...")
    try:
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

async def consultar_cgu_emendas(cpf_autor: str) -> list:
    """
    Rastreia a liberação de Emendas Parlamentares (incluindo Emendas PIX) 
    via Portal da Transparência API de Dados Abertos
    """
    cpf_limpo = "".join(filter(str.isdigit, cpf_autor))
    ano_atual = datetime.now().year
    url = f"https://api.portaldatransparencia.gov.br/api-de-dados/emendas?ano={ano_atual}&codigoAutor={cpf_limpo}&pagina=1"
    print(f"💰 [CGU] Rastreando Emendas Parlamentares (PIX) para: {cpf_limpo}...")
    try:
        res = await asyncio.to_thread(requests.get, url, headers=HEADERS_CGU, timeout=10)
        if res.status_code == 200:
            return res.json()
        return []
    except Exception:
        return []

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
    """
    url = "https://dadosabertos.ibama.gov.br/api/3/action/datastore_search"
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
    print(f"🕵️‍♂️ [TSE] Buscando CNPJs em Declarações via OSINT para: {nome_politico}")
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
    print(f"🌐 [OSINT STF/PF] Iniciando Vasculha Síncrona Total para: {nome_politico}")
    
    # 3 Queries separadas para impedir bloqueio por complexidade do DuckDuckGo e obter mais dados reais
    query1 = f"{nome_politico} investigado STF corrupção"
    query2 = f"{nome_politico} condenado processo tribunal"
    query3 = f"{nome_politico} inquérito Polícia Federal"
    
    resultados = []
    try:
        with DDGS() as ddgs:
             res1 = list(ddgs.text(query1, region='br-pt', safesearch='off', max_results=3))
             res2 = list(ddgs.text(query2, region='br-pt', safesearch='off', max_results=3))
             res3 = list(ddgs.text(query3, region='br-pt', safesearch='off', max_results=3))
             resultados.extend(res1 + res2 + res3)
    except Exception as e:
        print(f"  ❌ Erro DuckDuckGo OSINT Criminal: {e}")
        
    return resultados

def avaliar_score_inicial_sincrono(nome_politico: str) -> tuple[int, list, list]:
    """
    Função mantida para inicialização rápida da View inicial, MAS sem lista negra e 
    dependendo puramente da internet e não de Hardcodes.
    """
    pontos_perdidos: int = 0
    red_flags: list[dict[str, str]] = []
    motivos: list[str] = []
    
    # DUCKDUCKGO OSINT STF/PF
    noticias = pesquisar_historico_criminal_sync(nome_politico)
    palavras_chave = ["réu", "propina", "desvio", "corrupção", "condenado", "lavagem de dinheiro", "inquérito", "indiciado", "lava jato", "stf", "polícia federal"]
    
    for r in noticias:
        texto = str(r.get('title', '') + " " + r.get('body', '')).lower()
        title = r.get('title', 'Notícia')
        url = r.get('href', '')
        encontrado = [p for p in palavras_chave if p in texto]
        if encontrado:
            motivos.append(f"OSINT revelou: {', '.join(encontrado)}")
            pontos_perdidos += 50 # Punição branda inicial, o Qwen julga o resto depois com profundidade
            red_flags.append({
                "data": datetime.now().strftime("%d/%m/%Y"),
                "titulo": title,
                "desc": f"Evidências OSINT Superficial: {', '.join(encontrado)}.",
                "fonte": url
            })
            print(f"  🚨 ALERTA OSINT SUPERFICIAL: {title} (-50 pts)")
            
    return pontos_perdidos, red_flags, motivos

async def auditar_malha_fina_assincrona(id_politico: int, nome_politico: str, cpf_real: str | None = None, cnpjs_fornecedores: list | None = None, red_flags_iniciais: list | None = None, pontos_perdidos_iniciais: int = 0, despesas_para_analise: list | None = None):
    """
    Motor Central de Auditoria Governamental Background.
    Cruza Receita Federal, CGU, IBAMA, TCU E Passa para a Qwen Julgar.
    """
    print(f"\n=======================================================")
    print(f"🚀 INICIANDO AUDITORIA GOVTECH MULTI-API: {nome_politico.upper()}")
    print(f"=======================================================")
    
    pontos_perdidos = pontos_perdidos_iniciais
    red_flags = list(red_flags_iniciais) if red_flags_iniciais else []
    empresas_detalhadas = []
    noticias_criminais = pesquisar_historico_criminal_sync(nome_politico)
    
    # 1. ISOLANDO SOBRENOMES DO POLÍTICO (Para cruzamento)
    partes_nome = nome_politico.lower().split()
    ignorar_conectivos = {"dos", "das", "de", "do", "da", "filho", "junior", "neto", "jr"}
    nomes_limpos: list[str] = [str(p) for p in partes_nome if len(p) > 2 and p not in ignorar_conectivos]
    
    if len(nomes_limpos) > 2:
        sobrenomes_politico = [nomes_limpos[-2], nomes_limpos[-1]]
    elif len(nomes_limpos) == 2:
        sobrenomes_politico = [nomes_limpos[-1]]
    else:
        sobrenomes_politico = list(nomes_limpos)
        
    nomes_comuns = {"maria", "joao", "ana", "paula", "jose", "pedro", "luiz", "carlos", "paulo", "antonio", "francisco"}
    sobrenomes_politico = [s for s in sobrenomes_politico if s not in nomes_comuns]
    
    if not cpf_real or cpf_real == "00000000000":
        print("⚠️ CPF real não fornecido ou nulo. A auditoria profunda na CGU PEP não ocorrerá.")
    else:
        is_pep = await consultar_cgu_pep(cpf_real)
        if is_pep:
            print("  🚨 POLÍTICO IDENTIFICADO COMO PEP ATIVO NA CGU.")
    
    # Limite aos primeiros 15 itens
    cnpjs = set(cnpjs_fornecedores[:15]) if cnpjs_fornecedores else set()
    cnpjs_tse = buscar_cpf_e_bens_tse_sync(nome_politico)
    cnpjs.update(cnpjs_tse)
    cnpjs = [c for c in cnpjs if c and c.strip()]
    
    # VARREDURA DE EMPRESAS FORNECEDORAS (RECEITA FEDERAL)
    for cnpj in cnpjs:
        dados_receita = await consultar_brasil_api_cnpj(cnpj)
        if dados_receita:
            nome_empresa = dados_receita.get("razao_social")
            socios = [s.get("nome_socio", "") for s in dados_receita.get("qsa", [])]
            empresas_detalhadas.append({
                "nome": nome_empresa,
                "cnpj": cnpj,
                "socios": socios,
                "valor": "Consulta BrasilAPI Confidencial"
            })
            
            nepotismo_encontrado = False
            for socio in socios:
                socio_lower = str(socio).lower()
                for sobrenome in sobrenomes_politico:
                    sobreno_str = str(sobrenome)
                    if sobreno_str in socio_lower:
                        red_flags.append({
                            "data": datetime.now().strftime("%d/%m/%Y"),
                            "titulo": "🚨 ALERTA: Possível Nepotismo / Laranja",
                            "desc": f"Fornecedor de gabinete possui sócio que partilha o sobrenome com o político.",
                            "fonte": f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
                        })
                        nepotismo_encontrado = True
                        break 
                if nepotismo_encontrado:
                    break
            
            # VARREDURA DE SANÇÕES (CGU)
            sancoes = await consultar_cgu_sancoes(cnpj)
            if sancoes:
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

    # VARREDURA DE MULTAS AMBIENTAIS (IBAMA)
    multas_ibama = await consultar_ibama_multas(nome_politico)
    if multas_ibama:
        for multa in multas_ibama:
            red_flags.append({
                "data": multa.get("DAT_HORA_AUTO_INFRACAO", "N/A"),
                "titulo": "Autuação Ambiental (IBAMA)",
                "desc": f"Infração: {multa.get('DES_INFRACAO', 'Crime ambiental detectado')[:100]}...",
                "fonte": "https://dadosabertos.ibama.gov.br/"
            })

    # RASTREIO DE EMENDAS PARLAMENTARES (PIX)
    emendas = []
    if cpf_real and cpf_real != "00000000000":
        dados_emendas = await consultar_cgu_emendas(cpf_real)
        for emenda in dados_emendas[:5]: # Top 5 recentes
            valor = emenda.get("valorEmpenhado", 0)
            if valor > 0:
                emendas.append({
                    "nome": f"Emenda: {emenda.get('funcao', 'Geral')} ({emenda.get('localidadeBeneficiada', 'BR')})",
                    "cargo": f"Nº {emenda.get('codigoEmenda')}",
                    "valor": f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    "fonte": "https://portaldatransparencia.gov.br/"
                })
        
        if len(emendas) > 0:
             print(f"  💸 EMENDAS ENCONTRADAS: Injetando {len(emendas)} no Grafo Financeiro.")
             empresas_detalhadas.extend(emendas)

    # ==========================================================
    # O JULGAMENTO DA IA - MOTOR QWEN
    # ==========================================================
    print("🧠 [LLM] Enviando Dossiê Sintetizado para a IA Julgar...")
    dossie_contexto = {
        "empresas_encontradas": empresas_detalhadas,
        "noticias_osint_criminais": noticias_criminais,
        "red_flags_extraidas": red_flags,
        "despesas_camara": despesas_para_analise
    }
    
    ia_engine = MotorIAQwen()
    resultado_ia = await ia_engine.analisar_dossie(dossie_contexto)
    
    nivel_risco = resultado_ia.get("nivel_risco", "BAIXO").upper()
    print(f"🧠 Análise de IA Concluída: Risco {nivel_risco}")
    
    # Atribuição pesada de punição gerida PELA I.A.
    if nivel_risco == "CRITICO":
        pontos_perdidos += 400
    elif nivel_risco == "ALTO":
        pontos_perdidos += 300
    elif nivel_risco == "MEDIO":
        pontos_perdidos += 150
    
    for rf_ia in resultado_ia.get("red_flags", []):
        red_flags.append({
            "data": datetime.now().strftime("%d/%m/%Y"),
            "titulo": f"🤖 Veridito IA (Qwen): Risco {nivel_risco}",
            "desc": str(rf_ia).get("motivo", str(rf_ia)),
            "fonte": "Auditoria IA Distribuída"
        })

    # Regra de Segurança: Score nunca é negativo
    score_final = 1000 - pontos_perdidos
    if score_final < 0: score_final = 0

    print(f"✅ Auditoria GovTech Concluída!")
    print(f"📊 SCORE REAL CALCULADO: {score_final}")
    print(f"🚩 Red Flags Encontradas: {len(red_flags)}")
    print(f"🏢 Entidades Financeiras Mapeadas: {len(empresas_detalhadas)}\n")

    os.makedirs("dossies", exist_ok=True)
    dossie = {
        "id_politico": id_politico,
        "redFlags": red_flags,
        "pontos_perdidos": pontos_perdidos,
        "empresas": empresas_detalhadas,
        "despesas_brutas": despesas_para_analise or [],
        "data_auditoria": datetime.now().isoformat()
    }
    
    caminho_arquivo = f"dossies/dossie_{id_politico}.json"
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(dossie, f, ensure_ascii=False, indent=4)
        
    return score_final, red_flags, empresas_detalhadas
