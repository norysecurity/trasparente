import os
import json
import httpx
from typing import Dict, Any

class MotorIAQwen:
    """
    Motor de IA que atua como um Auditor Investigativo usando a API do modelo Qwen.
    """
    def __init__(self):
        self.api_key = os.getenv("QWEN_API_KEY")
        # Usando a URL base da API compatível com o OpenAI client ou requisição direta
        self.base_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
        
        self.system_prompt = """
        Você é um Auditor Investigativo Sênior especializado em auditoria governamental, compliance e análise de grafos de corrupção.
        Sua missão é receber um dossiê de dados (TSE e Portal da Transparência) sobre um político, analisar e encontrar conexões suspeitas.
        
        Exemplos de "Red Flags" (bandeiras vermelhas):
        - O político possui participação em uma empresa que ganhou um contrato público.
        - Evolução patrimonial incompatível.
        - Empresa recém criada ganhando licitações milionárias.
        
        Sua resposta **DEVE** ser EXCLUSIVAMENTE um JSON válido, sem markdown envolta (sem ```json), com a seguinte estrutura:
        {
            "nivel_risco": "BAIXO" | "MEDIO" | "ALTO" | "CRITICO",
            "red_flags": [
                {
                    "motivo": "Descrição do problema encontrado",
                    "gravidade": 1 a 10
                }
            ],
            "resumo_auditoria": "Breve resumo textual das conclusões"
        }
        """

    async def analisar_dossie(self, dossie: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envia o dossiê para a IA Qwen e retorna a análise de risco em JSON.
        """
        if not self.api_key:
            return self._simular_resposta(dossie)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "qwen-max", # ou "qwen-plus"
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Analise o seguinte dossiê e retorne as Red Flags em JSON:\n\n{json.dumps(dossie, ensure_ascii=False, indent=2)}"}
            ],
            "temperature": 0.1 # Baixa criatividade para focar em precisão e fatos
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                # Limpa possível formatação markdown do JSON retornada pela LLM
                content = content.replace("```json\n", "").replace("```\n", "").replace("```", "").strip()
                return json.loads(content)
                
        except Exception as e:
            print(f"[Erro na IA Qwen] Falha ao processar ou parsear JSON: {e}")
            return self._simular_resposta(dossie) # Fallback para continuar fluindo se der erro na key
            
    def _simular_resposta(self, dossie: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback simulado caso falte a API Key ou ocorra erro.
        Analisa os dados estáticos do mock.
        """
        red_flags = []
        nivel_risco = "BAIXO"
        
        empresas = dossie["dados_tse"]["empresas_declaradas"]
        contratos = dossie["dados_governamentais"]["contratos_encontrados"]
        
        for contrato in contratos:
            for empresa in empresas:
                if empresa["nome"] in contrato["empresa_vencedora"]:
                    red_flags.append({
                        "motivo": f"Conflito de interesse: A empresa '{empresa['nome']}' declarada pertence ao político e venceu contrato de R$ {contrato['valor']:.2f}.",
                        "gravidade": 9
                    })
                    nivel_risco = "CRITICO"
                    
        return {
            "nivel_risco": nivel_risco,
            "red_flags": red_flags,
            "resumo_auditoria": "Análise gerada (MODO SIMULADO). Foram encontradas inconsistências contratuais." if red_flags else "Nenhuma inconsistência evidente encontrada nos dados."
        }
