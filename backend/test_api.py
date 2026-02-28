import httpx
import asyncio
import json

async def main():
    async with httpx.AsyncClient() as client:
        try:
            print("Fazendo requisição para a API de Auditoria...")
            response = await client.post(
                "http://127.0.0.1:8000/auditoria/investigar",
                json={"nome": "João das Couves", "cpf_cnpj": "12345678900"},
                timeout=40.0
            )
            response.raise_for_status()
            resultado = response.json()
            print("=== SUCESSO! ===")
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Erro na requisição: {e}")

if __name__ == "__main__":
    asyncio.run(main())
