import { NextResponse } from "next/server";
import { GoogleGenAI } from "@google/genai";
import * as dotenv from "dotenv";
import * as path from "path";

// Força leitura de `.env` que está na raiz primária
dotenv.config({ path: path.resolve(process.cwd(), '../.env') });

export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { politico_nome, empresas, redFlags, despesas } = body;

        // Validando Chave
        const apiKey = process.env.GEMINI_API_KEY;
        if (!apiKey) {
            return NextResponse.json({
                error: "GEMINI_API_KEY não configurada no servidor Next.js."
            }, { status: 500 });
        }

        const ai = new GoogleGenAI({ apiKey: apiKey });

        const prompt = `Você é um Analista Punitivo de OSINT e Corrupção (Estilo Operação Lava Jato / TCU). 
        Você está analisando o dossiê do político brasileiro: ${politico_nome}.
        
        Abaixo estão os dados financeiros raspados em tempo real (Receita Federal, IBAMA, CGU, Portal Transparência):
        
        1. RED FLAGS GOVERNAMENTAIS:
        ${JSON.stringify(redFlags, null, 2)}
        
        2. RELAÇÕES EMPRESARIAIS E CNPJs (Rabo Preso S/A):
        ${JSON.stringify(empresas, null, 2)}
        
        3. ÚLTIMAS DESPESAS DE GABINETE / CÂMARA (Amostragem Crítica):
        ${JSON.stringify(despesas, null, 2)}
        
        SUA TAREFA:
        Aja como a Máquina Aceleracionista de Bruno César. Analise profundamente e detecte as seguintes anomalias nas despesas (se houver):
        - Notas Fiscais Sequenciais ou Despesas fracionadas idênticas no mesmo dia/fornecedor (Típico de Caixa 2 ou Nota Fria).
        - Empresa recém aberta (ou com nome fantasia genérico) ganhando valor atípico.
        - Conflitos de Interesse visíveis entre as empresas do político e os gastos.
        
        REGRAS DE RETORNO:
        - NÃO invente fatos, cruze com o JSON fornecido rigidamente. Se a base for limpa, elogie.
        - Seja direto, cínico e técnico na sua resposta. (No máximo 4 parágrafos pequenos).
        - Use formatação Markdown (Negrito) para destacar os R$ Valores suspeitos e Nomes de Empresas falsas.
        
        Gere o laudo pericial final agora:
        `;

        // Executando no Modelo Obrigatório Gemini 3 Pro Preview
        const response = await ai.models.generateContent({
            model: "gemini-3-pro-preview",
            contents: prompt,
            config: {
                temperature: 0.2, // Baixa temperatura para fatos matemáticos/análise fria
            }
        });

        const parecerText = response.text;

        return NextResponse.json({
            status: "sucesso",
            insight: parecerText
        });

    } catch (e: any) {
        console.error("Erro na Auditoria IA:", e);
        return NextResponse.json({
            error: "Erro inesperado ao gerar a Auditoria de Inteligência Artificial.",
            details: e.message
        }, { status: 500 });
    }
}
