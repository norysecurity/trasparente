"use client";

import { useState } from "react";
import { Search, ShieldAlert, Award, Activity, AlertTriangle, ShieldCheck, MapPin, Building2, FileText, DollarSign } from "lucide-react";
import { ComposableMap, Geographies, Geography, ZoomableGroup } from "react-simple-maps";

const geoUrl = "/brazil-states.json"; // O arquivo deve estar na pasta public

export default function Home() {
  const [nome, setNome] = useState("");
  const [cpfCnpj, setCpfCnpj] = useState("");
  const [estadoSelecionado, setEstadoSelecionado] = useState("");
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<any>(null);
  const [erro, setErro] = useState("");

  const buscarPolitico = async (e?: React.FormEvent, nomeForcado?: string, documentoForcado?: string) => {
    if (e) e.preventDefault();

    const buscaNome = nomeForcado || nome;
    const buscaDoc = documentoForcado || cpfCnpj;

    if (!buscaNome) return;

    setLoading(true);
    setErro("");
    setResultado(null);

    try {
      const res = await fetch("http://localhost:8000/auditoria/investigar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome: buscaNome, cpf_cnpj: buscaDoc || "00000000000" }),
      });

      if (!res.ok) throw new Error("Falha na comunicação com o Motor de Auditoria.");
      const data = await res.json();
      setResultado(data);
    } catch (err: any) {
      setErro(err.message || "Erro desconhecido.");
    } finally {
      setLoading(false);
    }
  };

  const handleStateClick = (geo: any) => {
    const estadoNome = geo.properties.name;
    setEstadoSelecionado(estadoNome);
    // Simula pesquisar um político aleatório do estado clicado para fins de demonstração da PoC.
    const nomeDemo = `Político de ${estadoNome}`;
    setNome(nomeDemo);
    setCpfCnpj("11122233344"); // CPF Fake
    buscarPolitico(undefined, nomeDemo, "11122233344");
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-emerald-500/30">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-neutral-900 via-neutral-950 to-neutral-950 -z-10" />

      <main className="max-w-7xl mx-auto px-6 py-16 flex flex-col items-center">

        {/* Header */}
        <div className="text-center space-y-4 mb-12">
          <div className="inline-flex items-center justify-center p-3 bg-emerald-500/10 rounded-2xl mb-2 border border-emerald-500/20">
            <Activity className="w-8 h-8 text-emerald-400" />
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-400">
            GovTech Transparência
          </h1>
          <p className="text-lg text-neutral-400 max-w-2xl mx-auto">
            Auditoria Política Gamificada. Pesquise pelo Nome, ou <strong className="text-neutral-200">clique em um Estado no mapa</strong> para auditar agentes públicos da região.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 w-full">
          {/* Lado Esquerdo: Barra de Busca e Mapa */}
          <div className="flex flex-col gap-6">

            <div className="bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-6 shadow-2xl">
              <form onSubmit={buscarPolitico} className="flex flex-col gap-4">
                <input
                  type="text"
                  placeholder="Nome do Político"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  className="w-full bg-neutral-950/50 border border-neutral-800 rounded-xl px-4 py-3 text-neutral-200 placeholder-neutral-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all font-medium"
                />
                <div className="flex gap-4">
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
                      <Search className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </form>
              {erro && (
                <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl flex items-center gap-3 text-sm">
                  <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                  <p>{erro}</p>
                </div>
              )}
            </div>

            {/* Globo/Mapa */}
            <div className="bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-6 shadow-2xl relative overflow-hidden h-[400px] flex items-center justify-center">
              <h3 className="absolute top-6 left-6 text-neutral-400 font-bold tracking-widest text-xs uppercase flex items-center gap-2">
                <MapPin className="w-4 h-4" /> Mapa Interativo
              </h3>
              {estadoSelecionado && (
                <div className="absolute top-6 right-6 bg-emerald-500/20 text-emerald-300 px-3 py-1 rounded-full text-xs font-bold border border-emerald-500/30">
                  {estadoSelecionado}
                </div>
              )}
              <ComposableMap
                projection="geoMercator"
                projectionConfig={{ scale: 500, center: [-54, -15] }}
                className="w-full h-full object-cover"
              >
                <ZoomableGroup zoom={1}>
                  <Geographies geography={geoUrl}>
                    {({ geographies }) =>
                      geographies.map((geo) => (
                        <Geography
                          key={geo.rsmKey}
                          geography={geo}
                          onClick={() => handleStateClick(geo)}
                          className="focus:outline-none"
                          style={{
                            default: { fill: "#171717", stroke: "#333", strokeWidth: 0.5 },
                            hover: { fill: "#10b981", stroke: "#10b981", cursor: "pointer", transition: "all 250ms" },
                            pressed: { fill: "#059669" },
                          }}
                        />
                      ))
                    }
                  </Geographies>
                </ZoomableGroup>
              </ComposableMap>
            </div>
          </div>

          {/* Lado Direito: Resultados da Investigação */}
          <div className="flex flex-col min-h-[500px]">
            {!resultado && !loading && (
              <div className="h-full border-2 border-dashed border-neutral-800 rounded-3xl flex flex-col items-center justify-center text-neutral-600 p-8 text-center bg-neutral-900/20">
                <ShieldAlert className="w-16 h-16 mb-4 opacity-50" />
                <h3 className="text-xl font-bold mb-2">Aguardando Auditoria</h3>
                <p className="text-sm">Selecione um estado ou pesquise no painel ao lado para gerar o dossiê da IA e visualizar os contratos e score.</p>
              </div>
            )}

            {loading && (
              <div className="h-full border border-neutral-800 rounded-3xl flex flex-col items-center justify-center p-8 text-center bg-neutral-900/50">
                <div className="w-12 h-12 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-4" />
                <h3 className="text-lg font-bold text-emerald-400 animate-pulse">A IA está processando...</h3>
                <p className="text-neutral-500 text-sm mt-2">Cruzando dados do TSE e do Portal da Transparência no Grafo.</p>
              </div>
            )}

            {resultado && !loading && (
              <div className="space-y-6 animate-in fade-in slide-in-from-right-8 duration-500">
                {/* Score e Status Game */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-6 flex flex-col items-center text-center">
                    <h3 className="text-neutral-400 text-xs uppercase tracking-wider font-bold mb-1">Score Transparência</h3>
                    <div className={`text-5xl font-black ${resultado.resultado_gamificacao.score_auditoria >= 700 ? "text-emerald-400" :
                        resultado.resultado_gamificacao.score_auditoria >= 400 ? "text-yellow-400" : "text-red-400"
                      }`}>
                      {resultado.resultado_gamificacao.score_auditoria}
                    </div>
                  </div>

                  <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-6 flex flex-col items-center justify-center text-center">
                    <h3 className="text-neutral-400 text-xs uppercase tracking-wider font-bold mb-3">Status</h3>
                    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full font-bold text-xs ${resultado.resultado_gamificacao.status_jogador.includes("Limpa")
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : resultado.resultado_gamificacao.status_jogador.includes("Suspeito")
                          ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                          : "bg-red-500/10 text-red-400 border border-red-500/20"
                      }`}>
                      {resultado.resultado_gamificacao.status_jogador.includes("Limpa") ? <ShieldCheck className="w-3 h-3" /> : <ShieldAlert className="w-3 h-3" />}
                      {resultado.resultado_gamificacao.status_jogador}
                    </div>
                  </div>
                </div>

                {/* Resumo da IA */}
                <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6">
                  <h3 className="text-sm font-bold text-blue-400 tracking-wider flex items-center gap-2 mb-3">
                    <Activity className="w-4 h-4" /> Parecer do Auditor IA (Qwen)
                  </h3>
                  <p className="text-neutral-300 text-sm leading-relaxed">
                    {resultado.parecer_auditoria_ia.resumo_auditoria}
                  </p>

                  {/* Red flags */}
                  {resultado.parecer_auditoria_ia.red_flags.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {resultado.parecer_auditoria_ia.red_flags.map((flag: any, idx: number) => (
                        <div key={idx} className="flex gap-3 text-sm p-3 bg-red-500/10 border border-red-500/20 rounded-xl items-start">
                          <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                          <span className="text-red-200">{flag.motivo}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Detalhamento dos Dados Encontrados (Substitui Json Bruto) */}
                <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 space-y-4">
                  <h3 className="text-sm font-bold text-neutral-400 uppercase tracking-widest mb-4">Evidências Coletadas</h3>

                  {/* TSE - Bens e Empresas */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-neutral-950 p-4 rounded-xl border border-neutral-800/50">
                      <div className="flex items-center gap-2 text-cyan-400 mb-2">
                        <DollarSign className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase tracking-wide">Patrimônio Declarado (TSE)</span>
                      </div>
                      <p className="text-lg font-bold text-neutral-200">
                        R$ {resultado.dossie_enviado.dados_tse.bens_declarados_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                      </p>
                    </div>
                    <div className="bg-neutral-950 p-4 rounded-xl border border-neutral-800/50 flex flex-col justify-center">
                      <div className="flex items-center gap-2 text-purple-400 mb-2">
                        <Building2 className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase tracking-wide">Empresas Ligadas</span>
                      </div>
                      {resultado.dossie_enviado.dados_tse.empresas_declaradas.map((emp: any, idx: number) => (
                        <p key={idx} className="text-sm text-neutral-300 font-medium whitespace-nowrap overflow-hidden text-ellipsis">
                          {emp.nome} ({emp.participacao})
                        </p>
                      ))}
                    </div>
                  </div>

                  {/* Transparência - Contratos */}
                  <div className="bg-neutral-950 p-4 rounded-xl border border-neutral-800/50 mt-4">
                    <div className="flex items-center gap-2 text-emerald-400 mb-3">
                      <FileText className="w-4 h-4" />
                      <span className="text-xs font-bold uppercase tracking-wide">Contratos Públicos</span>
                    </div>
                    {resultado.dossie_enviado.dados_governamentais.contratos_encontrados.length > 0 ? (
                      <ul className="space-y-3">
                        {resultado.dossie_enviado.dados_governamentais.contratos_encontrados.map((con: any, idx: number) => (
                          <li key={idx} className="flex flex-col text-sm border-l-2 border-neutral-700 pl-3">
                            <span className="font-bold text-neutral-200">{con.objeto}</span>
                            <div className="flex flex-wrap justify-between text-neutral-400 mt-1">
                              <span>{con.empresa_vencedora}</span>
                              <span className="font-mono text-emerald-300">R$ {con.valor.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-neutral-500">Nenhum contrato público encontrado para os associados.</p>
                    )}
                  </div>

                </div>

                {/* Conquistas (Badges) */}
                <div className="flex items-center gap-2 justify-center pt-2">
                  {resultado.resultado_gamificacao.conquistas_desbloqueadas.map((c: string, idx: number) => (
                    <span key={idx} className="bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2 shadow-lg">
                      <Award className="w-4 h-4 text-emerald-400" />
                      {c}
                    </span>
                  ))}
                </div>

              </div>
            )}
          </div>

        </div>
      </main>
    </div>
  );
}
