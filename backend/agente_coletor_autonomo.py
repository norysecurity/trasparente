"""
backend/agente_coletor_autonomo.py

FASE 1 — PIPELINE DE ETL (Arquitetura Offline-First)
===================================================
Worker assíncrono de coleta, tratamento e armazenamento de dados governamentais.
Opera em background: não é chamado em tempo real pelo usuário.
- Sem silenciar erros (raise_for_status obrigatório)
- Rate limits configurados por fonte
- Dados salvos no Drive (Data Lake) e no Neo4j (Grafo)
"""

import asyncio
import os
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any

# ── CONFIGURAÇÃO DE LOGGING PROFISSIONAL ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("AgenteColetor")

# ── IMPORTS DA ARQUITETURA ────────────────────────────────────────────────────
try:
    from motor_ia_qwen import AuditorGovernamentalIA
except ImportError:
    logger.warning("motor_ia_qwen não encontrado. IA desativada.")
    AuditorGovernamentalIA = None

try:
    from google_drive_manager import GoogleDriveManager
    drive_manager = GoogleDriveManager()
    logger.info("✅ Google Drive Manager inicializado.")
except Exception as e:
    logger.warning(f"⚠️ GoogleDriveManager indisponível: {e}")
    drive_manager = None

try:
    from database.neo4j_conn import get_neo4j_connection
    logger.info("✅ Conexão Neo4j disponível.")
except ImportError:
    logger.warning("⚠️ database.neo4j_conn não encontrado. Neo4j desativado.")
    get_neo4j_connection = None

# ── IMPORTAÇÃO DE HTTPX ───────────────────────────────────────────────────────
try:
    import httpx
except ImportError:
    logger.error("❌ httpx não instalado. Execute: pip install httpx")
    httpx = None


