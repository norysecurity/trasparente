import asyncio
import os
import re
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from motor_ia_qwen import MotorIAQwen
from google_drive_manager import GoogleDriveManager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path)

CGU_API_KEY = os.getenv("CGU_API_KEY", "")
HEADERS_CGU = {"chave-api-dados": CGU_API_KEY, "Accept": "application/json"}

LISTA_NEGRA = ["aécio neves", "eduardo cunha", "geddel", "sergio cabral", "fernando collor", "bolsonaro", "lula", "arthur lira"]

# Instância do Drive Manager
drive_manager = GoogleDriveManager()

def buscar_familiares_e_pessoas_proximas_sync(nome_politico: str) -> list:
    """Rastreia nomes de cônjuges, filhos, irmãos e associados via OSINT"""
    print(f"👥 [OSINT FAMÍLIA] Mapeando círculo íntimo de: {nome_politico}...")
    query = f'"{nome_politico}" (esposa OR marido OR filho OR filha OR irmão OR irmã OR sócio)'
    familiares_encontrados = set()
    
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, region='br-pt', safesearch='off', max_results=15))
            for r in resultados:
                texto = str(r.get('body', '') + " " + r.get('title', '')).upper()
                
                # Extrai palavras em maiúsculo (nomes próprios) próximos a palavras-chave
                padroes = re.findall(r'(ESPOSA|MARIDO|FILH[OA]|IRM[ÃA]O) (?:DE |CHAMAD[OA] )?([A-Z][A-Z\s]+)', texto)
                for relacao, nome in padroes:
                    nome_limpo = nome.strip().split(',')[0].split('.')[0]
                    if len(nome_limpo.split()) >= 2 and nome_limpo.lower() not in nome_politico.lower():
                        familiares_encontrados.add(nome_limpo)
    except Exception as e:
        print(f"  ❌ Erro OSINT Família: {e}")
        
    familiares_lista = list(familiares_encontrados)
    if familiares_lista:
        print(f"  🩸 Familiares mapeados: {', '.join(familiares_lista)}")
    return familiares_lista

async def consultar_brasil_api_cnpj(cnpj: str) -> dict:
    cnpj_limpo = "".join(filter(str.isdigit, cnpj))
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
    try:
        res = await asyncio.to_thread(requests.get, url, timeout=10)
        return res.json() if res.status_code == 200 else {}
    except Exception: return {}

async def consultar_cgu_pep(cpf: str) -> bool:
    cpf_limpo = "".join(filter(str.isdigit, cpf))
    url = f"https://api.portaldatransparencia.gov.br/api-de-dados/peps?cpf={cpf_limpo}&pagina=1"
    try:
        res = await asyncio.to_thread(requests.get, url, headers=HEADERS_CGU, timeout=10)
        return True if res.status_code == 200 and len(res.json()) > 0 else False
    except Exception: return False

async def consultar_cgu_emendas(cpf_autor: str) -> list:
    cpf_limpo = "".join(filter(str.isdigit, cpf_autor))
    url = f"https://api.portaldatransparencia.gov.br/api-de-dados/emendas?ano={datetime.now().year}&codigoAutor={cpf_limpo}&pagina=1"
    try:
        res = await asyncio.to_thread(requests.get, url, headers=HEADERS_CGU, timeout=10)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

async def consultar_cgu_cartoes(cpf_portador: str) -> list:
    cpf_limpo = "".join(filter(str.isdigit, cpf_portador))
    url = f"https://api.portaldatransparencia.gov.br/api-de-dados/cartoes?cpfPortador={cpf_limpo}&pagina=1"
    try:
        res = await asyncio.to_thread(requests.get, url, headers=HEADERS_CGU, timeout=10)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

async def consultar_cgu_sancoes(cpf_ou_cnpj: str) -> list:
    doc_limpo = "".join(filter(str.isdigit, cpf_ou_cnpj))
    url = f"https://api.portaldatransparencia.gov.br/api-de-dados/ceis?codigoSancionado={doc_limpo}&pagina=1"
    try:
        res = await asyncio.to_thread(requests.get, url, headers=HEADERS_CGU, timeout=10)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

