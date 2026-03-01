"use client";
import React, { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ZoomIn, ZoomOut, RotateCcw, Move, ExternalLink, AlertTriangle } from "lucide-react";

// ── TIPOS ──────────────────────────────────────────────────────────────────────
type DocType = "foto" | "documento" | "laudo" | "mapa" | "recorte" | "postit";
interface Alvo {
    nome: string; cargo: string; partido: string;
    status: "investigado" | "denunciado" | "condenado" | "suspeito";
    cpf?: string; valorDesviado?: string; processo?: string;
    fonte?: string; resumo: string;
}
interface DocItem {
    id: string; tipo: DocType; titulo?: string; subtitulo?: string; nota?: string;
    x: number; y: number; w: number; h: number; rot: number;
    pinColor?: string; rasgado?: boolean; alvo?: Alvo;
}
type Pos = { x: number; y: number };
type PosMap = Record<string, Pos>;
const TORN = [
    "polygon(0 0,100% 0,100% 82%,97% 86%,100% 89%,95% 93%,99% 97%,100% 100%,0 100%)",
    "polygon(0 0,100% 0,100% 100%,5% 100%,0 95%,4% 90%,0 85%,4% 80%,0 75%)",
    "polygon(0 3%,3% 0,7% 3%,4% 7%,100% 0,100% 100%,0 100%)",
];

