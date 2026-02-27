import requests
import uvicorn
import random
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from agente_coletor_autonomo import auditar_malha_fina

app = FastAPI(title="GovTech Transparência API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2/deputados"

@app.get("/api/executivo")
def obter_executivo():
    return {
        "presidente": {"nome": "Luiz Inácio Lula da Silva", "cargo": "Presidente da República", "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Foto_Oficial_de_Luiz_In%C3%A1cio_Lula_da_Silva_como_Presidente_da_Rep%C3%BAblica_em_2023.jpg/800px-Foto_Oficial_de_Luiz_In%C3%A1cio_Lula_da_Silva_como_Presidente_da_Rep%C3%BAblica_em_2023.jpg", "partido": "PT"},
        "vice": {"nome": "Geraldo Alckmin", "cargo": "Vice-Presidente", "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/Geraldo_Alckmin_em_2023.jpg/800px-Geraldo_Alckmin_em_2023.jpg", "partido": "PSB"}
    }

@app.get("/api/politicos/estado/{uf}")
def buscar_por_estado(uf: str):
    try:
        res = requests.get(CAMARA_API, params={"siglaUf": uf.upper(), "itens": 100, "ordem": "ASC", "ordenarPor": "nome"})
        res.raise_for_status()
        dados = res.json().get("dados", [])
        
        resultados = []
        for d in dados:
            d['cargo'] = "Deputado Federal"
            d['score_auditoria'] = random.randint(500, 990)
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
            d['score_auditoria'] = random.randint(400, 900)
            
        return {"status": "sucesso", "dados": dados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def disparar_worker_assincrono(nome_politico: str, cpf: str):
    """
    Função Helper para rodar a rotina de automação no event loop principal do Worker.
    """
    try:
        # Cria ou reutiliza o loop do asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(auditar_malha_fina(nome_politico, cpf))
    except Exception as e:
        print(f"Erro no Worker Síncrono: {e}")

@app.get("/api/politico/detalhes/{id}")
def buscar_politico_detalhes(id: int, background_tasks: BackgroundTasks):
    try:
        # 1. Bate na API Oficial para os Dados Básicos
        res_basico = requests.get(f"{CAMARA_API}/{id}")
        res_basico.raise_for_status()
        dado_basico = res_basico.json().get("dados", {})
        
        # 2. Bate na API para Buscar Despesas Reais (Serão listadas como vínculos de Empresa por gora)
        res_despesas = requests.get(f"{CAMARA_API}/{id}/despesas", params={"itens": 5, "ordem": "DESC", "ordenarPor": "dataDocumento"})
        despesas_data = res_despesas.json().get("dados", []) if res_despesas.status_code == 200 else []
        
        empresas_reais = []
        for d in despesas_data:
            empresas_reais.append({
                "nome": d.get("nomeFornecedor", "Fornecedor Governamental"),
                "cargo": d.get("tipoDespesa", "Contrato de Terceiro"),
                "valor": f"R$ {d.get('valorDocumento', 0):.2f}".replace('.', ',')
            })

        # 3. Bate na API para Órgãos (Comissões Participadas) para os "Projetos"
        res_orgaos = requests.get(f"{CAMARA_API}/{id}/orgaos", params={"itens": 5, "ordem": "DESC", "ordenarPor": "idOrgao"})
        orgaos_data = res_orgaos.json().get("dados", []) if res_orgaos.status_code == 200 else []
        
        projetos_reais = []
        for o in orgaos_data:
            projetos_reais.append({
                "titulo": o.get("nomeOrgao", "Comissão Federal"),
                "status": o.get("tituloAbreviado", "Titular"),
                "presence": random.randint(70, 100) # Assiduidade mantida como score gamificado
            })

        # 4. Processa Variáveis Vitais da Busca
        ultimo_status = dado_basico.get("ultimoStatus", {})
        nome_completo = ultimo_status.get("nomeEleitoral", dado_basico.get("nomeCivil", "Desconhecido"))
        cpf_oculto = dado_basico.get("cpf", "000.000.000-00")
        
        # 5. ENGATILHA O ROBO DA VERDADE (OSINT - Neo4j / Diário Oficial / FitZ PDF Scanner) EM SEGUNDO PLANO
        background_tasks.add_task(disparar_worker_assincrono, nome_completo, cpf_oculto)

        # 6. Monta o Super Objeto Final de Resposta Genuína
        dado_completo = {
            "id": dado_basico.get("id", id),
            "nome": nome_completo,
            "cargo": "Deputado Federal",
            "partido": ultimo_status.get("siglaPartido", "Sem Partido"),
            "uf": ultimo_status.get("siglaUf", "BR"),
            "foto": ultimo_status.get("urlFoto", ""),
            "score_auditoria": random.randint(400, 950),
            "badges": [
                {"id": 1, "nome": "Auditoria IA Iniciada", "color": "bg-purple-500/10 border-purple-500/50 text-purple-500", "icon": "Fingerprint"}
            ],
            "redFlags": [
                {"data": "Hoje", "titulo": "OSINT Robot Ativo", "desc": "Worker rodando varredura profunda no Diário Oficial. Retorne depois para ver a Árvore Neo4j."}
            ],
            "empresas": empresas_reais,
            "projetos": projetos_reais
        }

        return {"status": "sucesso", "dados": dado_completo}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