async def consultar_ibama_multas(nome_ou_cnpj: str) -> list:
    url = "https://dadosabertos.ibama.gov.br/api/3/action/datastore_search"
    resource_id = "1138dd20-22b3-402d-88bc-b2f56110f63e"
    try:
        res = await asyncio.to_thread(requests.get, url, params={"resource_id": resource_id, "q": nome_ou_cnpj, "limit": 5}, timeout=10)
        return res.json().get("result", {}).get("records", []) if res.status_code == 200 else []
    except Exception: return []

def buscar_vazamentos_osint_cpf_sync(cpf: str, nome_politico: str) -> list:
    if not cpf or cpf == "00000000000": return []
    cpf_formatado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    query = f'"{cpf_formatado}" OR "{cpf}" "CNPJ" "sócio" OR "contrato"'
    cnpjs_encontrados = set()
    try:
        with DDGS() as ddgs:
            for r in list(ddgs.text(query, region='br-pt', safesearch='off', max_results=10)):
                for c in re.findall(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b', r.get('body', '') + " " + r.get('title', '')):
                    cnpjs_encontrados.add(re.sub(r'[^0-9]', '', c))
    except Exception: pass
    return list(cnpjs_encontrados)

def buscar_cpf_e_bens_tse_sync(nome_politico: str, cpf: str = None) -> list:
    termo_busca = f'"{nome_politico}"'
    if cpf and cpf != "00000000000": termo_busca += f' OR "{cpf}"'
    query = f'site:divulgacandcontas.tse.jus.br {termo_busca} bens declarados'
    cnpjs_encontrados = set()
    try:
        with DDGS() as ddgs:
            for r in list(ddgs.text(query, region='br-pt', safesearch='off', max_results=10)):
                for c in re.findall(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b', r.get('body', '') + " " + r.get('title', '')):
                    cnpjs_encontrados.add(re.sub(r'[^0-9]', '', c))
    except Exception: pass
    return list(cnpjs_encontrados)

def pesquisar_historico_criminal_sync(nome_politico: str):
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(f"{nome_politico} investigado corrupção STF", region='br-pt', safesearch='off', max_results=10))
    except Exception: return []

def avaliar_score_inicial_sincrono(nome_politico: str) -> tuple[int, list, list]:
    pontos_perdidos, red_flags, motivos = 0, [], []
    for mafioso in LISTA_NEGRA:
        if mafioso in nome_politico.lower():
            pontos_perdidos += 500
            motivos.append("Lista Negra Oficial")
            red_flags.append({"data": datetime.now().strftime("%d/%m/%Y"), "titulo": "Histórico Crítico em Foco Nacional", "desc": f"Este político consta na base negra inicial de alta corrupção ({mafioso.title()}).", "fonte": "Base Governamental"})
            break

    noticias = pesquisar_historico_criminal_sync(nome_politico)
    palavras_chave_criminal = ["réu", "propina", "desvio", "corrupção", "condenado", "lavagem de dinheiro", "inquérito", "indiciado", "lava jato", "stf", "polícia federal", "investigação", "preso", "investigado", "pf"]
    palavras_inocencia = ["absolvido", "inocentado", "arquivado", "falta de provas", "improcedente"]
    
    for n in list(noticias)[:5]:
        texto = f"{n.get('title', '')} {n.get('body', '')}".lower()
        
        tem_inocencia = any(pi in texto for pi in palavras_inocencia)
        
        if any(p in texto for p in palavras_chave_criminal):
            if not tem_inocencia:
                # Crime achado e sem absolvicão = TOMA PONTO
                pontos_perdidos += 200
                motivos.append(f"OSINT revelou: {', '.join([p for p in palavras_chave_criminal if p in texto])}")
                red_flags.append({
                    "data": datetime.now().strftime("%d/%m/%Y"), 
                    "titulo": f"Alerta OSINT: {n.get('title', 'Notícia/Processo')}", 
                    "desc": f"Evidências: {', '.join([p for p in palavras_chave_criminal if p in texto])}.",
                    "fonte": n.get('href', '')
                })
            else:
                # Investigado mas INOCENTADO
                red_flags.append({
                    "data": datetime.now().strftime("%d/%m/%Y"), 
                    "titulo": f"Alerta OSINT: {n.get('title', 'Notícia/Processo')}", 
                    "desc": f"⚠️ ATENÇÃO: Consta registro de investigação, porém o resultado aponta: {', '.join([pi for pi in palavras_inocencia if pi in texto]).upper()}.",
                    "fonte": n.get('href', '')
                })
            
    return pontos_perdidos, red_flags, motivos

async def auditar_malha_fina_assincrona(id_politico: int, nome_politico: str, cpf_real: str | None = None, cnpjs_fornecedores: list | None = None, red_flags_iniciais: list | None = None, pontos_perdidos_iniciais: int = 0, despesas_para_analise: list | None = None):
    print(f"\n🚀 INICIANDO AUDITORIA GOVTECH MULTI-API: {nome_politico.upper()}")
    pontos_perdidos = pontos_perdidos_iniciais
    red_flags = list(red_flags_iniciais) if red_flags_iniciais else []
    empresas_detalhadas = []
    
    # Busca Familiares e Pessoas Próximas (OSINT Avançado)
    familiares_conhecidos = buscar_familiares_e_pessoas_proximas_sync(nome_politico)

    partes_nome = nome_politico.lower().split()
    sobrenomes_politico = [p for p in partes_nome if len(p) > 2 and p not in {"dos", "das", "de", "do", "da", "filho", "junior", "neto", "jr", "maria", "joao", "ana", "jose", "pedro", "luiz", "carlos"}]
    
    if cpf_real and cpf_real != "00000000000":
        if await consultar_cgu_pep(cpf_real): print("  🚨 POLÍTICO É PEP ATIVO NA CGU.")
        sancoes_cpf = await consultar_cgu_sancoes(cpf_real)
        if sancoes_cpf:
            pontos_perdidos += 400
            red_flags.append({"data": sancoes_cpf[0].get("dataPublicacaoSancao", "N/A"), "titulo": "🚨 CPF Sancionado (CGU)", "desc": "O CPF do agente possui sanções ativas.", "fonte": "CEIS"})
            
        cnpjs_vazados = buscar_vazamentos_osint_cpf_sync(cpf_real, nome_politico)
        if cnpjs_vazados:
            cnpjs_fornecedores = (cnpjs_fornecedores or []) + cnpjs_vazados

    cnpjs = set(cnpjs_fornecedores[:30]) if cnpjs_fornecedores else set()
    cnpjs.update(buscar_cpf_e_bens_tse_sync(nome_politico, cpf_real))
    cnpjs = [c for c in cnpjs if c and c.strip()]
    
    for cnpj in cnpjs:
        dados_receita = await consultar_brasil_api_cnpj(cnpj)
        if dados_receita:
            nome_empresa = dados_receita.get("razao_social")
            socios = [s.get("nome_socio", "") for s in dados_receita.get("qsa", [])]
            empresas_detalhadas.append({"nome": nome_empresa, "cnpj": cnpj, "socios": socios, "valor": "Confidencial"})
            
            for socio in socios:
                socio_lower = str(socio).lower()
                if nome_politico.lower() in socio_lower:
                    pontos_perdidos += 600
                    red_flags.append({"data": datetime.now().strftime("%d/%m/%Y"), "titulo": "🚨 EXTREMO: Autocontratação", "desc": f"Político no QSA da empresa {nome_empresa}.", "fonte": f"Receita Federal (CNPJ {cnpj})"})
                    break
                
                # Checa por Familiares mapeados na OSINT
                familiar_detectado = next((f for f in familiares_conhecidos if f.lower() in socio_lower), None)
                if familiar_detectado:
                    pontos_perdidos += 500
                    red_flags.append({"data": datetime.now().strftime("%d/%m/%Y"), "titulo": "🚨 ALERTA: Conexão Direta (Nepotismo/Laranja)", "desc": f"Empresa ligada possui sócio ({socio}) identificado como próximo ({familiar_detectado}).", "fonte": f"Receita Federal"})
                    break

                for sobrenome in sobrenomes_politico:
                    if str(sobrenome) in socio_lower:
                        pontos_perdidos += 300
                        red_flags.append({"data": datetime.now().strftime("%d/%m/%Y"), "titulo": "Alerta: Possível Nepotismo", "desc": f"Sócio partilha sobrenome ({sobrenome})", "fonte": f"Receita Federal"})
                        break 
            
            sancoes = await consultar_cgu_sancoes(cnpj)
            if sancoes:
                pontos_perdidos += 300
                red_flags.append({"data": sancoes[0].get("dataPublicacaoSancao", "N/A"), "titulo": "Empresa Sancionada", "desc": f"{nome_empresa} possui sanções ativas.", "fonte": "CGU"})

    multas_ibama = await consultar_ibama_multas(nome_politico)
    for multa in multas_ibama:
        pontos_perdidos += 150
        red_flags.append({"data": multa.get("DAT_HORA_AUTO_INFRACAO", "N/A"), "titulo": "Autuação Ambiental", "desc": multa.get('DES_INFRACAO', '')[:100], "fonte": "IBAMA"})

    if cpf_real and cpf_real != "00000000000":
        for emenda in (await consultar_cgu_emendas(cpf_real))[:10]:
            if emenda.get("valorEmpenhado", 0) > 0:
                empresas_detalhadas.append({"nome": f"Emenda: {emenda.get('funcao', '')}", "cargo": f"Nº {emenda.get('codigoEmenda')}", "valor": f"R$ {emenda.get('valorEmpenhado'):,.2f}", "fonte": "CGU"})
        
        for cartao in (await consultar_cgu_cartoes(cpf_real))[:100]:
            valor_transacao = float(cartao.get("valorTransacao", "0").replace(".", "").replace(",", ".") if isinstance(cartao.get("valorTransacao"), str) else cartao.get("valorTransacao", 0))
            if valor_transacao > 0:
                fornecedor = cartao.get("estabelecimento", {}).get("nomeRecebedor", "Fornecedor Sigiloso")
                empresas_detalhadas.append({"nome": fornecedor, "cargo": "Cartão Corporativo (CPGF)", "valor": f"R$ {valor_transacao:,.2f}", "fonte": "Portal da Transparência"})

    resultado_ia = await MotorIAQwen().analisar_dossie({"cpf": cpf_real, "familiares_mapeados": familiares_conhecidos, "empresas": empresas_detalhadas, "noticias": pesquisar_historico_criminal_sync(nome_politico)})
    nivel_risco = resultado_ia.get("nivel_risco", "BAIXO").upper()
    pontos_perdidos += {"CRITICO": 500, "ALTO": 300, "MEDIO": 150, "BAIXO": 0}.get(nivel_risco, 0)
    for rf_ia in resultado_ia.get("red_flags", []):
        red_flags.append({"data": datetime.now().strftime("%d/%m/%Y"), "titulo": f"🤖 IA Alert: {nivel_risco}", "desc": rf_ia.get("motivo", ""), "fonte": "Qwen"})

    score_final = max(0, 1000 - pontos_perdidos)
    
    os.makedirs("dossies", exist_ok=True)
    dossie = {
        "id_politico": id_politico,
        "cpf_politico": cpf_real,
        "familiares_identificados": familiares_conhecidos,
        "redFlags": red_flags,
        "pontos_perdidos": pontos_perdidos,
        "empresas": empresas_detalhadas,
        "despesas_totais_encontradas": len(despesas_para_analise) if despesas_para_analise else 0,
        "despesas_brutas": despesas_para_analise or [],
        "data_auditoria": datetime.now().isoformat()
    }
    
    caminho_arquivo = f"dossies/dossie_{id_politico}.json"
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(dossie, f, ensure_ascii=False, indent=4)
        
    # Salva no Google Drive Automáticamente
    try:
        drive_manager.salvar_dossie_no_drive(nome_politico, caminho_arquivo)
    except Exception as e:
        print(f"⚠️ Erro ao salvar no Google Drive: {e}")
        
    try:
        from database.neo4j_conn import get_neo4j_connection
        neo4j_db = get_neo4j_connection()
        dossie_grafo = dossie.copy()
        dossie_grafo["nome_politico"] = nome_politico 
        neo4j_db.registrar_dossie_no_grafo(dossie_grafo)
        neo4j_db.close()
    except Exception as e: pass

    return score_final, red_flags, empresas_detalhadas
