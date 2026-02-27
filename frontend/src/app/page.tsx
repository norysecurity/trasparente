"use client";

import { useState } from "react";
import { Search, ShieldAlert, Award, Activity, AlertTriangle, ShieldCheck } from "lucide-react";

export default function Home() {
  const [nome, setNome] = useState("");
  const [cpfCnpj, setCpfCnpj] = useState("");
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<any>(null);
  const [erro, setErro] = useState("");

  const buscarPolitico = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nome || !cpfCnpj) return;

    setLoading(true);
    setErro("");
    setResultado(null);

    try {
      const res = await fetch("http://localhost:8000/auditoria/investigar", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ nome, cpf_cnpj: cpfCnpj }),
      });

      if (!res.ok) {
        throw new Error("Falha na comunicação com o Motor de Auditoria.");
      }

      const data = await res.json();
      setResultado(data);
    } catch (err: any) {
      setErro(err.message || "Erro desconhecido.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-emerald-500/30">
      {/* Background dinâmico */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-neutral-900 via-neutral-950 to-neutral-950 -z-10" />
      
      <main className="max-w-5xl mx-auto px-6 py-16 flex flex-col items-center">
        
        {/* Header */}
        <div className="text-center space-y-4 mb-12">
          <div className="inline-flex items-center justify-center p-3 bg-emerald-500/10 rounded-2xl mb-2 border border-emerald-500/20">
            <Activity className="w-8 h-8 text-emerald-400" />
          </div>
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-400">
            GovTech Transparência
          </h1>
          <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto">
            Auditoria Política Gamificada. Descubra conexões ocultas, contratos suspeitos e o 
            <strong className="text-neutral-200"> Score Serasa</strong> dos candidatos.
          </p>
        </div>

        {/* Barra de Busca (Painel Glassmorphism) */}
        <div className="w-full max-w-2xl bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-6 shadow-2xl">
          <form onSubmit={buscarPolitico} className="flex flex-col sm:flex-row gap-4">
            <input
              type="text"
              placeholder="Nome do Político"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              className="flex-1 bg-neutral-950/50 border border-neutral-800 rounded-xl px-4 py-3 text-neutral-200 placeholder-neutral-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all"
            />
            <input
              type="text"
              placeholder="CPF ou CNPJ"
              value={cpfCnpj}
              onChange={(e) => setCpfCnpj(e.target.value)}
              className="flex-1 bg-neutral-950/50 border border-neutral-800 rounded-xl px-4 py-3 text-neutral-200 placeholder-neutral-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all"
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-emerald-500 hover:bg-emerald-400 text-neutral-950 font-bold px-6 py-3 rounded-xl flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)]"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-neutral-950 border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <Search className="w-5 h-5" />
                  Auditar
                </>
              )}
            </button>
          </form>
          {erro && (
            <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              <p>{erro}</p>
            </div>
          )}
        </div>

        {/* Resultados da Investigação */}
        {resultado && (
          <div className="w-full mt-16 space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
            
            {/* Cards Superiores */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Score Serasa */}
              <div className="bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-6 flex flex-col items-center justify-center text-center relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                <h3 className="text-neutral-400 text-sm uppercase tracking-wider font-semibold mb-2">Score de Transparência</h3>
                <div className={`text-6xl font-black mb-2 ${
                  resultado.resultado_gamificacao.score_auditoria >= 700 ? "text-emerald-400" :
                  resultado.resultado_gamificacao.score_auditoria >= 400 ? "text-yellow-400" : "text-red-400"
                }`}>
                  {resultado.resultado_gamificacao.score_auditoria}
                </div>
                <p className="text-neutral-500 text-xs">Pontuação baseada em cruzamentos de dados oficiais.</p>
              </div>

              {/* Status Gamificado */}
              <div className="bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-6 flex flex-col items-center justify-center text-center">
                <h3 className="text-neutral-400 text-sm uppercase tracking-wider font-semibold mb-4">Status Gamificado</h3>
                <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full font-bold text-sm ${
                  resultado.resultado_gamificacao.status_jogador.includes("Limpa") 
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : resultado.resultado_gamificacao.status_jogador.includes("Suspeito")
                  ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                  : "bg-red-500/10 text-red-400 border border-red-500/20"
                }`}>
                  {resultado.resultado_gamificacao.status_jogador.includes("Limpa") ? <ShieldCheck className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
                  {resultado.resultado_gamificacao.status_jogador}
                </div>
              </div>

              {/* Conquistas (Badges) */}
              <div className="bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-6 flex flex-col items-center justify-center text-center">
                <h3 className="text-neutral-400 text-sm uppercase tracking-wider font-semibold mb-4">Conquistas (Badges)</h3>
                <div className="flex flex-wrap gap-2 justify-center">
                  {resultado.resultado_gamificacao.conquistas_desbloqueadas.map((c: string, idx: number) => (
                    <span key={idx} className="bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-3 py-1.5 rounded-full text-xs font-bold flex items-center gap-1.5">
                      <Award className="w-3.5 h-3.5" />
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Parecer da IA */}
            <div className="bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-blue-500/10 rounded-xl">
                  <Activity className="w-6 h-6 text-blue-400" />
                </div>
                <h2 className="text-2xl font-bold">Parecer da IA Investigativa</h2>
              </div>
              
              <p className="text-neutral-300 leading-relaxed mb-8 bg-neutral-950/50 p-6 rounded-2xl border border-neutral-800/50">
                "{resultado.parecer_auditoria_ia.resumo_auditoria}"
              </p>

              {resultado.parecer_auditoria_ia.red_flags.length > 0 ? (
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-neutral-400 uppercase tracking-wider">Red Flags Detectadas:</h3>
                  {resultado.parecer_auditoria_ia.red_flags.map((flag: any, idx: number) => (
                    <div key={idx} className="flex gap-4 items-start p-4 bg-red-500/5 border border-red-500/10 rounded-2xl">
                      <div className="p-2 bg-red-500/10 rounded-lg text-red-400 shrink-0 mt-0.5">
                        <AlertTriangle className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-neutral-200">{flag.motivo}</p>
                        <div className="mt-2 flex items-center gap-2">
                          <span className="text-xs font-semibold text-neutral-500">Gravidade:</span>
                          <div className="flex gap-1">
                            {[...Array(10)].map((_, i) => (
                              <div key={i} className={`w-1.5 h-1.5 rounded-full ${i < flag.gravidade ? 'bg-red-400' : 'bg-neutral-800'}`} />
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6 bg-emerald-500/5 border border-emerald-500/10 rounded-2xl flex items-center gap-4">
                  <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-400 shrink-0">
                    <ShieldCheck className="w-6 h-6" />
                  </div>
                  <p className="text-emerald-300/90 font-medium">Nenhuma inconsistência de alto risco foi encontrada nas bases de dados conectadas neste momento.</p>
                </div>
              )}
            </div>

            {/* Teia de Conexões (Dados Brutos Estruturados por enquanto) */}
            <div className="bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-purple-500/10 rounded-xl">
                  <Activity className="w-6 h-6 text-purple-400" />
                </div>
                <h2 className="text-2xl font-bold">Grafo de Conexões Encontradas</h2>
              </div>
              
              <div className="bg-neutral-950/80 rounded-2xl p-6 border border-neutral-800 overflow-x-auto">
                <pre className="text-xs text-neutral-400 font-mono">
                  {JSON.stringify(resultado.dossie_enviado, null, 2)}
                </pre>
              </div>
              <p className="text-xs text-neutral-600 mt-4 text-center">
                * No ambiente de produção, este bloco será renderizado por uma biblioteca como react-force-graph consumindo o retorno do Neo4j.
              </p>
            </div>

          </div>
        )}
      </main>
    </div>
  );
}
