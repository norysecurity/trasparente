"use client";

import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

export default function GrafoCorrupcao({ politicoData }: { politicoData: any }) {
    const graphRef = useRef<any>(null);
    const [dimensions, setDimensions] = useState({ width: 800, height: 400 });

    useEffect(() => {
        const updateDimensions = () => {
            const container = document.getElementById('grafo-container');
            if (container) {
                setDimensions({ width: container.clientWidth, height: container.clientHeight });
            }
        };
        window.addEventListener('resize', updateDimensions);
        updateDimensions();
        return () => window.removeEventListener('resize', updateDimensions);
    }, []);

    const graphData = useMemo(() => {
        if (!politicoData) return { nodes: [], links: [] };

        const nodes: any[] = [];
        const links: any[] = [];

        // Nó Central: Político
        nodes.push({
            id: politicoData.nome,
            name: politicoData.nome,
            group: 1, // 1 = Político Target
            val: 20
        });

        const empresas = politicoData.empresas || [];

        empresas.forEach((emp: any) => {
            const empId = emp.cnpj || emp.nome;
            // Nó da Empresa
            if (!nodes.find(n => n.id === empId)) {
                nodes.push({
                    id: empId,
                    name: emp.nome,
                    group: 2, // 2 = Empresa/Fornecedor
                    val: 10
                });
            }

            // Aresta Empresa -> Político
            links.push({
                source: empId,
                target: politicoData.nome,
                name: 'Forneceu/Ligação'
            });

            // Sócios/Familiares
            if (emp.socios && Array.isArray(emp.socios)) {
                emp.socios.forEach((socio: string) => {
                    if (!nodes.find(n => n.id === socio)) {
                        nodes.push({
                            id: socio,
                            name: socio,
                            group: 3, // 3 = Familiar/Laranja/Sócio
                            val: 5
                        });
                    }

                    // Aresta Sócio -> Empresa
                    links.push({
                        source: socio,
                        target: empId,
                        name: 'Societário'
                    });
                });
            }
        });

        return { nodes, links };
    }, [politicoData]);

    useEffect(() => {
        // Encaixe automágico na tela com delayzinho suave
        setTimeout(() => {
            if (graphRef.current) {
                graphRef.current.zoomToFit(800, 50); // 800ms dur, 50 padding
            }
        }, 300);
    }, [graphData]);

    const nodeColor = useCallback((node: any) => {
        switch (node.group) {
            case 1: return '#10b981'; // Político (Verde Esmeralda)
            case 2: return '#a855f7'; // Entidades Financeiras (Roxo)
            case 3: return '#f43f5e'; // CPFs / Laranjas (Vermelho/Rose)
            default: return '#52525b';
        }
    }, []);

    return (
        <div id="grafo-container" className="w-full h-full min-h-[400px] bg-neutral-950 rounded-2xl overflow-hidden shadow-inner relative border border-purple-500/20">
            {/* Overlay informativo flutuante */}
            <div className="absolute top-4 left-4 z-10 pointer-events-none flex flex-col gap-2">
                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-emerald-500" /> <span className="text-[10px] text-emerald-400 font-mono tracking-widest uppercase font-bold">Ponto Central</span></div>
                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-purple-500" /> <span className="text-[10px] text-purple-400 font-mono tracking-widest uppercase font-bold">Entidade Fin.</span></div>
                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-rose-500" /> <span className="text-[10px] text-rose-400 font-mono tracking-widest uppercase font-bold">Sócio / Familiar</span></div>
            </div>

            <ForceGraph2D
                ref={graphRef}
                width={dimensions.width}
                height={dimensions.height}
                graphData={graphData}
                nodeAutoColorBy="group"
                nodeColor={nodeColor}
                nodeLabel="name"
                linkDirectionalParticles={4}
                linkDirectionalParticleSpeed={d => 0.005} // Particles speed
                linkDirectionalParticleColor={() => '#a855f7'}
                linkColor={() => 'rgba(168, 85, 247, 0.2)'} // Roxo translúcido
                backgroundColor="#0a0a0a"
                // Efeito Hover Node Highlighter
                onNodeHover={(node, prevNode) => {
                    const canvas = document.getElementById('grafo-container');
                    if (canvas) canvas.style.cursor = node ? 'pointer' : 'default';
                }}
                onNodeClick={(node) => {
                    if (node.group !== 1) {
                        alert(`⚠️ [ACESSO NEGADO]\n\nAuditoria profunda em ramificações secundárias (${node.name}) requer Liberação de Nível 2.\nFuncionalidade restrita para mapeamento de Laranjas e Fornecedores Indiretos.`);
                    }
                }}
            />
        </div>
    );
}
