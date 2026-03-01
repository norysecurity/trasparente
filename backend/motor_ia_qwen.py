"""
backend/motor_ia_qwen.py

FASE 3 — MOTOR DE IA AUDITORA (Arquitetura Offline-First)
=========================================================
Não faz web scraping. Recebe o JSON do Neo4j e analisa anomalias.
Regra Inquebrável: toda divergência DEVE ter um link Markdown oficial.
Validação automática: resposta rejeitada se não houver link https://.
"""

import os
import re
import json
import logging
from typing import Dict, Any

logger = logging.getLogger("AuditorGovernamentalIA")

try:
    import httpx
    _HTTPX_OK = True
except ImportError:
    _HTTPX_OK = False
    logger.error("httpx não instalado. Execute: pip install httpx")


class AuditorGovernamentalIA:
    """
    Motor Cognitivo de Auditoria.
    - Analisa subgrafos do Neo4j em busca de anomalias.
    - Gera laudos com links clicáveis para fontes governamentais oficiais.
    - Valida automaticamente se a resposta contém links Markdown.
    """

    # ── ENDPOINT E MODELO ─────────────────────────────────────────────────────
    BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
    MODELO   = "qwen-max"  # Modelo principal — não alterar para modelos legados

    def __init__(self):
        self.api_key = os.getenv("QWEN_API_KEY")
        if not self.api_key:
            logger.warning("⚠️  QWEN_API_KEY não definida. Modo FALLBACK ativo.")

    # ── SYSTEM PROMPT INQUEBRÁVEL ─────────────────────────────────────────────
    @property
    def _system_prompt(self) -> str:
        return """
Você é um Auditor Investigativo Governamental Sênior, especializado em análise de
grafos de corrupção, licitações fraudulentas e desvios de conduta de agentes públicos.

══════════════════════════════════════════════════════════════════════
REGRA INQUEBRÁVEL — OBRIGATORIEDADE DE LINKS OFICIAIS
══════════════════════════════════════════════════════════════════════
Ao identificar QUALQUER divergência, red flag, anomalia ou irregularidade:
1. Você DEVE apresentar um LINK EM MARKDOWN apontando para a FONTE OFICIAL DO GOVERNO.
2. Fontes válidas: Portal da Transparência, PNCP, Receita Federal, TSE, TCU, STF, CGU.
3. Se o JSON contiver os campos "fonte", "url", "link" ou "documento" — USE-OS.
4. Se NÃO houver fonte oficial verificável no contexto, NÃO cite a divergência.
5. NUNCA invente URLs, NUNCA crie PDFs fictícios. Apenas dados fornecidos no JSON.

FORMAT OBRIGATÓRIO DE CADA RED FLAG:
### 🔴 [Tipo da Divergência]
[Descrição técnica e investigativa da irregularidade]

📎 Evidência Oficial:
[Nome do Documento ou Entidade](https://link.oficial.gov.br)

══════════════════════════════════════════════════════════════════════
SAÍDA (JSON ESTRITAMENTE VÁLIDO — sem comentários, sem texto extra)
══════════════════════════════════════════════════════════════════════
{
    "score_risco": <inteiro de 0 a 100>,
    "red_flags": [
        {
            "motivo": "### 🔴 Tipo\\nDescrição...\\n\\n📎 Evidência Oficial:\\n[Fonte](https://...)"
        }
    ],
    "resumo_investigativo": "Texto completo do dossiê em Markdown com todos os links oficiais."
}
"""

    # ── MÉTODO PRINCIPAL ──────────────────────────────────────────────────────
    async def analisar_teia_financeira(self, json_do_neo4j: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recebe o subgrafo do Neo4j e retorna o laudo de risco com links oficiais.
        Rejeita automaticamente respostas sem links Markdown (https://).
        """
        logger.info("🧠 [IA AUDITORA] Inspecionando subgrafo em busca de anomalias...")

        if not self.api_key or not _HTTPX_OK:
            logger.warning("API Key ausente ou httpx faltando. Ativando fallback simulado.")
            return self._fallback_simulado(json_do_neo4j)

        headers = {
            "Authorization":  f"Bearer {self.api_key}",
            "Content-Type":   "application/json",
        }

        payload = {
            "model": self.MODELO,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Faça a auditoria investigativa da seguinte teia de relações extraída do "
                        "banco de grafos Neo4j:\n\n"
                        + json.dumps(json_do_neo4j, ensure_ascii=False, indent=2)
                    ),
                },
            ],
            "temperature": 0.05,  # Temperatura mínima para raciocínio determinístico
            "max_tokens":  2048,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(self.BASE_URL, headers=headers, json=payload)
                resp.raise_for_status()  # Lança erro real em vez de silenciar

                raw = resp.json()["choices"][0]["message"]["content"].strip()

                # ── Limpeza de formatação suja ────────────────────────────────
                raw = re.sub(r"^```json\s*", "", raw)
                raw = re.sub(r"^```\s*",     "", raw)
                raw = re.sub(r"\s*```$",      "", raw)
                raw = raw.strip()

                resultado = json.loads(raw)

                # ── VALIDAÇÃO INQUEBRÁVEL: deve existir ao menos um link Markdown
                texto_completo = json.dumps(resultado, ensure_ascii=False)
                if not re.search(r"\[.+?\]\(https?://.+?\)", texto_completo):
                    logger.warning(
                        "⚠️  IA gerou laudo SEM link oficial em Markdown. "
                        "Resposta rejeitada — ativando fallback simulado."
                    )
                    return self._fallback_simulado(json_do_neo4j)

                logger.info(f"⚖️  Score de Risco: {resultado.get('score_risco', 0)}/100 "
                            f"| Red Flags: {len(resultado.get('red_flags', []))}")
                return resultado

        except json.JSONDecodeError as je:
            logger.error(f"❌ JSON inválido na resposta da IA: {je}")
            return self._fallback_simulado(json_do_neo4j)

        except httpx.HTTPStatusError as he:
            logger.error(
                f"❌ Falha na API Qwen (Status {he.response.status_code}): "
                f"{he.response.text[:300]}"
            )
            return self._fallback_simulado(json_do_neo4j)

        except Exception as e:
            logger.error(f"❌ Erro não esperado no motor IA: {e}")
            return self._fallback_simulado(json_do_neo4j)

    # ── FALLBACK SIMULADO (quando API cai) ────────────────────────────────────
    def _fallback_simulado(self, json_do_neo4j: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ativado quando a API Qwen está indisponível.
        Analisa o JSON do Neo4j de forma heurística e gera um laudo mínimo.
        Nota: Este fallback NÃO deve substituir a IA real em produção.
        """
        score_risco = 20
        red_flags   = []

        empresas   = json_do_neo4j.get("empresas",              [])
        familiares = json_do_neo4j.get("familiares_mapeados",   [])
        contratos  = json_do_neo4j.get("contratos_suspeitos",   [])

        if empresas and familiares:
            score_risco += 30
            red_flags.append({
                "motivo": (
                    "### 🔴 Potencial Nepotismo\n"
                    "Familiares e empresas associadas ao investigado foram detectados no grafo. "
                    "Revisão manual aprofundada necessária.\n\n"
                    "📎 Evidência Oficial:\n"
                    "[Consulta Societária — Receita Federal]"
                    "(https://solucoes.receita.fazenda.gov.br/Servicos/cnpjreva/Cnpjreva_Solicitacao.asp)"
                )
            })

        if contratos:
            score_risco += 20
            red_flags.append({
                "motivo": (
                    "### 🔴 Contratos no PNCP para Revisão\n"
                    "Contratos associados ao CPF investigado identificados no banco de dados.\n\n"
                    "📎 Evidência Oficial:\n"
                    "[Portal de Compras — PNCP](https://pncp.gov.br)"
                )
            })

        return {
            "score_risco":          min(score_risco, 100),
            "red_flags":            red_flags,
            "resumo_investigativo": (
                "**[MODO FALLBACK]** Análise executada de forma heurística. "
                "O motor LLM Qwen estava indisponível no momento da auditoria. "
                "Os dados acima são uma triagem automática, não um laudo definitivo. "
                "Reinicie o processo quando a API estiver disponível."
            ),
        }
