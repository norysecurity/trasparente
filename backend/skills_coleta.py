import asyncio
import random
from typing import Dict, Any

async def consultar_portal_transparencia(cpf_cnpj: str) -> Dict[str, Any]:
    """
    Simula uma requisição assíncrona ao Portal da Transparência (CGU).
    Em um cenário real, usaria a biblioteca `httpx` ou `aiohttp` com a CGU_API_KEY.
    """
    print(f"[🔍 Coleta] Consultando Portal da Transparencia para: {cpf_cnpj}...")
    await asyncio.sleep(1) # Simula latência da rede
    
    # Dados simulados
    contratos = []
    if random.random() > 0.3: # 70% de chance de ter encontrado algo suspeito para a demo
        contratos.append({
            "id_contrato": f"CT-{random.randint(1000, 9999)}",
            "valor": random.uniform(50000.0, 5000000.0),
            "objeto": "Serviços de consultoria em TI",
            "empresa_vencedora": "Tech Familiar LTDA"
        })
        
    return {
        "fonte": "Portal da Transparência",
        "documento": cpf_cnpj,
        "contratos_encontrados": contratos
    }


async def extrair_dados_tse(nome_politico: str) -> Dict[str, Any]:
    """
    Simula a extração de dados públicos de candidaturas e bens declarados ao TSE.
    """
    print(f"[🔍 Coleta] Extraindo dados do TSE para o candidato: {nome_politico}...")
    await asyncio.sleep(1.5) # Simula latência da rede

    # Dados simulados
    return {
        "fonte": "TSE Oficial",
        "candidato": nome_politico,
        "partido": "PTG (Partido Tecnológico Global)",
        "bens_declarados_total": random.uniform(100000.0, 10000000.0),
        "empresas_declaradas": [
            {"nome": "Tech Familiar LTDA", "participacao": "50%"}
        ]
    }

async def gerar_dossie_completo(nome_politico: str, cpf_cnpj: str) -> Dict[str, Any]:
    """
    Orquestra a coleta de dados de múltiplas fontes concorrentemente.
    """
    dados_tse, dados_transparencia = await asyncio.gather(
        extrair_dados_tse(nome_politico),
        consultar_portal_transparencia(cpf_cnpj)
    )
    
    return {
        "identificacao": {
            "nome": nome_politico,
            "documento": cpf_cnpj
        },
        "dados_tse": dados_tse,
        "dados_governamentais": dados_transparencia
    }
