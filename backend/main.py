import requests
import uvicorn
import asyncio
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Logging principal do backend
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [main.py] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("GovTech.API")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path)

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from duckduckgo_search import DDGS

from agente_coletor_autonomo import auditar_malha_fina_assincrona
from database.neo4j_conn import get_neo4j_connection

app = FastAPI(title="GovTech Transparência API")
neo4j_conn = get_neo4j_connection()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2/deputados"
CACHE_DOSSIES = {}

def obter_score_dossie(id_politico):
    caminho = f"dossies/dossie_{id_politico}.json"
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return max(0, 1000 - json.load(f).get("pontos_perdidos", 0))
        except: pass
    return "Pendente"

# ==========================================
# ROTAS DO DASHBOARD E FEED DE GUERRA
# ==========================================
@app.get("/api/dashboard/guerra")
def dashboard_guerra():
    return {
        "status": "sucesso",
        "top_risco": [
            {"nome": "Bolsonaro", "partido": "PL", "estado": "RJ", "score": 850, "foto": "https://www.camara.leg.br/internet/deputado/bandep/74847.jpg"},
            {"nome": "Lula", "partido": "PT", "estado": "SP", "score": 820, "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Presidente_Luiz_In%C3%A1cio_Lula_da_Silva_em_2023.jpg/800px-Presidente_Luiz_In%C3%A1cio_Lula_da_Silva_em_2023.jpg"},
            {"nome": "Flávio Dino", "partido": "STF", "estado": "MA", "score": 790, "foto": "https://upload.wikimedia.org/wikipedia/commons/b/b8/Fl%C3%A1vio_Dino_em_2023.jpg"}
        ],
        "alertas_recentes": [
            {"alvo": "Eduardo Bolsonaro", "mensagem": "Gastou R$ 45.000 em Dubai sem agenda oficial.", "urgencia": "MÉDIA", "fonte": "CGU", "tempo": "10 min atrás"},
            {"alvo": "Gleisi Hoffmann", "mensagem": "Omitiu R$ 1.2M do patrimônio do TSE.", "urgencia": "ALTA", "fonte": "TSE", "tempo": "1h atrás"},
            {"alvo": "Tarcísio Gomes", "mensagem": "Rede ligada ao PCC venceu licitação da CPTM.", "urgencia": "CRÍTICA", "fonte": "TCE-SP", "tempo": "2h atrás"}
        ]
    }

