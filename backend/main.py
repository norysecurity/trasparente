from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import uvicorn

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
        "presidente": {
            "nome": "Luiz Inácio Lula da Silva", 
            "cargo": "Presidente da República", 
            "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Foto_Oficial_de_Luiz_In%C3%A1cio_Lula_da_Silva_como_Presidente_da_Rep%C3%BAblica_em_2023.jpg/800px-Foto_Oficial_de_Luiz_In%C3%A1cio_Lula_da_Silva_como_Presidente_da_Rep%C3%BAblica_em_2023.jpg", 
            "partido": "PT"
        },
        "vice": {
            "nome": "Geraldo Alckmin", 
            "cargo": "Vice-Presidente", 
            "foto": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/Geraldo_Alckmin_em_2023.jpg/800px-Geraldo_Alckmin_em_2023.jpg", 
            "partido": "PSB"
        }
    }

@app.get("/api/politicos/estado/{uf}")
def buscar_por_estado(uf: str):
    try:
        res = requests.get(CAMARA_API, params={"siglaUf": uf.upper(), "itens": 10, "ordem": "ASC", "ordenarPor": "nome"})
        res.raise_for_status()
        dados = res.json().get("dados", [])
        # Mockando scores para a interface gamificada
        for d in dados:
            d['score_auditoria'] = 1000 - (dados.index(d) * 50) 
        return {"status": "sucesso", "dados": dados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/politicos/buscar")
def buscar_politico(nome: str = None, cargo: str = None):
    try:
        params = {}
        if nome: params["nome"] = nome
        res = requests.get(CAMARA_API, params=params)
        res.raise_for_status()
        dados = res.json().get("dados", [])
        if not dados:
            return {"status": "vazio", "mensagem": "Político não encontrado nas bases."}
        for d in dados:
            d['score_auditoria'] = 850
        return {"status": "sucesso", "dados": dados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
