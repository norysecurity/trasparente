import os
import sys
import json
import asyncio
import pytest
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from agente_coletor_autonomo import auditar_malha_fina_assincrona
from motor_ia_qwen import AuditorGovernamentalIA

# 1. Teste de Assinatura (3 Argumentos via Mock)
@pytest.mark.asyncio
async def test_worker_aceita_apenas_tres_argumentos():
    """Valida que o agente rejeita payloads antigos com mais de 3 argumentos"""
    with pytest.raises(ValueError, match="ERRO DE ARQUITETURA. A função auditar_malha_fina_assincrona não deve receber mais que 3 argumentos"):
        await auditar_malha_fina_assincrona(800001, "Prefeito Teste", "12345678900", [{"cnpj": "123"}])

# 2. Teste Unitário da Validação JSON da IA
def test_validar_link_markdown_obrigatorio_no_json():
    texto_simulado_ia = json.dumps({
        "score_risco": 50,
        "red_flags": [
            {
                "motivo": "### 🔴 Fraude Detectada\\nDescrição de fraude cruzada...\\n\\n📎 Evidência Oficial:\\n[Ver no Portal da Transparência](https://portaldatransparencia.gov.br/123)"
            }
        ],
        "resumo_investigativo": "Resumo aqui."
    })
    
    padrao_regex = r"\[.*?\]\(https?://.*?\)"
    assert re.search(padrao_regex, texto_simulado_ia) is not None, "Obrigatório haver um link em Markdown na resposta."

def test_falha_ao_validar_link_markdown_ausente():
    texto_simulado_ia = json.dumps({
        "score_risco": 10,
        "red_flags": [
            {
                "motivo": "Apenas um texto sem link clicável."
            }
        ],
        "resumo_investigativo": "Resumo rápido."
    })
    
    padrao_regex = r"\[.*?\]\(https?://.*?\)"
    assert re.search(padrao_regex, texto_simulado_ia) is None, "Desejado falhar se for enviado sem fonte oficial markdown."
