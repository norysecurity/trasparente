'use client'

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Search,
    FileText,
    ShieldAlert,
    ShieldCheck,
    ChevronRight,
    ChevronLeft,
    X,
    Folder,
    MapPin,
    AlertCircle,
    Download,
    ExternalLink,
    Activity,
    Database,
    Clock
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface DossieResumo {
    id: string;
    nome: string;
    score: number;
    nivel: string;
    uf: string;
    cidade: string;
    filename: string;
}

interface SalaArquivosProps {
    aoFechar: () => void;
}

type NavegacaoModo = 'estados' | 'cidades' | 'arquivos' | 'dossie'

export default function SalaArquivos({ aoFechar }: SalaArquivosProps) {
    const [modo, setModo] = useState<NavegacaoModo>('estados')
    const [estadoSel, setEstadoSel] = useState('')
    const [cidadeSel, setCidadeSel] = useState('')
    const [dossieSel, setDossieSel] = useState<any | null>(null)

    const [items, setItems] = useState<any[]>([])
    const [carregando, setCarregando] = useState(false)
    const [busca, setBusca] = useState('')

    // Carregar Estados inicialmente
    useEffect(() => {
        carregarEstrutura()
    }, [modo, estadoSel, cidadeSel])

    const carregarEstrutura = async () => {
        setCarregando(true)
        try {
            let url = 'http://localhost:8000/api/dossies/arvore'
            if (modo === 'cidades') url += `?uf=${estadoSel}`
            if (modo === 'arquivos') url += `?uf=${estadoSel}&cidade=${cidadeSel}`

            const res = await fetch(url)
            const data = await res.json()
            setItems(data.items || [])
        } catch (error) {
            console.error("Erro ao carregar estrutura:", error)
        } finally {
            setCarregando(false)
        }
    }

    const abrirDossie = async (filename: string) => {
        setCarregando(true)
        try {
            const res = await fetch(`http://localhost:8000/api/politico/detalhes/arquivo?path=${filename}`)
            const data = await res.json()
            setDossieSel(data)
            setModo('dossie')
        } catch (error) {
            console.error("Erro ao abrir dossiê:", error)
        } finally {
            setCarregando(false)
        }
    }

    const voltar = () => {
        if (modo === 'dossie') setModo('arquivos')
        else if (modo === 'arquivos') setModo('cidades')
        else if (modo === 'cidades') setModo('estados')
    }

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] bg-white text-black flex flex-col font-sans"
        >
            {/* TOPO: BARRA DE NAVEGAÇÃO E TÍTULO CLEAN */}
            <header className="p-8 border-b-2 border-neutral-100 flex justify-between items-center bg-white shadow-sm">
                <div className="flex items-center gap-6">
                    <button
                        onClick={aoFechar}
                        className="p-3 bg-neutral-100 hover:bg-neutral-200 rounded-full transition-colors"
                    >
                        <X className="w-8 h-8" />
                    </button>
                    <div>
                        <h1 className="text-4xl font-black tracking-tight uppercase flex items-center gap-3">
                            <Database className="w-10 h-10 text-red-600" />
                            Sala de Arquivos <span className="text-neutral-300">/</span> Auditoria Sênior
                        </h1>
                        <p className="text-lg text-neutral-500 font-medium">Gestão Nacional de Dossiês e Evidências</p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 bg-neutral-100 px-4 py-2 rounded-full">
                        <Clock className="w-5 h-5 text-neutral-400" />
                        <span className="text-sm font-bold text-neutral-600">Sincronizado: {new Date().toLocaleDateString('pt-BR')}</span>
                    </div>
                </div>
            </header>

            <main className="flex-1 overflow-hidden flex flex-col p-10 bg-neutral-50">
                {/* CAMINHO DE PASTA (BREADCRUMB) */}
                <nav className="mb-10 flex items-center gap-4 text-2xl font-bold">
                    <button
                        onClick={() => setModo('estados')}
                        className={`hover:text-red-600 transition-colors ${modo === 'estados' ? 'text-red-600' : 'text-neutral-400'}`}
                    >
                        Brasil
                    </button>
                    {estadoSel && (
                        <>
                            <ChevronRight className="w-6 h-6 text-neutral-300" />
                            <button
                                onClick={() => setModo('cidades')}
                                className={`hover:text-red-600 transition-colors ${modo === 'cidades' ? 'text-red-600' : 'text-neutral-400'}`}
                            >
                                {estadoSel}
                            </button>
                        </>
                    )}
                    {cidadeSel && modo !== 'estados' && modo !== 'cidades' && (
                        <>
                            <ChevronRight className="w-6 h-6 text-neutral-300" />
                            <button
                                onClick={() => setModo('arquivos')}
                                className={`hover:text-red-600 transition-colors ${modo === 'arquivos' ? 'text-red-600' : 'text-neutral-400'}`}
                            >
                                {cidadeSel}
                            </button>
                        </>
                    )}
                </nav>

                {/* BUSCA RÁPIDA (Clear Input) */}
                <div className="mb-12 relative max-w-4xl">
                    <Search className="absolute left-6 top-1/2 -translate-y-1/2 w-10 h-10 text-neutral-300" />
                    <input
                        type="text"
                        placeholder="Pesquisar nos arquivos nacionais..."
                        className="w-full bg-white border-4 border-neutral-100 rounded-3xl p-8 pl-20 text-3xl font-bold shadow-xl outline-none focus:border-red-500 transition-all placeholder-neutral-200"
                        value={busca}
                        onChange={(e) => setBusca(e.target.value)}
                    />
                </div>

                <div className="flex-1 overflow-y-auto pr-6 custom-scrollbar">
                    <AnimatePresence mode="wait">
                        {carregando ? (
                            <motion.div
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                className="flex flex-col items-center justify-center h-full gap-6"
                            >
                                <div className="w-20 h-20 border-8 border-red-600 border-t-transparent rounded-full animate-spin"></div>
                                <p className="text-3xl font-black uppercase text-neutral-300">Acessando Cofres Federais...</p>
                            </motion.div>
                        ) : modo === 'dossie' && dossieSel ? (
                            <motion.div
                                initial={{ y: 50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 20, opacity: 0 }}
                                className="bg-white rounded-[40px] shadow-2xl overflow-hidden border-2 border-neutral-100 max-w-6xl mx-auto"
                            >
                                {/* HEADER DOSSIE (Estilo Documento Governamental) */}
                                <div className="bg-neutral-900 p-12 text-white flex justify-between items-start">
                                    <div>
                                        <div className="flex items-center gap-4 mb-4">
                                            <span className="bg-red-600 text-white px-4 py-1 text-sm font-black uppercase tracking-tighter">Confidencial</span>
                                            <span className="text-neutral-400 font-mono text-sm tracking-widest uppercase">ID: {dossieSel.id}</span>
                                        </div>
                                        <h2 className="text-6xl font-black mb-2 uppercase leading-none">{dossieSel.nome_politico || "Político"}</h2>
                                        <div className="flex items-center gap-6 mt-6">
                                            <div className="flex items-center gap-2 px-6 py-2 bg-white/10 rounded-full border border-white/10">
                                                <MapPin className="w-5 h-5 text-red-500" />
                                                <span className="text-lg font-bold uppercase">{dossieSel.cidade} - {dossieSel.uf}</span>
                                            </div>
                                            <div className="flex items-center gap-2 px-6 py-2 bg-white/10 rounded-full border border-white/10">
                                                <ShieldCheck className="w-5 h-5 text-emerald-500" />
                                                <span className="text-lg font-bold uppercase">{dossieSel.partido || 'N/A'}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex flex-col items-center">
                                        <div className={`w-32 h-32 rounded-3xl flex items-center justify-center border-4 ${dossieSel.ia_analise?.score_risco > 70 ? 'border-red-500 bg-red-500/10' : 'border-emerald-500 bg-emerald-500/10'}`}>
                                            <span className="text-5xl font-black">{dossieSel.ia_analise?.score_risco || 0}</span>
                                        </div>
                                        <p className="mt-4 text-xs font-black uppercase tracking-widest text-neutral-500">Score de Risco</p>
                                    </div>
                                </div>

                                <div className="p-16 grid grid-cols-1 lg:grid-cols-3 gap-16">
                                    {/* COLUNA ESQUERDA: RED FLAGS */}
                                    <div className="lg:col-span-1 space-y-8">
                                        <h3 className="text-2xl font-black uppercase border-b-4 border-red-600 pb-2 inline-block">Anomalias Detectadas</h3>
                                        <div className="space-y-6">
                                            {dossieSel.ia_analise?.red_flags?.map((flag: any, i: number) => (
                                                <div key={i} className="p-6 bg-red-50 rounded-3xl border-2 border-red-100 shadow-sm">
                                                    <div className="flex items-center gap-3 mb-3">
                                                        <ShieldAlert className="w-8 h-8 text-red-600" />
                                                        <span className="text-sm font-black uppercase text-red-900 tracking-tighter">Alerta {flag.nivel}</span>
                                                    </div>
                                                    <div className="prose prose-sm prose-red font-bold text-red-800">
                                                        <ReactMarkdown>{flag.motivo}</ReactMarkdown>
                                                    </div>
                                                </div>
                                            ))}
                                            {(!dossieSel.ia_analise?.red_flags || dossieSel.ia_analise.red_flags.length === 0) && (
                                                <div className="p-8 border-4 border-dashed border-neutral-100 rounded-[40px] text-center">
                                                    <ShieldCheck className="w-16 h-16 text-emerald-300 mx-auto mb-4" />
                                                    <p className="text-lg font-bold text-neutral-400">Nenhuma anomalia crítica identificada até o momento.</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* COLUNA DIREITA: RELATÓRIO COMPLETO IA */}
                                    <div className="lg:col-span-2 space-y-8">
                                        <div className="flex justify-between items-end border-b-4 border-neutral-900 pb-2">
                                            <h3 className="text-2xl font-black uppercase">Parecer Técnico Investigativo</h3>
                                            <button className="flex items-center gap-2 p-3 bg-neutral-900 text-white rounded-xl hover:bg-black transition-colors">
                                                <Download className="w-5 h-5" />
                                                <span className="text-xs font-bold uppercase">Exportar PDF</span>
                                            </button>
                                        </div>
                                        <div className="bg-neutral-50 p-10 rounded-[40px] border-2 border-neutral-100 prose prose-lg prose-neutral max-w-none font-medium leading-relaxed">
                                            <ReactMarkdown>{dossieSel.ia_analise?.resumo_investigativo || "Relatório em branco."}</ReactMarkdown>
                                        </div>

                                        {/* EVIDENCIAS BRUTAS */}
                                        <div className="pt-10">
                                            <h4 className="text-xl font-black uppercase mb-6 flex items-center gap-3">
                                                <Database className="w-6 h-6 text-neutral-400" />
                                                Arquivos Brutos e Provas
                                            </h4>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                {dossieSel.empresas?.map((emp: any, i: number) => (
                                                    <div key={i} className="p-6 bg-white border-2 border-neutral-100 rounded-2xl flex justify-between items-center group hover:border-red-500 transition-all cursor-pointer">
                                                        <div>
                                                            <p className="text-[10px] font-black uppercase text-neutral-400">Contrato / Empresa</p>
                                                            <p className="text-lg font-bold text-neutral-800">{emp.razao_social}</p>
                                                        </div>
                                                        <ExternalLink className="w-6 h-6 text-neutral-200 group-hover:text-red-500 transition-colors" />
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        ) : (
                            <motion.div
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8"
                            >
                                {items.filter(item => item.nome.toLowerCase().includes(busca.toLowerCase())).map((item, i) => (
                                    <motion.div
                                        key={i}
                                        whileHover={{ y: -10, scale: 1.02 }}
                                        whileTap={{ scale: 0.98 }}
                                        onClick={() => {
                                            if (item.tipo === 'pasta') {
                                                if (modo === 'estados') { setEstadoSel(item.nome); setModo('cidades'); }
                                                else if (modo === 'cidades') { setCidadeSel(item.nome); setModo('arquivos'); }
                                            } else {
                                                abrirDossie(item.path);
                                            }
                                        }}
                                        className="bg-white p-10 rounded-[40px] shadow-xl border-4 border-neutral-100 cursor-pointer group hover:border-red-500 transition-all relative overflow-hidden"
                                    >
                                        {item.tipo === 'pasta' ? (
                                            <div className="flex flex-col h-full justify-between gap-10">
                                                <Folder className="w-20 h-20 text-red-500 group-hover:scale-110 transition-transform" />
                                                <div>
                                                    <h3 className="text-4xl font-black uppercase leading-none mb-2">{item.nome}</h3>
                                                    <p className="text-xl font-bold text-neutral-400 uppercase tracking-widest">{item.total || 0} Registros</p>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="flex flex-col h-full justify-between gap-10">
                                                <div className="flex justify-between items-start">
                                                    <FileText className="w-16 h-16 text-neutral-900" />
                                                    <div className={`px-4 py-1 rounded-lg text-sm font-black uppercase ${item.score > 70 ? 'bg-red-500 text-white' : 'bg-emerald-500 text-white'}`}>
                                                        Score: {item.score}
                                                    </div>
                                                </div>
                                                <div>
                                                    <h3 className="text-3xl font-black uppercase leading-[1.1] mb-2">{item.nome}</h3>
                                                    <p className="text-sm font-bold text-neutral-400 uppercase tracking-widest">{item.cidade} - {item.uf}</p>
                                                </div>
                                            </div>
                                        )}
                                        {/* EFEITO DE LUZ */}
                                        <div className="absolute top-0 right-0 w-24 h-24 bg-red-600/5 blur-3xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity"></div>
                                    </motion.div>
                                ))}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </main>

            {/* BOTÃO VOLTAR (Sticky) */}
            {modo !== 'estados' && (
                <button
                    onClick={voltar}
                    className="fixed bottom-10 left-10 p-6 bg-neutral-900 text-white rounded-full shadow-2xl hover:scale-110 transition-all z-[110] flex items-center gap-3 px-10"
                >
                    <ChevronLeft className="w-10 h-10" />
                    <span className="text-2xl font-black uppercase">Voltar</span>
                </button>
            )}

            <style jsx global>{`
                .custom-scrollbar::-webkit-scrollbar { width: 12px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: #f5f5f5; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: #edecec; border-radius: 20px; border: 4px solid #f5f5f5; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #dcdbdb; }
            `}</style>
        </motion.div>
    )
}