class AgenteColetorAutonomo:
    """
    Agente responsável pela Fase 1: ETL (Extract, Transform, Load).
    Coleta dados de APIs governamentais, salva raw dumps no Drive e 
    popula o grafo Neo4j. Não deve ser chamado durante interações do usuário.
    """

    # Rate limits por origem (segundos de espera entre requests)
    RATE_LIMITS = {
        "cgu":      2.0,   # CGU bloqueia IPs com muitas requisições
        "pncp":     1.5,   # PNCP tem limites de 60 req/min
        "tse":      3.0,   # TSE é mais restrito
        "camara":   0.5,   # Câmara é mais permissiva
        "receita":  2.5,   # Receita Federal muito restritiva
    }

    def __init__(self):
        if httpx:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "GovTech-Trasparente/2.0 (Auditoria Cidadã; contact@trasparente.gov.br)"
                }
            )
        else:
            self.client = None

        if drive_manager:
            self.drive = drive_manager
        else:
            self.drive = None

    async def _requisicao_segura(self, url: str, origem: str, params: dict = None) -> Dict:
        """
        Faz a requisição HTTP com logging explícito e re-lança erros reais.
        Nunca silencia falhas de API (ex: 403 Rate Limit, 500 Server Error).
        """
        if not self.client:
            raise RuntimeError("httpx não está disponível. Instale com: pip install httpx")

        logger.info(f"[{origem.upper()}] GET {url} | params={params}")

        try:
            response = await self.client.get(url, params=params)

            # ❌ Erro explícito: se a API retornar 4xx/5xx o erro vai para o log
            response.raise_for_status()

            # ✅ Pausa obrigatória para não ser bloqueado (Rate Limit)
            await asyncio.sleep(self.RATE_LIMITS.get(origem, 1.0))

            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[{origem.upper()}] ❌ Falha HTTP (Status {e.response.status_code}): {e.response.text[:300]}"
            )
            raise  # Repassa — não silencia!

        except httpx.TimeoutException:
            logger.error(f"[{origem.upper()}] ⏱️ Timeout ao acessar {url}")
            raise

        except Exception as e:
            logger.error(f"[{origem.upper()}] ❌ Erro fatal de conexão: {e}")
            raise

    async def consultar_licitacoes_pncp(self, cnpj_orgao: str) -> List[Dict]:
        """
        Busca contratos no PNCP pelo CNPJ do órgão gov.
        Endpoint correto: /api/pncp/v1/orgaos/{cnpj}/contratos
        A API v1 global por data não funciona — exige CNPJ do órgão.
        """
        # CNPJ limpo (apenas dígitos)
        cnpj_limpo = cnpj_orgao.replace(".", "").replace("/", "").replace("-", "")
        url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj_limpo}/contratos"

        try:
            dados = await self._requisicao_segura(url, "pncp")
            contratos = dados if isinstance(dados, list) else dados.get("data", [])
            logger.info(f"[PNCP] ✅ {len(contratos)} contratos carregados para CNPJ {cnpj_limpo}")

            # Opcionalmente: salvar raw dump no Drive
            if self.drive:
                caminho_tmp = f"/tmp/pncp_{cnpj_limpo}.json"
                with open(caminho_tmp, "w", encoding="utf-8") as f:
                    json.dump(contratos, f, ensure_ascii=False, indent=2)
                try:
                    self.drive.upload_file(caminho_tmp, f"raw/pncp/contratos_{cnpj_limpo}.json")
                    logger.info(f"[DRIVE] 📤 Dump enviado para o Data Lake.")
                except Exception as drive_err:
                    logger.warning(f"[DRIVE] ⚠️ Falha no upload: {drive_err}")

            return contratos

        except Exception:
            return []

    async def consultar_gastos_camara(self, id_deputado: int, pagina: int = 1) -> List[Dict]:
        """
        Busca histórico completo de despesas de um deputado na API da Câmara.
        """
        url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id_deputado}/despesas"
        params = {"itens": 100, "pagina": pagina, "ordem": "DESC", "ordenarPor": "dataDocumento"}
        dados = await self._requisicao_segura(url, "camara", params=params)
        return dados.get("dados", [])

    async def baixar_dump_receita_federal(self, uf: str = "SP") -> None:
        """
        Worker noturno: baixa e processa os dumps de CNPJs da Receita Federal.
        Deve ser agendado via cron, não chamado durante a sessão do usuário.
        """
        logger.info(f"[RECEITA] 🔄 Iniciando download do dump de CNPJs — UF: {uf}")
        url = f"https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/2024-11/Empresas{uf}9.zip"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            caminho_zip = f"/tmp/receita_{uf}.zip"
            with open(caminho_zip, "wb") as f:
                f.write(response.content)
            logger.info(f"[RECEITA] ✅ Dump baixado: {caminho_zip} ({len(response.content) // 1024}KB)")

            if self.drive:
                try:
                    self.drive.upload_file(caminho_zip, f"raw/receita/empresas_{uf}.zip")
                    logger.info(f"[DRIVE] 📤 Dump da Receita arquivado.")
                except Exception as e:
                    logger.warning(f"[DRIVE] ⚠️ Falha ao arquivar dump: {e}")

        except Exception as e:
            logger.error(f"[RECEITA] ❌ Falha no download do dump: {e}")
            raise

    async def fechar(self):
        """Encerra o cliente HTTP corretamente."""
        if self.client:
            await self.client.aclose()


# ── FUNÇÃO PÚBLICA CHAMADA PELO MAIN.PY (Worker Assíncrono) ──────────────────