// ── DADOS COM ALVOS ────────────────────────────────────────────────────────────
const DOCS: DocItem[] = [
    { id: "rec1", tipo: "recorte", titulo: "LICITAÇÃO SUSPEITA", subtitulo: "Contrato R$89M sem concorrência. Empresa criada 2 dias antes da licitação.", x: 1, y: 3, w: 160, h: 120, rot: -1.5, pinColor: "#3b82f6", rasgado: true },
    {
        id: "foto1", tipo: "foto", titulo: "SUSPEITO #1 · SILVA", x: 2, y: 23, w: 130, h: 105, rot: 2.5, pinColor: "#ef4444",
        alvo: { nome: "Dep. Fed. JOÃO SILVA SANTOS", cargo: "Deputado Federal — SP", partido: "PROGRESSISTAS", status: "investigado", cpf: "078.***.***.29", valorDesviado: "R$ 89.500.000", processo: "CGU/2024/0032 · TCU/2024/1847", fonte: "https://www.camara.leg.br/deputados/204521", resumo: "Investigado por superfaturamento em 23 contratos do Ministério da Fazenda. Empresa de fachada criada 2 dias antes da licitação. CPF aparece em 4 offshores BVI (Ilhas Virgens Britânicas) detectadas pela Receita Federal em outubro de 2024." }
    },
    {
        id: "foto2", tipo: "foto", titulo: "SUSPEITO #2 · CUNHA", x: 4, y: 52, w: 115, h: 95, rot: -3.0, pinColor: "#ef4444",
        alvo: { nome: "Ex-Presidente MARCOS CUNHA", cargo: "Ex-Dep. Federal — RJ", partido: "PP", status: "condenado", cpf: "041.***.***.17", valorDesviado: "R$ 247.000.000", processo: "STJ/2024/Ap.3847", fonte: "https://portal.stf.jus.br", resumo: "Condenado em 2ª instância por lavagem de dinheiro. Valores transferidos via Offshore BVI → Suíça → Ilhas Cayman. Delação premiada de 3 ex-assessores confirma participação direta." }
    },
    { id: "laudo1", tipo: "laudo", titulo: "LAUDO PERICIAL", subtitulo: "Impressões digitais — Min. Fazenda — 14/11/2024", x: 1, y: 72, w: 145, h: 110, rot: 1.8, pinColor: "#3b82f6", rasgado: true },
    { id: "mapa1", tipo: "mapa", titulo: "PLANTA OPERACIONAL", x: 20, y: 18, w: 190, h: 155, rot: -0.8, pinColor: "#ef4444" },
    {
        id: "foto3", tipo: "foto", titulo: "LOCAL DO CRIME", x: 18, y: 55, w: 140, h: 110, rot: 3.2, pinColor: "#ef4444",
        alvo: { nome: "MINISTÉRIO DA FAZENDA — BLOCO K", cargo: "Local de extração de dados", partido: "—", status: "suspeito", valorDesviado: "Acesso indevido a 87% dos processos", processo: "PF/2024/IPL-0847-DF", resumo: "Câmeras de vigilância registraram acesso ao servidor restrito do MF em 3 ocasiões fora do horário comercial. Logs de acesso foram apagados manualmente. Backup recuperado pela PF." }
    },
    { id: "rec2", tipo: "recorte", titulo: "FOLHA DE SÃO PAULO", subtitulo: "\"Desvio bilionário apontado pela CGU — ministério ignorou alertas por 3 anos\"", x: 16, y: 74, w: 170, h: 120, rot: -2.1, pinColor: "#3b82f6", rasgado: true },
    { id: "doc1", tipo: "documento", titulo: "RELATÓRIO CGU-2024", subtitulo: "CONFIDENCIAL\n\nIrregularidades em 23 contratos MINFAZ.\nDivergências: 87% dos processos.", x: 36, y: 10, w: 175, h: 145, rot: 0.5, pinColor: "#ef4444" },
    {
        id: "foto4", tipo: "foto", titulo: "REUNIÃO SIGILOSA", x: 38, y: 44, w: 145, h: 115, rot: -1.8, pinColor: "#ef4444",
        alvo: { nome: "REUNIÃO SECRETA — HOTEL NACIONAL BSB", cargo: "Encontro documentado por agente infiltrado", partido: "—", status: "investigado", valorDesviado: "Combinados: R$ 12.000.000", processo: "ABIN/2024/SI-0293", resumo: "Reunião fotografada por agente ABIN em 22/03/2024. Presentes: 4 deputados federais, 2 empresários e 1 assessor do ministério. Pauta: divisão de propina de licitação #RT-2024." }
    },
    { id: "laudo2", tipo: "laudo", titulo: "IMPRESSÕES DIGITAIS", subtitulo: "CPF 078.XXX.XXX-29 — correspondência confirmada", x: 35, y: 71, w: 155, h: 120, rot: 2.5, pinColor: "#3b82f6" },
    {
        id: "foto5", tipo: "foto", titulo: "OPERAÇÃO CAMPO", x: 57, y: 6, w: 135, h: 110, rot: -2.8, pinColor: "#ef4444",
        alvo: { nome: "Cel. RODRIGO FERREIRA", cargo: "Coronel PM — delegação especial", partido: "PL", status: "denunciado", cpf: "093.***.***.44", valorDesviado: "R$ 18.700.000", processo: "MPF/2024/PR-RJ/0182", resumo: "Denunciado pelo MPF por desvio de verba de segurança pública. Veículo blindado comprado por valor 340% acima do mercado. Beneficiária: empresa da esposa em paraíso fiscal." }
    },
    {
        id: "foto6", tipo: "foto", titulo: "VIGILÂNCIA #3", x: 55, y: 34, w: 125, h: 100, rot: 1.5, pinColor: "#ef4444",
        alvo: { nome: "MONITORAMENTO 72H — ALVO B", cargo: "Vigilância autorizada pelo STJ", partido: "—", status: "suspeito", valorDesviado: "R$ 4.200.000 transações suspeitas", processo: "STJ/2024/HC-290847", resumo: "72 horas de monitoramento revelaram 14 encontros com pessoas investigadas. Transferências via PIX acima de R$ 300k por dia. Conta corrente em nome de terceiro." }
    },
    { id: "rec3", tipo: "recorte", titulo: "VALOR DESVIADO", subtitulo: "R$ 247.000.000 via Offshore BVI → Suíça → Cayman", x: 53, y: 58, w: 160, h: 130, rot: -1.2, pinColor: "#ef4444", rasgado: true },
    { id: "laudo3", tipo: "laudo", titulo: "ANÁLISE PDNA", subtitulo: "Material biológico — documentos processo nº 0032/2024", x: 55, y: 78, w: 150, h: 110, rot: 2.8, pinColor: "#3b82f6", rasgado: true },
    {
        id: "foto7", tipo: "foto", titulo: "EVIDÊNCIA #3", x: 76, y: 3, w: 130, h: 105, rot: 3.5, pinColor: "#ef4444",
        alvo: { nome: "Senador PAULO DRAGÃO", cargo: "Senador — MG", partido: "UNION", status: "investigado", cpf: "052.***.***.88", valorDesviado: "R$ 62.000.000", processo: "CPMI 2024 / CGU 2024/R-0441", resumo: "Citado em 3 delações premiadas homologadas. Suspeito de liderar esquema de desvios em obras de infraestrutura federal. Patrimônio incompatível: R$ 12M declarados vs R$ 78M estimados." }
    },
    { id: "doc2", tipo: "documento", titulo: "OP. MALHA FINA", subtitulo: "RESERVADO NV.3\nAutoridades: PF+CGU+TCU\nData início: 03/2024", x: 75, y: 26, w: 155, h: 125, rot: -2.3, pinColor: "#ef4444" },
    { id: "laudo4", tipo: "laudo", titulo: "IMPRESSÃO PALMAR", subtitulo: "Coletada em contrato original — 24 mai 2024", x: 74, y: 58, w: 145, h: 120, rot: 1.8, pinColor: "#3b82f6" },
    {
        id: "foto8", tipo: "foto", titulo: "CÂMERA VIGILÂNCIA", x: 76, y: 79, w: 125, h: 100, rot: -3.0, pinColor: "#ef4444",
        alvo: { nome: "CÂMERA ANPR — OPERAÇÃO NOTURNA", cargo: "Registro veicular — 23:47h", partido: "—", status: "investigado", processo: "PF/2024/OP-BASILISCO", valorDesviado: "12 veículos cruzados com investigados", resumo: "Câmera de reconhecimento de placa registrou 12 veículos vinculados a investigados em frente ao alvo às 23h47. Inclui carro blindado de parlamentar federal." }
    },
    { id: "pi1", tipo: "postit", nota: "#1", x: 3, y: 18, w: 52, h: 46, rot: -4.5, pinColor: "#f59e0b" },
    { id: "pi2", tipo: "postit", nota: "#2", x: 14, y: 5, w: 52, h: 46, rot: 3.0, pinColor: "#84cc16" },
    { id: "pi3", tipo: "postit", nota: "Who?", x: 7, y: 63, w: 58, h: 46, rot: -2.5, pinColor: "#f59e0b" },
    { id: "pi4", tipo: "postit", nota: "Why five?", x: 28, y: 65, w: 68, h: 46, rot: 4.0, pinColor: "#84cc16" },
    { id: "pi5", tipo: "postit", nota: "ticket\n?", x: 32, y: 30, w: 56, h: 50, rot: -3.8, pinColor: "#f59e0b" },
    { id: "pi6", tipo: "postit", nota: "This\nway!", x: 63, y: 16, w: 58, h: 46, rot: 3.5, pinColor: "#84cc16" },
    { id: "pi7", tipo: "postit", nota: "about\nwhom?", x: 83, y: 20, w: 62, h: 46, rot: -4.2, pinColor: "#f59e0b" },
    { id: "pi8", tipo: "postit", nota: "24\nmay", x: 88, y: 7, w: 52, h: 46, rot: 2.8, pinColor: "#84cc16" },
    { id: "pi9", tipo: "postit", nota: "17\nmay", x: 85, y: 76, w: 52, h: 46, rot: -2.1, pinColor: "#84cc16" },
    { id: "pi10", tipo: "postit", nota: "#7", x: 32, y: 84, w: 48, h: 42, rot: 1.5, pinColor: "#f59e0b" },
    { id: "pi11", tipo: "postit", nota: "18h\nmeeting", x: 48, y: 87, w: 62, h: 46, rot: -3.5, pinColor: "#84cc16" },
    { id: "pi12", tipo: "postit", nota: "?", x: 10, y: 83, w: 44, h: 40, rot: 4.0, pinColor: "#f59e0b" },
];

