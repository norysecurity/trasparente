from typing import Dict, Any

def calcular_score_politico(analise_ia: Dict[str, Any]) -> float:
    """
    Calcula o "Score_Serasa" do político com base nas Red Flags detectadas pela IA.
    A pontuação base é 1000 e vai perdendo pontos por infração.
    """
    pontuacao_base = 1000.0
    
    # Penalidades fixas baseadas no nível de risco (Opcional, além das flags)
    penalidades_risco = {
        "BAIXO": 0,
        "MEDIO": 50,
        "ALTO": 150,
        "CRITICO": 300
    }
    
    nivel_risco = analise_ia.get("nivel_risco", "BAIXO").upper()
    pontuacao_base -= penalidades_risco.get(nivel_risco, 0)
    
    # Penalidades baseadas na gravidade de cada Red Flag encontrada
    red_flags = analise_ia.get("red_flags", [])
    for flag in red_flags:
        gravidade = flag.get("gravidade", 1) # Gravidade de 1 a 10
        # Exemplo: Cada ponto de gravidade subtrai 25 pontos do score
        pontos_perdidos = gravidade * 25
        pontuacao_base -= pontos_perdidos
        
    # Garante que o Score nunca seja menor que zero ou maior que 1000
    return max(0.0, min(1000.0, pontuacao_base))

def gerar_relatorio_gamificado(analise_ia: Dict[str, Any]) -> Dict[str, Any]:
    score = calcular_score_politico(analise_ia)
    
    status = "Ficha Limpa 🟢"
    if score < 400:
        status = "Alerta Vermelho 🔴"
    elif score < 700:
        status = "Suspeito 🟡"
        
    return {
        "score_auditoria": score,
        "status_jogador": status,
        "conquistas_desbloqueadas": ["Primeiro Dossiê"] if score > 800 else ["Investigador Implacável"],
        "detalhes": analise_ia
    }
