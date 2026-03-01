import asyncio
import os
import json
import logging
from datetime import datetime

# Logging e Drivers
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgenteTrasparente")

from motor_ia_qwen import AuditorGovernamentalIA

# Instância do Drive Manager (Para salvar o laudo final)
try:
    drive_manager = GoogleDriveManager()
except Exception as e:
    logger.error(f"Erro ao instanciar Drive Manager: {e}")
    drive_manager = None

async def auditar_malha_fina_assincrona(id_politico: int, nome_politico: str, cpf_real: str) -> tuple[int, list, list]:
    """
    Motor Central de Auditoria Governamental (Modelo Bruno - Offline First)
    
    Nova arquitetura:
    1. O Agente NÃO FAZ REQUESTS GET nem Web Scraping no momento do clique.
    2. Ele consulta o Banco em Grafo (Neo4j) que já foi alimentado de madrugada pelos Workers (ETL em lote).
    3. Entrega o Subgrafo Mastigado para a IA Qwen emitir o veredito pericial.
    4. Salva o Dossiê para a Interface Gráfica e nuvem.
    """
    logger.info(f"\n🚀 INICIANDO AUDITORIA GOVTECH OFFLINE: {nome_politico.upper()} | CPF: {cpf_real}")
    
    empresas_detalhadas = []
    
    # ---------------------------------------------------------
    # PASSO 1: EXTRAIR O SUBGRAFO LOCAL (NEO4J)
    # ---------------------------------------------------------
    neo4j_db = get_neo4j_connection()
    logger.info("🕸️ Buscando conexões no Banco de Grafos Local...")
    
    if not cpf_real or cpf_real == "00000000000":
        logger.warning("CPF Inválido. A precisão do grafo será nula.")
        subgrafo_json = {"erro": "CPF não fornecido para traçado da teia."}
    else:
        subgrafo_json = neo4j_db.extrair_subgrafo_para_ia(cpf_real)
        
    neo4j_db.close()
    
    # Prepara visualização pro FrontEnd (Tabelas de evidências)
    if "conexoes_diretas" in subgrafo_json:
        for c in subgrafo_json["conexoes_diretas"]:
            empresas_detalhadas.append({
                "nome": c.get("empresa_nome"),
                "cnpj": c.get("cnpj", "N/A"),
                "cargo": c.get("relacao", "VÍNCULO DETECTADO"),
                "valor": f"R$ {c.get('valor_envolvido', 0):,.2f}",
                "fonte": "DUMP GOVERNAMENTAL COLETADO"
            })

    # ---------------------------------------------------------
    # PASSO 2: PASSAR O SUBGRAFO PARA A IA (MOTOR COGNITIVO)
    # ---------------------------------------------------------
    logger.info("🤖 Enviando teia de conexões para a IA Qwen analisar anomalias...")
    motor_ia = AuditorGovernamentalIA()
    
    try:
        resultado_ia = await motor_ia.analisar_teia_financeira(subgrafo_json)
        score_risco = resultado_ia.get("score_risco", 20)
        
        red_flags = []
        for rf in resultado_ia.get("red_flags", []):
            red_flags.append({
                "data": datetime.now().strftime("%d/%m/%Y"), 
                "titulo": f"🤖 Alerta da IA", 
                "desc": rf.get("motivo", "Anomalia detectada."), 
                "fonte": "Auditoria de Grafo Qwen"
            })
            
        resumo_investigativo = resultado_ia.get("resumo_investigativo", "Análise inconclusiva.")
            
    except Exception as e:
        logger.error(f"❌ Erro ao invocar Motor da IA: {e}")
        score_risco = 30
        red_flags = [{"data": datetime.now().strftime("%d/%m/%Y"), "titulo": "Erro", "desc": "Falha na comunicação com o Motor de IA.", "fonte": "Sistema"}]
        resumo_investigativo = "Não foi possível gerar a perícia heurística das relações."

    # ---------------------------------------------------------
    # PASSO 3: GERAÇÃO DO DOSSIÊ OFICIAL
    # ---------------------------------------------------------
    os.makedirs("dossies", exist_ok=True)
    dossie = {
        "id_politico": id_politico,
        "cpf_politico": cpf_real,
        "nome_politico": nome_politico,
        "score_risco_calculado": score_risco,
        "resumo_investigativo": resumo_investigativo,
        "redFlags": red_flags,
        "empresas": empresas_detalhadas,
        "diagrama_relacional_cru": subgrafo_json,
        "data_auditoria_offline": datetime.now().isoformat()
    }
    
    caminho_arquivo = f"dossies/dossie_{id_politico}.json"
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(dossie, f, ensure_ascii=False, indent=4)
        
    # ---------------------------------------------------------
    # PASSO 4: REGISTRO NO DATA LAKE (GOOGLE DRIVE)
    # ---------------------------------------------------------
    if drive_manager:
        try:
            drive_manager.salvar_dossie_no_drive(nome_politico, caminho_arquivo)
        except Exception as e:
            logger.error(f"⚠️ Dossiê gerado localmente, mas não arquivado na nuvem por erro no Drive: {e}")

    logger.info(f"🏁 AUDITORIA FINALIZADA. Score emitido: {score_risco}/100")
    
    # O retorno deve ser compatível com a chamada original em gamificacao.py/main.py
    # Pontos perdidos é 1000 - score_risco se no antigo a base era 1000. Mas aqui vamos simplificar.
    # Assumindo que o score IA já é de Risco (0 = limpo, 100 = preso), 
    # mantemos uma reversão para Score Corridão do app "1000" pontos (0 perdido) etc.
    pontos_perdidos = int((score_risco / 100.0) * 1000)
    score_app = max(0, 1000 - pontos_perdidos)
    
    return score_app, red_flags, empresas_detalhadas