const CONNECTIONS: Array<[string, string, string?]> = [
    ["mapa1", "doc1", "Planta usada no planejamento do desvio"],
    ["mapa1", "foto1", "Silva identificado no local"], ["mapa1", "foto3", "Local monitorado 72h"],
    ["mapa1", "pi5", "Encontro marcado neste ponto"], ["mapa1", "foto4", "Reunião planejada aqui"],
    ["mapa1", "rec3", "R$247M rota confirmada"],
    ["doc1", "foto5", "Ferreira assinou o contrato"], ["doc1", "pi6", "Alerta ignorado — ver nota"],
    ["doc1", "rec1", "Contrato vinculado ao relatório"],
    ["foto4", "foto6", "Mesma reunião — câmera externa"],
    ["foto4", "laudo2", "Impressão coletada na sala da reunião"],
    ["foto3", "pi4", "5 acessos registrados"],
    ["foto1", "pi3", "Identidade confirmada"], ["foto1", "foto2", "Sócios ocultos — mesmo esquema"],
    ["laudo1", "rec1", "Assinatura presente no contrato"],
    ["doc2", "foto7", "Dragão citado no relatório"], ["doc2", "pi7", "Fonte protegida — v. nota"],
    ["rec3", "doc2", "valores confirmados na op."],
    ["laudo3", "doc2", "DNA exclui terceiros"],
    ["foto6", "rec3", "Transferência registrada no monitoramento"],
    ["foto5", "doc2", "Coronel subordinado à operação"],
    ["rec2", "pi10", "#7 é o delator"], ["pi8", "doc2", "Reunião de 24/mai consolidou tudo"],
    ["pi9", "laudo4", "Impressão coletada 17/mai"],
    ["laudo2", "laudo3", "Mesmas digitais — dois locais distintos"],
    ["laudo4", "foto8", "Veículos cadastrados em nome de Ferreira"],
];

// ── PhysicsString — fórmula EXATA do usuário + visuais extras ──────────────────
function PhysicsString({ startX, startY, endX, endY, onClick, active }: {
    startX: number; startY: number; endX: number; endY: number; onClick?: () => void; active?: boolean;
}) {
    const midX = (startX + endX) / 2;
    const distance = Math.sqrt(Math.pow(endX - startX, 2) + Math.pow(endY - startY, 2));
    const sag = Math.max(20, 150 - distance * 0.15);
    const midY = (startY + endY) / 2 + sag;
    const pathData = `M ${startX} ${startY} Q ${midX} ${midY} ${endX} ${endY}`;
    const shadowPath = `M ${startX + 2} ${startY + 5} Q ${midX + 2} ${midY + 6} ${endX + 2} ${endY + 5}`;
    return (
        <g>
            <path d={shadowPath} fill="none" stroke="rgba(0,0,0,0.55)" strokeWidth="5" strokeLinecap="round" />
            <path d={pathData} fill="none" stroke="#7a1010" strokeWidth="3.0" strokeLinecap="round" />
            <path d={pathData} fill="transparent" stroke={active ? "#ff6666" : "#cc0000"} strokeWidth="3.5"
                strokeLinecap="round" style={{ filter: "drop-shadow(3px 8px 4px rgba(0,0,0,0.7))" }} />
            {active && <path d={pathData} fill="none" stroke="rgba(255,100,100,0.4)" strokeWidth="10"
                strokeLinecap="round" style={{ filter: "blur(5px)" }} />}
            <path d={pathData} fill="none" stroke="rgba(255,180,180,0.25)"
                strokeWidth="0.7" strokeLinecap="round" strokeDasharray="4 10" />
            {/* Hit area clicável (invisível, mais largo) */}
            {onClick && <path d={pathData} fill="none" stroke="transparent" strokeWidth="28"
                style={{ cursor: "pointer", pointerEvents: "stroke" }} onClick={onClick} />}
        </g>
    );
}

// ── PIN ────────────────────────────────────────────────────────────────────────
function Pin({ color = "#ef4444" }: { color?: string }) {
    return <div style={{
        position: "absolute", left: "50%", top: -8, transform: "translateX(-50%)",
        zIndex: 10, width: 12, height: 12, borderRadius: "50%",
        background: `radial-gradient(circle at 35% 30%,rgba(255,255,255,0.55) 0%,${color} 50%,rgba(0,0,0,0.35) 100%)`,
        boxShadow: "0 2px 5px rgba(0,0,0,0.6),0 0 0 1px rgba(0,0,0,0.25)",
    }} />;
}

