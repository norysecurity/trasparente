#!/usr/bin/env python3
"""
setup_e_injeta.py
=================
1. Conecta ao Neo4j
2. Remove a constraint problemática de cpf (se ainda existir)
3. Cria constraint UNIQUE em id_tse (chave real do TSE)
4. Cria índice em id_tse para acelerar o MATCH na Fase 2
5. Aguarda o índice ficar ONLINE (até 5 minutos)
6. Chama o injetor principal (injetor_neo4j.py)
"""

import os
import sys
import time
import subprocess

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
load_dotenv("../.env")

from neo4j import GraphDatabase

uri  = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
user = os.getenv("NEO4J_USER",     "neo4j")
pwd  = os.getenv("NEO4J_PASSWORD", "password")
ano  = sys.argv[1] if len(sys.argv) > 1 else "2024"

SEP = "=" * 65

print(f"\n{SEP}")
print("  🔧 SETUP NEO4J — GovTech Trasparente")
print(SEP)
print(f"  URI  : {uri}")
print(f"  User : {user}")
print(f"  Ano  : {ano}\n")

# ─── CONECTA ──────────────────────────────────────────────────────────────────
print("📡 Conectando ao Neo4j...")
try:
    driver = GraphDatabase.driver(uri, auth=(user, pwd), connection_timeout=15)
    driver.verify_connectivity()
    print("  ✅ Conexão OK\n")
except Exception as e:
    print(f"  ❌ Falha ao conectar: {e}")
    sys.exit(1)

# ─── AJUSTA CONSTRAINTS E ÍNDICES ─────────────────────────────────────────────
print("🛠️  Ajustando constraints e índices...")
with driver.session() as s:

    # Remove constraint problemática de cpf (se existir)
    try:
        s.run("DROP CONSTRAINT constraint_eb9d1cba IF EXISTS")
        print("  ✅ Constraint cpf removida (ou não existia)")
    except Exception as e:
        print(f"  ⚠️  Drop cpf: {e}")

    # Garante constraint UNIQUE em id_tse
    try:
        s.run("CREATE CONSTRAINT politico_id_tse IF NOT EXISTS FOR (p:Politico) REQUIRE p.id_tse IS UNIQUE")
        print("  ✅ Constraint UNIQUE id_tse garantida")
    except Exception as e:
        print(f"  ⚠️  Constraint id_tse: {e}")

    # Cria índice de busca em id_tse (para MATCH rápido na Fase 2)
    try:
        s.run("CREATE INDEX politico_id_tse_idx IF NOT EXISTS FOR (p:Politico) ON (p.id_tse)")
        print("  ✅ Índice id_tse criado (ou já existia)")
    except Exception as e:
        print(f"  ⚠️  Índice id_tse: {e}")

    # Aguarda o índice ficar ONLINE — polling a cada 5s por até 5 minutos
    print("\n⏳ Aguardando índice ficar ONLINE (até 5 min)...")
    t0 = time.time()
    while True:
        r = s.run(
            'SHOW INDEXES YIELD name, state '
            'WHERE name = "politico_id_tse_idx"'
        ).data()
        estado = r[0]["state"] if r else "CRIANDO"
        decorrido = int(time.time() - t0)
        print(f"  [{decorrido:>3}s] Índice: {estado}  (aguardando ONLINE...)", end="\r", flush=True)

        if estado == "ONLINE":
            print(f"\n  ✅ Índice ONLINE após {decorrido}s!")
            break

        if decorrido > 300:
            print(f"\n  ⚠️  Timeout de 5 min. Continuando mesmo assim (índice: {estado})")
            break

        time.sleep(5)

driver.close()

# ─── MOSTRA STATUS DO GRAFO ANTES ─────────────────────────────────────────────
print("\n📊 Estado atual do grafo:")
try:
    d2 = GraphDatabase.driver(uri, auth=(user, pwd), connection_timeout=10)
    with d2.session() as s:
        for desc, q in [
            ("Nós :Politico",    "MATCH (p:Politico) RETURN count(p) AS n"),
            ("Nós :BemDeclarado","MATCH (b:BemDeclarado) RETURN count(b) AS n"),
            ("Arestas :DECLARA_BEM","MATCH ()-[r:DECLARA_BEM]->() RETURN count(r) AS n"),
        ]:
            n = s.run(q).data()[0]["n"]
            print(f"  {desc:<28}: {n:,}")
    d2.close()
except Exception as e:
    print(f"  ⚠️  Não foi possível contar: {e}")

# ─── INICIA O INJETOR ─────────────────────────────────────────────────────────
print(f"\n{SEP}")
print(f"  🚀 Iniciando injetor_neo4j.py --ano {ano} --fonte tse")
print(f"{SEP}\n")

result = subprocess.run(
    [sys.executable, "injetor_neo4j.py", "--ano", ano, "--fonte", "tse"],
    cwd=os.path.dirname(os.path.abspath(__file__))
)
sys.exit(result.returncode)
