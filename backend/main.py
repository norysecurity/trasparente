import requests
import uvicorn
import asyncio
import os
import json
from datetime import datetime
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path)

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from duckduckgo_search import DDGS

from agente_coletor_autonomo import avaliar_score_inicial_sincrono, auditar_malha_fina_assincrona

app = FastAPI(title="GovTech Transparência API")

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
        "top10": [
            {"nome": "Bolsonaro", "partido": "PL", "estado": "RJ", "score": 850, "foto": "https://www.camara.leg.br/internet/deputado/bandep/74847.jpg"},
            {"nome": "Lula", "partido": "PT", "estado": "SP", "score": 820, "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Presidente_Luiz_In%C3%A1cio_Lula_da_Silva_em_2023.jpg/800px-Presidente_Luiz_In%C3%A1cio_Lula_da_Silva_em_2023.jpg"},
            {"nome": "Flávio Dino", "partido": "STF", "estado": "MA", "score": 790, "foto": "https://upload.wikimedia.org/wikipedia/commons/b/b8/Fl%C3%A1vio_Dino_em_2023.jpg"}
        ],
        "feed": [
            {"alvo": "Eduardo Bolsonaro", "acao": "Gastou R$ 45.000 em Dubai sem agenda oficial.", "impacto": -80, "fonte": "CGU", "tempo": "10 min atrás"},
            {"alvo": "Gleisi Hoffmann", "acao": "Omitiu R$ 1.2M do patrimônio do TSE.", "impacto": -120, "fonte": "TSE", "tempo": "1h atrás"},
            {"alvo": "Tarcísio Gomes", "acao": "Rede ligada ao PCC venceu licitação da CPTM.", "impacto": -150, "fonte": "TCE-SP", "tempo": "2h atrás"}
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
        res = requests.get(CAMARA_API, params={"siglaUf": uf.upper(), "itens": 50})
        dados = res.json().get("dados", [])
        if not dados: return {"status": "vazio", "mensagem": "Nenhum político encontrado neste estado."}
        
        for d in dados:
            d['cargo'] = "Deputado Federal"
            d['score_auditoria'] = obter_score_dossie(d.get('id'))
            d = adicionar_nivel_boss(d)
                
        return {"status": "sucesso", "dados": dados}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao buscar dados do estado.")

@app.get("/api/politicos/cidade/{municipio}")
def buscar_politicos_cidade(municipio: str):
    import random
    nome_mun = municipio.title()
    politicos_mock = [
        {"id": 800001, "nome": f"Prefeito de {nome_mun}", "cargo": "Prefeito", "partido": "MDB", "score_auditoria": random.randint(300, 900), "uf": "BR"},
        {"id": 800002, "nome": f"João das Neves", "cargo": "Vereador", "partido": "PL", "score_auditoria": random.randint(300, 900), "uf": "BR"},
        {"id": 800003, "nome": f"Maria do Bairro", "cargo": "Vereador", "partido": "PT", "score_auditoria": random.randint(300, 900), "uf": "BR"},
        {"id": 800004, "nome": f"José Rico", "cargo": "Vereador", "partido": "UNIÃO", "score_auditoria": random.randint(300, 900), "uf": "BR"},
        {"id": 800005, "nome": f"Ana Clara", "cargo": "Vereador", "partido": "PSDB", "score_auditoria": random.randint(300, 900), "uf": "BR"},
        {"id": 800006, "nome": f"Carlos Magno", "cargo": "Vereador", "partido": "PP", "score_auditoria": random.randint(300, 900), "uf": "BR"}
    ]
    return {"status": "sucesso", "cidade": nome_mun, "politicos": politicos_mock}

def disparar_worker_assincrono(id_politico: int, nome_politico: str, cpf: str, cnpjs_fornecedores: list, red_flags: list, pts_perdidos: int, despesas_brutas: list):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(auditar_malha_fina_assincrona(id_politico, nome_politico, cpf, cnpjs_fornecedores, red_flags, pts_perdidos, despesas_brutas))
    except Exception as e: print(f"Erro Worker: {e}")
    finally:
        try: loop.close()
        except: pass

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
    if id in CACHE_DOSSIES: return {"status": "sucesso", "dados": CACHE_DOSSIES[id], "cached": True}

    id_pol = str(id)
    if id_pol in nome_presidenciais_dict:
        # É um VIP (Presidente, Ministro). Aciona OSINT profunda usando o CPF real embutido.
        vip_data = nome_presidenciais_dict[id_pol]
        background_tasks.add_task(
            avaliar_score_inicial_assincrono,
            id_pol,
            vip_data["nome_completo"],
            vip_data["cpf"], # ENVIA O CPF REAL! Isso liga o motor de buscas de CGU para esse CPF!
            [], # Sem despesas da camara
            {}, # Sem dados completos da camara
            []  # Sem projetos da camara
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

@app.get("/api/dashboard/guerra")
def dashboard_guerra():
    """Retorna os dados pro FEED de corrupção simulando o motor OSINT"""
    return {
        "status": "sucesso",
        "alertas_recentes": [
            {"id": 1, "mensagem": "Licitação suspeita encontrada em MG", "urgencia": "ALTA", "tempo": "Há 10 min"},
            {"id": 2, "mensagem": "Movimentação atípica no CPF de Senador X", "urgencia": "MÉDIA", "tempo": "Há 45 min"},
            {"id": 3, "mensagem": "Cruzamento de CNPJs aponta Laranja em SP", "urgencia": "ALTA", "tempo": "Há 1 hora"},
            {"id": 4, "mensagem": "Nova Red Flag: Processo Ambiental Ativo", "urgencia": "MÉDIA", "tempo": "Há 2 horas"},
            {"id": 5, "mensagem": "Alerta de Voo Privado sem registro na FAB", "urgencia": "BAIXA", "tempo": "Há 5 horas"}
        ],
        "top_risco": [
            {"nome": "Deputado A", "score": 210},
            {"nome": "Senador B", "score": 250},
            {"nome": "Assessor C", "score": 280},
            {"nome": "Ex-Ministro D", "score": 310},
            {"nome": "Prefeito E", "score": 340}
        ]
    }

    caminho_dossie = f"dossies/dossie_{id}.json"
    historico_redflags, empresas_geradas, score_base, pontos_perdidos, motivos_detalhados = [], [], 1000, 0, []
    
    if os.path.exists(caminho_dossie):
        try:
            with open(caminho_dossie, "r", encoding="utf-8") as f:
                dossie_cache = json.load(f)
                historico_redflags, pontos_perdidos, empresas_geradas = dossie_cache.get("redFlags", []), dossie_cache.get("pontos_perdidos", 0), dossie_cache.get("empresas", [])
        except: pass
    else:
        pontos_perdidos, historico_redflags, motivos_detalhados = avaliar_score_inicial_sincrono(nome_completo)
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
    
    # Executa a auditoria completa assíncrona (Apenas pega os 1000 primeiros gastos na IA para não explodir tokens, mas salva tudo)
    background_tasks.add_task(disparar_worker_assincrono, id, nome_completo, cpf_oculto, cnpjs_fornecedores, historico_redflags, pontos_perdidos, despesas_data)

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