// ── CONTEÚDO DOS DOCUMENTOS ────────────────────────────────────────────────────
function DocContent({ doc }: { doc: DocItem }) {
    const mono = "'Courier Prime','Courier New',monospace";
    const hand = "'Caveat',cursive";

    if (doc.tipo === "postit") {
        const g = doc.pinColor === "#84cc16";
        return <div style={{
            width: "100%", height: "100%", background: g ? "#bbf7d0" : "#fef08a",
            display: "flex", alignItems: "center", justifyContent: "center", padding: "6px",
            fontFamily: hand, fontSize: doc.nota && doc.nota.length <= 3 ? "22px" : "15px",
            fontWeight: 700, color: "#1c1917", lineHeight: 1.2, textAlign: "center", whiteSpace: "pre-line"
        }}>
            {doc.nota}
        </div>;
    }

    if (doc.tipo === "foto") {
        const hasAlvo = !!doc.alvo;
        return <div style={{ width: "100%", height: "calc(100% - 18px)", position: "relative", overflow: "hidden" }}>
            <div style={{
                width: "100%", height: "100%",
                background: "linear-gradient(145deg,#2d2416,#1a1408 40%,#221a0e)",
                display: "flex", alignItems: "center", justifyContent: "center",
                filter: "sepia(0.65) brightness(0.75) contrast(1.05) saturate(0.5)"
            }}>
                <svg viewBox="0 0 80 100" style={{ width: "48%", height: "48%", opacity: 0.55 }} fill="none">
                    <circle cx="40" cy="22" r="14" fill="#a89060" />
                    <path d="M12 95 C12 62 68 62 68 95" fill="#a89060" />
                    <rect x="18" y="52" width="44" height="38" rx="3" fill="#a89060" />
                </svg>
                <div style={{
                    position: "absolute", inset: 0,
                    background: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='f'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23f)' opacity='0.22'/%3E%3C/svg%3E\")",
                    mixBlendMode: "overlay"
                }} />
                <div style={{
                    position: "absolute", inset: 0,
                    background: "linear-gradient(145deg,rgba(180,130,40,0.18),rgba(120,80,20,0.25))", mixBlendMode: "multiply"
                }} />
                <div style={{ position: "absolute", inset: 0, boxShadow: "inset 0 0 18px rgba(160,110,30,0.5)" }} />
            </div>
            <div style={{
                position: "absolute", bottom: 0, left: 0, right: 0,
                background: "rgba(20,12,0,0.85)", color: hasAlvo ? "#ffaa44" : "#c8aa70",
                fontSize: "7px", fontFamily: mono, fontWeight: 700, padding: "2px 4px",
                textTransform: "uppercase", letterSpacing: "0.7px", display: "flex", justifyContent: "space-between"
            }}>
                <span>{doc.titulo}</span>
                {hasAlvo && <span style={{ color: "#ef4444", fontSize: "6px" }}>▶ CLIQUE</span>}
            </div>
        </div>;
    }

    if (doc.tipo === "laudo") return (
        <div style={{ width: "100%", height: "100%", padding: "7px", overflow: "hidden", background: "rgba(250,248,240,0.95)" }}>
            <div style={{ display: "flex", gap: "5px", marginBottom: 5 }}>
                {[0, 1, 2].map(i => <div key={i} style={{
                    width: 26, height: 34,
                    background: "linear-gradient(145deg,#e8e0cc,#d4c8a8)", borderRadius: "40% 40% 30% 30%",
                    display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid #b0a080"
                }}>
                    <svg viewBox="0 0 20 26" style={{ width: 19, height: 24, opacity: 0.55 }}>
                        {[5, 8, 11, 14].map((r, ri) => <ellipse key={ri} cx="10" cy="13" rx={r}
                            ry={Math.min(r * 1.3, 14)} fill="none" stroke="#4a3820" strokeWidth="1.1" />)}
                    </svg>
                </div>)}
            </div>
            <p style={{ fontFamily: mono, fontSize: "7.5px", color: "#2c1a08", fontWeight: 700, margin: "0 0 3px", textTransform: "uppercase" }}>{doc.titulo}</p>
            {doc.subtitulo && <p style={{ fontFamily: mono, fontSize: "6.5px", color: "#4a3820", margin: 0, lineHeight: 1.4, whiteSpace: "pre-line" }}>{doc.subtitulo}</p>}
        </div>
    );

    return (
        <div style={{
            width: "100%", height: "100%", padding: "8px 8px 6px", overflow: "hidden",
            background: doc.tipo === "recorte" ? "rgba(248,244,230,0.97)" : "rgba(252,250,244,0.97)"
        }}>
            <p style={{
                fontFamily: mono, fontSize: "8px", fontWeight: 900, color: "#1a0e00",
                textTransform: "uppercase", letterSpacing: "0.5px", margin: "0 0 5px",
                borderBottom: "1px solid #c8b890", paddingBottom: "4px"
            }}>{doc.titulo}</p>
            {doc.subtitulo
                ? <p style={{ fontFamily: mono, fontSize: "6.5px", color: "#4a3820", margin: 0, lineHeight: 1.45, whiteSpace: "pre-line" }}>{doc.subtitulo}</p>
                : <div>{Array.from({ length: 5 }).map((_, i) => <div key={i} style={{
                    height: 5,
                    background: `rgba(80,50,10,${0.09 - i * 0.012})`, borderRadius: 2, marginBottom: 4, width: `${82 + (i % 3) * 7}%`
                }} />)}</div>}
            {doc.tipo === "mapa" && <div style={{ marginTop: 5, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 3 }}>
                {Array.from({ length: 9 }).map((_, i) => <div key={i} style={{
                    height: 13,
                    background: i === 4 ? "#fee2e2" : "#f0e8d0", border: `1px solid ${i === 4 ? "#ef4444" : "#c8b890"}`, borderRadius: 1
                }} />)}
            </div>}
        </div>
    );
}

// ── PAINEL DOSSIE ──────────────────────────────────────────────────────────────
const STATUS_COLOR: Record<string, string> = {
    investigado: "#f59e0b", denunciado: "#f97316", condenado: "#ef4444", suspeito: "#a78bfa"
};
const STATUS_LABEL: Record<string, string> = {
    investigado: "● EM INVESTIGAÇÃO", denunciado: "▲ DENUNCIADO", condenado: "■ CONDENADO", suspeito: "◆ SUSPEITO"
};

