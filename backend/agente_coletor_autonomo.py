import asyncio
import os
import re
import requests
import fitz  # PyMuPDF
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

# Credenciais e Endpoints
CGU_API_KEY = os.getenv("CGU_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "govtech_password")

def get_neo4j_driver():
    try:
        from neo4j import GraphDatabase
        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except ImportError:
        print("Neo4j driver não instalado ou inacessível no Worker.")
        return None
    except Exception as e:
        print(f"Erro ao conectar ao Neo4j: {e}")
        return None

async def buscar_socios_receita(cnpj: str) -> list:
    """
    Objetivo: Descobrir familiares e laranjas usando a API pública do BrasilAPI.
    Retorno: Lista com nomes e cargos dos sócios do QSA.
    """
    print(f"🔍 Buscando Quadro de Sócios e Administradores (QSA) para o CNPJ: {cnpj}")
    cnpj_limpo = re.sub(r'[^0-9]', '', cnpj)
    
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
    try:
        # Executa requisição assíncrona usando o loop do asyncio
        resposta = await asyncio.to_thread(requests.get, url, timeout=10)
        if resposta.status_code == 200:
            dados = resposta.json()
            qsa = dados.get("qsa", [])
            socios = [{"nome": s.get("nome_socio"), "cargo": s.get("qualificacao_socio")} for s in qsa]
            print(f"  ✅ Encontrados {len(socios)} sócios.")
            return socios
        else:
            print(f"  ❌ Erro ao buscar QSA (Status: {resposta.status_code})")
            return []
    except Exception as e:
        print(f"  ⚠️ Falha de comunicação na API da Receita: {e}")
        return []

async def buscar_contratos_portal_transparencia(cnpj: str) -> list:
    """
    Objetivo: Ver se a empresa do familiar recebeu dinheiro do governo via Portal da Transparência.
    """
    print(f"💰 Verificando Recebimento de Verbas Públicas para o CNPJ: {cnpj}")
    if not CGU_API_KEY:
        print("  ⚠️ CGU_API_KEY não configurada. Simulando retorno.")
        # Simulação para desenvolvimento
        return [
            {"orgao": "Ministério da Saúde", "valor": "R$ 1.500.000,00", "data": "2023-05-10"}
        ]
        
    url = "https://api.portaldatransparencia.gov.br/api-de-dados/contratos"
    headers = {"chave-api-dados": CGU_API_KEY}
    params = {"cnpjContratada": re.sub(r'[^0-9]', '', cnpj), "pagina": 1}
    
    try:
        resposta = await asyncio.to_thread(requests.get, url, headers=headers, params=params, timeout=10)
        if resposta.status_code == 200:
            contratos = resposta.json()
            resultados = []
            for c in contratos:
                resultados.append({
                    "orgao": c.get("orgaoSuperior", {}).get("nomeOrgao"),
                    "valor": c.get("valorInicial"),
                    "data": c.get("dataAssinatura")
                })
            print(f"  ✅ Encontrados {len(resultados)} contratos públicos.")
            return resultados
        return []
    except Exception as e:
        print(f"  ⚠️ Falha ao buscar contratos: {e}")
        return []

async def raspar_diario_oficial_uniao_playwright(termo_busca: str):
    """
    Objetivo: Raspar edições do Diário Oficial usando automação Headless.
    Baixa o PDF do resultado, extrai o texto com PyMuPDF e caça CNPJs e Valores (Licitações).
    """
    print(f"📰 Iniciando OSINT no Diário Oficial da União (Termo: {termo_busca})")
    cnpjs_detectados = set()
    valores_detectados = set()
    
    async with async_playwright() as p:
        navegador = await p.chromium.launch(headless=True)
        pagina = await navegador.new_page()
        
        try:
            # Acessando site de busca da Imprensa Nacional (Simulador Simplificado)
            print("  -> Navegando para in.gov.br...")
            # Note: A busca no DOU costuma ser complexa; esta parte simula a busca de um documento em PDF
            # Na versão final em produção, o scraper iria navegar nos inputs e clicar em buscar
            # Como a URL do in.gov muda muito, vamos simular a extração de um arquivo PDF local/vazio para a prova de conceito
            
            # Simulando que o playwright encontrou o link do PDF da licitação e efetuou download
            pdf_path = "extrato_contrato_mock.pdf"
            
            # Criando um PDF falso com dados de corrupção usando fitz para o teste se não existir
            if not os.path.exists(pdf_path):
                doc = fitz.open()
                page = doc.new_page()
                page.insert_text((50, 50), f"EXTRATO DE CONTRATO Nº 15/2023. O {termo_busca} assinou " 
                                           f"contrato com a EMPRESA FANTASMA S/A, CNPJ: 12.345.678/0001-90, no valor de R$ 5.430.200,50.")
                doc.save(pdf_path)
            
            # --- Início da Extração PDF (PyMuPDF) ---
            print("  -> Extraindo texto do PDF Oficial...")
            doc = fitz.open(pdf_path)
            texto_completo = ""
            for num_pagina in range(len(doc)):
                pagina_pdf = doc.load_page(num_pagina)
                texto_completo += pagina_pdf.get_text("text") + " "
            
            # --- Início da Caça às Bruxas (Regex) ---
            print("  -> Minerando Padrões Suspeitos via Regex...")
            # Padrão CNPJ: 00.000.000/0000-00
            padrao_cnpj = re.compile(r'\d{2}\.\d{3}\.\d{3}/\d{4}\-\d{2}')
            # Padrão Valores em Reais: R$ 1.000,00 ou R$ 100.000,00
            padrao_valor = re.compile(r'R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}')
            
            cnpjs_detectados.update(padrao_cnpj.findall(texto_completo))
            valores_detectados.update(padrao_valor.findall(texto_completo))
            
            print(f"  🚨 Alerta: Identificados {len(cnpjs_detectados)} CNPJs e {len(valores_detectados)} Montantes Financeiros no texto publicado.")
            
        except Exception as e:
            print(f"  ❌ Erro durante a automação Crawler: {e}")
        finally:
            await navegador.close()
            
    return list(cnpjs_detectados), list(valores_detectados)

def salvar_malha_fina_neo4j(grafos_dados: dict):
    """
    Grava os nós e as arestas de relacionamento cruzado banco de grafos Neo4j.
    """
    driver = get_neo4j_driver()
    if not driver:
        print("📛 Neo4j Offline. Os relacionamentos não serão salvaguardados.")
        return

    query = """
    // 1. Cria Político
    MERGE (p:Politico {nome: $politico_nome})
    ON CREATE SET p.cpf = $politico_cpf, p.auditado_em = timestamp()
    
    // 2. Cria Empresas Declaradas pelo TSE
    FOREACH (emp IN $empresas |
        MERGE (e:Empresa {cnpj: emp.cnpj})
        ON CREATE SET e.nome = emp.nome
        MERGE (p)-[:DECLARA_SER_DONO_DE]->(e)
    )
    
    // 3. Cria Familiares/Sócios
    FOREACH (socio IN $socios |
        MERGE (s:Pessoa {nome: socio.nome})
        MERGE (p)-[:TEM_ASSOCIACAO_COM {cargo: socio.cargo}]->(s)
        MERGE (s)-[:OPERA_NA_EMPRESA]->(e) 
    )
    
    // 4. Cria Licitações/Órgãos (Rabo Preso)
    FOREACH (contrato IN $contratos |
        MERGE (o:Orgao {nome: contrato.orgao})
        MERGE (c:Contrato {valor: contrato.valor, data: contrato.data})
        MERGE (e)-[:RECEBEU_VERBA_DE]->(c)-[:PAGO_POR]->(o)
        
        // Se a empresa ligada ao politico recebeu verba, marca a bandeira vermelha
        MERGE (p)-[:ALERTA_VERMELHO {motivo: "Empresa ligada participou de licitação"}]->(c)
    )
    """
    try:
        with driver.session() as session:
            session.run(query, **grafos_dados)
            print(f"🕸️ Teia de Relacionamentos do Político {grafos_dados['politico_nome']} atualizada no Neo4j com Sucesso!")
    except Exception as e:
        print(f"Erro ao salvar grafos: {e}")
    finally:
        driver.close()

async def auditar_malha_fina(nome_politico: str, cpf_politico: str, cnpjs_reais: list = None):
    """
    Função Mestra que orquestra a inteligência investigativa:
    1. Lê CNPJs reais de despesas -> 2. Busca API Receita (Laranjas) -> 3. Busca Licitações (Portal) -> 4. Cruza no Grafo Neo4j.
    """
    print(f"\n=======================================================")
    print(f"🕵️  WORKER INICIANDO AUDITORIA: {nome_politico.upper()}")
    print(f"=======================================================")
    
    if not cnpjs_reais:
        print("📋 Sem CNPJs oficiais. Usando CNPJ de validação.")
        cnpjs_reais = ["00000000000191"] # CNPJ do BB para teste
        
    print(f"📋 Analisando {len(cnpjs_reais)} CNPJs vinculados às verbas do mandato...")
    empresas_do_politico = [{"nome": f"Fornecedor {cnpj}", "cnpj": cnpj} for cnpj in cnpjs_reais]
    
    todos_socios = []
    todos_contratos = []
    
    # b) Raspa Sócios e Colaboradores ligados às empresas do Político
    for empresa in empresas_do_politico:
        socios = await buscar_socios_receita(empresa["cnpj"])
        todos_socios.extend(socios)
        
        # c) Raspa licitações das empresas do Político ou de Laranjas
        contratos = await buscar_contratos_portal_transparencia(empresa["cnpj"])
        todos_contratos.extend(contratos)
        
    # Extra) Busca no Diário Oficial por Menções
    cnpjs_dou, valores_dou = await raspar_diario_oficial_uniao_playwright(nome_politico)
    
    # d) Conecta no Neo4j e Persiste Grafo Complexo
    dados_grafo = {
        "politico_nome": nome_politico,
        "politico_cpf": cpf_politico,
        "empresas": empresas_do_politico,
        "socios": todos_socios,
        "contratos": todos_contratos
    }
    
    salvar_malha_fina_neo4j(dados_grafo)
    print(f"✅ Auditoria Concluída: {nome_politico}\n")

async def worker_noturno():
    """
    Loop assíncrono projetado para rodar em standalone e analisar filas do Redis/RabbitMQ.
    """
    print("🌙 Inicializando Worker Autônomo de Varredura Noturna OSINT...")
    alvos = [
        {"nome": "Luiz Inácio Lula da Silva", "cpf": "000.000.000-01"},
        {"nome": "Romeu Zema", "cpf": "111.111.111-02"},
    ]
    
    for alvo in alvos:
        await auditar_malha_fina(alvo["nome"], alvo["cpf"])
        await asyncio.sleep(2) # Respeitar limites das APIs

if __name__ == "__main__":
    # Roda o worker em ambiente izolado
    asyncio.run(worker_noturno())
