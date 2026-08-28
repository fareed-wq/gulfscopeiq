import React, { useState, useMemo } from 'react';

const IntelligenceGraph = ({ data }) => {
  const [filter, setFilter] = useState('All');
  const [selectedNode, setSelectedNode] = useState(null);

  const graphData = useMemo(() => {
    if (!data || !data.organization_clusters || data.organization_clusters.length === 0) {
      return null;
    }

    const primaryCluster = data.organization_clusters[0];
    const rootId = primaryCluster.organization_id;
    const entities = data.entities || [];
    const relationships = data.relationships || [];

    const rootEntity = entities.find(e => e.id === rootId) || {
      id: rootId,
      type: 'Organization',
      label: primaryCluster.organization_name,
      attributes: {}
    };


    const allConnectedEdges = relationships.filter(r => r.source === rootId || r.target === rootId);
    const hop1EntityIds = new Set(allConnectedEdges.map(r => r.source === rootId ? r.target : r.source));
    hop1EntityIds.add(rootId);

    const hop2Edges = relationships.filter(r =>
       (hop1EntityIds.has(r.source) || hop1EntityIds.has(r.target)) &&
       (r.type === 'resolves_to' || r.type === 'uses')
    );

    // Combine edges and unique entity IDs
    const finalEdges = [...allConnectedEdges, ...hop2Edges];
    const connectedEntityIds = new Set();
    finalEdges.forEach(r => { connectedEntityIds.add(r.source); connectedEntityIds.add(r.target); });


    let validEntities = entities.filter(e => connectedEntityIds.has(e.id));

    if (filter !== 'All') {

      let allowedTypes = [];
      if (filter === 'News') allowedTypes = ['news_article'];
      else if (filter === 'Jobs') allowedTypes = ['job'];
      else if (filter === 'Documents') allowedTypes = ['document'];
      else if (filter === 'Tenders') allowedTypes = ['tender'];
      else if (filter === 'Infrastructure') allowedTypes = ['domain', 'ipaddress', 'technology'];

      validEntities = validEntities.filter(e => allowedTypes.includes(e.type.toLowerCase()));

    }

    const totalConnected = validEntities.length;

    const grouped = {};
    validEntities.forEach(e => {
      const t = e.type.toLowerCase();
      if (!grouped[t]) grouped[t] = [];
      grouped[t].push(e);
    });

    let finalEntities = [];
    const types = Object.keys(grouped);
    if (types.length > 0) {
      const MAX_NODES = 40;
      const nodesPerType = Math.max(1, Math.floor(MAX_NODES / types.length));
      let remainingCapacity = MAX_NODES;

      types.forEach(t => {
        const take = Math.min(nodesPerType, grouped[t].length);
        finalEntities.push(...grouped[t].slice(0, take));
        grouped[t] = grouped[t].slice(take);
        remainingCapacity -= take;
      });

      types.forEach(t => {
        if (remainingCapacity > 0 && grouped[t].length > 0) {
          const take = Math.min(remainingCapacity, grouped[t].length);
          finalEntities.push(...grouped[t].slice(0, take));
          grouped[t] = grouped[t].slice(take);
          remainingCapacity -= take;
        }
      });
    }

    const width = 800;
    const height = 600;
    const cx = width / 2;
    const cy = height / 2;
    const radius = 180;

    const nodes = [{ ...rootEntity, x: cx, y: cy, isRoot: true }];

    finalEntities.sort((a, b) => a.type.localeCompare(b.type));


    finalEntities.forEach((e, i) => {
      const angle = (i / finalEntities.length) * 2 * Math.PI - Math.PI / 2;
      let r = radius;
      if (e.type === 'Domain') r = 120;
      else if (e.type === 'IPAddress' || e.type === 'Technology') r = 240;

      nodes.push({
        ...e,
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
        isRoot: false
      });
    });


    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    const edges = finalEdges
      .filter(r => nodeMap.has(r.source) && nodeMap.has(r.target))
      .map(r => ({
        sourceNode: nodeMap.get(r.source),
        targetNode: nodeMap.get(r.target),
        type: r.type
      }));

    return {
      nodes,
      edges,
      totalConnected,
      renderedCount: finalEntities.length,
      width,
      height
    };
  }, [data, filter]);

  if (!graphData || (graphData.nodes.length <= 1 && graphData.totalConnected === 0)) {
    return (
      <div className="bg-slate-800 rounded-xl p-8 border border-slate-700 text-center">
        <p className="text-slate-400">No connected intelligence available to visualize.</p>
      </div>
    );
  }

  const { nodes, edges, totalConnected, renderedCount, width, height } = graphData;

  const handleNodeClick = (n) => {
    setSelectedNode(n);
  };

  const getBadgeColor = (type) => {
    const t = type.toLowerCase();
    if (t === 'news_article') return { color: '#3b82f6', bg: 'bg-blue-500' };
    if (t === 'job') return { color: '#a855f7', bg: 'bg-purple-500' };
    if (t === 'document') return { color: '#10b981', bg: 'bg-emerald-500' };
    if (t === 'tender') return { color: '#f97316', bg: 'bg-orange-500' };

    if (t === 'domain') return { color: '#0ea5e9', bg: 'bg-sky-500' };
    if (t === 'ipaddress') return { color: '#f43f5e', bg: 'bg-rose-500' };
    if (t === 'technology') return { color: '#8b5cf6', bg: 'bg-violet-500' };

    return { color: '#64748b', bg: 'bg-slate-500' };
  };

  const truncate = (str, len) => str.length > len ? str.substring(0, len) + '...' : str;

  const renderSelectedDetails = () => {
    if (!selectedNode) return <p className="text-sm text-slate-500">Select a node to view details</p>;

    const type = selectedNode.type.toLowerCase();
    const attrs = selectedNode.attributes || {};

    return (
      <div className="space-y-3">
        <div>
          <span className={`inline-block px-2 py-1 text-xs font-medium text-white rounded mb-2 ${selectedNode.isRoot ? 'bg-emerald-600' : getBadgeColor(selectedNode.type).bg}`}>
            {selectedNode.type}
          </span>
          <h4 className="font-bold text-white text-lg leading-snug">{selectedNode.label || selectedNode.name}</h4>
        </div>

        {type === 'news_article' && (
          <div className="text-sm text-slate-300 space-y-1 mt-2">
            {attrs.publisher && <p><span className="text-slate-500">Publisher:</span> {attrs.publisher}</p>}
            {attrs.published_at && <p><span className="text-slate-500">Date:</span> {attrs.published_at}</p>}
            {attrs.url && <a href={attrs.url} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline block mt-2">Read Article ↗</a>}
          </div>
        )}

        {type === 'job' && (
          <div className="text-sm text-slate-300 space-y-1 mt-2">
            {attrs.company && <p><span className="text-slate-500">Company:</span> {attrs.company}</p>}
            {attrs.location && <p><span className="text-slate-500">Location:</span> {attrs.location}</p>}
            {attrs.department && <p><span className="text-slate-500">Department:</span> {attrs.department}</p>}
            {attrs.published_at && <p><span className="text-slate-500">Date:</span> {attrs.published_at}</p>}
            {attrs.url && <a href={attrs.url} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline block mt-2">Source Link ↗</a>}
          </div>
        )}

        {type === 'document' && (
          <div className="text-sm text-slate-300 space-y-1 mt-2">
            {attrs.organization && <p><span className="text-slate-500">Organization:</span> {attrs.organization}</p>}
            {attrs.document_type && <p><span className="text-slate-500">Type:</span> {attrs.document_type}</p>}
            {attrs.published_at && <p><span className="text-slate-500">Date:</span> {attrs.published_at}</p>}
            <div className="flex gap-3 mt-3">
              {attrs.source_url && <a href={attrs.source_url} target="_blank" rel="noopener noreferrer" className="text-xs px-3 py-1.5 bg-slate-700 text-slate-300 rounded hover:bg-slate-600">Source Page</a>}
              {attrs.file_url && <a href={attrs.file_url} target="_blank" rel="noopener noreferrer" className="text-xs px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded hover:bg-emerald-500/30">Open PDF</a>}
            </div>
          </div>
        )}


        {type === 'domain' && (
          <div className="text-sm text-slate-300 space-y-1 mt-2">
            {attrs.registrar && <p><span className="text-slate-500">Registrar:</span> {attrs.registrar}</p>}
            {attrs.domain_status && <p><span className="text-slate-500">Status:</span> {attrs.domain_status}</p>}
          </div>
        )}

        {type === 'ipaddress' && (
          <div className="text-sm text-slate-300 space-y-1 mt-2">
            {attrs.network_organization && <p><span className="text-slate-500">Organization:</span> {attrs.network_organization}</p>}
            {attrs.country && <p><span className="text-slate-500">Country:</span> {attrs.country}</p>}
          </div>
        )}

        {type === 'technology' && (
          <div className="text-sm text-slate-300 space-y-1 mt-2">
            <p><span className="text-slate-500">Detected Technology</span></p>
          </div>
        )}

        {type === 'tender' && (
          <div className="text-sm text-slate-300 space-y-1 mt-2">
            {attrs.issuing_authority && <p><span className="text-slate-500">Authority:</span> {attrs.issuing_authority}</p>}
            {attrs.reference_number && <p><span className="text-slate-500">Ref:</span> {attrs.reference_number}</p>}
            {attrs.status && <p><span className="text-slate-500">Status:</span> {attrs.status}</p>}
            {attrs.deadline && <p><span className="text-slate-500">Deadline:</span> {attrs.deadline}</p>}
            {attrs.url && <a href={attrs.url} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline block mt-2">Source URL ↗</a>}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 shadow-lg overflow-hidden flex flex-col">
      <div className="p-4 border-b border-slate-700 flex flex-wrap gap-2 items-center justify-between">
        <h3 className="text-lg font-bold text-white">Intelligence Graph</h3>
        <div className="flex gap-2">
          {['All', 'News', 'Jobs', 'Documents', 'Tenders', 'Infrastructure'].map(f => (
            <button
              key={f}
              onClick={() => { setFilter(f); setSelectedNode(null); }}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${filter === f ? 'bg-emerald-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col md:flex-row">
        <div className="flex-1 relative bg-slate-900/50 min-h-[500px]">
          <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
            {edges.map((edge, idx) => {
              const mx = (edge.sourceNode.x + edge.targetNode.x) / 2;
              const my = (edge.sourceNode.y + edge.targetNode.y) / 2;
              return (
                <g key={idx}>
                  <line
                    x1={edge.sourceNode.x} y1={edge.sourceNode.y}
                    x2={edge.targetNode.x} y2={edge.targetNode.y}
                    stroke="#475569" strokeWidth="1.5" strokeOpacity="0.4"
                  />
                  <text x={mx} y={my} fill="#64748b" fontSize="10" textAnchor="middle" dy="-4" className="pointer-events-none">
                    {edge.type}
                  </text>
                </g>
              );
            })}

            {nodes.map(node => {
              const isSelected = selectedNode?.id === node.id;
              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  onClick={() => handleNodeClick(node)}
                  className="cursor-pointer"
                >
                  <circle
                    r={node.isRoot ? 35 : 20}
                    fill={node.isRoot ? '#059669' : '#1e293b'}
                    stroke={isSelected ? '#34d399' : node.isRoot ? '#34d399' : '#475569'}
                    strokeWidth={isSelected ? 3 : 2}
                    className="transition-all duration-200"
                  />

                  {!node.isRoot && (
                    <circle r="6" cy="-20" fill={getBadgeColor(node.type).color} />
                  )}

                  <text
                    y={node.isRoot ? 0 : 32}
                    textAnchor="middle"
                    fill="#e2e8f0"
                    fontSize={node.isRoot ? '12' : '10'}
                    fontWeight={node.isRoot ? 'bold' : 'normal'}
                    className="pointer-events-none"
                    dy={node.isRoot ? "4" : "0"}
                  >
                    {truncate(node.label || '', 20)}
                  </text>
                </g>
              );
            })}
          </svg>

          <div className="absolute bottom-3 left-4 text-xs text-slate-500">
            {renderedCount < totalConnected ? `Showing ${renderedCount} of ${totalConnected} connected items` : `Showing all ${totalConnected} connected items`}
          </div>
        </div>

        <div className="w-full md:w-72 bg-slate-800/80 p-5 border-t md:border-t-0 md:border-l border-slate-700">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Selected Intelligence</h3>
          {renderSelectedDetails()}
        </div>
      </div>
    </div>
  );
};

export default IntelligenceGraph;