function DossiePanel({ alvo, conexao, onClose }: { alvo?: Alvo; conexao?: { label: string }; onClose: () => void }) {
    const mono = "'Courier Prime','Courier New',monospace";
    if (!alvo && !conexao) return null;
    return (
        <motion.div
            initial={{ x: "100%", opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: "100%", opacity: 0 }}
            transition={{ type: "spring", stiffness: 220, damping: 28 }}
            style={{
                position: "absolute", top: 0, right: 0, bottom: 0, width: "42%", zIndex: 100,
                background: "linear-gradient(160deg,#0a0705 0%,#110c08 60%,#0d0a06 100%)",
                borderLeft: "1px solid rgba(239,68,68,0.25)",
                boxShadow: "-20px 0 60px rgba(0,0,0,0.9)",
                display: "flex", flexDirection: "column", gap: 0, overflow: "hidden",
            }}>

            {/* Cabeçalho vermelho */}
            <div style={{
                background: "linear-gradient(90deg,#7f1d1d,#991b1b)",
                padding: "14px 18px", borderBottom: "1px solid #ef4444", position: "relative"
            }}>
                <span style={{
                    fontFamily: mono, fontSize: "8px", color: "rgba(255,200,200,0.7)",
                    letterSpacing: "0.2em", display: "block", marginBottom: 4
                }}>
                    ████ CONFIDENCIAL — OPERAÇÃO MALHA FINA ████
                </span>
                {alvo && <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{
                        width: 44, height: 44, borderRadius: "50%",
                        background: "radial-gradient(circle,#3d2a1a,#1a0e06)",
                        border: "2px solid rgba(239,68,68,0.6)", display: "flex", alignItems: "center", justifyContent: "center"
                    }}>
                        <span style={{ fontSize: "20px" }}>👤</span>
                    </div>
                    <div>
                        <p style={{ fontFamily: mono, fontSize: "8px", color: "rgba(255,200,200,0.6)", margin: 0, letterSpacing: "0.1em" }}>ALVO IDENTIFICADO</p>
                        <p style={{ fontFamily: mono, fontSize: "13px", color: "#fff", fontWeight: 900, margin: "2px 0", letterSpacing: "0.05em", textTransform: "uppercase" }}>{alvo.nome}</p>
                        <p style={{ fontFamily: mono, fontSize: "9px", color: "rgba(255,220,180,0.8)", margin: 0 }}>{alvo.cargo} · {alvo.partido}</p>
                    </div>
                </div>}
                {conexao && <p style={{ fontFamily: mono, fontSize: "13px", color: "#fff", fontWeight: 900, margin: 0 }}>🔗 CONEXÃO IDENTIFICADA</p>}
                <button onClick={onClose} style={{
                    position: "absolute", top: 10, right: 12,
                    background: "transparent", border: "none", color: "rgba(255,180,180,0.7)", cursor: "pointer", fontSize: "18px"
                }}>✕</button>
            </div>

            {/* Body */}
            <div style={{ flex: 1, overflowY: "auto", padding: "16px 18px", display: "flex", flexDirection: "column", gap: 12 }}>

                {alvo && <>
                    {/* Status badge */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{
                            fontFamily: mono, fontSize: "9px", fontWeight: 900,
                            color: STATUS_COLOR[alvo.status] ?? "#f59e0b", letterSpacing: "0.15em",
                            border: `1px solid ${STATUS_COLOR[alvo.status] ?? "#f59e0b"}`,
                            padding: "3px 10px", borderRadius: 2
                        }}>
                            {STATUS_LABEL[alvo.status] ?? "● MONITORADO"}
                        </span>
                        {alvo.cpf && <span style={{ fontFamily: mono, fontSize: "8px", color: "rgba(255,200,180,0.5)" }}>CPF: {alvo.cpf}</span>}
                    </div>

                    {/* Resumo */}
                    <div style={{
                        background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)",
                        borderRadius: 4, padding: "12px"
                    }}>
                        <p style={{
                            fontFamily: mono, fontSize: "7px", color: "rgba(255,220,180,0.6)", margin: "0 0 6px",
                            letterSpacing: "0.15em", textTransform: "uppercase"
                        }}>/// RESUMO EXECUTIVO</p>
                        <p style={{ fontFamily: mono, fontSize: "10px", color: "rgba(255,240,220,0.85)", margin: 0, lineHeight: 1.6 }}>{alvo.resumo}</p>
                    </div>

                    {/* Grids de dados */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                        {[
                            { label: "VALOR DESVIADO", val: alvo.valorDesviado, color: "#ef4444" },
                            { label: "PROCESSO", val: alvo.processo, color: "#f59e0b" },
                            { label: "CARGO", val: alvo.cargo, color: "#a78bfa" },
                            { label: "PARTIDO", val: alvo.partido, color: "#60a5fa" },
                        ].map(({ label, val, color }) => val && (
                            <div key={label} style={{
                                background: "rgba(255,255,255,0.03)",
                                border: `1px solid ${color}22`, borderRadius: 4, padding: "8px 10px"
                            }}>
                                <p style={{ fontFamily: mono, fontSize: "6.5px", color: `${color}99`, margin: "0 0 3px", letterSpacing: "0.12em" }}>{label}</p>
                                <p style={{ fontFamily: mono, fontSize: "9px", color, fontWeight: 700, margin: 0 }}>{val}</p>
                            </div>
                        ))}
                    </div>

                    {/* Botões */}
                    <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                        {alvo.fonte && <a href={alvo.fonte} target="_blank" rel="noreferrer"
                            style={{
                                display: "flex", alignItems: "center", gap: 5, padding: "8px 14px",
                                background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.4)",
                                borderRadius: 4, color: "#fca5a5", fontSize: "9px", fontFamily: mono,
                                textDecoration: "none", letterSpacing: "0.1em", fontWeight: 700, cursor: "pointer"
                            }}>
                            <ExternalLink style={{ width: 11, height: 11 }} /> VER NO PORTAL
                        </a>}
                        <div style={{
                            display: "flex", alignItems: "center", gap: 5, padding: "8px 14px",
                            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
                            borderRadius: 4, color: "rgba(255,200,180,0.5)", fontSize: "9px", fontFamily: mono,
                            letterSpacing: "0.1em"
                        }}>
                            <AlertTriangle style={{ width: 11, height: 11 }} /> DADO OFICIAL
                        </div>
                    </div>
                </>}

                {conexao && <div style={{
                    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(239,68,68,0.15)",
                    borderRadius: 4, padding: "14px"
                }}>
                    <p style={{ fontFamily: mono, fontSize: "8px", color: "rgba(255,200,180,0.6)", margin: "0 0 8px", letterSpacing: "0.15em" }}>/// NATUREZA DA CONEXÃO</p>
                    <p style={{ fontFamily: mono, fontSize: "12px", color: "rgba(255,240,220,0.9)", margin: 0, lineHeight: 1.6 }}>{conexao.label}</p>
                </div>}
            </div>

            {/* Footer */}
            <div style={{
                padding: "10px 18px", borderTop: "1px solid rgba(255,255,255,0.05)",
                background: "rgba(0,0,0,0.4)"
            }}>
                <p style={{ fontFamily: mono, fontSize: "7px", color: "rgba(255,200,180,0.3)", margin: 0, textAlign: "center", letterSpacing: "0.12em" }}>
                    PLATAFORMA TRASPARENTE · CGU · PF · TCU · DADOS PÚBLICOS
                </p>
            </div>
        </motion.div>
    );
}

