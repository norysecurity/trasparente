"use client";

import { useState, useEffect } from "react";
import { Search, MapPin, User, ShieldCheck, Filter, AlertCircle, ChevronRight } from "lucide-react";
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

  useEffect(() => {
    fetch("http://localhost:8000/api/executivo")
      .then(res => res.json())
      .then(data => setExecutivo(data))
      .catch(() => console.log("Erro ao carregar executivo"));
  }, []);

  const realizarBusca = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!buscaNome) return;
    setLoading(true); setErro(""); setResultados([]); setEstadoSelecionado("");

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
    setLoading(true); setErro(""); setResultados([]); setBuscaNome("");
    try {
      const res = await fetch(`http://localhost:8000/api/politicos/estado/${uf}`);
      const data = await res.json();
      if (data.status === "sucesso") setResultados(data.dados);
    } catch (err) {
      setErro("Erro ao buscar políticos deste estado.");
    } finally {
      setLoading(false);
    }
  };

  const handleStateClick = (geo: any) => {
    const uf = geo.id || geo.properties.sigla || "SP"; // Ajuste conforme seu JSON
    setEstadoSelecionado(geo.properties.name);
    buscarPorEstado(uf);
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-emerald-500/30">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-neutral-900 via-neutral-950 to-neutral-950 -z-10" />

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
            <div className="flex items-center gap-4">
              <div className="text-right">
                <h2 className="text-lg font-bold text-white">{executivo.vice.nome}</h2>
                <p className="text-neutral-400 text-sm">{executivo.vice.cargo} - {executivo.vice.partido}</p>
              </div>
              <div className="w-12 h-12 rounded-full overflow-hidden border-2 border-neutral-600">
                <img src={executivo.vice.foto} alt="Vice" className="w-full h-full object-cover" />
              </div>
            </div>
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-6 py-12 flex flex-col items-center">

        {/* BARRA DE PESQUISA AVANÇADA */}
        <div className="w-full bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-6 shadow-2xl mb-12">
          <form onSubmit={realizarBusca} className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-3.5 text-neutral-500 w-5 h-5" />
              <input type="text" placeholder="Nome do Político (ex: Lula, Boulos...)" value={buscaNome} onChange={(e) => setBuscaNome(e.target.value)} className="w-full bg-neutral-950/50 border border-neutral-800 rounded-xl pl-12 pr-4 py-3 text-neutral-200 focus:ring-2 focus:ring-emerald-500/50" />
            </div>
            <div className="w-full md:w-1/4 relative">
              <Filter className="absolute left-4 top-3.5 text-neutral-500 w-5 h-5" />
              <select value={cargoFiltro} onChange={(e) => setCargoFiltro(e.target.value)} className="w-full bg-neutral-950/50 border border-neutral-800 rounded-xl pl-12 pr-4 py-3 text-neutral-200 appearance-none focus:ring-2 focus:ring-emerald-500/50">
                <option value="">Todos os Cargos</option>
                <option value="senador">Senador</option>
                <option value="deputado">Deputado Federal</option>
                <option value="governador">Governador</option>
              </select>
            </div>
            <button type="submit" className="bg-emerald-500 hover:bg-emerald-400 text-neutral-950 font-bold px-8 py-3 rounded-xl transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)]">
              Buscar
            </button>
          </form>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 w-full">
          {/* MAPA GIGANTE */}
          <div className="lg:col-span-3 bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-6 relative overflow-hidden h-[600px] flex items-center justify-center">
            <h3 className="absolute top-6 left-6 text-neutral-400 font-bold tracking-widest text-xs uppercase flex items-center gap-2">
              <MapPin className="w-4 h-4" /> Selecione um Estado
            </h3>
            <ComposableMap projection="geoMercator" projectionConfig={{ scale: 750, center: [-54, -15] }} className="w-full h-full object-contain">
              <ZoomableGroup zoom={1}>
                <Geographies geography={geoUrl}>
                  {({ geographies }) =>
                    geographies.map((geo) => (
                      <Geography key={geo.rsmKey} geography={geo} onClick={() => handleStateClick(geo)} style={{
                        default: { fill: "#171717", stroke: "#333", strokeWidth: 0.5 },
                        hover: { fill: "#10b981", stroke: "#10b981", cursor: "pointer", transition: "all 250ms" },
                        pressed: { fill: "#059669" },
                      }} />
                    ))
                  }
                </Geographies>
              </ZoomableGroup>
            </ComposableMap>
          </div>

          {/* RANKING E RESULTADOS */}
          <div className="lg:col-span-2 bg-neutral-900/30 border border-neutral-800 rounded-3xl p-6 overflow-y-auto max-h-[600px] custom-scrollbar">
            {loading && <div className="flex justify-center py-20"><div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div></div>}

            {erro && <div className="p-4 bg-red-500/10 text-red-400 rounded-xl flex gap-2"><AlertCircle className="w-5 h-5" /> {erro}</div>}

            {!loading && !erro && resultados.length === 0 && (
              <div className="text-center text-neutral-500 py-20">
                <User className="w-16 h-16 mx-auto mb-4 opacity-20" />
                <p>Clique num estado no mapa ou pesquise para ver o Ranking de Políticos.</p>
              </div>
            )}

            {!loading && resultados.length > 0 && (
              <div>
                <h3 className="text-lg font-bold text-emerald-400 mb-6 flex items-center gap-2">
                  {estadoSelecionado ? `Top Políticos: ${estadoSelecionado}` : "Resultados da Busca"}
                </h3>
                <div className="space-y-4">
                  {resultados.map((pol, index) => (
                    <div key={pol.id} className="bg-neutral-950 border border-neutral-800 rounded-2xl p-4 flex items-center gap-4 hover:border-emerald-500/50 transition cursor-pointer group">
                      <div className="font-black text-2xl text-neutral-800 group-hover:text-emerald-500/30 w-8">{index + 1}</div>
                      <div className="w-12 h-12 rounded-full overflow-hidden bg-neutral-800 border border-neutral-700">
                        {pol.urlFoto ? <img src={pol.urlFoto} alt={pol.nome} className="w-full h-full object-cover" /> : <User className="w-8 h-8 m-2 text-neutral-600" />}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-bold text-neutral-200 text-sm">{pol.nome}</h4>
                        <p className="text-xs text-neutral-500">{pol.siglaPartido} - {pol.siglaUf}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-emerald-400 font-bold">{pol.score_auditoria || 850}</div>
                        <div className="text-[10px] text-neutral-500 uppercase">Score</div>
                      </div>
                    </div>
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
