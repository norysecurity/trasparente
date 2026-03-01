import os
import json
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger("AuditorGovernamentalIA")

class AuditorGovernamentalIA:
    """
    O Motor Cognitivo (IA Auditora).
    Não busca dados na web. Sua função é ler o JSON do Neo4j e auditar a teia financeira
    em busca de anomalias governamentais e desvios de conduta.
    """
    def __init__(self):
        self.api_key = os.getenv("QWEN_API_KEY")
        self.base_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
        
        self.system_prompt = """
        Você é um Auditor Investigativo Sênior especializado em auditoria governamental, compliance e análise de grafos de corrupção.
        Sua missão é receber uma teia de conexões (JSON extraído do Neo4j) envolvendo um político, empresas, emendas e associados.
        
        Sua análise deve focar estritamente em anomalias como:
        - Autocontratação (sócio é parente do político).
        - Volume financeiro desproporcional à idade ou capacidade da empresa (ex: empresa recém-criada ganha milhões).
        - Densidade suspeita de contratos e repasses (Emendas diretas para aliados).

        Sua resposta DEVE ser um único objeto JSON válido. Não envolva o JSON com blocos Markdown (```json).
        O JSON RIGHOROSAMENTE necessita ter a seguinte estrutura exata:
        {
            "score_risco": <inteiro de 0 a 100>,
            "red_flags": [
                {
                    "motivo": "Descrição técnica da anomalia encontrada na teia de conexões"
                }
            ],
            "resumo_investigativo": "Texto em estilo de Dossiê Oficial explicando o esquema encontrado de forma pericial."
        }
        """

    async def analisar_teia_financeira(self, json_do_neo4j: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consome os dados do banco orientado a grafos organizados em JSON e audita.
        """
        logger.info("🧠 [IA AUDITORA] Inspecionando o grafo em busca de anomalias...")
        
        if not self.api_key:
            logger.warning("⚠️ QWEN_API_KEY não localizada. Retornando fallback de contingência.")
            return self._fallback_simulado(json_do_neo4j)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Conforme regra de uso de modelos mais modernos
        payload = {
            "model": "qwen-max", 
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Audite a seguinte teia do Neo4j:\n\n{json.dumps(json_do_neo4j, ensure_ascii=False, indent=2)}"}
            ],
            "temperature": 0.1 # Temperatura mínima para raciocínio lógico determinístico
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                
                # Tratamento robosto contra formatação suja gerada por LLM
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                
                content = content.strip()
                resultado = json.loads(content)
                logger.info(f"⚖️ Veredito Concluído: Score de Risco {resultado.get('score_risco', 0)}")
                return resultado
                
        except Exception as e:
            logger.error(f"❌ Falha de integração com a IA Qwen: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Detalhes: {e.response.text}")
            return self._fallback_simulado(json_do_neo4j)
            
    def _fallback_simulado(self, json_do_neo4j: Dict[str, Any]) -> Dict[str, Any]:
        """ Fallback quando a API cai. """
        score_risco = 20
        red_flags = []
        
        empresas = json_do_neo4j.get("empresas", [])
        familiares = json_do_neo4j.get("familiares_mapeados", [])
        
        if len(empresas) > 0 and len(familiares) > 0:
            red_flags.append({"motivo": "Existem empresas e possíveis familiares mapeados, exigindo revisão manual profunda."})
            score_risco += 30
            
        return {
            "score_risco": score_risco,
            "red_flags": red_flags,
            "resumo_investigativo": "Análise executada em modo offline simulado devido a falha de comunicação com motor LLM."
        }
