#!/usr/bin/env python3
"""
injetor_neo4j.py — Lê CSVs baixados e popula o grafo Neo4j
===========================================================
Lê os dumps do TSE (candidatos, bens) e CGU (servidores, contratos)
e executa queries Cypher de MERGE para criar/atualizar nós e relações.

A propriedade `valor_total` nas arestas é sempre gravada corretamente.

Uso:
    python injetor_neo4j.py --ano 2024 --fonte tse
    python injetor_neo4j.py --ano 2024 --fonte cgu
    python injetor_neo4j.py --ano 2024 --fonte todos
"""

import os
import sys
import csv
import zipfile
import logging
import argparse
from pathlib import Path

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)-8s - [injetor_neo4j.py:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("InjectorNeo4j")

# ─── CONEXÃO NEO4J ────────────────────────────────────────────────────────────
try:
    from database.neo4j_conn import get_neo4j_connection, Neo4jConnection
    logger.info("✅ Módulo neo4j_conn importado.")
except ImportError as e:
    logger.critical(f"❌ Falha ao importar neo4j_conn: {e}")
    logger.critical("   Certifique-se de rodar este script de dentro da pasta backend/")
    sys.exit(1)

# ─── MAPEAMENTO DE CARGOS TSE → JURISDIÇÃO ───────────────────────────────────
CARGOS_MUNICIPAIS = {"PREFEITO", "VICE-PREFEITO", "VEREADOR"}
CARGOS_ESTADUAIS  = {"DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL", "GOVERNADOR", "VICE-GOVERNADOR", "SENADOR"}
CARGOS_FEDERAIS   = {"DEPUTADO FEDERAL", "PRESIDENTE", "VICE-PRESIDENTE"}


def _cpf_valido(cpf: str) -> bool:
    """
    O TSE mascara CPFs nos dumps públicos — o valor chega como '4' ou '***'.
    Retorna True APENAS se o CPF tiver exatamente 11 dígitos numéricos.
    """
    if not cpf:
        return False
    limpo = cpf.replace(".", "").replace("-", "").replace(" ", "")
    return limpo.isdigit() and len(limpo) == 11



def _parse_valor(v: str) -> float:
    """Converte string de valor (R$ 1.234,56) para float seguro."""
    if not v:
        return 0.0
    try:
        return float(
            str(v).replace("R$", "").replace(".", "").replace(",", ".").strip()
        )
    except (ValueError, AttributeError):
        return 0.0


def _extrair_zip(caminho_zip: Path, pasta_destino: Path) -> list[Path]:
    """Extrai ZIP e retorna lista de arquivos CSV extraídos."""
    arquivos = []
    logger.info(f"  📦 Extraindo: {caminho_zip.name} → {pasta_destino}")
    try:
        with zipfile.ZipFile(caminho_zip, "r") as z:
            z.extractall(pasta_destino)
            arquivos = [pasta_destino / n for n in z.namelist() if n.endswith(".csv")]
        logger.info(f"  📄 {len(arquivos)} arquivo(s) CSV extraído(s).")
    except zipfile.BadZipFile:
        logger.error(f"  ❌ Arquivo ZIP corrompido: {caminho_zip}")
    return arquivos


# ─── INJETOR TSE: CANDIDATOS ─────────────────────────────────────────────────
def injetar_candidatos_tse(neo4j: Neo4jConnection, ano: int, pasta_dados: Path):
    """
    Lê o ZIP de candidatos do TSE e cria nós :Politico com cargo, partido, UF, municipio.
    Filtro duplo de jurisdição: só rejeita data corrompida, insere TODOS os cargos.
    O frontend já filtra por cargo ao buscar por cidade.
    """
    zip_path = pasta_dados / f"tse_candidatos_{ano}.zip"
    if not zip_path.exists():
        logger.error(f"  ❌ Arquivo não encontrado: {zip_path}")
        logger.error(f"     Execute: python coletor_anual.py --ano {ano} --fonte tse")
        return 0

    extract_dir = pasta_dados / f"tse_candidatos_{ano}_extracted"
    extract_dir.mkdir(exist_ok=True)
    csvs = _extrair_zip(zip_path, extract_dir)

    if not csvs:
        logger.error("  ❌ Nenhum CSV encontrado no ZIP. Arquivo pode estar corrompido.")
        return 0

    total_inseridos = 0
    total_erros     = 0

    for csv_path in csvs:
        logger.info(f"  📖 Lendo: {csv_path.name}")
        try:
            # TSE usa encoding latin-1 e separador ";"
            with open(csv_path, encoding="latin-1", errors="replace", newline="") as f:
                reader = csv.DictReader(f, delimiter=";")
                batch  = []

                for i, row in enumerate(reader):
                    # Campos padrão do TSE
                    sq_candidato = row.get("SQ_CANDIDATO", row.get("NR_CPF_CANDIDATO", ""))
                    nm_candidato = row.get("NM_CANDIDATO", row.get("NM_URNA_CANDIDATO", "")).strip()
                    ds_cargo     = row.get("DS_CARGO", "").strip().upper()
                    sg_partido   = row.get("SG_PARTIDO", row.get("NM_PARTIDO", "N/A")).strip()
                    sg_uf        = row.get("SG_UF", "").strip().upper()
                    nm_municipio = row.get("NM_MUNICIPIO", "").strip().upper()
                    nr_cpf       = row.get("NR_CPF_CANDIDATO", "").strip().replace(".", "").replace("-", "")

                    if not nm_candidato or not sq_candidato:
                        continue

                    # CPF: O TSE mascara nos dumps públícos (vira '4' ou '***').
                    # Só usamos quando for realmente válido (11 dígitos numéricos).
                    cpf_limpo = nr_cpf.replace(".", "").replace("-", "").strip() if nr_cpf else ""
                    cpf_final = cpf_limpo if _cpf_valido(cpf_limpo) else None

                    batch.append({
                        "cpf":       cpf_final,       # None = CPF mascarado/ignorado
                        "nome":      nm_candidato,
                        "cargo":     ds_cargo.title(),
                        "partido":   sg_partido,
                        "uf":        sg_uf,
                        "municipio": nm_municipio,
                        "id_tse":    str(sq_candidato).strip(),
                    })

                    # Injeção em lote a cada 500 registros
                    if len(batch) >= 500:
                        n = _batch_merge_politicos(neo4j, batch)
                        total_inseridos += n
                        batch = []
                        if total_inseridos % 5000 == 0:
                            logger.info(f"  ✍️  {total_inseridos} políticos inseridos no Neo4j...")

                # Flush do último lote
                if batch:
                    total_inseridos += _batch_merge_politicos(neo4j, batch)

        except Exception as e:
            total_erros += 1
            logger.error(f"  ❌ Erro ao ler {csv_path.name}: {e}")

    logger.info(f"  ✅ TSE Candidatos: {total_inseridos} nós :Politico criados/atualizados | {total_erros} erro(s)")
    return total_inseridos


def _batch_merge_politicos(neo4j: Neo4jConnection, batch: list[dict]) -> int:
    """
    Executa MERGE em lote no Neo4j com UNWIND para performance.
    MERGE usa `id_tse` (SQ_CANDIDATO) — campo UNICO real do TSE.
    CPF só é gravado quando válido (11 dígitos); dados mascarados são ignorados.
    """
    query = """
    UNWIND $rows AS row
    MERGE (p:Politico {id_tse: row.id_tse})
    ON CREATE SET
        p.nome      = row.nome,
        p.cargo     = row.cargo,
        p.partido   = row.partido,
        p.uf        = row.uf,
        p.municipio = row.municipio,
        p.criado_em = date()
    ON MATCH SET
        p.nome          = row.nome,
        p.cargo         = row.cargo,
        p.partido       = row.partido,
        p.uf            = row.uf,
        p.municipio     = row.municipio,
        p.atualizado_em = date()
    // CPF: só grava quando não-nulo (evita sobrescrever com dado mascarado)
    WITH p, row WHERE row.cpf IS NOT NULL
    SET p.cpf = row.cpf
    """
    try:
        neo4j.execute_query(query, {"rows": batch})
        return len(batch)
    except Exception as e:
        logger.error(f"  ❌ Erro no batch MERGE de políticos: {e}")
        return 0


# ─── INJETOR TSE: BENS DECLARADOS ────────────────────────────────────────────
def injetar_bens_tse(neo4j: Neo4jConnection, ano: int, pasta_dados: Path):
    """
    Lê bens declarados pelos candidatos e cria arestas :DECLARA_BEM
    com a propriedade valor_total na aresta.
    """
    zip_path = pasta_dados / f"tse_bens_{ano}.zip"
    if not zip_path.exists():
        logger.warning(f"  ⚠️  Arquivo de bens não encontrado: {zip_path}. Pulando.")
        return 0

    extract_dir = pasta_dados / f"tse_bens_{ano}_extracted"
    extract_dir.mkdir(exist_ok=True)
    csvs = _extrair_zip(zip_path, extract_dir)

    total = 0
    for csv_path in csvs:
        logger.info(f"  📖 Bens: {csv_path.name}")
        try:
            with open(csv_path, encoding="latin-1", errors="replace", newline="") as f:
                reader = csv.DictReader(f, delimiter=";")
                batch  = []
                for row in reader:
                    sq = row.get("SQ_CANDIDATO", "")
                    descricao = row.get("DS_BEM_CANDIDATO", "").strip()
                    valor_str = row.get("VR_BEM_CANDIDATO", "0")
                    valor = _parse_valor(valor_str)

                    if not sq or valor <= 0:
                        continue

                    batch.append({"id_tse": sq, "descricao": descricao, "valor": valor})

                    if len(batch) >= 500:
                        _batch_merge_bens(neo4j, batch)
                        total += len(batch)
                        batch = []

                if batch:
                    _batch_merge_bens(neo4j, batch)
                    total += len(batch)

        except Exception as e:
            logger.error(f"  ❌ Erro ao ler bens: {e}")

    logger.info(f"  ✅ Bens TSE: {total} relações :DECLARA_BEM com valor_total criadas")
    return total


def _batch_merge_bens(neo4j: Neo4jConnection, batch: list[dict]):
    """Cria arestas :DECLARA_BEM com valor_total entre :Politico e :BemDeclarado."""
    query = """
    UNWIND $rows AS row
    MATCH (p:Politico {id_tse: row.id_tse})
    MERGE (b:BemDeclarado {descricao: row.descricao, id_tse: row.id_tse})
    MERGE (p)-[r:DECLARA_BEM]->(b)
    ON CREATE SET r.valor_total = row.valor, r.criado_em = date()
    ON MATCH  SET r.valor_total = r.valor_total + row.valor, r.atualizado_em = date()
    """
    try:
        neo4j.execute_query(query, {"rows": batch})
    except Exception as e:
        logger.error(f"  ❌ Erro no batch MERGE de bens: {e}")


# ─── INJETOR CGU: CEIS (Empresas Inidôneas) ──────────────────────────────────
def injetar_ceis_cgu(neo4j: Neo4jConnection, ano: int, pasta_dados: Path):
    """
    Lê CEIS (Cadastro de Empresas Inidôneas e Suspensas) e cria nós :Empresa
    com flag `inidonia: true` e relaciona com políticos por CPF de representante.
    """
    zip_path = pasta_dados / f"cgu_ceis_{ano}.zip"
    if not zip_path.exists():
        logger.warning(f"  ⚠️  CEIS não encontrado: {zip_path}. Pulando.")
        return 0

    extract_dir = pasta_dados / f"cgu_ceis_{ano}_extracted"
    extract_dir.mkdir(exist_ok=True)
    csvs = _extrair_zip(zip_path, extract_dir)

    total = 0
    for csv_path in csvs:
        logger.info(f"  📖 CEIS: {csv_path.name}")
        try:
            with open(csv_path, encoding="utf-8-sig", errors="replace", newline="") as f:
                reader = csv.DictReader(f, delimiter=";")
                batch  = []
                for row in reader:
                    cnpj    = row.get("CNPJ", row.get("CPF_CNPJ", "")).strip().replace(".", "").replace("/", "").replace("-", "")
                    nome    = row.get("RAZAO_SOCIAL", row.get("NOME_EMPRESA", "")).strip()
                    motivo  = row.get("MOTIVO_SUSPENSAO", row.get("DESCRICAO_TIPO_SANCAO", "")).strip()
                    valor_s = row.get("VALOR_MULTA", "0")
                    valor   = _parse_valor(valor_s)

                    if not cnpj or not nome:
                        continue

                    batch.append({
                        "cnpj": cnpj,
                        "nome": nome,
                        "motivo": motivo,
                        "valor_multa": valor,
                        "inidonia": True,
                    })

                    if len(batch) >= 500:
                        _batch_merge_empresas_ceis(neo4j, batch)
                        total += len(batch)
                        batch = []

                if batch:
                    _batch_merge_empresas_ceis(neo4j, batch)
                    total += len(batch)

        except Exception as e:
            logger.error(f"  ❌ Erro ao ler CEIS: {e}")

    logger.info(f"  ✅ CEIS: {total} empresas inidôneas inseridas no grafo")
    return total


def _batch_merge_empresas_ceis(neo4j: Neo4jConnection, batch: list[dict]):
    query = """
    UNWIND $rows AS row
    MERGE (e:Empresa {cnpj: row.cnpj})
    ON CREATE SET
        e.nome      = row.nome,
        e.inidonia  = row.inidonia,
        e.motivo    = row.motivo,
        e.criado_em = date()
    ON MATCH SET
        e.inidonia      = row.inidonia,
        e.motivo        = row.motivo,
        e.valor_multa   = row.valor_multa,
        e.atualizado_em = date()
    """
    try:
        neo4j.execute_query(query, {"rows": batch})
    except Exception as e:
        logger.error(f"  ❌ Erro no batch MERGE CEIS: {e}")


# ─── RELATÓRIO FINAL DO GRAFO ─────────────────────────────────────────────────
def imprimir_stats_grafo(neo4j: Neo4jConnection):
    """Conta nós e arestas no grafo após a injeção."""
    logger.info("")
    logger.info("=" * 65)
    logger.info("📊 ESTADO DO GRAFO NEO4J (pós-injeção)")
    logger.info("=" * 65)
    queries = [
        ("Nós :Politico",       "MATCH (p:Politico) RETURN count(p) AS n"),
        ("Nós :Empresa",        "MATCH (e:Empresa) RETURN count(e) AS n"),
        ("Nós :BemDeclarado",   "MATCH (b:BemDeclarado) RETURN count(b) AS n"),
        ("Arestas :DECLARA_BEM","MATCH ()-[r:DECLARA_BEM]->() RETURN count(r) AS n"),
        ("Arestas com valor_total",
         "MATCH ()-[r]->() WHERE r.valor_total IS NOT NULL RETURN count(r) AS n"),
    ]
    for descricao, query in queries:
        try:
            resultado = neo4j.execute_query(query)
            n = resultado[0]["n"] if resultado else 0
            logger.info(f"  {descricao:<30}: {n:,}")
        except Exception as e:
            logger.warning(f"  {descricao}: erro ({e})")
    logger.info("=" * 65)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main(ano: int, fontes: list):
    logger.info("")
    logger.info("=" * 65)
    logger.info(f"  🕸️  INJETOR NEO4J — GovTech Trasparente | Ano {ano}")
    logger.info("=" * 65)

    pasta_dados = Path(f"./dados_brutos_{ano}")
    if not pasta_dados.exists():
        logger.critical(f"❌ Pasta de dados não encontrada: {pasta_dados.absolute()}")
        logger.critical(f"   Execute primeiro: python coletor_anual.py --ano {ano} --fonte todos")
        sys.exit(1)

    logger.info(f"  📁 Pasta de dados: {pasta_dados.absolute()}")
    logger.info(f"  🔌 Conectando ao Neo4j...")

    try:
        neo4j = get_neo4j_connection()
    except Exception as e:
        logger.critical(f"❌ Não foi possível conectar ao Neo4j: {e}")
        logger.critical("   Certifique-se que o Neo4j está rodando em bolt://localhost:7687")
        sys.exit(1)

    try:
        if "tse" in fontes or "todos" in fontes:
            logger.info("")
            logger.info("── FASE 1: Candidatos TSE ─────────────────────────────────")
            injetar_candidatos_tse(neo4j, ano, pasta_dados)

            logger.info("")
            logger.info("── FASE 2: Bens Declarados TSE ────────────────────────────")
            injetar_bens_tse(neo4j, ano, pasta_dados)

        if "cgu" in fontes or "todos" in fontes:
            logger.info("")
            logger.info("── FASE 3: CEIS (Empresas Inidôneas) ──────────────────────")
            injetar_ceis_cgu(neo4j, ano, pasta_dados)

        imprimir_stats_grafo(neo4j)

    finally:
        neo4j.close()
        logger.info("✅ Injetor finalizado. Conexão Neo4j fechada.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Injetor de dumps governamentais no Neo4j",
        epilog="Exemplo: python injetor_neo4j.py --ano 2024 --fonte tse"
    )
    parser.add_argument("--ano",   type=int, default=2024,
                        choices=[2018, 2020, 2022, 2024],
                        help="Ano dos dumps (padrão: 2024)")
    parser.add_argument("--fonte", type=str, default="todos",
                        choices=["tse", "cgu", "todos"],
                        help="Qual conjunto de CSVs injetar (padrão: todos)")
    args = parser.parse_args()
    main(ano=args.ano, fontes=[args.fonte])