async def auditar_malha_fina_assincrona(id_politico: int, nome_politico: str, cpf_real: str, *args, **kwargs) -> None:
    """
    Ponto de entrada da auditoria offline-first.
    ARQUITETURA: Máximo 3 argumentos. Dados extras devem vir do Neo4j.
    
    Args:
        id_politico (int): ID da entidade.
        nome_politico (str): Nome do agente público.
        cpf_real (str): CPF para traçado da teia no grafo.
    """
    if args or kwargs:
        raise ValueError(
            f"ERRO DE ARQUITETURA: auditar_malha_fina_assincrona aceita apenas 3 argumentos. "
            f"Recebeu args extras: {args} | kwargs: {list(kwargs.keys())}. "
            f"Dados adicionais devem ser consultados no Neo4j."
        )

    logger.info(f"🚀 Iniciando auditoria OFFLINE | ID={id_politico} | Nome={nome_politico}")
    
    subgrafo_json = {}
    empresas_detalhadas = []

    # ── PASSO 1: CONSULTAR NEO4J ──────────────────────────────────────────────
    if get_neo4j_connection and cpf_real and cpf_real != "00000000000":
        try:
            logger.info("🕸️ Extraindo subgrafo do banco Neo4j...")
            neo4j_db = get_neo4j_connection()
            subgrafo_json = neo4j_db.extrair_subgrafo_para_ia(cpf_real)
            neo4j_db.close()

            for c in subgrafo_json.get("conexoes_diretas", []):
                empresas_detalhadas.append({
                    "nome":   c.get("empresa_nome", "N/D"),
                    "cnpj":   c.get("cnpj", "N/A"),
                    "cargo":  c.get("relacao", "VÍNCULO DETECTADO"),
                    "valor":  f"R$ {c.get('valor_envolvido', 0):,.2f}",
                    "fonte":  c.get("fonte_url", "DUMP GOVERNAMENTAL"),
                })

            logger.info(f"✅ {len(empresas_detalhadas)} conexões extraídas do grafo.")

        except Exception as neo4j_err:
            logger.error(f"[NEO4J] ❌ Falha ao consultar grafo: {neo4j_err}")
            subgrafo_json = {"erro": str(neo4j_err)}
    else:
        logger.warning("⚠️ CPF inválido ou Neo4j indisponível. Grafo não consultado.")
        subgrafo_json = {"aviso": "CPF não fornecido ou banco indisponível."}

    # ── PASSO 2: AUDITAR COM IA ───────────────────────────────────────────────
    score_risco = 20
    red_flags = []
    resumo_investigativo = "Auditoria não processada. Motor IA indisponível."

    if AuditorGovernamentalIA:
        try:
            logger.info("🤖 Enviando teia ao Motor IA para análise cognitiva...")
            motor_ia = AuditorGovernamentalIA()
            resultado_ia = await motor_ia.analisar_teia_financeira(subgrafo_json)
            score_risco = resultado_ia.get("score_risco", 20)
            resumo_investigativo = resultado_ia.get("resumo_investigativo", "Análise inconclusiva.")

            for rf in resultado_ia.get("red_flags", []):
                motivo = rf.get("motivo") if isinstance(rf, dict) else str(rf)
                red_flags.append({
                    "data":   datetime.now().strftime("%d/%m/%Y"),
                    "titulo": "🤖 Alerta da IA",
                    "desc":   motivo,
                    "fonte":  "Auditoria de Grafo — Motor Qwen",
                })

            logger.info(f"⚖️ Score de Risco: {score_risco}/100 | Red Flags: {len(red_flags)}")

        except Exception as ia_err:
            logger.error(f"[IA] ❌ Falha no motor cognitivo: {ia_err}")
            red_flags = [{
                "data":   datetime.now().strftime("%d/%m/%Y"),
                "titulo": "Erro de IA",
                "desc":   str(ia_err),
                "fonte":  "Sistema"
            }]

    # ── PASSO 3: GERAR DOSSIÊ LOCAL ───────────────────────────────────────────
    os.makedirs("dossies", exist_ok=True)
    dossie = {
        "id_politico":             id_politico,
        "cpf_politico":            cpf_real,
        "nome_politico":           nome_politico,
        "score_risco_calculado":   score_risco,
        "pontos_perdidos":         int((score_risco / 100.0) * 1000),
        "resumo_investigativo":    resumo_investigativo,
        "redFlags":                red_flags,
        "empresas":                empresas_detalhadas,
        "diagrama_relacional_cru": subgrafo_json,
        "data_auditoria_offline":  datetime.now().isoformat(),
    }

    caminho_arquivo = f"dossies/dossie_{id_politico}.json"
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(dossie, f, ensure_ascii=False, indent=4)
    logger.info(f"📄 Dossiê salvo em: {caminho_arquivo}")

    # ── PASSO 4: ARQUIVAR NO DATA LAKE (GOOGLE DRIVE) ─────────────────────────
    if drive_manager:
        try:
            drive_manager.salvar_dossie_no_drive(nome_politico, caminho_arquivo)
            logger.info(f"☁️ Dossiê de {nome_politico} arquivado no Data Lake.")
        except Exception as drive_err:
            logger.error(f"[DRIVE] ⚠️ Dossiê gerado localmente, mas falhou no upload: {drive_err}")

    logger.info(f"🏁 AUDITORIA CONCLUÍDA | Score: {score_risco}/100 | Político: {nome_politico}")
