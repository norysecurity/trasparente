"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Map, { Marker, ViewState, MapRef } from "react-map-gl/mapbox";
import 'mapbox-gl/dist/mapbox-gl.css';
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, ShieldAlert, Activity, User, ShieldCheck, MapPin, Target, ChevronRight, Navigation
} from "lucide-react";

// OBSERVAÇÃO AO ARQUITETO/DEV:
// O GitHub bloqueou o Push anterior devido à detecção de secret (Secret Scanning).
// A chave pública: pk.eyJ1Ijoid2VsbGluZ3Rvbm1tIiwiYSI6ImNtbTNweHR3bz...
// DEVE ser declarada no seu arquivo .env.local como:
// NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ1Ij...
const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "COLE_SUA_CHAVE_PK_AQUI_SE_FOR_RODAR_LOCAL_SEM_ENV";

// Cidades Estratégicas Base
const CIDADES_RADAR_FIXAS = [
  { nome: "Brasília", lat: -15.8267, lng: -47.9218, tipo: "Centro de Poder Supremo" }
];

// Gerador Procedural Simples de Cidades "Vizinhas" baseadas em uma coordenada Real
const gerarCidadesProximas = (uLat: number, uLng: number) => {
  // Gera 4 bolinhas espalhadas em um raio de ~30 a 100km
  const offsets = [
    { dLat: 0.15, dLng: 0.2, tipo: "Foco Regional" },
    { dLat: -0.2, dLng: -0.1, tipo: "Malha Fina" },
    { dLat: 0.3, dLng: -0.25, tipo: "Investigação" },
    { dLat: -0.1, dLng: 0.35, tipo: "Suspeita Ativa" }
  ];

  return offsets.map((off, idx) => ({
    nome: `Alvo Prox #${idx + 1}`, // Nome genérico até o usuário clicar
    lat: uLat + off.dLat,
    lng: uLng + off.dLng,
    tipo: off.tipo
  }));
};

