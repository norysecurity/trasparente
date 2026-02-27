import os
import requests
import asyncio
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (Chaves de API)
load_dotenv()
CGU_API_KEY = os.getenv("CGU_API_KEY")

async def buscar_deputado_camara(nome_busca: str) -> dict:
    """
    Faz uma requisição REAL à API de Dados Abertos da Câmara dos Deputados.
    """
    url = "https://dadosabertos.camara.leg.br/api/v2/deputados"
    try:
        # Faz a busca pelo nome passado na barra de pesquisa
        resposta = requests.get(url, params={"nome": nome_busca})
        resposta.raise_for_status()
        dados = resposta.json().get("dados", [])
        
        if not dados:
            return None
            
        # Pega o primeiro político que a API do governo retornar
        return dados[0]
    except Exception as e:
        print(f"Erro ao conectar com a API da Câmara: {e}")
        return None

async def buscar_contratos_cgu(cnpj_ou_nome: str) -> list:
    """
    Integração futura com o Portal da Transparência usando a CGU_API_KEY.
    """
    # Se a chave da CGU estiver configurada no .env, faríamos a chamada real aqui.
    # Por segurança e para não quebrar a PoC caso a chave não exista, retornamos vazio ou dados estruturados.
    return []

async def gerar_dossie_completo(nome: str, cpf_cnpj: str) -> dict:
    """
    Gera o dossiê real cruzando as APIs do governo.
    Esta função é chamada pelo main.py na rota /auditoria/investigar.
    """
    print(f"[COLETA] Buscando dados oficiais para: {nome}")
    
    # 1. Busca os dados reais de identificação na Câmara
    dados_oficiais = await buscar_deputado_camara(nome)
    
    if not dados_oficiais:
        raise ValueError(f"Não foram encontrados registos oficiais para o nome '{nome}' nas bases do Governo.")

    # 2. Monta o Dossiê no formato exato que a IA e o Frontend (page.tsx) exigem
    dossie = {
        "identificacao": {
            "id_governo": dados_oficiais.get("id"),
            "nome_oficial": dados_oficiais.get("nome"),
            "partido": dados_oficiais.get("siglaPartido"),
            "estado": dados_oficiais.get("siglaUf"),
            "foto_oficial": dados_oficiais.get("urlFoto"),
            "documento_pesquisado": cpf_cnpj
        },
        "dados_tse": {
            # Aqui no futuro entra o Crawler real do DivulgaCand do TSE
            "bens_declarados_total": 0.0,
            "empresas_declaradas": [
                # Exemplo de estrutura que a IA espera para cruzar dados
                # {"nome": "Empresa X", "participacao": "100%"}
            ]
        },
        "dados_governamentais": {
            "contratos_encontrados": await buscar_contratos_cgu(cpf_cnpj)
        }
    }
    
    return dossie
