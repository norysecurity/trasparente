#!/usr/bin/env python3
"""
coletor_anual.py — Motor de Extração em Lote (Bulk Download)
=============================================================
Baixa dumps anuais das fontes oficiais do governo:
  - TSE: Candidatos municipais (PREFEITO, VEREADOR) — ano específico
  - Portal da Transparência (CGU): CEAP, CEIS, CNEP
  - IBGE: Lista de municípios

REGRA ABSOLUTA: Nunca silenciar erros. Todo passo aparece no terminal.
Execute:
  python coletor_anual.py --ano 2024 --fonte tse
  python coletor_anual.py --ano 2024 --fonte todos --force --injetar
"""

import asyncio
import httpx
import logging
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

# ── CONFIGURAÇÃO DE LOGGING OBRIGATÓRIA ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)-8s - [%(filename)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"coleta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("MotorExtracaoGoverno")


# ── FONTES OFICIAIS DE DOWNLOAD ───────────────────────────────────────────────
FONTES = {
    "tse": {
        "nome": "TSE — Tribunal Superior Eleitoral",
        "candidatos": {
            2024: "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2024.zip",
            2022: "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2022.zip",
            2020: "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2020.zip",
            2018: "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2018.zip",
        },
        "bens": {
            2024: "https://cdn.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2024.zip",
            2020: "https://cdn.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2020.zip",
        }
    },
    "cgu": {
        "nome": "CGU — Controladoria-Geral da União",
        "ceap": "https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip",   # CEAP Câmara
        "ceis": "https://portaldatransparencia.gov.br/download-de-dados/ceis/{ano}",
        "cnep": "https://portaldatransparencia.gov.br/download-de-dados/cnep/{ano}",
        "servidores": "https://portaldatransparencia.gov.br/download-de-dados/servidores/{ano}07_Servidores.zip",
    },
    "pncp": {
        "nome": "PNCP — Portal Nacional de Contratações Públicas",
        "contratos": "https://pncp.gov.br/api/pncp/v1/contratos?dataInicial={ano}0101&dataFinal={ano}1231&pagina=1&tamanhoPagina=500",
    },
    "ibge": {
        "nome": "IBGE — Municípios e regiões",
        "municipios": "https://servicodados.ibge.gov.br/api/v1/localidades/municipios",
    }
}


