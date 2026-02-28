"use client";

import { useState, useEffect } from "react";
import { Search, User, Filter, Crown, Castle, Fish, MapPin } from "lucide-react";
import { ComposableMap, Geographies, Geography, ZoomableGroup } from "react-simple-maps";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";

const geoUrl = "/brazil-states.json";

export default function Home() {
  const router = useRouter();
  const [buscaNome, setBuscaNome] = useState("");
  const [cargoFiltro, setCargoFiltro] = useState("");
  const [estadoSelecionado, setEstadoSelecionado] = useState("");
  const [loading, setLoading] = useState(false);
  const [resultados, setResultados] = useState<any[]>([]);
  const [presidenciais, setPresidenciais] = useState<any[]>([]);
  const [erro, setErro] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/api/eleicoes2026/presidenciais")
      .then(res => res.json())
      .then(data => {
        if (data.status === "sucesso") {
          setPresidenciais(data.dados);
        }
      })
      .catch(() => console.log("Erro ao carregar presidenciais"));
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
        const sorted = data.dados.sort((a: any, b: any) => {
          let va = a.score_auditoria === "Pendente" ? 1000 : a.score_auditoria;
          let vb = b.score_auditoria === "Pendente" ? 1000 : b.score_auditoria;
          return vb - va;
        });
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

  const resultadosFiltrados = resultados.filter(pol => {
    if (!cargoFiltro) return true;
    return pol.cargo.toLowerCase().includes(cargoFiltro.toLowerCase());
  });

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-emerald-500/30">

      {/* DESTAQUE PRESIDENCIAL 2026 */}
      <div className="w-full bg-neutral-900/50 border-b border-neutral-800 pt-8 pb-12 overflow-hidden relative">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-yellow-500/5 via-neutral-950 to-neutral-950 pointer-events-none" />
        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <h2 className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-yellow-600 mb-8 flex items-center gap-3 justify-center md:justify-start">
            <Crown className="w-8 h-8 text-yellow-500" /> Corrida Presidencial 2026
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {presidenciais.map((pres) => (
              <motion.div
                whileHover={{ scale: 1.02, y: -5 }}
                key={pres.id}
                onClick={() => router.push(`/politico/${pres.id}`)}
                className="bg-neutral-950 border-2 border-yellow-500/20 rounded-3xl p-6 cursor-pointer relative overflow-hidden group shadow-[0_0_15px_rgba(234,179,8,0.05)] hover:shadow-[0_0_30px_rgba(234,179,8,0.2)] hover:border-yellow-500/50 transition-all"
              >
                <div className="absolute top-0 right-0 p-3">
                  <span className="text-xs font-bold text-yellow-500 bg-yellow-500/10 px-2 py-1 rounded-md border border-yellow-500/20 flex items-center gap-1">
                    <Crown className="w-3 h-3" /> Chefão
                  </span>
                </div>

                <div className="flex flex-col items-center">
                  <motion.div
                    animate={{ boxShadow: ['0 0 15px rgba(234,179,8,0.3)', '0 0 30px rgba(234,179,8,0.6)', '0 0 15px rgba(234,179,8,0.3)'] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="w-24 h-24 rounded-full overflow-hidden border-2 border-yellow-500 mb-4 animate-pulse relative"
                  >
                    <img src={pres.urlFoto} alt={pres.nome} className="w-full h-full object-cover" onError={(e) => { e.currentTarget.src = "https://via.placeholder.com/150"; }} />
                  </motion.div>
                  <h3 className="text-lg font-bold text-white text-center mb-1 truncate w-full px-2">{pres.nome}</h3>
                  <p className="text-sm text-neutral-400 mb-4">{pres.cargo} - {pres.siglaPartido}</p>

                  <div className="w-full bg-neutral-900 rounded-xl p-3 flex justify-between items-center border border-neutral-800">
                    <span className="text-xs font-mono text-neutral-500 uppercase">Score Dossiê</span>
                    <motion.span
                      initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                      className={`text-lg font-black ${pres.score_auditoria >= 700 ? 'text-emerald-500' : pres.score_auditoria >= 500 ? 'text-yellow-500' : 'text-red-500'}`}
                    >
                      {pres.score_auditoria}
                    </motion.span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-6 py-12 flex flex-col items-center relative">

        {/* BARRA DE PESQUISA PRINCIPAL */}
        <div className="w-full bg-neutral-900/50 backdrop-blur-xl border border-neutral-800 rounded-3xl p-6 shadow-2xl mb-12 relative z-20">
          <form onSubmit={realizarBusca} className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-3.5 text-neutral-500 w-5 h-5" />
              <input type="text" placeholder="Investigue Deputados, Senadores ou Governadores..." value={buscaNome} onChange={(e) => setBuscaNome(e.target.value)} className="w-full bg-neutral-950/50 border border-neutral-800 rounded-xl pl-12 pr-4 py-3 text-neutral-200 focus:ring-2 focus:ring-purple-500/50 outline-none transition" />
            </div>
            <button type="submit" className="bg-purple-600 hover:bg-purple-500 text-white font-bold px-8 py-3 rounded-xl transition-all shadow-[0_0_15px_rgba(147,51,234,0.3)]">
              Auditar
            </button>
          </form>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 w-full">
          {/* MAPA ESTADUAL */}
          <div className="lg:col-span-3 bg-neutral-900/30 border border-neutral-800 rounded-3xl p-6 relative h-[600px] flex items-center justify-center">
            <div className="absolute top-6 left-6 z-10">
              <h3 className="text-lg font-bold text-neutral-400 mb-1">Exploração Local</h3>
              <p className="text-xs text-neutral-600">Selecione um estado para listar políticos vinculados</p>
            </div>
            <ComposableMap projection="geoMercator" projectionConfig={{ scale: 750, center: [-54, -15] }} className="w-full h-full">
              <ZoomableGroup zoom={1}>
                <Geographies geography={geoUrl}>
                  {({ geographies }) =>
                    geographies.map((geo) => {
                      const isSelected = estadoSelecionado === geo.properties.name;
                      return (
                        <Geography key={geo.rsmKey} geography={geo} onClick={() => handleStateClick(geo)} style={{
                          default: { fill: isSelected ? "#10b981" : "#171717", stroke: "#333", strokeWidth: 0.5, outline: "none" },
                          hover: { fill: "#10b981", stroke: "#059669", cursor: "pointer", transition: "all 250ms", outline: "none" },
                          pressed: { outline: "none", fill: "#059669" }
                        }} />
                      );
                    })
                  }
                </Geographies>
              </ZoomableGroup>
            </ComposableMap>
          </div>

          {/* COLUNA DIREITA: RANKING ESTADUAL E FILTRO */}
          <div className="lg:col-span-2 bg-neutral-900/30 border border-neutral-800 rounded-3xl p-6 flex flex-col max-h-[600px]">

            <div className="flex justify-between items-end mb-6">
              <h3 className="text-lg font-bold text-purple-400 flex items-center gap-2">
                {estadoSelecionado ? `Alvos: ${estadoSelecionado}` : "Resultados Globais"}
              </h3>

              <div className="relative w-40">
                <Filter className="absolute left-3 top-2.5 text-neutral-500 w-4 h-4" />
                <select value={cargoFiltro} onChange={(e) => setCargoFiltro(e.target.value)} className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-9 pr-3 py-2 text-sm text-neutral-200 outline-none focus:ring-1 focus:ring-purple-500/50">
                  <option value="">Todos</option>
                  <option value="governador">Governadores</option>
                  <option value="senador">Senadores</option>
                  <option value="deputado">Deputados</option>
                </select>
              </div>
            </div>

            {loading && <div className="flex justify-center py-20"><div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div></div>}
            {erro && <div className="p-4 bg-red-500/10 text-red-400 border border-red-500/20 rounded-xl text-sm">{erro}</div>}

            {!loading && !erro && resultados.length === 0 && (
              <div className="flex-1 flex flex-col items-center justify-center text-neutral-600 text-sm">
                <MapPin className="w-8 h-8 mb-2 opacity-50" />
                Clique num estado ou faça uma busca.
              </div>
            )}

            <div className="overflow-y-auto custom-scrollbar flex-1 space-y-3 pr-2">
              {resultadosFiltrados.map((pol, index) => {
                const isRei = pol.nivel_boss === "🏰 Rei Estadual";
                return (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}
                    key={pol.id}
                    onClick={() => router.push(`/politico/${pol.id}`)}
                    className={`bg-neutral-950 border ${isRei ? 'border-purple-500/30 shadow-[0_0_10px_rgba(168,85,247,0.1)]' : 'border-neutral-800'} rounded-2xl p-4 flex items-center gap-4 hover:border-purple-500/50 transition cursor-pointer group`}
                  >
                    <div className="font-black text-xl text-neutral-800 group-hover:text-purple-500/30 w-6">{index + 1}</div>

                    <div className={`relative w-12 h-12 rounded-full overflow-hidden bg-neutral-800 flex-shrink-0 ${isRei ? 'border-2 border-purple-500' : 'border border-neutral-700'}`}>
                      {pol.urlFoto ? <img src={pol.urlFoto} alt={pol.nome} className="w-full h-full object-cover" /> : <User className="w-8 h-8 m-2 text-neutral-600" />}
                    </div>

                    <div className="flex-1 min-w-0">
                      <h4 className="font-bold text-neutral-200 text-sm truncate flex items-center gap-1">
                        {pol.nome}
                      </h4>
                      <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2 mt-0.5">
                        <span className="text-[10px] text-neutral-500 truncate">{pol.cargo} - {pol.siglaPartido}</span>
                        <span className={`text-[9px] px-1.5 py-[1px] rounded uppercase font-bold w-fit ${isRei ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' : 'bg-neutral-800 text-neutral-400'}`}>
                          {isRei ? <Castle className="w-2.5 h-2.5 inline mr-1" /> : <Fish className="w-2.5 h-2.5 inline mr-1" />}
                          {pol.nivel_boss.replace(/[🏰🐟]/g, '').trim()}
                        </span>
                      </div>
                    </div>

                    <div className="text-right flex-shrink-0">
                      <div className={`font-black text-lg ${pol.score_auditoria >= 700 ? 'text-emerald-500' : pol.score_auditoria >= 400 ? 'text-yellow-500' : 'text-red-500'}`}>
                        {pol.score_auditoria}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
