import requests
import uvicorn
import asyncio
import random
import os
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from agente_coletor_autonomo import auditar_malha_fina
from duckduckgo_search import DDGS

app = FastAPI(title="GovTech Transparência API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2/deputados"

CACHE_POLITICOS = {}

def obter_score_dossie(id_politico):
    caminho = f"dossies/dossie_{id_politico}.json"
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dossie = json.load(f)
                return max(0, 1000 - dossie.get("pontos_perdidos", 0))
        except:
            pass
    return "Pendente"

# Mapeamento de Fontes: Nomenclatura Editorial Neutra/Acadêmica
MAPA_LINHA_EDITORIAL = {
    # Mídia Progressista (Antiga Esquerda)
    "CartaCapital": "Progressista",
    "Brasil 247": "Progressista",
    "Revista Fórum": "Progressista",
    "DCM": "Progressista",
    "Diário do Centro do Mundo": "Progressista",
    "Intercept Brasil": "Progressista",
    "Agência Pública": "Progressista",
    "Opera Mundi": "Progressista",

    # Mídia Conservadora (Antiga Direita)
    "Jovem Pan": "Conservadora",
    "Gazeta do Povo": "Conservadora",
    "Revista Oeste": "Conservadora",
    "O Antagonista": "Conservadora",
    "Pleno.News": "Conservadora",
    "Conexão Política": "Conservadora",
    "Terra Brasil Notícias": "Conservadora",

    # Mídia Institucional / Corporativa (Antigo Centro)
    "G1": "Institucional",
    "UOL": "Institucional",
    "Folha de S.Paulo": "Institucional",
    "O Estado de S. Paulo": "Institucional",
    "Estadão": "Institucional",
    "O Globo": "Institucional",
    "CNN Brasil": "Institucional",
    "Veja": "Institucional",
    "Metrópoles": "Institucional",
    "Poder360": "Institucional",
    "BBC Brasil": "Institucional"
}

@app.get("/api/executivo")
def obter_executivo():
    return {
        "presidente": {"nome": "Luiz Inácio Lula da Silva", "cargo": "Presidente da República", "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Foto_Oficial_de_Luiz_In%C3%A1cio_Lula_da_Silva_como_Presidente_da_Rep%C3%BAblica_em_2023.jpg/800px-Foto_Oficial_de_Luiz_In%C3%A1cio_Lula_da_Silva_como_Presidente_da_Rep%C3%BAblica_em_2023.jpg", "partido": "PT"},
        "vice": {"nome": "Geraldo Alckmin", "cargo": "Vice-Presidente", "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/Geraldo_Alckmin_em_2023.jpg/800px-Geraldo_Alckmin_em_2023.jpg", "partido": "PSB"}
    }

@app.get("/api/eleicoes2026/presidenciais")
def buscar_presidenciais():
    candidatos = [
        {
            "id": 900001,
            "nome": "Luiz Inácio Lula da Silva",
            "cargo": "Presidente",
            "siglaPartido": "PT",
            "siglaUf": "BR",
            "urlFoto": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Foto_Oficial_de_Luiz_In%C3%A1cio_Lula_da_Silva_como_Presidente_da_Rep%C3%BAblica_em_2023.jpg/800px-Foto_Oficial_de_Luiz_In%C3%A1cio_Lula_da_Silva_como_Presidente_da_Rep%C3%BAblica_em_2023.jpg",
            "nivel_boss": "👑 Chefão Supremo",
            "score_auditoria": obter_score_dossie(900001)
        },
        {
            "id": 900002,
            "nome": "Tarcísio de Freitas",
            "cargo": "Governador SP",
            "siglaPartido": "REP",
            "siglaUf": "SP",
            "urlFoto": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Tarc%C3%ADsio_Gomes_de_Freitas.jpg/800px-Tarc%C3%ADsio_Gomes_de_Freitas.jpg",
            "nivel_boss": "👑 Chefão Supremo",
            "score_auditoria": obter_score_dossie(900002)
        },
        {
            "id": 900003,
            "nome": "Romeu Zema",
            "cargo": "Governador MG",
            "siglaPartido": "NOVO",
            "siglaUf": "MG",
            "urlFoto": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Romeu_Zema_Governador_do_Estado_de_Minas_Gerais_-_foto_Pedro_Gontijo.jpg/800px-Romeu_Zema_Governador_do_Estado_de_Minas_Gerais_-_foto_Pedro_Gontijo.jpg",
            "nivel_boss": "👑 Chefão Supremo",
            "score_auditoria": obter_score_dossie(900003)
        },
        {
            "id": 900004,
            "nome": "Ronaldo Caiado",
            "cargo": "Governador GO",
            "siglaPartido": "UB",
            "siglaUf": "GO",
            "urlFoto": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Ronaldo_Caiado%2C_Governador_do_Estado_de_Goi%C3%A1s.png/800px-Ronaldo_Caiado%2C_Governador_do_Estado_de_Goi%C3%A1s.png",
            "nivel_boss": "👑 Chefão Supremo",
            "score_auditoria": obter_score_dossie(900004)
        }
    ]
    return {"status": "sucesso", "dados": candidatos}

def adicionar_nivel_boss(dado):
    cargo = dado.get("cargo", "").lower()
    if "governador" in cargo or "senador" in cargo:
        dado["nivel_boss"] = "🏰 Rei Estadual"
    else:
        dado["nivel_boss"] = "🐟 Peixe Pequeno"
    return dado

@app.get("/api/politicos/estado/{uf}")
def buscar_por_estado(uf: str):
    try:
        res = requests.get(CAMARA_API, params={"siglaUf": uf.upper(), "itens": 100, "ordem": "ASC", "ordenarPor": "nome"})
        res.raise_for_status()
        dados = res.json().get("dados", [])
        
        resultados = []
        for d in dados:
            d['cargo'] = "Deputado Federal"
            d['score_auditoria'] = obter_score_dossie(d.get('id'))
            d = adicionar_nivel_boss(d)
            resultados.append(d)
            
        return {"status": "sucesso", "dados": resultados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/politicos/buscar")
def buscar_politico(nome: str):
    try:
        res = requests.get(CAMARA_API, params={"nome": nome})
        res.raise_for_status()
        dados = res.json().get("dados", [])
        if not dados:
            return {"status": "vazio", "mensagem": "Político não encontrado nas bases."}
        
        for d in dados:
            d['cargo'] = "Deputado Federal"
            d['score_auditoria'] = obter_score_dossie(d.get('id'))
            d = adicionar_nivel_boss(d)
            
        return {"status": "sucesso", "dados": dados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def disparar_worker_assincrono(id_politico: int, nome_politico: str, cpf: str, cnpjs_suspeitos: list):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(auditar_malha_fina(id_politico, nome_politico, cpf, cnpjs_suspeitos))
    except Exception as e:
        print(f"Erro no Worker Síncrono: {e}")

@app.get("/api/politico/detalhes/{id}")
def buscar_politico_detalhes(id: int, background_tasks: BackgroundTasks):
    if id in CACHE_POLITICOS:
        dado_cache = CACHE_POLITICOS[id]
        score_atual = obter_score_dossie(id)
        if score_atual != "Pendente":
            dado_cache["score_auditoria"] = score_atual
            
        return {"status": "sucesso", "dados": dado_cache, "cached": True}

    # Se for um ID simulado de Presidenciável
    presidenciais_simulados = {
        900001: {"nome": "Luiz Inácio Lula da Silva", "cargo": "Presidente", "partido": "PT", "uf": "BR", "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Foto_Oficial_de_Luiz_In%C3%A1cio_Lula_da_Silva_como_Presidente_da_Rep%C3%BAblica_em_2023.jpg/800px-Foto_Oficial_de_Luiz_In%C3%A1cio_Lula_da_Silva_como_Presidente_da_Rep%C3%BAblica_em_2023.jpg"},
        900002: {"nome": "Tarcísio de Freitas", "cargo": "Governador SP", "partido": "REP", "uf": "SP", "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Tarc%C3%ADsio_Gomes_de_Freitas.jpg/800px-Tarc%C3%ADsio_Gomes_de_Freitas.jpg"},
        900003: {"nome": "Romeu Zema", "cargo": "Governador MG", "partido": "NOVO", "uf": "MG", "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Romeu_Zema_Governador_do_Estado_de_Minas_Gerais_-_foto_Pedro_Gontijo.jpg/800px-Romeu_Zema_Governador_do_Estado_de_Minas_Gerais_-_foto_Pedro_Gontijo.jpg"},
        900004: {"nome": "Ronaldo Caiado", "cargo": "Governador GO", "partido": "UB", "uf": "GO", "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Ronaldo_Caiado%2C_Governador_do_Estado_de_Goi%C3%A1s.png/800px-Ronaldo_Caiado%2C_Governador_do_Estado_de_Goi%C3%A1s.png"}
    }

    if id in presidenciais_simulados:
        dado_basico = presidenciais_simulados[id]
        nome_completo = dado_basico["nome"]
        cargo = dado_basico["cargo"]
        partido = dado_basico["partido"]
        uf = dado_basico["uf"]
        foto = dado_basico["foto"]
        cpf_oculto = "00000000000"
        
        # Simulando uma despesa para iniciar worker
        despesas_data = [{"cnpjCpfFornecedor": "00000000000191", "nomeFornecedor": "Governo Federal", "tipoDespesa": "Publicidade", "valorDocumento": 500000, "urlDocumento": "https://portaltransparencia.gov.br"}]
        orgaos_data = [{"nomeOrgao": "Gabinete do Executivo", "tituloAbreviado": "Titular"}]
    else:
        try:
            res_basico = requests.get(f"{CAMARA_API}/{id}")
            res_basico.raise_for_status()
            api_dado = res_basico.json().get("dados", {})
            
            ultimo_status = api_dado.get("ultimoStatus", {})
            nome_completo = ultimo_status.get("nomeEleitoral", api_dado.get("nomeCivil", "Desconhecido"))
            cargo = "Deputado Federal"
            partido = ultimo_status.get("siglaPartido", "Sem Partido")
            uf = ultimo_status.get("siglaUf", "BR")
            foto = ultimo_status.get("urlFoto", "")
            cpf_oculto = api_dado.get("cpf", "00000000000")

            res_despesas = requests.get(f"{CAMARA_API}/{id}/despesas", params={"itens": 100, "ordem": "DESC", "ordenarPor": "dataDocumento"})
            despesas_data = res_despesas.json().get("dados", []) if res_despesas.status_code == 200 else []

            res_orgaos = requests.get(f"{CAMARA_API}/{id}/orgaos", params={"itens": 5, "ordem": "DESC", "ordenarPor": "idOrgao"})
            orgaos_data = res_orgaos.json().get("dados", []) if res_orgaos.status_code == 200 else []
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    empresas_reais = []
    cnpjs_para_osint = []
    total_despesas = 0

    for d in despesas_data:
        cnpj_raw = str(d.get("cnpjCpfFornecedor", "")).replace(".", "").replace("-", "").replace("/", "").strip()
        if cnpj_raw and len(cnpj_raw) == 14:
            cnpjs_para_osint.append(cnpj_raw)

        valor_despesa = d.get('valorDocumento', 0)
        total_despesas += valor_despesa

        empresas_reais.append({
            "nome": d.get("nomeFornecedor", "Fornecedor"),
            "cargo": d.get("tipoDespesa", "Despesa"),
            "valor": f"R$ {valor_despesa:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            "fonte": d.get("urlDocumento", "")
        })

    projetos_reais = []
    for o in orgaos_data:
        projetos_reais.append({
            "titulo": o.get("nomeOrgao", "Comissão Federal"),
            "status": o.get("tituloAbreviado", "Titular"),
            "presence": 100
        })

    score_base = 1000
    motivos_deducao = []
    if total_despesas > 20000:
        score_base -= 150
        motivos_deducao.append(f"Alta movimentação nas últimas 5 despesas (R$ {total_despesas:,.2f})")
    
    if len(projetos_reais) == 0:
        score_base -= 50
        motivos_deducao.append("Baixa participação em comissões recentes")

    caminho_dossie = f"dossies/dossie_{id}.json"
    historico_redflags = []
    
    if os.path.exists(caminho_dossie):
        try:
            with open(caminho_dossie, "r", encoding="utf-8") as f:
                dossie_cache = json.load(f)
                historico_redflags = dossie_cache.get("redFlags", [])
                score_base -= dossie_cache.get("pontos_perdidos", 0)
                motivos_deducao.append(f"Alerta OSINT: {len(historico_redflags)} processos graves/notícias no STF/PF")
        except:
            pass

    score_final = max(0, score_base) if os.path.exists(caminho_dossie) else "Pendente"

    explicacao_score = "Comportamento dentro do padrão no histórico analisado."
    if motivos_deducao:
        explicacao_score = f"Deduções aplicadas: {', '.join(motivos_deducao)}."
    elif score_final == "Pendente":
        explicacao_score = "O Worker OSINT ainda está auditando este político. Aguarde."
    
    if cnpjs_para_osint:
        background_tasks.add_task(disparar_worker_assincrono, id, nome_completo, cpf_oculto, cnpjs_para_osint)
    else:
        background_tasks.add_task(disparar_worker_assincrono, id, nome_completo, cpf_oculto, [""])

    noticias_limpas = []
    try:
        noticias_brutas = DDGS().news(keywords=nome_completo, region="br-pt", max_results=5)
        if noticias_brutas:
            for n in noticias_brutas:
                fonte_raw = n.get("source", "Outros")
                linha_calc = "Independente/Outros"
                
                for k, v in MAPA_LINHA_EDITORIAL.items():
                    if k.lower() in fonte_raw.lower():
                        linha_calc = v
                        break
                        
                noticias_limpas.append({
                    "titulo": n.get("title", "Sem Título"),
                    "fonte": fonte_raw,
                    "linha_editorial": linha_calc,
                    "data": n.get("date", "Recente"),
                    "url": n.get("url", "#")
                })
    except Exception as e:
        print(f"Erro ao buscar noticias: {e}")

    dado_completo = {
        "id": id,
        "nome": nome_completo,
        "cargo": cargo,
        "partido": partido,
        "uf": uf,
        "foto": foto,
        "score_auditoria": score_final,
        "explicacao_score": explicacao_score,
        "badges": [
            {"id": 1, "nome": "Auditoria IA Iniciada", "color": "bg-purple-500/10 border-purple-500/50 text-purple-500", "icon": "Fingerprint"}
        ],
        "redFlags": historico_redflags,
        "empresas": empresas_reais,
        "projetos": projetos_reais,
        "noticias": noticias_limpas
    }
    
    CACHE_POLITICOS[id] = dado_completo
    return {"status": "sucesso", "dados": dado_completo}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