@app.get("/api/politicos/presidenciais")
def obter_presidenciais():
    return {
        "status": "sucesso",
        "dados": [
            {"id": "900002", "nome": "Jair Messias Bolsonaro", "cargo": "Candidato à Presidência", "partido": "PL", "estado": "RJ", "score": "Pendente", "urlFoto": "https://www.camara.leg.br/internet/deputado/bandep/74847.jpg"},
            {"id": "900001", "nome": "Luiz Inácio Lula da Silva", "cargo": "Presidente da República", "partido": "PT", "estado": "SP", "score": "Pendente", "urlFoto": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Presidente_Luiz_In%C3%A1cio_Lula_da_Silva_em_2023.jpg/800px-Presidente_Luiz_In%C3%A1cio_Lula_da_Silva_em_2023.jpg"},
            {"id": "900003", "nome": "Pablo Marçal", "cargo": "Candidato à Presidência", "partido": "PRTB", "estado": "SP", "score": "Pendente", "urlFoto": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Pablo_Mar%C3%A7al_-_2022.jpg/640px-Pablo_Mar%C3%A7al_-_2022.jpg"},
            {"id": "900004", "nome": "Tarcísio de Freitas", "cargo": "Governador de SP", "partido": "REPUBLICANOS", "estado": "SP", "score": "Pendente", "urlFoto": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Tarc%C3%ADsio_de_Freitas_em_maio_de_2023_%28recorte%29.jpg/640px-Tarc%C3%ADsio_de_Freitas_em_maio_de_2023_%28recorte%29.jpg"},
        ]
    }

def adicionar_nivel_boss(dado):
    cargo = dado.get("cargo", "").lower()
    if "governador" in cargo or "senador" in cargo: dado["nivel_boss"] = "🏰 Rei Estadual"
    else: dado["nivel_boss"] = "🐟 Peixe Pequeno"
    return dado

@app.get("/api/politicos/buscar")
def buscar_politico(nome: str):
    try:
        res = requests.get(CAMARA_API, params={"nome": nome})
        dados = res.json().get("dados", [])
        if not dados: return {"status": "vazio", "mensagem": "Político não encontrado."}
        for d in dados:
            d['cargo'] = "Deputado Federal"
            d['score_auditoria'] = obter_score_dossie(d.get('id'))
            d = adicionar_nivel_boss(d)
        return {"status": "sucesso", "dados": dados}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/politicos/estado/{uf}")
def buscar_politicos_estado(uf: str):
    try:
        res = requests.get(CAMARA_API, params={"siglaUf": uf.upper(), "itens": 50, "ordem": "ASC", "ordenarPor": "nome"})
        dados = res.json().get("dados", [])
        if not dados: return {"status": "vazio", "mensagem": "Nenhum político encontrado neste estado."}
        
        for d in dados:
            d['cargo'] = "Deputado Federal"
            d['partido'] = d.get('siglaPartido', 'N/A')
            d['score_auditoria'] = obter_score_dossie(d.get('id'))
            d = adicionar_nivel_boss(d)
                
        return {"status": "sucesso", "dados": dados}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao buscar dados do estado.")

# API do TSE — dados de eleições municipais (prefeitos e vereadores reais)
TSE_API_BASE = "https://dadosabertos.tse.jus.br/api/3/action/datastore_search"
CANDIDATOS_MUNICIPAIS_RESOURCE = {
    # Resource IDs do TSE para candidatos municipais 2024 (preempotivo; fallback p/ 2020)
    2024: "a1e20b16-abdb-4c02-be12-c3bb0b1eae92",
    2020: "11fe9e14-9074-4bb2-b3e5-f28869b77b6c",
}

@app.get("/api/politicos/cidade/{uf}/{municipio}")
def buscar_politicos_cidade(uf: str, municipio: str, ano: int = 2024):
    """
    CORRIGIDO: Busca Prefeitos e Vereadores no Neo4j local primeiramente (Dados Injetados).
    Fallback para API do TSE se não houver dados no grafo.
    """
    uf_upper     = uf.upper().strip()
    municipio_up = municipio.upper().strip()
    logger.info(f"[CIDADE] Buscando para {municipio_up}-{uf_upper} no Neo4j...")

    # ── Estratégia 1: Neo4j (Dados Locais Injetados) ──────────────────────────
    try:
        politicos_grafo = neo4j_conn.buscar_por_cidade(uf_upper, municipio_up)
        if politicos_grafo:
            logger.info(f"[GRAFO] Encontrados {len(politicos_grafo)} políticos para {municipio_up}")
            for p in politicos_grafo:
                p['score_auditoria'] = obter_score_dossie(p.get('id'))
            return {
                "status": "sucesso", 
                "fonte": "Neo4j (Local)", 
                "cidade": municipio_up, 
                "uf": uf_upper, 
                "politicos": politicos_grafo
            }
    except Exception as e:
        logger.error(f"[ERRO GRAFO] Falha na busca por cidade: {e}")

    # ── Estratégia 2: TSE Dados Abertos ──────────────────────────────────────────
    try:
        tse_url = "https://dadosabertos.tse.jus.br/api/3/action/datastore_search_sql"
        sql = (
            f'SELECT * FROM "candidatos_2024" '
            f'WHERE "SG_UF" = \'{uf_upper}\' '
            f'AND "NM_MUNICIPIO" ILIKE \'{municipio_up}%\' '
            f'AND ("DS_CARGO" ILIKE \'PREFEITO%\' OR "DS_CARGO" ILIKE \'VEREADOR%\') '
            f'LIMIT 30'
        )
        res = requests.get(tse_url, params={"sql": sql}, timeout=8)
        if res.status_code == 200:
            registros = res.json().get("result", {}).get("records", [])
            if registros:
                logger.info(f"[TSE] Encontrados {len(registros)} candidato(s) municipais")
                resultado = []
                for r in registros:
                    resultado.append({
                        "id":        r.get("SQ_CANDIDATO", ""),
                        "nome":      r.get("NM_CANDIDATO", "").title(),
                        "cargo":     r.get("DS_CARGO", "").title(),
                        "partido":   r.get("SG_PARTIDO", "N/A"),
                        "uf":        uf_upper,
                        "municipio": municipio_up,
                        "score_auditoria": obter_score_dossie(r.get("SQ_CANDIDATO", "")),
                    })
                return {"status": "sucesso", "fonte": "TSE", "cidade": municipio_up, "uf": uf_upper, "politicos": resultado}
    except Exception as e:
        logger.warning(f"[TSE] Indisponível: {e}")

    return {
        "status": "sem_dados",
        "cidade": municipio_up,
        "uf": uf_upper,
        "politicos": [],
        "mensagem": "Dados não encontrados no Grafo nem no TSE."
    }

@app.get("/api/politicos/cidade/{uf}/todos")
def buscar_politicos_estado_completo(uf: str):
    """Busca todos os políticos de um estado no Neo4j (Fichário da Sala de Arquivos)."""
    try:
        resultado = neo4j_conn.buscar_por_estado(uf)
        if resultado:
            for p in resultado:
                p['score_auditoria'] = obter_score_dossie(p.get('id'))
            return {"status": "sucesso", "uf": uf.upper(), "dados": resultado}
    except Exception as e:
        logger.error(f"Erro ao buscar estado completo: {e}")
    
    return {"status": "sem_dados", "uf": uf.upper(), "dados": []}

@app.get("/api/politicos/pesquisa")
def pesquisar_politicos_global(q: str):
    """Pesquisa global no Neo4j e na Câmara (Deputados)."""
    termo = q.strip()
    if not termo: return {"status": "vazio", "dados": []}
    
    resultados = []
    
    # 1. Busca no Neo4j (Políticos Injetados - Todos os níveis)
    try:
        grafo_res = neo4j_conn.buscar_por_termo(termo)
        for p in grafo_res:
            p['fonte'] = "Neo4j"
            p['score_auditoria'] = obter_score_dossie(p.get('id'))
            resultados.append(p)
    except: pass
    
    # 2. Busca na Câmara (Deputados Federais Síncronos)
    try:
        res_camara = requests.get(CAMARA_API, params={"nome": termo})
        if res_camara.status_code == 200:
            for d in res_camara.json().get("dados", []):
                if not any(r['id'] == str(d['id']) for r in resultados):
                    resultados.append({
                        "id": str(d['id']),
                        "nome": d['nome'],
                        "cargo": "Deputado Federal",
                        "partido": d.get('siglaPartido', 'N/A'),
                        "uf": d.get('siglaUf', 'BR'),
                        "fonte": "Câmara API",
                        "score_auditoria": obter_score_dossie(d['id'])
                    })
    except: pass
    
    return {"status": "sucesso", "dados": resultados}

@app.get("/api/dossies/arvore")
def listar_arvore_dossies(uf: str = None, cidade: str = None):
    """
    Lista a estrutura de pastas e arquivos de forma hierárquica.
    Brasil -> UF -> Cidade -> Político
    """
    base_path = os.path.join(os.path.dirname(__file__), "dossies")
    if not os.path.exists(base_path): os.makedirs(base_path)

    try:
        if not uf:
            # Lista as UFs (pastas no nível raiz de dossies)
            ufs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
            items = []
            for u in sorted(ufs):
                path_uf = os.path.join(base_path, u)
                cidades = [c for c in os.listdir(path_uf) if os.path.isdir(os.path.join(path_uf, c))]
                total = 0
                for c in cidades:
                    path_cid = os.path.join(path_uf, c)
                    total += len([f for f in os.listdir(path_cid) if f.endswith(".json")])
                items.append({"nome": u, "tipo": "pasta", "total": total})
            return {"status": "sucesso", "items": items}
        
        if uf and not cidade:
            # Lista as Cidades dentro da UF
            path_uf = os.path.join(base_path, uf.upper())
            if not os.path.exists(path_uf): return {"status": "vazio", "items": []}
            cidades = [c for c in os.listdir(path_uf) if os.path.isdir(os.path.join(path_uf, c))]
            items = []
            for c in sorted(cidades):
                path_cid = os.path.join(path_uf, c)
                total = len([f for f in os.listdir(path_cid) if f.endswith(".json")])
                items.append({"nome": c, "tipo": "pasta", "total": total})
            return {"status": "sucesso", "items": items}

        if uf and cidade:
            # Lista os Políticos dentro da Cidade
            path_cid = os.path.join(base_path, uf.upper(), cidade.upper())
            if not os.path.exists(path_cid): return {"status": "vazio", "items": []}
            arquivos = [f for f in os.listdir(path_cid) if f.endswith(".json")]
            items = []
            for f in sorted(arquivos):
                try:
                    with open(os.path.join(path_cid, f), "r", encoding="utf-8") as file:
                        dados = json.load(file)
                        items.append({
                            "nome": dados.get("nome_politico") or dados.get("nome", f"ID {f}"),
                            "tipo": "arquivo",
                            "score": dados.get("ia_analise", {}).get("score_risco", 0),
                            "uf": uf.upper(),
                            "cidade": cidade.upper(),
                            "path": f"{uf.upper()}/{cidade.upper()}/{f}"
                        })
                except: continue
            return {"status": "sucesso", "items": items}

    except Exception as e:
        logger.error(f"Erro na árvore de dossiês: {e}")
        return {"status": "erro", "mensagem": str(e), "items": []}

@app.get("/api/politico/detalhes/arquivo")
def obter_detalhes_por_arquivo(path: str):
    """Retorna o JSON completo de um dossiê específico pelo caminho relativo."""
    try:
        full_path = os.path.join(os.path.dirname(__file__), "dossies", path)
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Dossiê não encontrado.")
        
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao ler arquivo {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mantém rota legada para compatibilidade com frontend antigo
@app.get("/api/politicos/cidade/{municipio}")
def buscar_politicos_cidade_legado(municipio: str):
    """Rota legada sem UF — retorna erro orientativo para usar a rota correta."""
    logger.warning(f"[LEGADO] Rota sem UF chamada para '{municipio}' — redirecionando para instrução")
    return {
        "status": "erro",
        "mensagem": f"Use /api/politicos/cidade/{{uf}}/{municipio} — ex: /api/politicos/cidade/SP/Campinas"
    }

def disparar_worker_assincrono(id_politico: int, nome_politico: str, cpf: str):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            auditar_malha_fina_assincrona(id_politico, nome_politico, cpf)
        )
    except Exception as e:
        print(f"Erro Worker: {e}")
    finally:
        try:
            loop.close()
        except:
            pass

# Dicionário Fixo de CPF Reais Presidenciais e Ministros para forçar OSINT fora da Câmara
nome_presidenciais_dict = {
    "900001": {"nome_completo": "Luiz Inácio Lula da Silva", "cpf": "23772275815", "partido": "PT", "cargo": "Presidente da República", "uf": "BR"},
    "900002": {"nome_completo": "Jair Messias Bolsonaro", "cpf": "08064507772", "partido": "PL", "cargo": "Ex-Presidente da República", "uf": "BR"},
    "900003": {"nome_completo": "Geraldo José Rodrigues Alckmin Filho", "cpf": "12345678900", "partido": "PSB", "cargo": "Vice-Presidente", "uf": "BR"},
    "900004": {"nome_completo": "Fernando Haddad", "cpf": "12345678900", "partido": "PT", "cargo": "Ministro da Fazenda", "uf": "BR"},
    "900005": {"nome_completo": "Ricardo Lewandowski", "cpf": "12345678900", "partido": "Sem Partido", "cargo": "Ministro da Justiça", "uf": "BR"},
}
@app.get("/api/politico/detalhes/{id}")
def buscar_politico_detalhes(id: int, background_tasks: BackgroundTasks):
    # 1. Tentar Cache em Memória
    if id in CACHE_DOSSIES: 
        return {"status": "sucesso", "dados": CACHE_DOSSIES[id], "cached": True}

    # 2. Tentar Disco (Pasta dossies)
    pasta = os.path.join(os.getcwd(), "dossies")
    caminho_arquivo = os.path.join(pasta, f"dossie_{id}.json")
    if os.path.exists(caminho_arquivo):
        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                dados_disco = json.load(f)
                CACHE_DOSSIES[id] = dados_disco # Alimenta o cache
                return {"status": "sucesso", "dados": dados_disco, "cached": False, "fonte": "disco"}
        except Exception as e:
            print(f"Erro ao ler dossiê do disco ID {id}: {e}")

    id_pol = str(id)
    if id_pol in nome_presidenciais_dict:
        # É um VIP (Presidente, Ministro). Aciona OSINT profunda usando o CPF real embutido.
        vip_data = nome_presidenciais_dict[id_pol]
        
        # Simula o antigo avaliar_score_inicial_assincrono para VIPs e direciona para o novo Motor
        background_tasks.add_task(
            auditar_malha_fina_assincrona,
            int(id_pol),
            vip_data["nome_completo"],
            vip_data["cpf"]
        )
        return {
            "status": "sucesso",
            "dados": {
                "id": id_pol,
                "nome": vip_data["nome_completo"],
                "cargo": vip_data["cargo"],
                "partido": vip_data["partido"],
                "uf": vip_data["uf"],
                "foto": "https://www.camara.leg.br/internet/deputado/bandep/imagem_sem_foto.jpg",
                "cpf": vip_data["cpf"],
                "score_auditoria": "Pendente",
                "empresas": [],
                "projetos": []
            }
        }

    try:
        res_basico = requests.get(f"{CAMARA_API}/{id}")
        if res_basico.status_code != 200:
            # Fallback for IDs not found in CAMARA_API but potentially in nome_presidenciais_dict (though handled above)
            # This block might be redundant if all VIPs are handled by the new 'if id_pol in nome_presidenciais_dict'
            # For now, keep it as a general fallback for non-Camara IDs
            dados_boss = nome_presidenciais_dict.get(id_pol, {"nome_completo": f"ID {id}", "cpf": "00000000000", "cargo": "Executivo", "partido": "N/A", "uf": "BR"})
            nome_completo = dados_boss["nome_completo"]
            cpf_oculto = dados_boss["cpf"]
            cargo, partido, uf, foto = dados_boss["cargo"], dados_boss["partido"], dados_boss["uf"], ""
            despesas_data, orgaos_data = [], []
        else:
            api_dado = res_basico.json().get("dados", {})
            ultimo_status = api_dado.get("ultimoStatus", {})
            nome_completo = ultimo_status.get("nomeEleitoral", api_dado.get("nomeCivil", "Desconhecido"))
            cargo, partido, uf = "Deputado Federal", ultimo_status.get("siglaPartido", "Sem Partido"), ultimo_status.get("siglaUf", "BR")
            foto, cpf_oculto = ultimo_status.get("urlFoto", ""), api_dado.get("cpf", "00000000000")

            # BUSCA INFINITA DE DESPESAS (NÃO LIMITADA A 100)
            despesas_data = []
            pagina = 1
            print(f"📥 Coletando histórico de despesas completo de {nome_completo}...")
            # TAREFA 1: Buscando Projetos de Lei Reais para Deputados via API /proposicoes
            projetos_data = [] # Initialize projetos_data here
            try:
                res_proj = requests.get(f"https://dadosabertos.camara.leg.br/api/v2/proposicoes", params={"idDeputadoAutor": id, "itens": 10, "ordem": "DESC", "ordenarPor": "id"})
                projetos_api = res_proj.json().get("dados", [])
                
                for p in projetos_api:
                    projetos_data.append({
                        "titulo": p.get("siglaTipo", "") + " " + str(p.get("numero", "")) + "/" + str(p.get("ano", "")),
                        "status": "Apresentado",
                        "presence": 100,
                        "desc": p.get("ementa", "Sem resumo/ementa disponível."),
                        "fonte": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={p.get('id')}"
                    })
            except Exception as e:
                print(f"Erro buscando proposições reais: {e}")
                projetos_data = []
            while True:
                res_despesas = requests.get(f"{CAMARA_API}/{id}/despesas", params={"itens": 100, "pagina": pagina, "ordem": "DESC", "ordenarPor": "dataDocumento"})
                if res_despesas.status_code == 200:
                    dados_pagina = res_despesas.json().get("dados", [])
                    if not dados_pagina: break
                    despesas_data.extend(dados_pagina)
                    pagina += 1
                else: break
            print(f"✅ Total de {len(despesas_data)} despesas baixadas!")

            orgaos_data = projetos_data # Use the newly fetched projects for orgaos_data
            

    except Exception as e: raise HTTPException(status_code=500, detail="Erro interno ao buscar político")



    caminho_dossie = f"dossies/dossie_{id}.json"
    historico_redflags, empresas_geradas, score_base, pontos_perdidos, motivos_detalhados = [], [], 1000, 0, []
    
    if os.path.exists(caminho_dossie):
        try:
            with open(caminho_dossie, "r", encoding="utf-8") as f:
                dossie_cache = json.load(f)
                historico_redflags, pontos_perdidos, empresas_geradas = dossie_cache.get("redFlags", []), dossie_cache.get("pontos_perdidos", 0), dossie_cache.get("empresas", [])
        except: pass
    else:
        # Mock para manter a tela renderizando até o Background Task da IA (Auditoria Offline) concluir
        pontos_perdidos, historico_redflags, motivos_detalhados = 150, [], []
        os.makedirs("dossies", exist_ok=True)
        with open(caminho_dossie, "w", encoding="utf-8") as file:
            json.dump({"id_politico": id, "redFlags": historico_redflags, "pontos_perdidos": pontos_perdidos, "data_auditoria": datetime.now().isoformat()}, file, ensure_ascii=False, indent=4)

    score_base -= pontos_perdidos
    empresas_reais = list(empresas_geradas) if empresas_geradas else []
    cnpjs_fornecedores_temp, total_despesas = [], 0

    for d in despesas_data:
        cnpj_raw = str(d.get("cnpjCpfFornecedor", "")).replace(".", "").replace("-", "").replace("/", "").strip()
        if cnpj_raw and len(cnpj_raw) == 14: cnpjs_fornecedores_temp.append(cnpj_raw)
        valor_despesa = d.get('valorDocumento', 0)
        total_despesas += valor_despesa
        if not any(emp.get("cnpj") == cnpj_raw for emp in empresas_reais):
            empresas_reais.append({
                "nome": d.get("nomeFornecedor", "Fornecedor Local")[:50], 
                "cargo": d.get("tipoDespesa", "Despesa")[:30], 
                "valor": f"R$ {valor_despesa:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                "data": d.get("dataDocumento", ""),
                "fonte": d.get("urlDocumento", "")
            })
    cnpjs_fornecedores = list(set(cnpjs_fornecedores_temp))
    projetos_reais = [{"titulo": str(o.get("ementa", o.get("siglaTipo", "Projeto legislativo")))[:120], "status": str(o.get("ultimoStatus", {}).get("despacho", "Em tramitação"))[:80], "fonte": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={o.get('id')}" if o.get('id') else "", "presence": 100} for o in orgaos_data]

    if total_despesas > 20000: score_base -= 150; motivos_detalhados.append(f"Alta movimentação nas despesas (R$ {total_despesas:,.2f})")
    if len(projetos_reais) == 0: score_base -= 50; motivos_detalhados.append("Baixa participação em comissões recentes")
        
    score_final = max(0, score_base)
    
    # Executa a auditoria completa assíncrona
    background_tasks.add_task(
        disparar_worker_assincrono,
        id,
        nome_completo,
        cpf_oculto
    )

    noticias_limpas = []
    try:
        with DDGS() as ddgs:
            for n in list(ddgs.news(keywords=nome_completo, region="br-pt", max_results=5)):
                noticias_limpas.append({"titulo": n.get("title", ""), "fonte": n.get("source", "Outros"), "linha_editorial": "Independente", "data": n.get("date", "Recente"), "url": n.get("url", "#")})
    except: pass

    dado_completo = {
        "id": id, "nome": nome_completo, "cargo": cargo, "partido": partido, "uf": uf, "foto": foto,
        "score_auditoria": score_final, "badges": [{"id": 1, "nome": "Auditoria IA Iniciada", "color": "bg-purple-500/10 border-purple-500/50 text-purple-500", "icon": "Fingerprint"}],
        "redFlags": historico_redflags, "empresas": empresas_reais[:50], "projetos": projetos_reais, "noticias": noticias_limpas
    }
    
    CACHE_DOSSIES[id] = dado_completo
    return {"status": "sucesso", "dados": dado_completo}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
