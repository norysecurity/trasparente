"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Search, User, MapPin, Activity, ChevronLeft } from "lucide-react";

function BuscaContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const query = searchParams.get("q") || "";
    const [resultados, setResultados] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (query) {
            setLoading(true);
            fetch(`http://localhost:8000/api/politicos/pesquisa?q=${encodeURIComponent(query)}`)
                .then((res) => res.json())
                .then((data) => {
                    if (data.status === "sucesso") {
                        setResultados(data.dados);
                    }
                    setLoading(false);
                })
                .catch((err) => {
                    console.error("Erro na busca:", err);
                    setLoading(false);
                });
        }
    }, [query]);

    return (
        <div className="min-h-screen bg-black text-white p-8 font-sans">
            <div className="max-w-6xl mx-auto">
                <button
                    onClick={() => router.push("/")}
                    className="flex items-center gap-2 text-neutral-400 hover:text-white mb-8 transition-colors group"
                >
                    <ChevronLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
                    Voltar para o Mapa
                </button>

                <div className="flex items-center gap-4 mb-12">
                    <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-2xl">
                        <Search className="w-8 h-8 text-purple-500" />
                    </div>
                    <div>
                        <h1 className="text-4xl font-black uppercase tracking-tight">Resultados da Busca</h1>
                        <p className="text-neutral-400 font-mono tracking-widest text-xs uppercase">
                            Pesquisando por: <span className="text-purple-400">"{query}"</span>
                        </p>
                    </div>
                </div>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-4">
                        <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
                        <p className="font-mono text-xs tracking-widest text-purple-400 animate-pulse">Consultando Agência Nacional de Inteligência...</p>
                    </div>
                ) : resultados.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {resultados.map((p, idx) => (
                            <div
                                key={idx}
                                onClick={() => router.push(`/politico/${p.id}`)}
                                className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 hover:border-purple-500/50 transition-all cursor-pointer group hover:-translate-y-1 shadow-xl"
                            >
                                <div className="flex justify-between items-start mb-4">
                                    <div className="w-12 h-12 bg-neutral-800 rounded-xl flex items-center justify-center group-hover:bg-purple-500/20 transition-colors">
                                        <User className="w-6 h-6 text-neutral-500 group-hover:text-purple-500" />
                                    </div>
                                    <div className="text-right">
                                        <span className="text-[10px] text-neutral-500 font-mono uppercase tracking-tighter">Score</span>
                                        <p className={`text-lg font-black font-mono ${p.score_auditoria === 'Pendente' ? 'text-yellow-500' : (p.score_auditoria > 600 ? 'text-emerald-500' : 'text-red-500')}`}>
                                            {p.score_auditoria}
                                        </p>
                                    </div>
                                </div>

                                <h3 className="text-xl font-bold mb-1 truncate">{p.nome}</h3>
                                <div className="space-y-2 mb-6">
                                    <p className="text-sm text-neutral-400 flex items-center gap-2">
                                        <Activity className="w-3 h-3" /> {p.cargo} — {p.partido}
                                    </p>
                                    <p className="text-sm text-neutral-500 flex items-center gap-2">
                                        <MapPin className="w-3 h-3" /> {p.municipio ? `${p.municipio} / ${p.uf}` : p.uf}
                                    </p>
                                </div>

                                <div className="pt-4 border-t border-neutral-800 flex justify-between items-center text-[10px] font-mono uppercase tracking-widest">
                                    <span className="px-2 py-0.5 bg-neutral-800 rounded text-neutral-400">ID: {p.id}</span>
                                    <span className="text-purple-400 group-hover:underline">Ver Dossiê</span>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-32 bg-neutral-900/20 border border-dashed border-neutral-800 rounded-3xl">
                        <Search className="w-16 h-16 text-neutral-700 mx-auto mb-4" />
                        <p className="text-xl font-bold text-neutral-500 mb-2">Nenhum alvo encontrado.</p>
                        <p className="text-neutral-600 text-sm">Tente buscar por nome completo, CPF ou ID do TSE.</p>
                    </div>
                )}
            </div>
        </div>
    );
}

export default function BuscaPage() {
    return (
        <Suspense fallback={<div>Carregando...</div>}>
            <BuscaContent />
        </Suspense>
    );
}
