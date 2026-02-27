"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ShieldCheck, ArrowLeft, ExternalLink, FileText, Banknote, Scale, MapPin } from "lucide-react";
import { motion } from "framer-motion";

export default function RelatorioCompleto() {
    const params = useParams();
    const router = useRouter();
    const idPolitico = params.id;
    const [loading, setLoading] = useState(true);
    const [politicoData, setPoliticoData] = useState<any>(null);

    useEffect(() => {
        if (!idPolitico) return;

        fetch(`http://localhost:8000/api/politico/detalhes/${idPolitico}`)
            .then(res => res.json())
            .then(data => {
                if (data.status === "sucesso") {
                    setPoliticoData(data.dados);
                }
            })
            .catch(err => console.error("Erro ao buscar dossiê completo ID:", err))
            .finally(() => setLoading(false));
    }, [idPolitico]);

    if (loading) {
        return (
            <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center text-red-500">
                <div className="w-20 h-20 border-4 border-red-500 border-t-transparent rounded-full animate-spin shadow-[0_0_40px_rgba(220,38,38,0.5)]"></div>
                <p className="mt-8 font-mono tracking-widest text-lg animate-pulse font-bold">CARREGANDO DADOS CLASSIFICADOS...</p>
            </div>
        );
    }

    if (!politicoData) {
        return <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center text-neutral-500">Erro: Relatório não encontrado.</div>;
    }

    return (
        <div className="min-h-screen bg-neutral-950 text-neutral-200 font-sans selection:bg-red-500/30">
            <div className="fixed inset-0 bg-[linear-gradient(to_bottom,rgba(220,38,38,0.05),transparent_20%)] pointer-events-none" />

            {/* TOP BAR FIXA COM VOLTAR */}
            <div className="sticky top-0 z-50 bg-neutral-950/90 backdrop-blur-xl border-b border-neutral-800 px-6 py-4 flex items-center justify-between shadow-xl shadow-black/50">
                <button
                    onClick={() => router.push(`/politico/${idPolitico}`)}
                    className="flex items-center gap-2 text-neutral-400 hover:text-white transition group bg-neutral-900 border border-neutral-800 px-4 py-2 rounded-lg hover:border-neutral-700"
                >
                    <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition" />
                    Voltar ao Resumo
                </button>
                <div className="flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-red-500" />
                    <span className="font-mono text-xs tracking-widest text-red-500 hidden sm:block">GOVTECH // AUDITORIA SUPREMA</span>
                </div>
            </div>

            <main className="max-w-5xl mx-auto px-6 py-12">
                {/* HEADER DO RELATÓRIO */}
                <div className="flex flex-col md:flex-row items-center gap-6 mb-16 border-b border-neutral-800 pb-12">
                    <img src={politicoData.foto} alt={politicoData.nome} className="w-32 h-32 rounded-2xl object-cover border border-neutral-700 grayscale hover:grayscale-0 transition duration-500" />
                    <div className="text-center md:text-left">
                        <h1 className="text-4xl font-black text-white">{politicoData.nome}</h1>
                        <p className="text-lg text-neutral-400 font-bold mt-1">{politicoData.cargo} • {politicoData.partido} • {politicoData.uf}</p>
                        <p className="text-sm mt-3 text-red-400 bg-red-500/10 inline-block px-3 py-1 rounded-md border border-red-500/20">
                            Nível de Periculosidade / Score: {politicoData.score_auditoria}
                        </p>
                    </div>
                </div>

                {/* SESSÃO DE DESPESAS (RABO PRESO S/A) - SEM LIMITE DE ALTURA */}
                <section className="mb-20">
                    <h2 className="text-2xl font-black text-white mb-6 flex items-center gap-3">
                        <Banknote className="w-8 h-8 text-purple-500" />
                        Histórico Completo de Despesas (Rabo Preso S/A)
                    </h2>
                    <div className="bg-neutral-900/40 border border-neutral-800 rounded-2xl overflow-hidden shadow-2xl">
                        {politicoData.empresas && politicoData.empresas.length > 0 ? (
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-neutral-900 border-b border-neutral-800 text-neutral-400 text-sm">
                                        <th className="p-4 font-bold">Fornecedor / Beneficiado</th>
                                        <th className="p-4 font-bold">Tipo de Despesa</th>
                                        <th className="p-4 font-bold text-right">Valor Declarado</th>
                                        <th className="p-4 font-bold text-center">Fonte</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {politicoData.empresas.map((emp: any, idx: number) => (
                                        <motion.tr
                                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.05 }}
                                            key={idx} className="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition group"
                                        >
                                            <td className="p-4 text-neutral-200 font-medium">{emp.nome}</td>
                                            <td className="p-4 text-neutral-500 text-sm">{emp.cargo}</td>
                                            <td className="p-4 font-mono text-purple-400 text-right">{emp.valor}</td>
                                            <td className="p-4 flex items-center justify-center">
                                                {emp.fonte ? (
                                                    <a href={emp.fonte} target="_blank" rel="noreferrer" className="w-8 h-8 bg-neutral-800 rounded-full flex items-center justify-center text-neutral-400 hover:text-white hover:bg-purple-500 transition">
                                                        <ExternalLink className="w-4 h-4" />
                                                    </a>
                                                ) : (
                                                    <span className="text-neutral-600 text-xs">-</span>
                                                )}
                                            </td>
                                        </motion.tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : (
                            <div className="p-12 text-center text-neutral-500">Nenhum registro de despesa localizado nesta legislatura.</div>
                        )}
                    </div>
                </section>

                {/* SESSÃO RADAR CRIMINAL COMPLETO */}
                <section className="mb-20">
                    <h2 className="text-2xl font-black text-white mb-6 flex items-center gap-3">
                        <Scale className="w-8 h-8 text-red-500" />
                        Trilha de Red Flags (Radar Criminal)
                    </h2>

                    {politicoData.redFlags && politicoData.redFlags.length > 0 ? (
                        <div className="space-y-6 border-l w-full border-red-900/30 pl-6 ml-4 relative">
                            {politicoData.redFlags.map((flag: any, idx: number) => (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.1 }}
                                    key={idx} className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-6 relative group hover:border-red-900/50 transition-colors"
                                >
                                    <div className="absolute -left-[37px] top-8 w-4 h-4 bg-red-600 rounded-full border-4 border-neutral-950 group-hover:bg-red-500 transition-colors shadow-[0_0_10px_rgba(220,38,38,0.8)]" />
                                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                                        <h3 className="text-xl font-bold text-red-400">{flag.titulo}</h3>
                                        <span className="font-mono text-sm px-3 py-1 bg-neutral-950 rounded-md text-neutral-500 border border-neutral-800">{flag.data}</span>
                                    </div>
                                    <p className="text-neutral-300 leading-relaxed text-sm md:text-base">{flag.desc}</p>

                                    {flag.fonte && (
                                        <div className="mt-6 pt-4 border-t border-neutral-800/50">
                                            <a href={flag.fonte} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 bg-neutral-950 border border-neutral-800 px-4 py-2 rounded-lg text-sm text-neutral-400 hover:text-white hover:border-red-500/50 transition">
                                                <FileText className="w-4 h-4" /> Ver Autos Processuais (PDF)
                                            </a>
                                        </div>
                                    )}
                                </motion.div>
                            ))}
                        </div>
                    ) : (
                        <div className="bg-neutral-900/30 border border-dashed border-red-900/20 rounded-2xl p-12 text-center flex flex-col items-center">
                            <Scale className="w-12 h-12 text-neutral-600 mb-4 opacity-50" />
                            <h3 className="text-neutral-400 font-bold mb-2">Nenhuma ocorrência grave detetada ainda.</h3>
                            <p className="text-neutral-600 text-sm max-w-md">O Robô Autônomo e o Diário Oficial não devolveram correspondências positivas para os CNPJs auditados nesta sessão.</p>
                        </div>
                    )}
                </section>

                {/* SESSÃO ATUAÇÃO (COMISSÕES E PROJETOS) */}
                <section className="mb-12">
                    <h2 className="text-2xl font-black text-white mb-6 flex items-center gap-3">
                        <MapPin className="w-8 h-8 text-emerald-500" />
                        Participação em Órgãos e Comissões
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {politicoData.projetos && politicoData.projetos.length > 0 ? (
                            politicoData.projetos.map((proj: any, idx: number) => (
                                <div key={idx} className="bg-neutral-900/40 border border-neutral-800 p-5 rounded-xl hover:border-emerald-500/30 transition">
                                    <h4 className="font-bold text-neutral-200 mb-1 leading-snug">{proj.titulo}</h4>
                                    <div className="flex items-center justify-between mt-4">
                                        <span className="text-xs font-mono px-2 py-1 bg-neutral-950 border border-neutral-800 rounded text-neutral-400">{proj.status}</span>
                                        <span className="text-xs text-emerald-500 font-bold">Assiduidade: {proj.presence}%</span>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <p className="text-neutral-500 col-span-2 ml-2">Sem comissões ativas nos dados base.</p>
                        )}
                    </div>
                </section>

            </main>
        </div>
    );
}
