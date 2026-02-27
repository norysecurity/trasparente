"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ShieldAlert, Fingerprint, FileText, Banknote, Building2, Scale, ArrowLeft } from "lucide-react";

export default function PoliticoPerfil() {
    const params = useParams();
    const router = useRouter();
    const idPolitico = params.id;
    const [loading, setLoading] = useState(true);

    // Variável com dados Simulados Densamente Gamificados
    const politicoData = {
        nome: "Aécio Neves",
        cargo: "Deputado Federal",
        partido: "PSDB",
        uf: "MG",
        foto: "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/A%C3%A9cio_Neves.jpg/800px-A%C3%A9cio_Neves.jpg",
        score_auditoria: 350,
        badges: [
            { id: 1, nome: "Alvo da Lava-Jato", icon: <ShieldAlert className="w-4 h-4 text-red-400" />, color: "bg-red-500/10 border-red-500/50 text-red-500" },
            { id: 2, nome: "Teto de Gastos Violado", icon: <Banknote className="w-4 h-4 text-orange-400" />, color: "bg-orange-500/10 border-orange-500/50 text-orange-500" },
            { id: 3, nome: "Rabo Preso Detectado", icon: <Fingerprint className="w-4 h-4 text-purple-400" />, color: "bg-purple-500/10 border-purple-500/50 text-purple-500" }
        ],
        redFlags: [
            { data: "2017", titulo: "Áudios da JBS", desc: "Gravações sobre recebimento de propinas." },
            { data: "2020", titulo: "Inquérito Furnas", desc: "Corrupção passiva e lavagem de dinheiro." },
            { data: "2023", titulo: "Licitações Suspeitas", desc: "Empresas ligadas a parentes com contratos públicos." }
        ],
        empresas: [
            { nome: "Aeroporto de Cláudio Participações", cargo: "Declarado pelo TSE", valor: "R$ 14.000.000,00" },
            { nome: "Rádio Arco-Íris", cargo: "Associação Familiar", valor: "R$ 5.400.000,00" }
        ],
        projetos: [
            { titulo: "PEC do Teto", status: "Aprovado", presence: 85 },
            { titulo: "Reforma Trabalhista", status: "Aprovado", presence: 90 },
        ]
    };

    useEffect(() => {
        // Simula chamadas lentas à API local
        const timer = setTimeout(() => setLoading(false), 800);
        return () => clearTimeout(timer);
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center text-emerald-500">
                <div className="w-16 h-16 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin shadow-[0_0_30px_rgba(16,185,129,0.5)]"></div>
                <p className="mt-6 font-mono tracking-widest animate-pulse">CARREGANDO DOSSIÊ OFICIAL...</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-neutral-950 text-neutral-200 font-sans selection:bg-purple-500/30 overflow-x-hidden">
            <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-neutral-900/40 via-neutral-950 to-neutral-950 pointer-events-none" />

            {/* NAVBAR */}
            <nav className="fixed w-full z-50 bg-neutral-950/80 backdrop-blur-md border-b border-neutral-800 p-4">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <button onClick={() => router.push('/')} className="flex items-center gap-2 text-neutral-400 hover:text-white transition group">
                        <ArrowLeft className="w-5 h-5 group-hover:-translate-x-1 transition" />
                        Voltar ao Dashboard
                    </button>
                    <div className="font-mono text-xs tracking-widest text-emerald-500">ID: {idPolitico} // AUDITORIA GOVTECH ATIVA</div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto px-6 pt-28 pb-12 relative z-10">

                {/* HEADER ÉPICO */}
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className="flex flex-col md:flex-row gap-8 items-center bg-neutral-900/40 border border-neutral-800 rounded-3xl p-8 mb-8 backdrop-blur-lg relative overflow-hidden"
                >
                    {/* Luz Vermelha de fundo se Score for baixo */}
                    {politicoData.score_auditoria < 500 && (
                        <div className="absolute -top-40 -right-40 w-96 h-96 bg-red-600/10 blur-[100px] rounded-full pointer-events-none" />
                    )}

                    <div className="w-40 h-40 rounded-full overflow-hidden border-4 border-neutral-800 shadow-2xl shrink-0 relative">
                        <img src={politicoData.foto} alt={politicoData.nome} className="w-full h-full object-cover" />
                        {politicoData.score_auditoria < 500 && <div className="absolute inset-0 bg-red-500/20 mix-blend-multiply" />}
                    </div>

                    <div className="flex-1 text-center md:text-left">
                        <h1 className="text-5xl font-black text-white mb-2">{politicoData.nome}</h1>
                        <h2 className="text-xl text-neutral-400 font-bold mb-4">{politicoData.cargo} - <span className="text-neutral-300">{politicoData.partido}/{politicoData.uf}</span></h2>

                        {/* BADGES */}
                        <div className="flex flex-wrap items-center justify-center md:justify-start gap-3">
                            {politicoData.badges.map(badge => (
                                <div key={badge.id} className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-bold uppercase tracking-wider ${badge.color}`}>
                                    {badge.icon} {badge.nome}
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="shrink-0 flex flex-col items-center">
                        <div className="relative w-32 h-32 flex items-center justify-center">
                            <svg className="absolute w-full h-full -rotate-90">
                                <circle cx="64" cy="64" r="56" className="stroke-neutral-800 fill-none stroke-[8]"></circle>
                                <motion.circle
                                    initial={{ strokeDasharray: "351", strokeDashoffset: "351" }}
                                    animate={{ strokeDashoffset: `${351 - (351 * politicoData.score_auditoria) / 1000}` }}
                                    transition={{ duration: 1.5, ease: "easeOut", delay: 0.5 }}
                                    cx="64" cy="64" r="56"
                                    className={`fill-none stroke-[8] ${politicoData.score_auditoria >= 700 ? 'stroke-emerald-500' : politicoData.score_auditoria >= 400 ? 'stroke-yellow-500' : 'stroke-red-500'}`}
                                    style={{ strokeLinecap: 'round' }}
                                ></circle>
                            </svg>
                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <span className={`text-4xl font-black ${politicoData.score_auditoria >= 700 ? 'text-emerald-500' : politicoData.score_auditoria >= 400 ? 'text-yellow-500' : 'text-red-500'}`}>{politicoData.score_auditoria}</span>
                            </div>
                        </div>
                        <p className="text-neutral-500 text-xs font-bold uppercase mt-2">Score Serasa</p>
                    </div>
                </motion.div>

                {/* 3 COLUNAS GRID */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                    {/* COLUNA 1: ATUAÇÃO */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }}
                        className="bg-neutral-900/30 border border-neutral-800 rounded-3xl p-6"
                    >
                        <h3 className="text-emerald-400 font-bold mb-6 flex items-center gap-2 border-b border-neutral-800 pb-4">
                            <FileText className="w-5 h-5" /> Legislação & Assiduidade
                        </h3>
                        <div className="space-y-6">
                            {politicoData.projetos.map((proj, idx) => (
                                <div key={idx}>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span className="font-bold text-neutral-200">{proj.titulo}</span>
                                        <span className="text-neutral-500">{proj.status}</span>
                                    </div>
                                    <div className="w-full bg-neutral-800 rounded-full h-1.5">
                                        <motion.div initial={{ width: 0 }} animate={{ width: `${proj.presence}%` }} transition={{ duration: 1, delay: 0.5 }} className="bg-emerald-500 h-1.5 rounded-full" />
                                    </div>
                                    <p className="text-right text-[10px] text-neutral-500 mt-1 uppercase tracking-widest">Adesão: {proj.presence}%</p>
                                </div>
                            ))}
                        </div>
                    </motion.div>

                    {/* COLUNA 2: RADAR CRIMINAL */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.3 }}
                        className="bg-neutral-900/30 border border-red-500/20 rounded-3xl p-6 relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/5 blur-[50px] rounded-full pointer-events-none" />
                        <h3 className="text-red-400 font-bold mb-6 flex items-center gap-2 border-b border-red-500/20 pb-4">
                            <Scale className="w-5 h-5" /> Radar Criminal DOJ
                        </h3>

                        <div className="space-y-6 relative before:absolute before:inset-0 before:ml-2.5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-neutral-800 before:to-transparent">
                            {politicoData.redFlags.map((flag, idx) => (
                                <motion.div
                                    initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5, delay: 0.5 + (idx * 0.1) }}
                                    key={idx} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active"
                                >
                                    <div className="flex items-center justify-center w-6 h-6 rounded-full border border-neutral-800 bg-neutral-900 text-neutral-500 group-[.is-active]:text-red-500 group-[.is-active]:bg-red-500/10 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2">
                                        <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                                    </div>
                                    <div className="w-[calc(100%-2rem)] md:w-[calc(50%-1.5rem)] p-4 rounded-xl border border-neutral-800 bg-neutral-950/50 backdrop-blur-sm -mt-2">
                                        <div className="flex items-center justify-between mb-1">
                                            <div className="font-bold text-neutral-300 text-sm">{flag.titulo}</div>
                                            <time className="font-mono text-xs text-red-500/50">{flag.data}</time>
                                        </div>
                                        <div className="text-neutral-500 text-xs">{flag.desc}</div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </motion.div>

                    {/* COLUNA 3: TEIA EMPRESARIAL */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.4 }}
                        className="bg-neutral-900/30 border border-neutral-800 rounded-3xl p-6"
                    >
                        <h3 className="text-purple-400 font-bold mb-6 flex items-center gap-2 border-b border-neutral-800 pb-4">
                            <Building2 className="w-5 h-5" /> Rabo Preso S/A
                        </h3>
                        <div className="space-y-4">
                            {politicoData.empresas.map((emp, idx) => (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.6 + (idx * 0.1) }}
                                    key={idx} className="bg-neutral-950 border border-neutral-800 p-4 rounded-2xl flex items-center gap-4 group"
                                >
                                    <div className="w-10 h-10 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-400 shrink-0">
                                        <Banknote className="w-5 h-5" />
                                    </div>
                                    <div>
                                        <h4 className="font-bold text-neutral-200 text-sm leading-tight">{emp.nome}</h4>
                                        <p className="text-xs text-neutral-500 mt-1">{emp.cargo}</p>
                                        <p className="font-mono text-xs text-purple-400 mt-1">{emp.valor}</p>
                                    </div>
                                </motion.div>
                            ))}
                        </div>

                        <button className="w-full mt-6 py-3 border border-purple-500/30 text-purple-400 font-bold rounded-xl text-sm hover:bg-purple-500 hover:text-white transition shadow-[0_0_15px_rgba(168,85,247,0.1)] hover:shadow-[0_0_20px_rgba(168,85,247,0.4)]">
                            Abrir Teia no Neo4j
                        </button>
                    </motion.div>

                </div>
            </main>
        </div>
    );
}
