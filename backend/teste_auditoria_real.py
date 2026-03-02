import asyncio
import sys
import os

# Adiciona o diretório atual ao path para encontrar os módulos
sys.path.append(os.getcwd())

from agente_coletor_autonomo import auditar_malha_fina_assincrona

async def main():
    print("🚀 Iniciando Teste de Auditoria Real...")
    # Usando dados reais encontrados no CSV 2024
    id_politico = 250002029385
    nome = "GUILHERME BARDAUIL BOULOS"
    cpf = "288247820159" # CPF de teste encontrado no CSV
    
    try:
        await auditar_malha_fina_assincrona(id_politico, nome, cpf)
        print("✅ Teste finalizado com sucesso!")
    except Exception as e:
        print(f"❌ Falha no teste: {e}")

if __name__ == "__main__":
    asyncio.run(main())
