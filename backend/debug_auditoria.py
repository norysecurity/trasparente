import asyncio
import json
import os
import logging
from motor_ia_qwen import AuditorGovernamentalIA
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

async def debug_audit():
    auditor = AuditorGovernamentalIA()
    # Mock de uma teia para teste
    teia_fake = {
        "politico": "Teste",
        "cpf": "123",
        "id_tse": "456",
        "conexoes_diretas": [
            {"empresa_nome": "CONSTRO S.A.", "cnpj_ou_id": "111", "relacao": "Doador", "valor_envolvido": 1000000}
        ],
        "rede_societaria": [
            {"socio": "Irmão do Político", "empresa_alvo": "CONSTRO S.A."}
        ]
    }
    
    print("Iniciando auditoria real com Qwen-Max...")
    resultado = await auditor.analisar_teia_financeira(teia_fake)
    print("--- RESULTADO ---")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(debug_audit())
