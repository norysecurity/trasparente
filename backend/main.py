import requests
import uvicorn
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
        # Injetar um Governador e Senador simulados para testar os filtros de UI
        resultados.append({
            "id": 999991, "nome": f"Governador de {uf.upper()}", "siglaPartido": "NOVO", "siglaUf": uf.upper(),
            "urlFoto": "", "cargo": "Governador", "score_auditoria": random.randint(600, 950)
        })
        resultados.append({
            "id": 999992, "nome": f"Senador de {uf.upper()}", "siglaPartido": "PL", "siglaUf": uf.upper(),
            "urlFoto": "", "cargo": "Senador", "score_auditoria": random.randint(400, 800)
        })

        for d in dados:
            d['cargo'] = "Deputado Federal"
            # Simular um score realista (Se for Aécio Neves, força um score baixo para teste)
            if "Aécio" in d['nome']:
                d['score_auditoria'] = 350
            else:
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

@app.get("/api/politico/detalhes/{id}")
def buscar_politico_detalhes(id: int):
    try:
        # Busca detalhes basilares
        res = requests.get(f"{CAMARA_API}/{id}")
        res.raise_for_status()
        dado_basico = res.json().get("dados", {})
        
        # Simula Busca Avançada (como as funções OSINT do Neo4j que criamos no Worker que não tem API ainda)
        dado_completo = {
            "id": dado_basico.get("id", id),
            "nome": dado_basico.get("ultimoStatus", {}).get("nomeEleitoral", dado_basico.get("nomeCivil", "Desconhecido")),
            "cargo": "Deputado Federal",
            "partido": dado_basico.get("ultimoStatus", {}).get("siglaPartido", "S/P"),
            "uf": dado_basico.get("ultimoStatus", {}).get("siglaUf", "BR"),
            "foto": dado_basico.get("ultimoStatus", {}).get("urlFoto", ""),
            "score_auditoria": 350 if "Aécio" in dado_basico.get("ultimoStatus", {}).get("nomeEleitoral", "") else random.randint(400, 980),
            "badges": [
                {"id": 1, "nome": "Investigado", "color": "bg-red-500/10 border-red-500/50 text-red-500", "icon": "ShieldAlert"},
                {"id": 2, "nome": "Teto de Gastos Violado", "color": "bg-orange-500/10 border-orange-500/50 text-orange-500", "icon": "Banknote"}
            ],
            "redFlags": [
                {"data": "2023", "titulo": "Licitações Suspeitas", "desc": "Empresas ligadas a parentes com contratos públicos."}
            ],
            "empresas": [
                {"nome": "Empresa Fictícia Limpeza", "cargo": "Associação Familiar", "valor": "R$ 5.400.000,00"}
            ],
            "projetos": [
                 {"titulo": "PEC do Teto", "status": "Aprovado", "presence": 85}
            ]
        }
        
        # Corrige score baseado no ID Mock de prefeitos
        if id == 999991:
             dado_completo["nome"] = "Governador Simulado"
             dado_completo["cargo"] = "Governador"
        elif id == 999992:
             dado_completo["nome"] = "Senador Simulado"
             dado_completo["cargo"] = "Senador"

        return {"status": "sucesso", "dados": dado_completo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
