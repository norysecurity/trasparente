"use client";

import { useState, useEffect } from "react";
import { Search, MapPin, User, ShieldAlert, Filter, AlertCircle, X, ShieldCheck } from "lucide-react";
import { ComposableMap, Geographies, Geography, ZoomableGroup } from "react-simple-maps";

const geoUrl = "/brazil-states.json";

export default function Home() {
  const [buscaNome, setBuscaNome] = useState("");
  const [cargoFiltro, setCargoFiltro] = useState("");
  const [estadoSelecionado, setEstadoSelecionado] = useState("");
  const [loading, setLoading] = useState(false);
  const [resultados, setResultados] = useState<any[]>([]);
  const [executivo, setExecutivo] = useState<any>(null);
  const [erro, setErro] = useState("");

  // Estado para o Modal do Dossiê
  const [politicoSelecionado, setPoliticoSelecionado] = useState<any>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/executivo")
      .then(res => res.json())
      .then(data => setExecutivo(data))
      .catch(() => console.log("Erro ao carregar executivo"));
  }, []);

  const realizarBusca = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!buscaNome) return;
    setLoading(true); setErro(""); setResultados([]); setEstadoSelecionado(""); setCargoFiltro("");

    try {
      const res = await fetch(`http://localhost:8000/api/politicos/buscar?nome=${buscaNome}`);
      const data = await res.json();
      if (data.status === "sucesso") setResultados(data.dados);
      else setErro(data.mensagem);
    } catch (err) {
      setErro("Erro de conexão com a API.");
    } finally {
      setLoading(false);
    }
  };

  const buscarPorEstado = async (uf: string) => {
    setLoading(true); setErro(""); setResultados([]); setBuscaNome(""); setCargoFiltro("");
    try {
      const res = await fetch(`http://localhost:8000/api/politicos/estado/${uf}`);
      const data = await res.json();
      if (data.status === "sucesso") {
        // Ordena por score do maior para o menor (Ranking)
        const sorted = data.dados.sort((a: any, b: any) => b.score_auditoria - a.score_auditoria);
        setResultados(sorted);
      }
    } catch (err) {
      setErro("Erro ao buscar políticos deste estado.");
    } finally {
      setLoading(false);
    }
  };

  const handleStateClick = (geo: any) => {
    const uf = geo.id || geo.properties.sigla || "SP";
    setEstadoSelecionado(geo.properties.name);
    buscarPorEstado(uf);
  };

  // Aplica o filtro de cargo apenas no Frontend
  const resultadosFiltrados = resultados.filter(pol => {
    if (!cargoFiltro) return true;
    return pol.cargo.toLowerCase() === cargoFiltro.toLowerCase();
  });

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-emerald-500/30">

      {/* HEADER EXECUTIVO */}
      {executivo && (
        <div className="w-full bg-neutral-900/80 border-b border-neutral-800 p-6 shadow-lg">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full overflow-hidden border-2 border-emerald-500">
                <img src={executivo.presidente.foto} alt="Presidente" className="w-full h-full object-cover" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">{executivo.presidente.nome}</h2>
                <p className="text-emerald-400 text-sm font-semibold">{executivo.presidente.cargo} - {executivo.presidente.partido}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-6 py-12 flex flex-col items-center relative">

        {/* BARRA DE PESQUISA PRINCIPAL */}
        <div className="w-full bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-6 shadow-2xl mb-12">
          <form onSubmit={realizarBusca} className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-3.5 text-neutral-500 w-5 h-5" />
              <input type="text" placeholder="Pesquisar por Nome (ex: Boulos, Aécio...)" value={buscaNome} onChange={(e) => setBuscaNome(e.target.value)} className="w-full bg-neutral-950/50 border border-neutral-800 rounded-xl pl-12 pr-4 py-3 text-neutral-200 focus:ring-2 focus:ring-emerald-500/50" />
            </div>
            <button type="submit" className="bg-emerald-500 hover:bg-emerald-400 text-neutral-950 font-bold px-8 py-3 rounded-xl transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)]">
              Buscar
            </button>
          </form>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 w-full">
          {/* MAPA */}
          <div className="lg:col-span-3 bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-6 relative overflow-hidden h-[600px] flex items-center justify-center">
            <ComposableMap projection="geoMercator" projectionConfig={{ scale: 750, center: [-54, -15] }} className="w-full h-full object-contain">
              <ZoomableGroup zoom={1}>
                <Geographies geography={geoUrl}>
                  {({ geographies }) =>
                    geographies.map((geo) => (
                      <Geography key={geo.rsmKey} geography={geo} onClick={() => handleStateClick(geo)} style={{
                        default: { fill: "#171717", stroke: "#333", strokeWidth: 0.5 },
                        hover: { fill: "#10b981", stroke: "#10b981", cursor: "pointer", transition: "all 250ms" },
                      }} />
                    ))
                  }
                </Geographies>
              </ZoomableGroup>
            </ComposableMap>
          </div>

          {/* COLUNA DIREITA: RANKING E FILTRO DE CARGOS */}
          <div className="lg:col-span-2 bg-neutral-900/30 border border-neutral-800 rounded-3xl p-6 flex flex-col max-h-[600px]">

            <div className="flex justify-between items-end mb-6">
              <h3 className="text-lg font-bold text-emerald-400 flex items-center gap-2">
                {estadoSelecionado ? `Top Políticos: ${estadoSelecionado}` : "Resultados da Busca"}
              </h3>

              {/* FILTRO NOVO MOVIDO PARA CÁ */}
              <div className="relative w-40">
                <Filter className="absolute left-3 top-2.5 text-neutral-500 w-4 h-4" />
                <select value={cargoFiltro} onChange={(e) => setCargoFiltro(e.target.value)} className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-9 pr-3 py-2 text-sm text-neutral-200 appearance-none focus:ring-2 focus:ring-emerald-500/50">
                  <option value="">Todos</option>
                  <option value="governador">Governadores</option>
                  <option value="senador">Senadores</option>
                  <option value="deputado federal">Deputados</option>
                </select>
              </div>
            </div>

            {loading && <div className="flex justify-center py-20"><div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div></div>}
            {erro && <div className="p-4 bg-red-500/10 text-red-400 rounded-xl">{erro}</div>}

            <div className="overflow-y-auto custom-scrollbar flex-1 space-y-3 pr-2">
              {resultadosFiltrados.map((pol, index) => (
                <div
                  key={pol.id}
                  onClick={() => setPoliticoSelecionado(pol)}
                  className="bg-neutral-950 border border-neutral-800 rounded-2xl p-4 flex items-center gap-4 hover:border-emerald-500/50 transition cursor-pointer group"
                >
                  <div className="font-black text-xl text-neutral-800 group-hover:text-emerald-500/30 w-6">{index + 1}</div>
                  <div className="w-12 h-12 rounded-full overflow-hidden bg-neutral-800 border border-neutral-700 flex-shrink-0">
                    {pol.urlFoto ? <img src={pol.urlFoto} alt={pol.nome} className="w-full h-full object-cover" /> : <User className="w-8 h-8 m-2 text-neutral-600" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-neutral-200 text-sm truncate">{pol.nome}</h4>
                    <p className="text-xs text-neutral-500 truncate">{pol.cargo} - {pol.siglaPartido}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className={`font-bold ${pol.score_auditoria >= 700 ? 'text-emerald-400' : pol.score_auditoria >= 400 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {pol.score_auditoria}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* MODAL DO DOSSIÊ (ABRE AO CLICAR NO POLÍTICO) */}
      {politicoSelecionado && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-neutral-900 border border-neutral-800 rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl relative">
            <button onClick={() => setPoliticoSelecionado(null)} className="absolute top-4 right-4 p-2 bg-neutral-800 hover:bg-neutral-700 rounded-full text-white transition z-10">
              <X className="w-5 h-5" />
            </button>

            <div className="p-8">
              <div className="flex gap-6 items-center mb-8 pb-8 border-b border-neutral-800">
                <div className="w-24 h-24 rounded-full overflow-hidden bg-neutral-800 border-4 border-neutral-700">
                  {politicoSelecionado.urlFoto ? <img src={politicoSelecionado.urlFoto} alt={politicoSelecionado.nome} className="w-full h-full object-cover" /> : <User className="w-16 h-16 m-4 text-neutral-600" />}
                </div>
                <div>
                  <h2 className="text-3xl font-black text-white mb-1">{politicoSelecionado.nome}</h2>
                  <p className="text-neutral-400">{politicoSelecionado.cargo} - {politicoSelecionado.siglaPartido}/{politicoSelecionado.siglaUf}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div className="bg-neutral-950 p-6 rounded-2xl border border-neutral-800 text-center flex flex-col items-center justify-center">
                  <h3 className="text-xs font-bold text-neutral-500 uppercase tracking-widest mb-2">Score de Transparência</h3>
                  <div className={`text-6xl font-black ${politicoSelecionado.score_auditoria >= 700 ? 'text-emerald-400' : politicoSelecionado.score_auditoria >= 400 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {politicoSelecionado.score_auditoria}
                  </div>
                </div>

                <div className="bg-neutral-950 p-6 rounded-2xl border border-neutral-800 flex flex-col justify-center">
                  <h3 className="text-sm font-bold text-purple-400 mb-2 flex items-center gap-2">🤖 Auditoria da IA</h3>
                  {politicoSelecionado.score_auditoria < 500 ? (
                    <p className="text-sm text-neutral-300">
                      <strong className="text-red-400">ALERTA:</strong> A Inteligência Artificial detectou anomalias graves no histórico, incluindo investigações ativas ou conflitos de interesse em licitações.
                    </p>
                  ) : (
                    <p className="text-sm text-neutral-300">
                      <strong className="text-emerald-400">Ficha Limpa:</strong> Não foram detectadas irregularidades graves nas fontes oficiais conectadas.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
