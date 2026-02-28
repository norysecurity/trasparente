"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowDownRight, ArrowUpRight, Wallet, Receipt, Calendar, CreditCard } from "lucide-react";

export default function ExtratoBancario() {
    const params = useParams();
    const router = useRouter();
    const idPolitico = params.id;
    const [loading, setLoading] = useState(true);
    const [politicoData, setPoliticoData] = useState<any>(null);

    // Filtros Menus
    const [filtroMes, setFiltroMes] = useState("Todos");
    const [filtroAno, setFiltroAno] = useState("Todos");

    useEffect(() => {
        fetch(`http://localhost:8000/api/politico/detalhes/${idPolitico}`)
            .then(res => res.json())
            .then(data => {
                if (data.status === "sucesso") {
                    setPoliticoData(data.dados);
                }
            })
            .catch(err => console.error("Erro:", err))
            .finally(() => setLoading(false));
    }, [idPolitico]);

    if (loading) {
        return (
            <div className="min-h-screen bg-black flex items-center justify-center text-emerald-500">
                <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
        );
    }

    if (!politicoData) return <div className="min-h-screen bg-black text-white p-6">Erro ao carregar dados.</div>;

    const despesasFiltradas = politicoData.empresas?.filter((emp: any) => {
        if (!emp.data) return true;
        const [ano, mes] = emp.data.split('-'); // Formato: 2024-03-12T...
        const mesInt = parseInt(mes, 10);

        const mesMatch = filtroMes === "Todos" || mesInt.toString() === filtroMes;
        const anoMatch = filtroAno === "Todos" || ano === filtroAno;
        return mesMatch && anoMatch;
    }) || [];

    const totalGasto = despesasFiltradas.reduce((acc: number, emp: any) => {
        const valorNumerico = parseFloat(emp.valor.replace("R$ ", "").replace(/\./g, "").replace(",", "."));
        return acc + (isNaN(valorNumerico) ? 0 : valorNumerico);
    }, 0) || 0;

    return (
        <div className="min-h-screen bg-neutral-950 font-sans selection:bg-emerald-500/30 flex justify-center">
            {/* Limitador de largura para parecer uma tela de celular no Desktop */}
            <div className="w-full max-w-md bg-black min-h-screen relative shadow-2xl border-x border-neutral-900 overflow-x-hidden">

                {/* Header App de Banco */}
                <header className="bg-neutral-900 pt-12 pb-6 px-6 rounded-b-3xl relative z-10 border-b border-neutral-800">
                    <button onClick={() => router.back()} className="text-neutral-400 hover:text-white mb-6 transition">
                        <ArrowLeft className="w-6 h-6" />
                    </button>

                    <div className="flex items-center gap-4 mb-6">
                        <img src={politicoData.foto} alt="Foto" className="w-14 h-14 rounded-full border-2 border-neutral-700 object-cover" />
                        <div>
                            <p className="text-neutral-400 text-sm">Conta Pública GovTech</p>
                            <h1 className="text-white font-bold text-lg leading-tight truncate w-48">{politicoData.nome}</h1>
                        </div>
                    </div>

                    <div className="bg-neutral-950 rounded-2xl p-5 border border-neutral-800 shadow-inner">
                        <div className="flex justify-between items-center mb-1">
                            <span className="text-neutral-500 text-xs font-bold uppercase flex items-center gap-1"><Wallet className="w-3 h-3" /> Gasto Acumulado</span>
                        </div>
                        <div className="text-3xl font-black text-white tracking-tight">
                            {totalGasto.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                        </div>
                        <p className="text-red-500 text-xs mt-2 flex items-center gap-1 font-mono">
                            <ArrowDownRight className="w-3 h-3" /> Dinheiro do Contribuinte
                        </p>
                    </div>
                </header>

                {/* Lista de Transações (Extrato) */}
                <div className="px-6 py-6">
                    {/* FILTROS DE DATA */}
                    <div className="flex gap-2 mb-6">
                        <select
                            value={filtroMes}
                            onChange={(e) => setFiltroMes(e.target.value)}
                            className="bg-neutral-900 border border-neutral-800 text-white rounded-lg px-3 py-2 text-sm w-full outline-none focus:border-emerald-500"
                        >
                            <option value="Todos">Mês (Todos)</option>
                            <option value="1">Janeiro</option>
                            <option value="2">Fevereiro</option>
                            <option value="3">Março</option>
                            <option value="4">Abril</option>
                            <option value="5">Maio</option>
                            <option value="6">Junho</option>
                            <option value="7">Julho</option>
                            <option value="8">Agosto</option>
                            <option value="9">Setembro</option>
                            <option value="10">Outubro</option>
                            <option value="11">Novembro</option>
                            <option value="12">Dezembro</option>
                        </select>
                        <select
                            value={filtroAno}
                            onChange={(e) => setFiltroAno(e.target.value)}
                            className="bg-neutral-900 border border-neutral-800 text-white rounded-lg px-3 py-2 text-sm w-full outline-none focus:border-emerald-500"
                        >
                            <option value="Todos">Ano (Todos)</option>
                            <option value="2025">2025</option>
                            <option value="2024">2024</option>
                            <option value="2023">2023</option>
                            <option value="2022">2022</option>
                            <option value="2021">2021</option>
                        </select>
                    </div>

                    <h2 className="text-white font-bold mb-6 flex items-center gap-2">
                        <Calendar className="w-5 h-5 text-emerald-500" /> Extrato Mensal/Anual
                    </h2>

                    <div className="space-y-4">
                        {despesasFiltradas.length > 0 ? (
                            despesasFiltradas.map((emp: any, idx: number) => (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: idx * 0.05 }}
                                    key={idx}
                                >
                                    <div className="flex justify-between items-center bg-neutral-900/50 p-4 rounded-2xl border border-neutral-800/50">
                                        <div className="flex gap-4 items-center">
                                            <div className="w-10 h-10 rounded-full bg-neutral-800 flex items-center justify-center shrink-0">
                                                {emp.cargo.includes("Passagem") || emp.cargo.includes("Combustível") ? (
                                                    <CreditCard className="w-5 h-5 text-neutral-400" />
                                                ) : (
                                                    <Receipt className="w-5 h-5 text-neutral-400" />
                                                )}
                                            </div>
                                            <div>
                                                <p className="text-white font-bold text-sm w-36 truncate">{emp.nome}</p>
                                                <p className="text-neutral-500 text-[10px] uppercase truncate w-36">{emp.cargo}</p>
                                                {emp.data && <p className="text-neutral-600 text-[9px] mt-1">{emp.data}</p>}
                                            </div>
                                        </div>
                                        <div className="flex flex-col items-end gap-1 shrink-0">
                                            <p className="text-red-400 font-mono font-bold text-sm">-{emp.valor}</p>
                                            {/* BOTÃO PARA ABRIR A NOTA FISCAL OFICIAL */}
                                            {emp.fonte && emp.fonte.startsWith("http") && (
                                                <a href={emp.fonte} target="_blank" rel="noopener noreferrer" className="text-[10px] text-emerald-500 hover:text-emerald-400 flex items-center gap-1 bg-emerald-500/10 px-2 py-1 rounded">
                                                    Ver Nota Oficial <ArrowUpRight className="w-3 h-3" />
                                                </a>
                                            )}
                                        </div>
                                    </div>
                                </motion.div>
                            ))
                        ) : (
                            <div className="text-center py-10 text-neutral-500 text-sm">
                                Nenhuma transação registrada neste ciclo.
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer Disclaimer */}
                <div className="text-center p-6 text-[10px] text-neutral-600 font-mono uppercase pb-12">
                    Transações baseadas em dados do Portal da Transparência e Câmara. Valores simulados para interface visual.
                </div>
            </div>
        </div>
    );
}
