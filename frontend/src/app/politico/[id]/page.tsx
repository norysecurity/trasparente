"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ShieldAlert, Fingerprint, FileText, Banknote, Building2, Scale, ArrowLeft, ExternalLink, Newspaper, Bot, Receipt, Gavel } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import dynamic from 'next/dynamic';

const GrafoCorrupcao = dynamic(() => import('@/components/GrafoCorrupcao'), {
    ssr: false,
    loading: () => <div className="w-full h-full flex flex-col items-center justify-center text-purple-500 bg-neutral-950 animate-pulse font-mono text-xs tracking-widest gap-4">
        <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
        INICIALIZANDO MOTOR FÍSICO 2D...
    </div>
});

export default function PoliticoPerfil() {
    const params = useParams();
    const router = useRouter();
    const idPolitico = params.id;
    const [loading, setLoading] = useState(true);
    const [filtroEditorial, setFiltroEditorial] = useState("Todas as Fontes");
    const [politicoData, setPoliticoData] = useState<any>(null);
    const [isTeiaModalOpen, setIsTeiaModalOpen] = useState(false);

    // IA States
    const [isAuditando, setIsAuditando] = useState(false);
    const [parecerIA, setParecerIA] = useState<string | null>(null);

    useEffect(() => {
        if (!idPolitico) return;

        fetch(`http://localhost:8000/api/politico/detalhes/${idPolitico}`)
            .then(res => res.json())
            .then(data => {
                if (data.status === "sucesso") {
                    setPoliticoData(data.dados);
                }
            })
            .catch(err => console.error("Erro ao buscar dossiê ID:", err))
            .finally(() => setLoading(false));
    }, [idPolitico]);

    const gerarParecerAceleracionista = async () => {
        if (!politicoData) return;
        setIsAuditando(true);
        setParecerIA(null);

        try {
            const res = await fetch("/api/auditoria-ai", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    politico_nome: politicoData.nome,
                    empresas: politicoData.empresas,
                    redFlags: politicoData.redFlags,
                    despesas: [] // Será populado se a API principal enviar as puras
                })
            });
            const dat = await res.json();
            if (dat.status === "sucesso") {
                setParecerIA(dat.insight);
            } else {
                setParecerIA("Erro ao contatar Tribunal AI: " + dat.error);
            }
        } catch (e) {
            setParecerIA("Falha na varredura. IA Indisponível no momento.");
        } finally {
            setIsAuditando(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center text-emerald-500">
                <div className="w-16 h-16 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin shadow-[0_0_30px_rgba(16,185,129,0.5)]"></div>
                <p className="mt-6 font-mono tracking-widest animate-pulse">CARREGANDO DOSSIÊ OFICIAL...</p>
            </div>
        );
    }

    if (!politicoData) {
        return <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center text-red-500">Falha ao carregar dados.</div>
    }

    return (
        <div className="min-h-screen bg-neutral-950 text-neutral-200 font-sans selection:bg-purple-500/30 overflow-x-hidden">
            <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-neutral-900/40 via-neutral-950 to-neutral-950 pointer-events-none" />

            {/* NAVBAR */}
            <nav className="fixed w-full z-50 bg-neutral-950/80 backdrop-blur-md border-b border-neutral-800 p-4">
                <div className="max-w-[95%] mx-auto flex items-center justify-between">
                    <button onClick={() => router.push('/')} className="flex items-center gap-2 text-neutral-400 hover:text-white transition group">
                        <ArrowLeft className="w-5 h-5 group-hover:-translate-x-1 transition" />
                        Voltar ao Dashboard
                    </button>
                    <div className="font-mono text-xs tracking-widest text-emerald-500">ID: {idPolitico} // AUDITORIA GOVTECH ATIVA</div>
                </div>
            </nav>

            <main className="max-w-[95%] mx-auto px-6 pt-28 pb-12 relative z-10">

                {/* HEADER ÉPICO */}
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className="flex flex-col md:flex-row gap-8 items-center bg-neutral-900/40 border border-neutral-800 rounded-3xl p-8 mb-8 backdrop-blur-lg relative overflow-hidden"
                >
                    {politicoData.score_auditoria < 500 && (
                        <div className="absolute -top-40 -right-40 w-96 h-96 bg-red-600/10 blur-[100px] rounded-full pointer-events-none" />
                    )}

                    <div className="w-40 h-40 rounded-full overflow-hidden border-4 border-neutral-800 shadow-2xl shrink-0 relative flex items-center justify-center bg-neutral-900">
                        {politicoData.foto ? (
                            <img src={politicoData.foto} alt={politicoData.nome} className="w-full h-full object-cover" />
                        ) : (
                            <span className="text-6xl font-black text-neutral-700 uppercase">{politicoData.nome?.charAt(0)}</span>
                        )}
                        {politicoData.score_auditoria < 500 && <div className="absolute inset-0 bg-red-500/20 mix-blend-multiply" />}
                    </div>

                    <div className="flex-1 text-center md:text-left">
                        <h1 className="text-5xl font-black text-white mb-2">{politicoData.nome}</h1>
                        <h2 className="text-xl text-neutral-400 font-bold mb-4">{politicoData.cargo} - <span className="text-neutral-300">{politicoData.partido}/{politicoData.uf}</span></h2>

                        <div className="flex flex-wrap items-center justify-center md:justify-start gap-3">
                            {politicoData.badges && politicoData.badges.map((badge: any) => (
                                <div key={badge.id} className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-bold uppercase tracking-wider ${badge.color}`}>
                                    {badge.icon === 'ShieldAlert' && <ShieldAlert className="w-4 h-4 text-red-400" />}
                                    {badge.icon === 'Banknote' && <Banknote className="w-4 h-4 text-orange-400" />}
                                    {badge.icon === 'Fingerprint' && <Fingerprint className="w-4 h-4 text-purple-400" />}
                                    {badge.nome}
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="shrink-0 flex flex-col items-center max-w-[200px]">
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
                                ></motion.circle>
                            </svg>
                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <span className={`text-4xl font-black ${politicoData.score_auditoria >= 700 ? 'text-emerald-500' : politicoData.score_auditoria >= 400 ? 'text-yellow-500' : 'text-red-500'}`}>{politicoData.score_auditoria}</span>
                            </div>
                        </div>
                        <p className="text-neutral-500 text-xs font-bold uppercase mt-2 text-center">Score Serasa</p>
                        <p className="text-neutral-600 text-[10px] mt-2 text-center leading-tight">{politicoData.explicacao_score}</p>
                    </div>
                </motion.div>

                {/* 4 COLUNAS GRID */}
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 lg:gap-12 xl:gap-12 gap-8">

                    {/* COLUNA 1: ATUAÇÃO */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }}
                        className="bg-neutral-900/30 border border-neutral-800 rounded-3xl p-6"
                    >
                        <h3 className="text-emerald-400 font-bold mb-6 flex items-center gap-2 border-b border-neutral-800 pb-4">
                            <FileText className="w-5 h-5" /> Projetos de Lei
                        </h3>
                        {politicoData.projetos && politicoData.projetos.length > 0 ? (
                            <div className="space-y-6 max-h-[450px] overflow-y-auto custom-scrollbar pr-2">
                                {politicoData.projetos.map((proj: any, idx: number) => (
                                    <div key={idx} className="hover:bg-neutral-800/50 p-2 rounded-lg transition-colors cursor-default">
                                        <div className="flex justify-between text-sm mb-1">
                                            <span className="font-bold text-neutral-200 truncate pr-2" title={proj.titulo}>{proj.titulo}</span>
                                            <span className="text-neutral-500 flex-shrink-0">{proj.status}</span>
                                        </div>
                                        {proj.fonte && (
                                            <a href={proj.fonte} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-[10px] uppercase text-emerald-500 hover:text-emerald-400 w-fit mb-2">
                                                <ExternalLink className="w-3 h-3" /> Ver na Câmara
                                            </a>
                                        )}
                                        <div className="w-full bg-neutral-800 rounded-full h-1.5">
                                            <motion.div initial={{ width: 0 }} animate={{ width: `${proj.presence}%` }} transition={{ duration: 1, delay: 0.5 }} className="bg-emerald-500 h-1.5 rounded-full" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center p-6 text-center border border-dashed border-neutral-700 bg-neutral-900/20 rounded-2xl">
                                <FileText className="w-8 h-8 text-neutral-500 mb-2" />
                                <span className="text-xs text-neutral-500 font-mono tracking-widest">Registros de projetos legislativos ausentes no ciclo atual.</span>
                            </div>
                        )}

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

                        {politicoData.redFlags && politicoData.redFlags.length > 0 ? (
                            <div className="space-y-6 relative max-h-[450px] overflow-y-auto custom-scrollbar pr-2 overflow-x-hidden before:absolute before:inset-0 before:ml-2.5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-neutral-800 before:to-transparent">
                                {politicoData.redFlags.map((flag: any, idx: number) => (
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
                                            {flag.fonte && (
                                                flag.fonte.startsWith("http") ? (
                                                    <a href={flag.fonte} target="_blank" rel="noreferrer" className="mt-3 flex items-center gap-1 text-[10px] uppercase text-red-400 hover:text-red-300">
                                                        <ExternalLink className="w-3 h-3" /> Visualizar Fonte
                                                    </a>
                                                ) : (
                                                    <span className="mt-3 flex items-center gap-1 text-[10px] uppercase text-red-500/70">
                                                        <ExternalLink className="w-3 h-3" /> Fonte: {flag.fonte}
                                                    </span>
                                                )
                                            )}
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center p-6 text-center border border-dashed border-red-900/30 bg-red-950/10 rounded-2xl shadow-inner">
                                <Scale className="w-8 h-8 text-red-900/50 mb-2 opacity-50" />
                                <span className="text-xs text-red-300/50 font-mono tracking-widest leading-relaxed">Nenhuma Sanção Direta, Crime Ambiental (IBAMA) ou Processo no STF reportado pelo Motor até o momento.</span>
                            </div>
                        )}
                    </motion.div>

                    {/* COLUNA 3: TEIA EMPRESARIAL (MODIFICADA) */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.4 }}
                        className="bg-neutral-900/30 border border-neutral-800 rounded-3xl p-6"
                    >
                        <h3 className="text-purple-400 font-bold mb-6 flex items-center gap-2 border-b border-neutral-800 pb-4">
                            <Building2 className="w-5 h-5" /> Rabo Preso S/A
                        </h3>

                        <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-6 lg:col-span-1">
                            <h3 className="text-xl font-bold flex items-center mb-6 text-neutral-300">
                                <div className="w-8 h-8 rounded-full bg-red-500/10 flex items-center justify-center mr-3 border border-red-500/20">
                                    <Scale className="w-4 h-4 text-red-400" />
                                </div>
                                "Rabo Preso" S/A
                            </h3>

                            <div className="space-y-4">
                                {politicoData.processos ? (
                                    politicoData.processos.map((proc: any, idx: number) => (
                                        <div key={idx} className="bg-neutral-950 border border-red-500/30 rounded-xl p-4 flex gap-4">
                                            <div className="w-10 h-10 rounded-full bg-red-500/10 flex-shrink-0 flex items-center justify-center border border-red-500/20 mt-1">
                                                <Gavel className="w-5 h-5 text-red-500" />
                                            </div>
                                            <div>
                                                <p className="text-xs text-red-400 font-black mb-1">
                                                    {proc.data}
                                                </p>
                                                <h4 className="font-bold text-sm text-neutral-200 leading-tight mb-2">
                                                    {proc.titulo}
                                                </h4>
                                                <p className="text-xs text-neutral-400">
                                                    {proc.desc}
                                                </p>
                                                {proc.fonte && (
                                                    <a href={proc.fonte} target="_blank" rel="noopener noreferrer" className="mt-3 text-xs text-red-400 flex items-center gap-1 hover:text-red-300 transition-colors bg-red-500/10 w-fit px-2 py-1 rounded-md border border-red-500/20">
                                                        <ExternalLink className="w-3 h-3" /> Ver Processo Original
                                                    </a>
                                                )}
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="flex flex-col items-center justify-center p-6 text-center border border-dashed border-neutral-700 bg-neutral-900/20 rounded-2xl">
                                        <span className="text-xs text-neutral-500 font-mono tracking-widest">Nenhuma despesa ou empresa associada encontrada nos registros iniciais.</span>
                                    </div>
                                )}
                            </div>

                            <button
                                onClick={() => setIsTeiaModalOpen(true)}
                                className="block text-center w-full mt-6 py-3 border border-purple-500/30 text-purple-400 font-bold rounded-xl text-sm hover:bg-purple-500 hover:text-white transition shadow-[0_0_15px_rgba(168,85,247,0.1)] hover:shadow-[0_0_20px_rgba(168,85,247,0.4)] flex flex-col items-center justify-center gap-1 group"
                            >
                                <span>Gerar Teia de Corrupção</span>
                                <span className="text-[10px] font-normal opacity-70 group-hover:opacity-100 transition-opacity">Visualizar ligações hierárquicas</span>
                            </button>

                            {/* NOVO BOTÃO: EXTRATO BANCÁRIO */}
                            <button
                                onClick={() => router.push(`/politico/${idPolitico}/extrato`)}
                                className="block text-center w-full mt-3 py-3 bg-neutral-900 border border-neutral-700 text-neutral-300 font-bold rounded-xl text-sm hover:bg-neutral-800 transition flex items-center justify-center gap-2"
                            >
                                <Receipt className="w-4 h-4" />
                                <span>Ver Extrato Completo</span>
                            </button>
                        </div>
                    </motion.div>

                    {/* COLUNA 4: NOTÍCIAS RECENTES */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.5 }}
                        className="bg-neutral-900/30 border border-blue-500/20 rounded-3xl p-6 relative overflow-hidden flex flex-col"
                    >
                        <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 blur-[50px] rounded-full pointer-events-none" />
                        <h3 className="text-blue-400 font-bold mb-4 flex items-center gap-2 border-b border-blue-500/20 pb-4">
                            <Newspaper className="w-5 h-5" /> Monitoramento de Imprensa
                        </h3>

                        {politicoData.noticias && politicoData.noticias.length > 0 ? (
                            <>
                                <div className="flex flex-wrap gap-2 mb-4">
                                    {["Todas as Fontes", "Institucional", "Progressista", "Conservadora"].map(f => (
                                        <button
                                            key={f}
                                            onClick={() => setFiltroEditorial(f)}
                                            className={`text-[10px] uppercase font-bold px-3 py-1.5 rounded-md transition-colors ${filtroEditorial === f ? 'bg-blue-600 text-white' : 'bg-neutral-900 border border-neutral-700 text-neutral-400 hover:bg-neutral-800 hover:border-neutral-600'}`}
                                        >
                                            {f}
                                        </button>
                                    ))}
                                </div>
                                <div className="space-y-4 relative max-h-[450px] overflow-y-auto custom-scrollbar pr-2 flex-1">
                                    {politicoData.noticias
                                        .filter((n: any) => filtroEditorial === "Todas as Fontes" || n.linha_editorial === filtroEditorial)
                                        .map((noticia: any, idx: number) => {

                                            const badgeColor = noticia.linha_editorial === 'Progressista' ? 'bg-rose-900/30 text-rose-400 border-rose-900/50' :
                                                noticia.linha_editorial === 'Conservadora' ? 'bg-cyan-900/30 text-cyan-400 border-cyan-900/50' :
                                                    noticia.linha_editorial === 'Institucional' ? 'bg-neutral-800 text-neutral-300 border-neutral-700' :
                                                        'bg-amber-900/30 text-amber-400 border-amber-900/50';

                                            return (
                                                <motion.div
                                                    initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3 }}
                                                    key={`${idx}-${noticia.titulo}`} className="bg-neutral-950/50 border border-neutral-800 p-4 rounded-2xl flex flex-col gap-2 hover:border-blue-500/30 transition group"
                                                >
                                                    <div className="flex items-center justify-between flex-wrap gap-y-2">
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-[10px] uppercase font-bold text-blue-400 font-mono tracking-wider">{noticia.fonte}</span>
                                                            <span className={`text-[8px] uppercase font-bold px-1.5 py-0.5 rounded border ${badgeColor}`}>
                                                                {noticia.linha_editorial || 'Independente'}
                                                            </span>
                                                        </div>
                                                        <span className="text-[10px] text-neutral-500 ml-auto">{noticia.data}</span>
                                                    </div>
                                                    <h4 className="font-bold text-neutral-200 text-sm leading-snug">{noticia.titulo}</h4>
                                                    <div className="mt-2 pt-2 border-t border-neutral-800">
                                                        <a href={noticia.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-[11px] font-bold text-blue-500 hover:text-blue-400 w-fit">
                                                            Ler Matéria Completa <ExternalLink className="w-3 h-3" />
                                                        </a>
                                                    </div>
                                                </motion.div>
                                            );
                                        })}
                                    {politicoData.noticias.filter((n: any) => filtroEditorial === "Todas as Fontes" || n.linha_editorial === filtroEditorial).length === 0 && (
                                        <div className="text-center p-4 text-xs text-neutral-500 font-mono">
                                            Nenhuma notícia classificada como {filtroEditorial} neste ciclo.
                                        </div>
                                    )}
                                </div>
                            </>
                        ) : (
                            <div className="flex flex-col items-center justify-center p-6 text-center border border-dashed border-neutral-700 bg-neutral-900/20 rounded-2xl flex-1">
                                <span className="text-xs text-neutral-500 font-mono tracking-widest">Nenhuma notícia recente encontrada nos principais portais.</span>
                            </div>
                        )}
                    </motion.div>

                </div>



                {/* WIDGET GEMINI IA */}
                <motion.div
                    initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.9 }}
                    className="mt-12 bg-neutral-900/40 border border-emerald-500/30 rounded-3xl p-8 relative overflow-hidden"
                >
                    <div className="absolute top-0 left-0 w-64 h-64 bg-emerald-500/5 blur-[80px] rounded-full pointer-events-none" />
                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-8 relative z-10">
                        <div>
                            <h3 className="text-2xl font-black text-emerald-400 flex items-center gap-3">
                                <Bot className="w-8 h-8" /> Parecer do Fiscal IA (Gemini 3)
                            </h3>
                            <p className="text-sm text-neutral-400 mt-2 max-w-2xl">
                                Acione a Inteligência Artificial especializada em Controle Externo para ler os JSONs cruzados das empresas declaradas, red flags no STF e identificar conluios invisíveis a olho nu.
                            </p>
                        </div>
                        <button
                            onClick={gerarParecerAceleracionista}
                            disabled={isAuditando}
                            className={`shrink-0 font-bold uppercase tracking-widest text-xs px-8 py-4 rounded-xl transition-all flex items-center gap-2 ${isAuditando ? 'bg-neutral-800 text-neutral-500 cursor-not-allowed border border-neutral-700' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/50 hover:bg-emerald-500 hover:text-white shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)]'}`}
                        >
                            {isAuditando ? (
                                <><div className="w-4 h-4 border-2 border-neutral-500 border-t-transparent rounded-full animate-spin"></div> Vasculhando...</>
                            ) : (
                                <><Fingerprint className="w-4 h-4" /> Executar Varredura Profunda</>
                            )}
                        </button>
                    </div>

                    {parecerIA && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                            className="bg-neutral-950 border border-emerald-500/20 p-6 rounded-2xl relative z-10"
                        >
                            <div className="prose prose-invert prose-emerald max-w-none prose-p:text-sm prose-p:leading-relaxed prose-p:text-neutral-300 prose-strong:text-emerald-400">
                                <ReactMarkdown>{parecerIA}</ReactMarkdown>
                            </div>
                        </motion.div>
                    )}
                </motion.div>

                {/* MODAL INTERNO DO GRAFO REAL 2D */}
                {isTeiaModalOpen && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                        <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="bg-neutral-950 border border-purple-500/50 shadow-[0_0_50px_rgba(168,85,247,0.2)] rounded-3xl p-6 md:p-8 max-w-5xl w-full h-[85vh] relative flex flex-col">
                            <button onClick={() => setIsTeiaModalOpen(false)} className="absolute top-4 right-4 text-neutral-500 hover:text-white z-50">✕</button>
                            <h2 className="text-2xl font-black text-purple-400 mb-6 flex items-center gap-2 shrink-0"><Building2 className="w-6 h-6" /> Teia Empresarial de OSINT</h2>
                            <div className="flex-1 w-full bg-black rounded-2xl border border-neutral-800 overflow-hidden relative">
                                <GrafoCorrupcao politicoData={politicoData} />
                            </div>
                            <div className="shrink-0 mt-4 text-center text-xs text-neutral-500 font-mono">
                                Utilize o mouse/touch para arrastar os nós e dar Zoom. Motor de Grafos renderizado via Canvas HTML5.
                            </div>
                        </motion.div>
                    </div>
                )}
            </main>
        </div>
    );
}
}