export default function Home() {
  const router = useRouter();
  const mapRef = useRef<MapRef>(null);

  // Estados do Mapa
  const [viewState, setViewState] = useState<ViewState>({
    longitude: -51.9253,
    latitude: -14.235,
    zoom: 3.5,
    pitch: 0,
    bearing: 0,
    padding: { top: 0, bottom: 0, left: 0, right: 0 }
  });

  // Estado para Localização do Usuário Real e Bolinhas Dinâmicas
  const [userLocation, setUserLocation] = useState<{ lat: number, lng: number } | null>(null);
  const [cidadesDinamicas, setCidadesDinamicas] = useState<any[]>([]);

  // Estados da Interface e Dados
  const [loading, setLoading] = useState(false);
  const [buscaNome, setBuscaNome] = useState("");
  const [cidadeSelecionada, setCidadeSelecionada] = useState("");
  const [politicosLocais, setPoliticosLocais] = useState<any[]>([]);

  // Estados do Dashboard Lateral (Esquerdo)
  const [feedGuerra, setFeedGuerra] = useState<any[]>([]);
  const [topRanking, setTopRanking] = useState<any[]>([]);

  // Init: Carrega Dashboard Esquerdo (Guerra & Top Risco) e Localização Real
  useEffect(() => {
    fetch("http://localhost:8000/api/dashboard/guerra")
      .then(res => res.json())
      .then(data => {
        if (data.status === "sucesso") {
          setFeedGuerra(data.alertas_recentes || []);
          setTopRanking(data.top_risco || []);
        }
      })
      .catch(err => console.error("Erro ao carregar Dashboard:", err));

    // Capturar localização do usuário
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const uLat = position.coords.latitude;
          const uLng = position.coords.longitude;
          setUserLocation({ lat: uLat, lng: uLng });
          setCidadesDinamicas(gerarCidadesProximas(uLat, uLng));

          // Opcional: Animar a câmera para a localização do usuário ao entrar
          if (mapRef.current) {
            mapRef.current.flyTo({
              center: [uLng, uLat],
              zoom: 11,
              pitch: 45,
              duration: 3000
            });
          }
        },
        (error) => {
          console.warn("Geolocalização negada ou falhou:", error);
          // Fallback: Mostrar só Brasilia se a pessoa negar GPS. Não precisa fazer nada extra, cidadesDinamicas = []
        }
      );
    }
  }, []);

  // Ação de Clique Dinâmico no Mapa (Qualquer Cidade do Brasil)
  const handleMapClick = async (evt: any) => {
    if (evt.defaultPrevented) return;

    const { lng, lat } = evt.lngLat;
    setLoading(true);
    setCidadeSelecionada("Buscando alvo...");

    try {
      const res = await fetch(`https://api.mapbox.com/geocoding/v5/mapbox.places/${lng},${lat}.json?types=place,region&country=br&access_token=${MAPBOX_TOKEN}`);
      const data = await res.json();

      if (data.features && data.features.length > 0) {
        const place = data.features[0];
        const nomeCidade = place.text;
        const [centerLng, centerLat] = place.center;

        voarParaCidade(centerLat, centerLng, nomeCidade);
      } else {
        setCidadeSelecionada("Alvo Indeterminado");
        setPoliticosLocais([]);
        setLoading(false);
      }
    } catch (err) {
      console.error("Erro ao resolver alvo no mapa:", err);
      setCidadeSelecionada("Sinal Perdido");
      setLoading(false);
    }
  };

  // Ação Principal: Voar para a Cidade e Abrir Painel Direito
  const voarParaCidade = async (lat: number, lng: number, nomeCidade: string) => {
    if (mapRef.current) {
      // Efeito cinematográfico: zoom in profundo com inclinação (pitch)
      mapRef.current.flyTo({
        center: [lng, lat],
        zoom: 13,
        pitch: 65,
        bearing: 20,
        duration: 2500,
        essential: true
      });
    }

    setCidadeSelecionada(nomeCidade);
    setLoading(true);

    try {
      const res = await fetch(`http://localhost:8000/api/politicos/cidade/${encodeURIComponent(nomeCidade)}`);
      const data = await res.json();
      if (data.status === "sucesso") {
        // Ordena por Score, piores primeiro (score menor é pior? ou maior é pior? Vamos assumir que Score menor é pior Serasa style, então ordem decrescente de perigo ou crescente de score. Vamos ordenar decrescente pelo score simulado)
        const sorted = (data.politicos || []).sort((a: any, b: any) => b.score_auditoria - a.score_auditoria);
        setPoliticosLocais(sorted);
      } else {
        setPoliticosLocais([]);
      }
    } catch (err) {
      console.error("Erro ao puxar dados da cidade:", err);
      setPoliticosLocais([]);
    } finally {
      setLoading(false);
    }
  };

  // Ação de Busca Rápida (Topo)
  const realizarBusca = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!buscaNome) return;
    router.push(`/busca?q=${encodeURIComponent(buscaNome)}`); // Rota simplificada para exemplo ou adaptação futura
  };

  return (
    <div className="relative w-full h-screen bg-black overflow-hidden selection:bg-purple-500/30 font-sans text-neutral-200">

      {/* BACKGROUND: MAPBOX 3D */}
      <div className="absolute inset-0 z-0">
        <Map
          ref={mapRef}
          {...viewState}
          onMove={evt => setViewState(evt.viewState)}
          onClick={handleMapClick}
          mapStyle="mapbox://styles/mapbox/dark-v11"
          mapboxAccessToken={MAPBOX_TOKEN}
          terrain={{ source: 'mapbox-dem', exaggeration: 1.5 }}
          minZoom={3}
          cursor="pointer"
        >
          {/* Marcador da Localização do Usuário */}
          {userLocation && (
            <Marker longitude={userLocation.lng} latitude={userLocation.lat} anchor="bottom">
              <div className="relative flex flex-col items-center justify-center group">
                {/* Tooltip Flutuante */}
                <div className="absolute bottom-full mb-1 bg-neutral-900/90 backdrop-blur-md border border-red-500/50 px-3 py-1.5 rounded-lg whitespace-nowrap z-20 shadow-xl opacity-100 transition-opacity">
                  <p className="text-xs font-bold text-white tracking-wider flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-red-500" /> SUA LOCALIZAÇÃO
                  </p>
                  <p className="text-[9px] text-red-400 font-mono tracking-widest uppercase">Cidades Próximas</p>
                </div>
                {/* Pino Vermelho (Prego) */}
                <div className="w-4 h-4 bg-red-600 rounded-full border-2 border-white shadow-[0_0_15px_rgba(220,38,38,0.8)] z-10 relative flex items-center justify-center">
                  <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></div>
                </div>
                <div className="w-0.5 h-6 bg-gradient-to-b from-red-600 to-transparent -mt-1"></div>
                {/* Sombra base */}
                <div className="w-4 h-1 bg-black/50 blur-[2px] rounded-full absolute -bottom-1"></div>
              </div>
            </Marker>
          )}

          {/* Marcadores Luminosos (Radar Nodes Fixos & Dinâmicos) */}
          {[...CIDADES_RADAR_FIXAS, ...cidadesDinamicas].map((cidade, idx) => (
            <Marker key={idx} longitude={cidade.lng} latitude={cidade.lat} anchor="center">
              <div
                className="relative flex flex-col items-center justify-center group cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  // Para cidades estáticas do radar, nós forçamos o nome. Pra clicks livres passamos o nome da Reverse API.
                  // Aqui no radar, se for "Alvo Prox", fazemos um fetch rápido de geocoding pra descobrir o nome verdadeiro
                  if (cidade.nome.startsWith("Alvo Prox")) {
                    // Passa pra ação de click global que ela resolve o reverse geo e abre o menu
                    handleMapClick({ defaultPrevented: false, lngLat: { lng: cidade.lng, lat: cidade.lat } });
                  } else {
                    voarParaCidade(cidade.lat, cidade.lng, cidade.nome);
                  }
                }}
              >

                {/* Etiqueta 3D Flutuante Permanente Acima da Bolinha Roxa */}
                {(cidade.nome && !cidade.nome.startsWith("Alvo Prox")) && (
                  <div className="absolute bottom-6 font-black text-xl tracking-tight text-white uppercase drop-shadow-[0_4px_4px_rgba(0,0,0,1)] pointer-events-none whitespace-nowrap opacity-60 group-hover:opacity-100 transition-opacity">
                    {cidade.nome}
                  </div>
                )}

                {/* Nome de Cidades Clicadas Livres (Nome Dinâmico da API que jogamos no Tooltip) */}
                {cidadeSelecionada && cidade.nome.startsWith("Alvo Prox") && cidadeSelecionada !== "Buscando alvo..." && cidadeSelecionada !== "Alvo Indeterminado" && (
                  // Esse bloco serve mais se a lista mapeasse itens livre; como "cidade.nome" dos nós visuais não repassa cidadeSelecionada local, o relevo baseia-se na const ativa local abaixo
                  null
                )}

                <div className="relative flex items-center justify-center p-2">
                  {/* Bolinha Roxa Fixa */}
                  <div className="absolute inset-0 bg-purple-500 rounded-full animate-ping opacity-75"></div>
                  <div className="relative w-4 h-4 bg-purple-600 border-2 border-white rounded-full shadow-[0_0_15px_rgba(168,85,247,0.8)] z-10"></div>
                </div>

                {/* Tooltip Hover Redondezas */}
                <div className="absolute -bottom-8 hidden group-hover:flex bg-black/80 backdrop-blur-md border border-purple-500/40 px-2 py-1 rounded-lg whitespace-nowrap z-20 shadow-xl pointer-events-none">
                  <p className="text-[9px] text-purple-400 font-mono tracking-widest">{cidade.tipo}</p>
                </div>
              </div>
            </Marker>
          ))}

          {/* Rótulo 3D Dinâmico para Cidades Selecionadas via Clique Livre */}
          {cidadeSelecionada && cidadeSelecionada !== "Buscando alvo..." && cidadeSelecionada !== "Alvo Indeterminado" && mapRef.current && (
            // Vamos reaproveitar a posição central do mapa para mostrar o título 3D grandão
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[15vh] pointer-events-none z-0">
              <h2 className="text-6xl md:text-8xl font-black text-white/5 uppercase blur-[1px] tracking-tighter" style={{ WebkitTextStroke: '2px rgba(255,255,255,0.2)' }}>
                {cidadeSelecionada}
              </h2>
            </div>
          )}
        </Map>
      </div>

      {/* OVERLAYS UI (z-10) */}
      <div className="absolute inset-0 z-10 pointer-events-none flex flex-col justify-between">

        {/* TOPO: BARRA DE BUSCA E BRANDING */}
        <div className="w-full p-6 flex justify-between items-start pointer-events-auto">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
                <Target className="w-5 h-5 text-emerald-500" />
              </div>
              <h1 className="text-2xl font-black tracking-tight text-white uppercase">
                Trasparente<span className="text-emerald-500">.</span>
              </h1>
            </div>
            <span className="text-[10px] text-neutral-400 font-mono tracking-widest uppercase ml-10">GovTech Sistema de Auditoria</span>
          </div>

          <form onSubmit={realizarBusca} className="flex relative w-full max-w-md">
            <input
              type="text"
              placeholder="Buscar político ou CPF/CNPJ..."
              className="w-full bg-black/60 backdrop-blur-md border border-neutral-800 text-white px-5 py-3 rounded-full text-sm outline-none focus:border-purple-500 transition-colors shadow-2xl placeholder-neutral-600"
              value={buscaNome}
              onChange={(e) => setBuscaNome(e.target.value)}
            />
            <button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 bg-purple-600 hover:bg-purple-500 w-8 h-8 rounded-full flex items-center justify-center transition-colors shadow-[0_0_10px_rgba(168,85,247,0.4)]">
              <Search className="w-4 h-4 text-white" />
            </button>
          </form>
        </div>

        {/* ÁREA CENTRAL LATERAL (Painéis) */}
        <div className="flex-1 flex justify-between items-end p-6 gap-6 relative overflow-hidden pointer-events-none">

          {/* PAINEL ESQUERDO: Radar Criminal & Top 10 (Fixo) */}
          <div className="w-full max-w-sm flex flex-col gap-4 pointer-events-auto max-h-[calc(100vh-120px)] overflow-y-auto custom-scrollbar">
            {/* Radar Criminal (Guerra) */}
            <div className="bg-black/80 backdrop-blur-lg border border-red-500/20 rounded-2xl p-5 shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-red-500/10 blur-[40px] rounded-full pointer-events-none" />
              <h2 className="text-red-400 font-bold mb-4 flex items-center gap-2 border-b border-red-500/20 pb-3 uppercase tracking-wider text-xs">
                <ShieldAlert className="w-4 h-4" /> Radar Criminal / Monitoramento
              </h2>
              <div className="space-y-4">
                {feedGuerra.map((alerta, idx) => (
                  <div key={idx} className="flex gap-3">
                    <div className="mt-1 flex-shrink-0">
                      <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    </div>
                    <div>
                      <p className="text-xs text-neutral-300 leading-tight mb-1">{alerta.mensagem}</p>
                      <div className="flex gap-2 text-[9px] font-mono tracking-widest text-neutral-500 uppercase">
                        <span className={alerta.urgencia === 'ALTA' ? 'text-red-500' : 'text-yellow-500'}>[{alerta.urgencia}]</span>
                        <span>{alerta.tempo}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top 5 Risco (Malha Fina) */}
            <div className="bg-black/80 backdrop-blur-lg border border-purple-500/20 rounded-2xl p-5 shadow-2xl relative overflow-hidden">
              <h2 className="text-purple-400 font-bold mb-4 flex items-center gap-2 border-b border-purple-500/20 pb-3 uppercase tracking-wider text-xs">
                <Activity className="w-4 h-4" /> Alvos Críticos na Malha Fina
              </h2>
              <div className="space-y-3">
                {topRanking.map((alvo, idx) => (
                  <div key={idx} className="flex justify-between items-center bg-white/5 px-3 py-2 rounded-lg border border-white/5 hover:border-purple-500/30 transition-colors cursor-default">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-neutral-600 font-bold w-4">{idx + 1}.</span>
                      <span className="text-sm font-bold text-neutral-200">{alvo.nome}</span>
                    </div>
                    <span className="text-xs font-mono text-purple-400 font-bold">{alvo.score} pts</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* PAINEL DIREITO: Tropa Municipal (Deslizante) */}
          <AnimatePresence>
            {cidadeSelecionada && (
              <motion.div
                initial={{ x: "120%", opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: "120%", opacity: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className="w-full max-w-sm pointer-events-auto absolute right-6 top-6 bottom-6 flex flex-col pt-[88px]" // Offset para não tampar Top Right
              >
                <div className="h-full bg-neutral-950/90 backdrop-blur-xl border border-emerald-500/30 rounded-3xl p-6 shadow-[0_0_50px_rgba(0,0,0,0.8)] flex flex-col relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-40 h-40 bg-emerald-500/10 blur-[60px] rounded-full pointer-events-none" />

                  <button
                    onClick={() => {
                      setCidadeSelecionada("");
                      // Reset view
                      if (mapRef.current) mapRef.current.flyTo({ center: [-51.9253, -14.235], zoom: 3.5, pitch: 0, duration: 2000 });
                    }}
                    className="absolute top-6 right-6 text-neutral-500 hover:text-white transition-colors"
                  >
                    ✕
                  </button>

                  <h2 className="text-2xl font-black text-white mb-1 pr-8 leading-tight">{cidadeSelecionada}</h2>
                  <p className="text-[10px] text-emerald-400 font-mono tracking-widest uppercase mb-6 flex items-center gap-1">
                    <Navigation className="w-3 h-3" /> Foco Ativo / Interceptação
                  </p>

                  {loading ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-emerald-500 gap-4">
                      <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                      <p className="font-mono text-[10px] tracking-widest uppercase animate-pulse">Varrendo Bases do TSE...</p>
                    </div>
                  ) : (
                    <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 space-y-3">
                      {politicosLocais.map((pol, idx) => (
                        <div key={idx} className="bg-black/50 border border-neutral-800 rounded-xl p-4 hover:border-emerald-500/50 transition-colors group">
                          <div className="flex justify-between items-start mb-3">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <span className={`text-[8px] font-bold uppercase px-2 py-0.5 rounded ${pol.cargo === 'Prefeito' ? 'bg-amber-500/20 text-amber-500 border border-amber-500/30' : 'bg-neutral-800 text-neutral-400'}`}>
                                  {pol.cargo}
                                </span>
                                <span className="text-[10px] text-neutral-500 font-bold">{pol.partido}</span>
                              </div>
                              <h3 className="font-bold text-neutral-200 text-sm">{pol.nome}</h3>
                            </div>
                            <div className="flex flex-col items-end">
                              <span className="text-[10px] uppercase text-neutral-500 font-mono tracking-tighter">Score</span>
                              <span className={`text-sm font-black font-mono ${pol.score_auditoria > 600 ? 'text-emerald-500' : 'text-red-500'}`}>
                                {pol.score_auditoria}
                              </span>
                            </div>
                          </div>
                          <button
                            onClick={() => router.push(`/politico/${pol.id}`)}
                            className="w-full py-2 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-[11px] font-bold text-emerald-400 uppercase tracking-wider flex items-center justify-center gap-1 transition-colors"
                          >
                            Abrir Dossiê <ChevronRight className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                      {politicosLocais.length === 0 && (
                        <div className="text-center p-6 border border-dashed border-neutral-800 rounded-xl text-neutral-500">
                          <ShieldCheck className="w-8 h-8 mx-auto mb-2 opacity-50" />
                          <p className="text-xs uppercase font-bold text-neutral-600">Nenhum dado suspeito reportado.</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </div>

      <style jsx global>{`
                .custom-scrollbar::-webkit-scrollbar { width: 4px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #555; }
            `}</style>
    </div>
  );
}