class MotorExtracaoGoverno:
    """
    Motor de ETL com logging obrigatório.
    Cada request, cada byte baixado, cada erro — TUDO aparece no terminal.
    """

    def __init__(self, ano_alvo: int, pasta_base: str = "./dados_brutos", force: bool = False):
        self.ano_alvo        = ano_alvo
        self.force           = force
        self.pasta_destino   = Path(f"{pasta_base}_{ano_alvo}")
        self.pasta_destino.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Pasta de destino: {self.pasta_destino.absolute()}")
        logger.info(f"📅 Ano-alvo: {ano_alvo} | Force: {'SIM — arquivos antigos serão deletados' if force else 'Não'}")

        self.cliente = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=15.0, read=300.0, write=60.0, pool=5.0),
            follow_redirects=True,
            headers={
                "User-Agent": "GovTech-Trasparente/3.0 (Auditoria Cidada; opensource)",
                "Accept":     "application/json, text/csv, application/zip, */*",
            }
        )
        self.stats = {"ok": 0, "erro": 0, "bytes": 0}

    # ── DOWNLOAD COM STREAMING E PROGRESSO ───────────────────────────────────
    async def _baixar_com_progresso(self, url: str, caminho_destino: Path) -> bool:
        """Faz o download com log de progresso a cada chunk. NUNCA silencia erros."""
        logger.info(f"  ⬇️  Conectando em: {url}")
        try:
            async with self.cliente.stream("GET", url) as resp:
                tamanho_total = int(resp.headers.get("content-length", 0))
                logger.info(f"  📊 Status HTTP: {resp.status_code} | Tamanho: {tamanho_total/1024/1024:.1f} MB")

                # Lança exceção se 4xx ou 5xx — NUNCA ignora
                resp.raise_for_status()

                bytes_baixados = 0
                ultimo_log    = 0
                intervalo_log = max(1024*1024, tamanho_total // 10)  # Log a cada 10% ou 1MB

                with open(caminho_destino, "wb") as arquivo:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        arquivo.write(chunk)
                        bytes_baixados += len(chunk)

                        # Log de progresso
                        if bytes_baixados - ultimo_log >= intervalo_log:
                            pct = (bytes_baixados / tamanho_total * 100) if tamanho_total else 0
                            logger.info(
                                f"  📦 {caminho_destino.name}: {bytes_baixados/1024/1024:.1f} MB"
                                + (f" / {tamanho_total/1024/1024:.1f} MB ({pct:.0f}%)" if tamanho_total else "")
                            )
                            ultimo_log = bytes_baixados

                self.stats["bytes"] += bytes_baixados
                self.stats["ok"]    += 1
                logger.info(f"  ✅ CONCLUÍDO: {caminho_destino} ({bytes_baixados/1024/1024:.2f} MB)")
                return True

        except httpx.HTTPStatusError as e:
            self.stats["erro"] += 1
            logger.error(f"  ❌ BLOQUEIO DO GOVERNO: HTTP {e.response.status_code} em {url}")
            logger.error(f"     Cabeçalhos de resposta: {dict(e.response.headers)}")
            logger.error(f"     Corpo (primeiros 500 chars): {e.response.text[:500]}")
            if e.response.status_code == 403:
                logger.error("     → CAUSA PROVÁVEL: Bloqueio de IP / Rate Limit. Aguarde antes de tentar novamente.")
            elif e.response.status_code == 404:
                logger.error("     → CAUSA PROVÁVEL: URL desatualizada. Verifique o site do governo manualmente.")
            elif e.response.status_code == 429:
                logger.error("     → CAUSA PROVÁVEL: Rate Limit atingido. Reduza a frequência de requests.")
            return False

        except httpx.ConnectError as e:
            self.stats["erro"] += 1
            logger.error(f"  ❌ ERRO DE CONEXÃO: Não conseguiu conectar em {url}")
            logger.error(f"     Detalhe: {e}")
            logger.error("     → CAUSA PROVÁVEL: DNS falhou, site fora do ar ou bloqueio de firewall.")
            return False

        except httpx.TimeoutException as e:
            self.stats["erro"] += 1
            logger.error(f"  ❌ TIMEOUT: Servidor demorou demais em {url}")
            logger.error(f"     Detalhe: {e}")
            logger.error("     → AÇÃO: Tente novamente. Se persistir, o servidor está sobrecarregado.")
            return False

        except Exception as e:
            self.stats["erro"] += 1
            logger.error(f"  ❌ ERRO FATAL INESPERADO: {type(e).__name__}: {e}")
            logger.error("     Este erro não foi previsto. Verifique o stack trace acima.")
            raise  # Re-lança para visibilidade total

    # ── TSE: CANDIDATOS E BENS ────────────────────────────────────────────────
    async def baixar_dump_tse_candidatos(self):
        """Baixa ZIP com todos os candidatos do ano (inclui PREFEITO e VEREADOR municipais)."""
        logger.info("=" * 70)
        logger.info(f"🗳️  TSE | Candidatos {self.ano_alvo}")
        logger.info("=" * 70)

        urls_candidatos = FONTES["tse"]["candidatos"]
        if self.ano_alvo not in urls_candidatos:
            anos_disp = list(urls_candidatos.keys())
            logger.error(f"❌ Ano {self.ano_alvo} não disponível no TSE.")
            logger.error(f"   Anos disponíveis: {anos_disp}")
            logger.error(f"   Use --ano com um dos valores acima.")
            return

        url = urls_candidatos[self.ano_alvo]
        destino = self.pasta_destino / f"tse_candidatos_{self.ano_alvo}.zip"

        if destino.exists():
            if self.force:
                logger.warning(f"   🔥 --force ativo: deletando {destino.name} ({destino.stat().st_size/1024/1024:.1f} MB)")
                destino.unlink()
            else:
                logger.warning(f"   ⚠️  Arquivo já existe: {destino} ({destino.stat().st_size/1024/1024:.1f} MB)")
                logger.warning("   → Use --force para re-baixar sobrescrevendo o arquivo.")
                return

        logger.info(f"   Fonte oficial TSE: {url}")
        logger.info("   ⚠️  AVISO: Arquivo pode ser grande (centenas de MB). Seja paciente.")
        await self._baixar_com_progresso(url, destino)

    async def baixar_bens_candidatos_tse(self):
        """Baixa declaração de bens dos candidatos para cruzar com patrimônio declarado."""
        logger.info("=" * 70)
        logger.info(f"💰 TSE | Bens declarados {self.ano_alvo}")
        logger.info("=" * 70)

        urls_bens = FONTES["tse"]["bens"]
        if self.ano_alvo not in urls_bens:
            logger.warning(f"   ⚠️  Ano {self.ano_alvo} não disponível para bens. Tentando 2020.")
            self.ano_alvo = 2020

        url = urls_bens.get(self.ano_alvo, urls_bens[2020])
        destino = self.pasta_destino / f"tse_bens_{self.ano_alvo}.zip"

        if destino.exists():
            if self.force:
                logger.warning(f"   🔥 --force: deletando {destino.name}")
                destino.unlink()
            else:
                logger.warning(f"   ⚠️  Já existe: {destino}. Use --force para re-baixar.")
                return
        await self._baixar_com_progresso(url, destino)

    # ── CGU / PORTAL DA TRANSPARÊNCIA ────────────────────────────────────────
    async def baixar_ceis_cnep_cgu(self):
        """Baixa CEIS (empresas inidôneas) e CNEP (sanções)."""
        logger.info("=" * 70)
        logger.info(f"🔴 CGU | CEIS + CNEP {self.ano_alvo}")
        logger.info("=" * 70)

        urls = [
            (FONTES["cgu"]["ceis"].format(ano=self.ano_alvo),
             self.pasta_destino / f"cgu_ceis_{self.ano_alvo}.zip",
             "CEIS — Cadastro de Empresas Inidôneas e Suspensas"),
            (FONTES["cgu"]["cnep"].format(ano=self.ano_alvo),
             self.pasta_destino / f"cgu_cnep_{self.ano_alvo}.zip",
             "CNEP — Cadastro Nacional de Empresas Punidas"),
            (FONTES["cgu"]["servidores"].format(ano=self.ano_alvo),
             self.pasta_destino / f"cgu_servidores_{self.ano_alvo}.zip",
             "CGU — Servidores Públicos Federais"),
        ]

        for url, destino, descricao in urls:
            logger.info(f"  📄 {descricao}")
            if destino.exists():
                if self.force:
                    logger.warning(f"     🔥 --force: deletando {destino.name}")
                    destino.unlink()
                else:
                    logger.warning(f"     ⚠️  Já existe: {destino}. Use --force para re-baixar.")
                    await asyncio.sleep(0.5)
                    continue
            await self._baixar_com_progresso(url, destino)
            logger.info(f"     💤 Aguardando 3s (Rate Limit CGU)...")
            await asyncio.sleep(3.0)

    async def baixar_ceap_camara(self):
        """Baixa dados de CEAP (cotas de exercício parlamentar da Câmara)."""
        logger.info("=" * 70)
        logger.info(f"💳 CÂMARA | CEAP {self.ano_alvo}")
        logger.info("=" * 70)
        url = FONTES["cgu"]["ceap"].format(ano=self.ano_alvo)
        destino = self.pasta_destino / f"ceap_camara_{self.ano_alvo}.csv.zip"
        if destino.exists():
            if self.force:
                logger.warning(f"   🔥 --force: deletando {destino.name}")
                destino.unlink()
            else:
                logger.warning(f"   ⚠️  Já existe. Use --force para re-baixar.")
                return
        logger.info(f"   Fonte: {url}")
        await self._baixar_com_progresso(url, destino)

    # ── IBGE: LISTA DE MUNICÍPIOS ─────────────────────────────────────────────
    async def baixar_municipios_ibge(self):
        """Baixa lista completa de municípios do IBGE (útil para validar jurisdição)."""
        logger.info("=" * 70)
        logger.info("🗺️  IBGE | Lista de Municípios")
        logger.info("=" * 70)
        destino = self.pasta_destino / "ibge_municipios.json"
        if destino.exists():
            if self.force:
                logger.warning(f"   🔥 --force: deletando {destino.name}")
                destino.unlink()
            else:
                logger.warning(f"   ⚠️  Já existe. Use --force para re-baixar.")
                return
        url = FONTES["ibge"]["municipios"]
        logger.info(f"   GET {url}")
        try:
            r = await self.cliente.get(url)
            r.raise_for_status()
            municipios = r.json()
            with open(destino, "w", encoding="utf-8") as f:
                import json
                json.dump(municipios, f, ensure_ascii=False, indent=2)
            logger.info(f"   ✅ {len(municipios)} municípios salvos em {destino}")
            self.stats["ok"] += 1
        except httpx.HTTPStatusError as e:
            logger.error(f"   ❌ IBGE retornou HTTP {e.response.status_code}")
            self.stats["erro"] += 1
        except Exception as e:
            logger.error(f"   ❌ Erro IBGE: {e}")
            self.stats["erro"] += 1

    # ── VALIDADOR DE JURISDIÇÃO MUNICIPAL ────────────────────────────────────
    def verificar_jurisdicao_municipal(self, cargo: str) -> bool:
        """
        Filtro rigoroso de jurisdição.
        Retorna True APENAS para cargos municipais legítimos.
        """
        cargo_up = cargo.strip().upper()
        CARGOS_MUNICIPAIS = {"PREFEITO", "VICE-PREFEITO", "VEREADOR"}
        CARGOS_PROIBIDOS  = {"DEPUTADO", "SENADOR", "PRESIDENTE", "GOVERNADOR",
                              "MINISTRO", "SECRETÁRIO ESTADUAL"}

        for proibido in CARGOS_PROIBIDOS:
            if proibido in cargo_up:
                logger.warning(f"[JURISDICAO] Cargo '{cargo_up}' REJEITADO — esfera federal/estadual")
                return False

        for permitido in CARGOS_MUNICIPAIS:
            if permitido in cargo_up:
                return True

        logger.warning(f"[JURISDICAO] Cargo '{cargo_up}' desconhecido — rejeitado por precaução")
        return False

    # ── RESUMO FINAL ─────────────────────────────────────────────────────────
    def imprimir_resumo(self):
        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 RESUMO DA COLETA")
        logger.info("=" * 70)
        logger.info(f"   ✅ Arquivos baixados com sucesso: {self.stats['ok']}")
        logger.info(f"   ❌ Erros de download:            {self.stats['erro']}")
        logger.info(f"   📦 Total baixado:                {self.stats['bytes']/1024/1024:.2f} MB")
        logger.info(f"   📁 Pasta de dados:               {self.pasta_destino.absolute()}")
        logger.info("=" * 70)

    async def fechar(self):
        await self.cliente.aclose()


# ── MAIN ──────────────────────────────────────────────────────────────────────
async def main(ano: int, fontes: list, force: bool = False, injetar: bool = False):
    logger.info("")
    logger.info("=" * 70)
    logger.info("  ████ MOTOR DE EXTRAÇÃO ANTIGRAVITY — GovTech Trasparente ████")
    logger.info(f"  Ano-alvo: {ano} | Fontes: {', '.join(fontes)} | Force: {force} | Injetar Neo4j: {injetar}")
    logger.info(f"  Iniciado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info("=" * 70)
    logger.info("")

    motor = MotorExtracaoGoverno(ano_alvo=ano, force=force)

    try:
        # Municípios sempre — base para validação de jurisdição
        if "ibge" in fontes or "todos" in fontes:
            await motor.baixar_municipios_ibge()

        if "tse" in fontes or "todos" in fontes:
            await motor.baixar_dump_tse_candidatos()
            logger.info("  💤 Pausa de 5s entre downloads (Rate Limit TSE)...")
            await asyncio.sleep(5.0)
            await motor.baixar_bens_candidatos_tse()

        if "cgu" in fontes or "todos" in fontes:
            logger.info("  💤 Pausa de 5s antes do CGU...")
            await asyncio.sleep(5.0)
            await motor.baixar_ceis_cnep_cgu()
            await asyncio.sleep(3.0)
            await motor.baixar_ceap_camara()

    except KeyboardInterrupt:
        logger.warning("")
        logger.warning("⚠️  INTERROMPIDO PELO USUÁRIO (Ctrl+C)")
        logger.warning("   Os arquivos baixados até agora foram salvos.")
    except Exception as e:
        logger.critical(f"💥 ERRO CRÍTICO NÃO TRATADO: {type(e).__name__}: {e}")
        raise
    finally:
        motor.imprimir_resumo()
        await motor.fechar()
        logger.info("✅ Motor de coleta finalizado.")

    # ── FASE 2: INJEÇÃO NO NEO4J (opcional, após download) ───────────────────
    if injetar:
        logger.info("")
        logger.info("=" * 70)
        logger.info("  🕸️  INICIANDO INJEÇÃO NO NEO4J (Fase 2)")
        logger.info("=" * 70)
        try:
            from injetor_neo4j import main as injetar_neo4j
            injetar_neo4j(ano=ano, fontes=fontes)
        except ImportError:
            logger.error("❌ injetor_neo4j.py não encontrado. Execute manualmente:")
            logger.error(f"   python injetor_neo4j.py --ano {ano} --fonte {fontes[0]}")
        except Exception as e:
            logger.error(f"❌ Erro na injeção Neo4j: {type(e).__name__}: {e}")
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Motor de ETL — Dados Governamentais Brasileiros",
        epilog="Exemplos:\n  python coletor_anual.py --ano 2024 --fonte tse\n  python coletor_anual.py --ano 2024 --force --injetar"
    )
    parser.add_argument("--ano",   type=int, default=2024,
                        choices=[2018, 2020, 2022, 2024],
                        help="Ano eleitoral alvo (padrão: 2024)")
    parser.add_argument("--fonte", type=str, default="todos",
                        choices=["tse", "cgu", "ibge", "todos"],
                        help="Fonte de dados a baixar (padrão: todos)")
    parser.add_argument("--force", action="store_true", default=False,
                        help="Força re-download: deleta arquivos existentes antes de baixar")
    parser.add_argument("--injetar", action="store_true", default=False,
                        help="Após download, injeta os CSVs no Neo4j automaticamente")
    args = parser.parse_args()

    asyncio.run(main(ano=args.ano, fontes=[args.fonte], force=args.force, injetar=args.injetar))

