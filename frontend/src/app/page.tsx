"use client";

import { useState, useEffect } from "react";
import {
  Search,
  Map as MapIcon,
  Filter,
  Briefcase,
  Play,
  ArrowRight,
  User,
  Hash,
  AlertTriangle,
  ShieldCheck,
  FileText,
  CheckCircle2,
  ShieldAlert,
  Activity,
  Crown,
  Castle,
  Fish,
  MapPin,
} from "lucide-react";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from "react-simple-maps";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";

const geoUrl = "/brazil-states.json";

export default function Home() {
  const router = useRouter();
  const [buscaNome, setBuscaNome] = useState("");
  const [cargoFiltro, setCargoFiltro] = useState("");
  const [estadoSelecionado, setEstadoSelecionado] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [resultados, setResultados] = useState<any[]>([]);
  const [presidenciais, setPresidenciais] = useState<any[]>([]);
  const [cidades, setCidades] = useState<any[]>([]);
  const [cidadeSelecionada, setCidadeSelecionada] = useState<string>("");
  const [municipiosLocal, setMunicipiosLocal] = useState<{ id: number; nome: string }[]>([]);
  const [feedGuerra, setFeedGuerra] = useState<any[]>([]);
  const [topRanking, setTopRanking] = useState<any[]>([]);
  const [erro, setErro] = useState("");
  const [zoomMap, setZoomMap] = useState<number>(1);
  const [centerMap, setCenterMap] = useState<[number, number]>([-55, -15]);

  // TAREFA 5: Mapa do Brasil Interativo (Coordenadas para Zoom Animado)
  const mapCoordinates: Record<string, [number, number]> = {
    "AC": [-70.5, -9.0], "AL": [-36.5, -9.5], "AM": [-64.0, -4.0], "AP": [-51.5, 1.5],
    "BA": [-41.5, -12.5], "CE": [-39.5, -5.0], "DF": [-47.9, -15.8], "ES": [-40.3, -19.5],
    "GO": [-50.0, -16.0], "MA": [-45.0, -5.0], "MG": [-44.0, -18.5], "MS": [-54.5, -20.5],
    "MT": [-56.0, -13.0], "PA": [-52.0, -4.0], "PB": [-36.5, -7.0], "PE": [-37.5, -8.5],
    "PI": [-43.0, -7.5], "PR": [-51.5, -24.5], "RJ": [-42.5, -22.0], "RN": [-36.5, -5.5],
    "RO": [-62.5, -11.0], "RR": [-61.0, 2.0], "RS": [-53.0, -29.5], "SC": [-50.5, -27.0],
    "SE": [-37.5, -10.5], "SP": [-49.0, -22.5], "TO": [-48.5, -10.5]
  };

  useEffect(() => {
    // Carrega dados pro Dashboard e Mock Presidenciais
    Promise.all([
      fetch("http://localhost:8000/api/dashboard/guerra").then((r) => r.json()),
      fetch("http://localhost:8000/api/politicos/presidenciais").then((r) =>
        r.json(),
      ),
    ])
      .then(([dashData, presData]) => {
        if (dashData.status === "sucesso") {
          setFeedGuerra(dashData.feed || []);
          setTopRanking(dashData.top10 || []);
        }
        if (presData.status === "sucesso") {
          setPresidenciais(presData.dados);
        }
      })
      .catch(console.error);
  }, []);

  const realizarBusca = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!buscaNome) return;
    setLoading(true);
    setErro("");
    setResultados([]);
    setEstadoSelecionado("");
    setCargoFiltro("");

    try {
      const res = await fetch(
        `http://localhost:8000/api/politicos/buscar?nome=${buscaNome}`,
      );
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
    setLoading(true);
    setErro("");
    setResultados([]);
    setBuscaNome("");
    setCargoFiltro("");
    try {
      const res = await fetch(
        `http://localhost:8000/api/politicos/estado/${uf}`,
      );
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

  const handleStateClick = async (geo: any) => {
    const siglaEstado = geo.properties.SIGLA_UF || geo.properties.UF_05;
    if (siglaEstado && geoUrl) {
      setEstadoSelecionado(siglaEstado);
      setCidadeSelecionada(""); // Reseta a cidade ao trocar de estado

      // Aplica o Zoom Físico e Centralização
      if (mapCoordinates[siglaEstado]) {
        setCenterMap(mapCoordinates[siglaEstado]);
        setZoomMap(4); // Zoom in
      }

      // TAREFA 5: Busca Cidades do IBGE para o Estado
      try {
        const ibgeRes = await fetch(`https://servicodados.ibge.gov.br/api/v1/localidades/estados/${siglaEstado}/municipios`);
        const ibgeData = await ibgeRes.json();
        setMunicipiosLocal(ibgeData);
      } catch (e) {
        console.error("Erro IBGE Municipios", e);
      }

      setLoading(true);
      setErro("");
      // Traz politicos estaduais (Senadores/Govs/Deps Estaduais) da API
      try {
        const res = await fetch(`http://localhost:8000/api/politicos/estado/${siglaEstado}`);
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
    }
  };

  const mapReset = () => {
    setEstadoSelecionado("");
    setCidadeSelecionada("");
    setCenterMap([-55, -15]);
    setZoomMap(1);
    setResultados([]); // Limpa resultados para forçar o backend total ou manter vazio
  }

  // TAREFA 5: Busca Políticos Locais (Municipais - Preparo API TSE)
  const buscarPoliticosLocais = async (city: string) => {
    setCidadeSelecionada(city);
    if (!city) return;
    setLoading(true);
    setErro("");

    // ATENÇÃO: Rota atual usa o FastAPI Mocado. 
    // FUTURO: Esta rota será platinada no TSE/CGU para prefeitos reais.
    try {
      const res = await fetch(
        `http://localhost:8000/api/politicos/cidade/${encodeURIComponent(city)}`,
      );
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
      setErro("Erro ao buscar políticos TSE/IBGE.");
    } finally {
      setLoading(false);
    }
  };

  const handleCityChange = async (e: any) => {
    const city = e.target.value;
    setCidadeSelecionada(city);
    if (!city) {
      buscarPorEstado(estadoSelecionado); // fallback state
      return;
    }

    setLoading(true);
    setErro("");
    setResultados([]);
    setBuscaNome("");
    setCargoFiltro("");
    try {
      const res = await fetch(
        `http://localhost:8000/api/politicos/cidade/${encodeURIComponent(city)}`,
      );
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
      setErro("Erro ao buscar políticos desta cidade.");
    } finally {
      setLoading(false);
    }
  };

  const resultadosFiltrados = resultados.filter((pol) => {
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
            <Crown className="w-8 h-8 text-yellow-500" /> Corrida Presidencial
            2026
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
                    animate={{
                      boxShadow: [
                        "0 0 15px rgba(234,179,8,0.3)",
                        "0 0 30px rgba(234,179,8,0.6)",
                        "0 0 15px rgba(234,179,8,0.3)",
                      ],
                    }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="w-24 h-24 rounded-full overflow-hidden border-2 border-yellow-500 mb-4 animate-pulse relative"
                  >
                    <img
                      src={pres.urlFoto}
                      alt={pres.nome}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.currentTarget.src = "https://via.placeholder.com/150";
                      }}
                    />
                  </motion.div>
                  <h3 className="text-lg font-bold text-white text-center mb-1 truncate w-full px-2">
                    {pres.nome}
                  </h3>
                  <p className="text-sm text-neutral-400 mb-4">
                    {pres.cargo} - {pres.siglaPartido}
                  </p>

                  <div className="w-full bg-neutral-900 rounded-xl p-3 flex justify-between items-center border border-neutral-800">
                    <span className="text-xs font-mono text-neutral-500 uppercase">
                      Score Dossiê
                    </span>
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className={`text-lg font-black ${pres.score_auditoria >= 700 ? "text-emerald-500" : pres.score_auditoria >= 500 ? "text-yellow-500" : "text-red-500"}`}
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
          <form
            onSubmit={realizarBusca}
            className="flex flex-col md:flex-row gap-4"
          >
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-3.5 text-neutral-500 w-5 h-5" />
              <input
                type="text"
                placeholder="Investigue Deputados, Senadores ou Governadores..."
                value={buscaNome}
                onChange={(e) => setBuscaNome(e.target.value)}
                className="w-full bg-neutral-950/50 border border-neutral-800 rounded-xl pl-12 pr-4 py-3 text-neutral-200 focus:ring-2 focus:ring-purple-500/50 outline-none transition"
              />
            </div>
            <button
              type="submit"
              className="bg-purple-600 hover:bg-purple-500 text-white font-bold px-8 py-3 rounded-xl transition-all shadow-[0_0_15px_rgba(147,51,234,0.3)]"
            >
              Auditar
            </button>
          </form>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 w-full">
          {/* MAPA INTERATIVO - TAREFA 5 */}
          <div className="lg:col-span-3 relative w-full h-[500px] bg-neutral-900 border border-neutral-800 rounded-3xl overflow-hidden shadow-2xl flex-1 group">
            <div className="absolute inset-x-0 top-0 h-2 bg-gradient-to-r from-emerald-500/20 via-purple-500/20 to-emerald-500/20 opacity-0 group-hover:opacity-100 transition-opacity z-10" />

            {/* INTERAÇÃO IBGE */}
            {estadoSelecionado && (
              <div className="absolute top-4 left-4 z-20 flex flex-col gap-2 w-72">
                <span className="bg-neutral-950/80 backdrop-blur border border-purple-500/50 text-purple-400 font-bold px-4 py-2 rounded-xl flex items-center gap-2 shadow-lg shadow-purple-500/10 w-fit">
                  <MapIcon className="w-5 h-5" /> Estado: {estadoSelecionado}
                </span>

                <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="w-full bg-neutral-950/90 backdrop-blur border border-neutral-700 rounded-xl max-h-48 overflow-y-auto custom-scrollbar p-1 shadow-2xl">
                  <div className="p-2 text-[10px] uppercase font-bold text-neutral-500 border-b border-neutral-800 mb-1 flex items-center justify-between">
                    <span>Drilldown Municipal (TSE)</span>
                    <span onClick={mapReset} className="cursor-pointer text-red-500 hover:text-red-400">Limpar UF</span>
                  </div>
                  {municipiosLocal.map(mun => (
                    <div
                      key={mun.id}
                      onClick={() => buscarPoliticosLocais(mun.nome)}
                      className={`px-3 py-2 text-sm rounded-lg cursor-pointer transition-colors ${cidadeSelecionada === mun.nome ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'text-neutral-300 hover:bg-neutral-800'}`}
                    >
                      {mun.nome}
                    </div>
                  ))}
                </motion.div>
              </div>
            )}

            {!geoUrl ? (
              <div className="flex w-full h-full items-center justify-center text-neutral-500 font-mono text-sm bg-neutral-950/50 backdrop-blur animate-pulse">
                Sincronizando Cartografia Nacional...
              </div>
            ) : (
              <ComposableMap
                projection="geoMercator"
                projectionConfig={{ scale: 800 }}
                className="w-full h-full"
              >
                <ZoomableGroup center={centerMap} zoom={zoomMap} minZoom={1} maxZoom={5}>
                  <Geographies geography={geoUrl}>
                    {({ geographies }) =>
                      geographies.map((geo) => {
                        const sigla = geo.properties.SIGLA_UF || geo.properties.UF_05;
                        const isSelected = estadoSelecionado === sigla;
                        return (
                          <Geography
                            key={geo.rsmKey}
                            geography={geo}
                            onClick={() => handleStateClick(geo)}
                            style={{
                              default: {
                                fill: isSelected ? "#a855f7" : "#171717",
                                stroke: isSelected ? "#d8b4fe" : "#262626",
                                strokeWidth: isSelected ? 1.5 : 0.5,
                                outline: "none",
                                transition: "all 0.3s ease",
                              },
                              hover: {
                                fill: "#9333ea",
                                stroke: "#d8b4fe",
                                strokeWidth: 2,
                                outline: "none",
                                cursor: "pointer",
                                transition: "all 0.2s ease",
                              },
                              pressed: {
                                fill: "#7e22ce",
                                outline: "none",
                              },
                            }}
                          />
                        );
                      })
                    }
                  </Geographies>
                </ZoomableGroup>
              </ComposableMap>
            )}
          </div>
          {/* --- MODO DASHBOARD DE GUERRA (Se não tiver busca ativa, exibe o Painel Nacional) --- */}
          {!buscaNome && !estadoSelecionado && !cargoFiltro && (
            <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* FEED DA CORRUPÇÃO */}
              <div className="bg-neutral-900/40 border border-neutral-800 rounded-2xl p-6 flex flex-col h-[500px]">
                <h3 className="text-emerald-400 font-bold mb-4 flex items-center gap-2 border-b border-neutral-800 pb-3">
                  <Activity className="w-5 h-5" />
                  Radar Nacional (Tempo Real)
                </h3>
                <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
                  {feedGuerra.length > 0 ? (
                    feedGuerra.map((item, idx) => (
                      <div
                        key={idx}
                        className="border-l-2 border-emerald-500 pl-4 py-1"
                      >
                        <div className="flex justify-between items-start mb-1">
                          <span className="font-bold text-neutral-200 text-sm">
                            {item.nome}
                          </span>
                          <span className="text-[10px] text-neutral-500 bg-neutral-800/50 px-2 py-0.5 rounded">
                            {item.data}
                          </span>
                        </div>
                        <p className="text-red-400 text-xs font-bold mb-1">
                          {item.motivo}
                        </p>
                        <p
                          className="text-neutral-400 text-xs line-clamp-2"
                          title={item.desc}
                        >
                          {item.desc}
                        </p>
                      </div>
                    ))
                  ) : (
                    <div className="text-neutral-500 text-sm text-center py-10 font-mono">
                      Radar silenciado. Nenhuma anomalia crítica nas últimas
                      24h.
                    </div>
                  )}
                </div>
              </div>

              {/* RANKING TOP ANOMALIAS */}
              <div className="bg-neutral-900/40 border border-neutral-800 rounded-2xl p-6 flex flex-col h-[500px]">
                <h3 className="text-red-400 font-bold mb-4 flex items-center gap-2 border-b border-neutral-800 pb-3">
                  <ShieldAlert className="w-5 h-5" />
                  Malha Fina (Maiores Riscos)
                </h3>
                <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
                  {topRanking.length > 0 ? (
                    topRanking.map((item, idx) => (
                      <div
                        key={idx}
                        className="bg-neutral-950/50 border border-red-900/30 rounded-lg p-3 flex justify-between items-center cursor-pointer hover:border-red-500/50 transition-colors"
                        onClick={() => router.push(`/politico/${item.id}`)}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-red-950 flex items-center justify-center font-bold text-red-500 text-xs shadow-[0_0_10px_rgba(220,38,38,0.2)]">
                            #{idx + 1}
                          </div>
                          <span className="font-bold text-neutral-200 text-sm">
                            Alvo {item.id}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-xs text-neutral-500 uppercase block mb-0.5">
                            Pontos Perdidos
                          </span>
                          <span className="font-mono text-red-400 font-bold text-sm">
                            -{item.pontos_perdidos}
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-neutral-500 text-sm text-center py-10 font-mono">
                      Nenhum alvo processado com red flags graves.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* --- RESULTADOS GLOBAIS / ESTADUAIS DA PESQUISA --- */}
          {(buscaNome || estadoSelecionado || cargoFiltro) && (
            <div className="lg:col-span-2 bg-neutral-900/30 border border-neutral-800 rounded-3xl p-6 flex flex-col max-h-[600px]">
              <div className="flex justify-between items-start md:items-end mb-6 flex-wrap gap-4">
                <div className="flex flex-col gap-2">
                  <h3 className="text-lg font-bold text-purple-400 flex items-center gap-2">
                    {estadoSelecionado
                      ? `Alvos: ${estadoSelecionado}`
                      : "Resultados Globais"}
                  </h3>
                  {cidades.length > 0 && (
                    <select
                      value={cidadeSelecionada}
                      onChange={handleCityChange}
                      className="bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-1.5 text-sm text-neutral-200 outline-none focus:ring-1 focus:ring-emerald-500/50 max-w-[220px]"
                    >
                      <option value="">-- Filtrar Município --</option>
                      {cidades.map((c) => (
                        <option key={c.id} value={c.nome}>
                          {c.nome}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <div className="relative w-40">
                  <Filter className="absolute left-3 top-2.5 text-neutral-500 w-4 h-4" />
                  <select
                    value={cargoFiltro}
                    onChange={(e) => setCargoFiltro(e.target.value)}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-lg pl-9 pr-3 py-2 text-sm text-neutral-200 outline-none focus:ring-1 focus:ring-purple-500/50"
                  >
                    <option value="">Todos</option>
                    <option value="governador">Governadores</option>
                    <option value="prefeito">Prefeitos</option>
                    <option value="senador">Senadores</option>
                    <option value="deputado">Deputados</option>
                    <option value="vereador">Vereadores</option>
                  </select>
                </div>
              </div>

              {loading && (
                <div className="flex justify-center py-20">
                  <div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
              )}
              {erro && (
                <div className="p-4 bg-red-500/10 text-red-400 border border-red-500/20 rounded-xl text-sm">
                  {erro}
                </div>
              )}

              {!loading && !erro && resultados.length === 0 && (
                <div className="flex-1 flex flex-col items-center justify-center text-neutral-600 text-sm py-10">
                  <MapPin className="w-8 h-8 mb-2 opacity-50" />
                  Clique num estado ou faça uma busca.
                </div>
              )}

              <div className="overflow-y-auto custom-scrollbar flex-1 space-y-3 pr-2">
                {resultadosFiltrados.map((pol, index) => {
                  const isRei = pol.nivel_boss === "🏰 Rei Estadual";
                  return (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      key={pol.id}
                      onClick={() => router.push(`/politico/${pol.id}`)}
                      className={`bg-neutral-950 border ${isRei ? "border-purple-500/30 shadow-[0_0_10px_rgba(168,85,247,0.1)]" : "border-neutral-800"} rounded-2xl p-4 flex items-center gap-4 hover:border-purple-500/50 transition cursor-pointer group`}
                    >
                      <div className="font-black text-xl text-neutral-800 group-hover:text-purple-500/30 w-6">
                        {index + 1}
                      </div>

                      <div
                        className={`relative w-12 h-12 rounded-full overflow-hidden bg-neutral-800 flex-shrink-0 ${isRei ? "border-2 border-purple-500" : "border border-neutral-700"}`}
                      >
                        {pol.urlFoto ? (
                          <img
                            src={pol.urlFoto}
                            alt={pol.nome}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <User className="w-8 h-8 m-2 text-neutral-600" />
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <h4 className="font-bold text-neutral-200 text-sm truncate flex items-center gap-1">
                          {pol.nome}
                        </h4>
                        <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2 mt-0.5">
                          <span className="text-[10px] text-neutral-500 truncate">
                            {pol.cargo} - {pol.siglaPartido}
                          </span>
                          <span
                            className={`text-[9px] px-1.5 py-[1px] rounded uppercase font-bold w-fit ${isRei ? "bg-purple-500/20 text-purple-400 border border-purple-500/30" : "bg-neutral-800 text-neutral-400"}`}
                          >
                            {isRei ? (
                              <Castle className="w-2.5 h-2.5 inline mr-1" />
                            ) : (
                              <Fish className="w-2.5 h-2.5 inline mr-1" />
                            )}
                            {pol.nivel_boss.replace(/[🏰🐟]/g, "").trim()}
                          </span>
                        </div>
                      </div>

                      <div className="text-right flex-shrink-0">
                        <div
                          className={`font-black text-lg ${pol.score_auditoria >= 700 ? "text-emerald-500" : pol.score_auditoria >= 400 ? "text-yellow-500" : "text-red-500"}`}
                        >
                          {pol.score_auditoria}
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
