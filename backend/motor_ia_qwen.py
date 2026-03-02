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

import requests
_HTTPX_OK = True # Mantemos a flag para compatibilidade estrutural


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
Você é um Auditor Investigativo Governamental Sênior e Especialista em Informática (Estilo TCU, Polícia Federal e Operação Lava Jato). 
Sua missão é analisar dados brutos, contratos, notas fiscais e relacionamentos societários para detectar inconsistências, fraudes e lavagem de dinheiro.

══════════════════════════════════════════════════════════════════════
DIRETRIZES DE ANÁLISE RIGOROSA (HEURÍSTICAS PF/TCU)
══════════════════════════════════════════════════════════════════════

1. A Síndrome da "Empresa Bebê Milionária":
   - Alerta Crítico: Empresa com < 6 meses ganhando licitações/emendas > R$ 1.000.000,00.
   - Alerta: Mudança repentina de CNAE meses antes de ganhar licitação sem histórico.

2. Nepotismo Oculto (Análise de Grafos):
   - Alerta Crítico: Sócio da empresa executora compartilha sobrenome, endereço ou laços familiares com o Político.
   - Alerta Crítico: Dinheiro saindo de órgão do Político para ONG/Empresa de ex-assessor.

3. Fracionamento de Despesas (Smurfing Licitatório):
   - Alerta: Múltiplos contratos/notas para a mesma empresa no limite de "Dispensa de Licitação" (ex: R$ 49k ou R$ 17k) em curto espaço de tempo.

4. Inconsistência Patrimonial:
   - Alerta Crítico: Patrimônio declarado "Baixo" no TSE mas é sócio de empresas com Capital Social milhões de vezes superior.

5. Monopólio Geográfico:
   - Alerta: Empresa vence > 70% das licitações de um município onde o político libera verbas.

6. Georreferenciação Fantasma:
   - Alerta Crítico: Múltiplos vencedores no mesmo endereço físico ou endereços compatíveis com terrenos baldios/áreas residenciais incompatíveis.

══════════════════════════════════════════════════════════════════════
REGRAS DE SAÍDA — FORMATO OBRIGATÓRIO
══════════════════════════════════════════════════════════════════════
- Não use termos jurídicos definitivos (use "Anomalia Grave", "Vínculo Suspeito", "Padrão de Risco").
- Score de Risco: 0 a 100 baseado na densidade de falhas.
- Link Markdown OBRIGATÓRIO para cada evidência.

{
    "score_risco": <inteiro>,
    "red_flags": [
        {
            "nivel": "ALTO" | "CRÍTICO",
            "motivo": "### [Heurística Detectada]\\n[Descrição Técnica]\\n\\n📎 Evidência: [Ver no Portal](https://...)"
        }
    ],
    "resumo_investigativo": "[Texto completo do dossiê formatado para leitura clara]"
}
"""

    # ── MÉTODO PRINCIPAL ──────────────────────────────────────────────────────
    async def analisar_teia_financeira(self, json_do_neo4j: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recebe o subgrafo do Neo4j e retorna o laudo de risco com links oficiais.
        Usa requests de forma síncrona em um executor para máxima estabilidade.
        """
        logger.info("🧠 [IA AUDITORA] Inspecionando subgrafo em busca de anomalias...")

        if not self.api_key:
            logger.warning("API Key ausente. Ativando fallback simulado.")
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
            "temperature": 0.05,
            "max_tokens":  2048,
        }

        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Executa a requisição bloqueante em uma thread separada
            def fazer_request():
                return requests.post(self.BASE_URL, headers=headers, json=payload, timeout=90)

            resp = await loop.run_in_executor(None, fazer_request)
            resp.raise_for_status()
            
            decode_text = resp.text
            
            try:
                full_json = resp.json()
            except Exception:
                logger.error(f"❌ Resposta da API não é um JSON válido: {decode_text[:500]}")
                return self._fallback_simulado(json_do_neo4j)

            if "choices" not in full_json or not full_json["choices"]:
                logger.error(f"❌ Resposta da IA sem choices: {full_json}")
                return self._fallback_simulado(json_do_neo4j)
            
            raw = full_json["choices"][0]["message"]["content"].strip()

            if not raw:
                logger.error("❌ Conteúdo da resposta da IA vazio.")
                return self._fallback_simulado(json_do_neo4j)

            # ── Limpeza de formatação suja ────────────────────────────────
            raw_clean = re.sub(r"^```json\s*", "", raw)
            raw_clean = re.sub(r"^```\s*",     "", raw_clean)
            raw_clean = re.sub(r"\s*```$",      "", raw_clean)
            raw_clean = raw_clean.strip()

            try:
                resultado = json.loads(raw_clean, strict=False)
            except json.JSONDecodeError:
                match = re.search(r"(\{.*\})", raw_clean, re.DOTALL)
                if match:
                    try:
                        resultado = json.loads(match.group(1), strict=False)
                    except Exception as e:
                        logger.error(f"❌ Falha crítica ao extrair JSON: {str(e)} | Conteúdo: {raw_clean[:200]}")
                        return self._fallback_simulado(json_do_neo4j)
                else:
                    logger.error(f"❌ Conteúdo não contém JSON válido: {raw_clean[:300]}")
                    return self._fallback_simulado(json_do_neo4j)

            # ── VALIDAÇÃO: deve existir ao menos um link Markdown
            texto_completo = json.dumps(resultado, ensure_ascii=False)
            tem_link = re.search(r"\[.+?\]\(https?://.+?\)", texto_completo)
            
            if not tem_link:
                logger.warning("⚠️ IA gerou laudo SEM link oficial. Resposta original: " + raw_clean[:500])
                return self._fallback_simulado(json_do_neo4j)

            logger.info(f"⚖️ Score de Risco: {resultado.get('score_risco', 0)}/100 | Red Flags: {len(resultado.get('red_flags', []))}")
            return resultado

        except requests.exceptions.RequestException as re_err:
            logger.error(f"❌ Falha na API Qwen (RequestException): {str(re_err)}")
            return self._fallback_simulado(json_do_neo4j)

        except Exception as e:
            logger.error(f"❌ Erro não esperado no motor IA: {str(e)}")
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