// ── COMPONENTE PRINCIPAL ───────────────────────────────────────────────────────
export default function QuadroInvestigacao({ onClose }: { onClose: () => void }) {
    const boardRef = useRef<HTMLDivElement>(null);
    const [sz, setSz] = useState({ w: 1300, h: 750 });
    const [positions, setPositions] = useState<PosMap>({});
    const [dragging, setDragging] = useState<string | null>(null);
    const [isPanning, setIsPanning] = useState(false);
    const [pan, setPan] = useState({ x: 0, y: 0 });
    const [zoom, setZoom] = useState(1.0);
    const [cinematic, setCinematic] = useState(false);

    // Dossie state
    const [focusedAlvo, setFocusedAlvo] = useState<Alvo | null>(null);
    const [focusedConex, setFocusedConex] = useState<string | null>(null);
    const [activeString, setActiveString] = useState<number | null>(null);

    const docDragRef = useRef<{ mx: number; my: number; px: number; py: number; moved: boolean } | null>(null);
    const panRef = useRef<{ mx: number; my: number; px: number; py: number } | null>(null);

    useEffect(() => {
        if (!boardRef.current) return;
        const w = boardRef.current.clientWidth, h = boardRef.current.clientHeight;
        setSz({ w, h });
        const init: PosMap = {};
        DOCS.forEach(d => { init[d.id] = { x: (d.x / 100) * w, y: (d.y / 100) * h }; });
        setPositions(init);
    }, []);

    // ── Câmera cinematográfica ──────────────────────────────────────────────────
    const focusOnDoc = useCallback((docId: string) => {
        const pos = positions[docId]; if (!pos) return;
        const targetZoom = 2.0;
        // transformOrigin center center → pan = (W/2 - x)*z, (H/2 - y)*z
        const targetPan = {
            x: (sz.w / 2 - pos.x) * targetZoom,
            y: (sz.h / 2 - pos.y) * targetZoom - 60,
        };
        setCinematic(true);
        setTimeout(() => { setPan(targetPan); setZoom(targetZoom); }, 30);
        const doc = DOCS.find(d => d.id === docId);
        if (doc?.alvo) {
            setTimeout(() => { setFocusedAlvo(doc.alvo ?? null); setCinematic(false); }, 1300);
        } else { setTimeout(() => setCinematic(false), 1300); }
    }, [positions, sz]);

    // ── Drag documentos ────────────────────────────────────────────────────────
    const onDocMouseDown = useCallback((e: React.MouseEvent, id: string) => {
        e.preventDefault(); e.stopPropagation();
        setDragging(id);
        docDragRef.current = {
            mx: e.clientX, my: e.clientY,
            px: positions[id]?.x ?? 0, py: positions[id]?.y ?? 0, moved: false
        };
    }, [positions]);

    // ── Pan câmera ────────────────────────────────────────────────────────────
    const onBoardMouseDown = useCallback((e: React.MouseEvent) => {
        if (dragging || focusedAlvo || focusedConex) return;
        setIsPanning(true);
        panRef.current = { mx: e.clientX, my: e.clientY, px: pan.x, py: pan.y };
    }, [dragging, focusedAlvo, focusedConex, pan]);

    const onWheel = useCallback((e: React.WheelEvent) => {
        if (focusedAlvo || focusedConex) return;
        e.preventDefault();
        setZoom(z => Math.max(0.35, Math.min(2.5, z + (e.deltaY > 0 ? -0.08 : 0.08))));
    }, [focusedAlvo, focusedConex]);

    useEffect(() => {
        const onMove = (e: MouseEvent) => {
            if (dragging && docDragRef.current) {
                const dx = e.clientX - docDragRef.current.mx, dy = e.clientY - docDragRef.current.my;
                if (Math.abs(dx) > 4 || Math.abs(dy) > 4) docDragRef.current.moved = true;
                if (!docDragRef.current.moved) return;
                setPositions(prev => ({
                    ...prev, [dragging]: {
                        x: docDragRef.current!.px + dx / zoom,
                        y: docDragRef.current!.py + dy / zoom,
                    }
                }));
            }
            if (isPanning && panRef.current) {
                setPan({
                    x: panRef.current.px + (e.clientX - panRef.current.mx),
                    y: panRef.current.py + (e.clientY - panRef.current.my),
                });
            }
        };
        const onUp = (e: MouseEvent) => {
            // Detectar click (sem arrastar)
            if (dragging && docDragRef.current && !docDragRef.current.moved) {
                const doc = DOCS.find(d => d.id === dragging);
                if (doc?.alvo) focusOnDoc(dragging);
            }
            setDragging(null); setIsPanning(false);
        };
        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
        return () => { window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); };
    }, [dragging, isPanning, zoom, focusOnDoc]);

    const closeDossie = () => { setFocusedAlvo(null); setFocusedConex(null); setActiveString(null); };
    const resetView = () => {
        setPan({ x: 0, y: 0 }); setZoom(1);
        const init: PosMap = {};
        DOCS.forEach(d => { init[d.id] = { x: (d.x / 100) * sz.w, y: (d.y / 100) * sz.h }; });
        setPositions(init); closeDossie();
    };

    return (
        <>
            <style>{`@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&family=Courier+Prime:wght@400;700&display=swap');`}</style>
            <AnimatePresence>
                <motion.div key="overlay" className="fixed inset-0 z-[200] flex items-center justify-center"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    style={{ background: "rgba(0,0,0,0.97)", backdropFilter: "blur(8px)" }}>

                    <motion.div
                        initial={{ scale: 0.88, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.88, opacity: 0 }} transition={{ type: "spring", stiffness: 260, damping: 28 }}
                        style={{
                            position: "relative", width: "97vw", height: "93vh",
                            border: "14px solid #9ca3af", outline: "3px solid #6b7280",
                            boxShadow: "0 0 0 5px #4b5563,0 30px 80px rgba(0,0,0,0.9),inset 0 0 0 2px #d1d5db",
                            borderRadius: "4px", overflow: "hidden"
                        }}>

                        {/* HEADER */}
                        <div style={{
                            position: "absolute", top: 0, left: 0, right: 0, zIndex: 60,
                            display: "flex", justifyContent: "space-between", alignItems: "center",
                            padding: "10px 14px", background: "linear-gradient(to bottom,rgba(0,0,0,0.9),transparent)",
                            pointerEvents: "none"
                        }}>
                            <div>
                                <h2 style={{
                                    fontFamily: "'Courier Prime',monospace", fontSize: "16px", fontWeight: 900,
                                    color: "#f5f0e8", letterSpacing: "0.12em", textTransform: "uppercase",
                                    textShadow: "0 0 18px rgba(239,68,68,0.4)", margin: 0
                                }}>
                                    🕵️‍♂️ MURAL DE INVESTIGAÇÃO FEDERAL
                                </h2>
                                <p style={{
                                    fontFamily: "'Courier Prime',monospace", fontSize: "8px",
                                    color: "#ef4444", letterSpacing: "0.18em", opacity: 0.8, margin: "2px 0 0", textTransform: "uppercase"
                                }}>
                                    CONFIDENCIAL — OPERAÇÃO MALHA FINA
                                </p>
                            </div>
                            <div style={{ display: "flex", gap: "6px", pointerEvents: "auto" }}>
                                {[
                                    { icon: <ZoomIn className="w-4 h-4" />, fn: () => setZoom(z => Math.min(z + 0.2, 2.5)) },
                                    { icon: <ZoomOut className="w-4 h-4" />, fn: () => setZoom(z => Math.max(z - 0.2, 0.35)) },
                                    { icon: <Move className="w-4 h-4" />, fn: () => setPan({ x: 0, y: 0 }) },
                                    { icon: <RotateCcw className="w-4 h-4" />, fn: resetView },
                                ].map((b, i) => (
                                    <button key={i} onClick={b.fn}
                                        style={{
                                            padding: "6px", borderRadius: "50%", background: "rgba(0,0,0,0.75)",
                                            border: "1px solid rgba(255,255,255,0.1)", cursor: "pointer", color: "#aaa",
                                            display: "flex", alignItems: "center", justifyContent: "center"
                                        }}>
                                        {b.icon}
                                    </button>
                                ))}
                                <button onClick={onClose} style={{
                                    padding: "6px", borderRadius: "50%", background: "rgba(0,0,0,0.75)",
                                    border: "1px solid rgba(239,68,68,0.35)", cursor: "pointer", color: "#999",
                                    display: "flex", alignItems: "center", justifyContent: "center"
                                }}>
                                    <X style={{ width: 18, height: 18 }} />
                                </button>
                            </div>
                        </div>

                        {/* Hint */}
                        <div style={{
                            position: "absolute", bottom: 10, left: "50%", transform: "translateX(-50%)", zIndex: 60,
                            pointerEvents: "none", display: "flex", gap: "16px", background: "rgba(0,0,0,0.7)",
                            backdropFilter: "blur(6px)", borderRadius: "20px", padding: "5px 18px",
                            border: "1px solid rgba(255,255,255,0.06)"
                        }}>
                            {[["🖱️ Scroll", "Zoom"], ["🤚 Arrastar fundo", "Pan"], ["🖐️ Arrastar papel", "Mover"], ["🖱️ Clicar foto/fio", "Abrir dossie"]].map(([k, v], i) => (
                                <span key={i} style={{
                                    fontFamily: "'Courier Prime',monospace", fontSize: "8.5px",
                                    color: "#666", letterSpacing: "0.08em"
                                }}>
                                    <span style={{ color: "#999", fontWeight: 700 }}>{k}</span> · {v}
                                </span>
                            ))}
                        </div>

                        {/* BOARD — CORTIÇA */}
                        <div ref={boardRef} onMouseDown={onBoardMouseDown} onWheel={onWheel}
                            style={{
                                position: "absolute", inset: 0,
                                background: `
                  repeating-linear-gradient(0deg,rgba(0,0,0,0.055) 0px,rgba(0,0,0,0.055) 1px,transparent 1px,transparent 4px),
                  repeating-linear-gradient(90deg,rgba(0,0,0,0.04) 0px,rgba(0,0,0,0.04) 1px,transparent 1px,transparent 6px),
                  repeating-linear-gradient(135deg,rgba(170,90,20,0.1) 0px,transparent 3px,transparent 7px),
                  radial-gradient(ellipse at 22% 22%,rgba(225,140,50,0.2) 0%,transparent 50%),
                  radial-gradient(ellipse at 78% 78%,rgba(185,100,25,0.18) 0%,transparent 45%),
                  linear-gradient(145deg,#c07830 0%,#b86e28 25%,#c88040 50%,#bf7530 75%,#b46a22 100%)
                `,
                                cursor: dragging ? "grabbing" : isPanning ? "grabbing" : "grab", overflow: "hidden",
                            }}>
                            {/* Vignette */}
                            <div style={{
                                position: "absolute", inset: 0, pointerEvents: "none", zIndex: 2,
                                background: "radial-gradient(ellipse 78% 68% at 50% 48%,transparent 35%,rgba(0,0,0,0.2) 65%,rgba(0,0,0,0.6) 100%)"
                            }} />

                            {/* OVERLAY de foco quando dossie aberto */}
                            {(focusedAlvo || focusedConex) && (
                                <div onClick={closeDossie} style={{
                                    position: "absolute", inset: 0, zIndex: 88,
                                    background: "rgba(0,0,0,0.35)", cursor: "pointer", pointerEvents: "auto"
                                }} />
                            )}

                            {/* CONTEÚDO COM PAN + ZOOM */}
                            <div style={{
                                position: "absolute", inset: 0, zIndex: 3,
                                transform: `translate(${pan.x}px,${pan.y}px) scale(${zoom})`,
                                transformOrigin: "center center",
                                transition: cinematic
                                    ? "transform 1.2s cubic-bezier(0.6,0.05,0.25,1)"
                                    : (isPanning || dragging) ? "none" : "transform 0.08s linear",
                            }}>
                                {/* SVG FIOS (PhysicsString) */}
                                <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", overflow: "visible", zIndex: 5 }}
                                    viewBox={`0 0 ${sz.w} ${sz.h}`}>
                                    {CONNECTIONS.map(([from, to, label], i) => {
                                        const fp = positions[from], tp = positions[to];
                                        if (!fp || !tp) return null;
                                        return <PhysicsString key={i}
                                            startX={fp.x} startY={fp.y} endX={tp.x} endY={tp.y}
                                            active={activeString === i}
                                            onClick={() => {
                                                setActiveString(i);
                                                setFocusedConex(label ?? "Conexão investigativa identificada");
                                                setFocusedAlvo(null);
                                                // Zoom no centro do fio
                                                const cx = (fp.x + tp.x) / 2, cy = (fp.y + tp.y) / 2;
                                                const tz = 1.8;
                                                setCinematic(true);
                                                setTimeout(() => {
                                                    setPan({ x: (sz.w / 2 - cx) * tz, y: (sz.h / 2 - cy) * tz });
                                                    setZoom(tz);
                                                }, 30);
                                                setTimeout(() => setCinematic(false), 1300);
                                            }} />;
                                    })}
                                </svg>

                                {/* DOCUMENTOS */}
                                {DOCS.map((doc, di) => {
                                    const pos = positions[doc.id]; if (!pos) return null;
                                    const isDrag = dragging === doc.id;
                                    const isPostit = doc.tipo === "postit";
                                    const clip = doc.rasgado ? TORN[di % TORN.length] : undefined;
                                    const clickable = doc.tipo === "foto" && !!doc.alvo;
                                    return (
                                        <motion.div key={doc.id}
                                            animate={{ scale: isDrag ? 1.08 : 1, rotate: isDrag ? doc.rot * 1.6 : doc.rot, y: isDrag ? -12 : 0 }}
                                            transition={{ type: "spring", stiffness: 350, damping: 22 }}
                                            style={{
                                                position: "absolute", left: pos.x, top: pos.y,
                                                width: doc.w, height: doc.h, translateX: "-50%", translateY: "-50%",
                                                cursor: isDrag ? "grabbing" : clickable ? "pointer" : "grab",
                                                userSelect: "none", zIndex: isDrag ? 50 : isPostit ? 14 : 12,
                                                boxShadow: isDrag ? "0 20px 55px rgba(0,0,0,0.9),4px 5px 0 rgba(0,0,0,0.45)" : "3px 5px 0 rgba(0,0,0,0.45),6px 8px 22px rgba(0,0,0,0.38)",
                                                background: isPostit ? "transparent" : undefined,
                                                outline: isPostit ? "none" : "1px solid rgba(0,0,0,0.08)",
                                                clipPath: clip, touchAction: "none",
                                            }}
                                            onMouseDown={e => onDocMouseDown(e, doc.id)}>
                                            <Pin color={doc.pinColor ?? "#ef4444"} />
                                            <DocContent doc={doc} />
                                            {clickable && !isDrag && <div style={{
                                                position: "absolute", inset: 0, borderRadius: 1,
                                                border: "1px solid rgba(239,68,68,0)",
                                                transition: "border-color 0.2s",
                                                background: "rgba(239,68,68,0)",
                                            }} className="foto-hover" />}
                                        </motion.div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* PAINEL DOSSIE */}
                        <AnimatePresence>
                            {(focusedAlvo || focusedConex) && (
                                <DossiePanel
                                    alvo={focusedAlvo ?? undefined}
                                    conexao={focusedConex ? { label: focusedConex } : undefined}
                                    onClose={closeDossie} />
                            )}
                        </AnimatePresence>
                    </motion.div>
                </motion.div>
            </AnimatePresence>
        </>
    );
}
