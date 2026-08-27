import { useState, useEffect } from 'react'

function App() {
  const [apiStatus, setApiStatus] = useState('Checking...')
  const [activeTab, setActiveTab] = useState('company') // 'company' or 'tender'

  // Company State
  const [companyName, setCompanyName] = useState('')
  const [website, setWebsite] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Tender State
  const [tenderQuery, setTenderQuery] = useState('')
  const [tenderCountry, setTenderCountry] = useState('QA')
  const [tenderLoading, setTenderLoading] = useState(false)
  const [tenderResult, setTenderResult] = useState(null)
  const [tenderError, setTenderError] = useState(null)

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => setApiStatus(data.status === 'ok' ? 'Online' : 'Offline'))
      .catch(() => setApiStatus('Offline'))
  }, [])

  const handleInvestigate = async (e) => {
    e.preventDefault()
    if (!companyName.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const payload = { company_name: companyName.trim() }
      if (website.trim()) {
        payload.website = website.trim()
      }

      const res = await fetch('/api/company/investigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(
          Array.isArray(data.detail)
            ? data.detail[0].msg
            : data.detail || 'API request failed'
        )
      }
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleTenderSearch = async (e) => {
    e.preventDefault()
    if (!tenderQuery.trim()) return

    setTenderLoading(true)
    setTenderError(null)
    setTenderResult(null)

    try {
      const payload = {
        query: tenderQuery.trim(),
        country_code: tenderCountry
      }

      const res = await fetch('/api/tenders/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      const data = await res.json()
      if (!res.ok) {
        throw new Error(
          Array.isArray(data.detail)
            ? data.detail[0].msg
            : data.detail || 'API request failed'
        )
      }
      setTenderResult(data)
    } catch (err) {
      setTenderError(err.message)
    } finally {
      setTenderLoading(false)
    }
  }

  const renderCompanyContent = () => {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center p-12 space-y-4">
          <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <div className="text-slate-400 font-medium">Gathering intelligence...</div>
        </div>
      )
    }

    if (error) {
      return (
        <div className="bg-rose-900/20 border border-rose-800 rounded-xl p-6 text-rose-300">
          <h3 className="font-semibold text-rose-400 mb-2">Investigation Failed</h3>
          <p>{error}</p>
        </div>
      )
    }

    if (!result) {
      return (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center text-slate-500">
          <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <p className="text-lg">Enter a company name to begin investigation.</p>
        </div>
      )
    }

    const { company, entities, status } = result
    const attrs = company.attributes || {}
    const discovery = attrs.discovery
    const web = attrs.web_intelligence

    const emails = [...new Set(entities.filter(e => e.type === 'email_address').map(e => e.label))]
    const phones = [...new Set(entities.filter(e => e.type === 'phone_number').map(e => e.label))]
    const socials = [...new Set(entities.filter(e => e.type === 'social_profile').map(e => e.label))]

    const newsEntities = [...entities]
      .filter(e => e.type === 'news_article')
      .sort((a, b) => {
        const dateA = a.attributes?.published_at ? new Date(a.attributes.published_at).getTime() : 0;
        const dateB = b.attributes?.published_at ? new Date(b.attributes.published_at).getTime() : 0;
        return dateB - dateA;
      })
      .slice(0, 10);

    return (
      <div className="space-y-6">
        {/* 1. Company Overview */}
        <section className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
          <h2 className="text-xl font-bold text-white mb-4 border-b border-slate-700 pb-2">Company Overview</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-slate-400 block">Name</span>
              <span className="text-slate-200 font-medium">{company.name}</span>
            </div>
            <div>
              <span className="text-sm text-slate-400 block">Status</span>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                {status}
              </span>
            </div>
            <div className="col-span-2">
              <span className="text-sm text-slate-400 block">Final Website</span>
              <span className="text-emerald-400 truncate block">
                {company.website ? (
                  <a href={company.website} target="_blank" rel="noreferrer" className="hover:underline">{company.website}</a>
                ) : 'N/A'}
              </span>
            </div>
          </div>
        </section>

        {/* 2. Website Discovery */}
        <section className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
          <h2 className="text-xl font-bold text-white mb-4 border-b border-slate-700 pb-2">Website Discovery</h2>
          {discovery ? (
            <div className="space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-sm text-slate-400 block">Discovered URL</span>
                  <span className="text-slate-200">{discovery.website || 'None found'}</span>
                </div>
                <div className="text-right">
                  <span className="text-sm text-slate-400 block">Confidence</span>
                  <span className={`capitalize font-medium ${discovery.confidence === 'high' ? 'text-emerald-400' : 'text-yellow-400'}`}>
                    {discovery.confidence || 'Low'}
                  </span>
                </div>
              </div>
              <div>
                <span className="text-sm text-slate-400 block">Source</span>
                <span className="text-slate-300 text-sm">{discovery.source}</span>
              </div>
              {discovery.candidates && discovery.candidates.length > 0 && (
                <div className="mt-4 p-3 bg-slate-900/50 rounded border border-slate-700/50">
                  <span className="text-xs text-slate-400 block mb-2 uppercase tracking-wider">Top Candidates</span>
                  <ul className="text-sm text-slate-300 space-y-2">
                    {discovery.candidates.slice(0, 3).map((c, i) => (
                      <li key={i} className="flex justify-between">
                        <span className="truncate pr-4 text-emerald-500/80">{c.url}</span>
                        <span className="text-slate-500">Score: {c.score}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="text-slate-400">
              {website ? 'Bypassed (User provided website)' : 'No discovery data available'}
            </div>
          )}
        </section>

        {/* 3. Web Intelligence */}
        <section className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
          <h2 className="text-xl font-bold text-white mb-4 border-b border-slate-700 pb-2">Web Intelligence</h2>
          {web ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="col-span-full">
                <span className="text-sm text-slate-400 block">Title</span>
                <span className="text-slate-200">{web.title || 'N/A'}</span>
              </div>
              <div className="col-span-full">
                <span className="text-sm text-slate-400 block">Meta Description</span>
                <span className="text-slate-300 text-sm line-clamp-3">{web.meta_description || 'N/A'}</span>
              </div>
              <div>
                <span className="text-sm text-slate-400 block">HTTP Status</span>
                <span className={`font-medium ${web.http_status === 200 ? 'text-emerald-400' : 'text-yellow-400'}`}>
                  {web.http_status || 'Unknown'}
                </span>
              </div>
              <div>
                <span className="text-sm text-slate-400 block">Language</span>
                <span className="text-slate-200 uppercase">{web.language || 'N/A'}</span>
              </div>
              <div className="col-span-full">
                <span className="text-sm text-slate-400 block">Canonical URL</span>
                <span className="text-slate-400 text-sm truncate block">{web.canonical_url || 'N/A'}</span>
              </div>
            </div>
          ) : (
            <div className="text-slate-400">No web data extracted</div>
          )}
        </section>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 4. Public Contacts */}
          <section className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
            <h2 className="text-xl font-bold text-white mb-4 border-b border-slate-700 pb-2">Public Contacts</h2>
            <div className="space-y-4">
              <div>
                <span className="text-sm text-slate-400 block mb-1">Emails</span>
                {emails.length > 0 ? (
                  <ul className="space-y-1">
                    {emails.map((e, i) => <li key={i} className="text-slate-200">{e}</li>)}
                  </ul>
                ) : <span className="text-slate-500 text-sm">None discovered</span>}
              </div>
              <div>
                <span className="text-sm text-slate-400 block mb-1">Phones</span>
                {phones.length > 0 ? (
                  <ul className="space-y-1">
                    {phones.map((p, i) => <li key={i} className="text-slate-200">{p}</li>)}
                  </ul>
                ) : <span className="text-slate-500 text-sm">None discovered</span>}
              </div>
            </div>
          </section>

          {/* 5. Social Presence */}
          <section className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
            <h2 className="text-xl font-bold text-white mb-4 border-b border-slate-700 pb-2">Social Presence</h2>
            <div>
              {socials.length > 0 ? (
                <ul className="space-y-2">
                  {socials.map((s, i) => (
                    <li key={i} className="text-slate-200 truncate">
                      <a href={s} target="_blank" rel="noreferrer" className="hover:text-emerald-400 transition-colors">{s}</a>
                    </li>
                  ))}
                </ul>
              ) : <span className="text-slate-500 text-sm">None discovered</span>}
            </div>
          </section>
        </div>

        {/* Recent Company News */}
        <section className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
          <div className="flex justify-between items-center mb-4 border-b border-slate-700 pb-2">
            <h2 className="text-xl font-bold text-white">Recent Company News</h2>
            <span className="text-xs bg-slate-700 text-slate-300 px-3 py-1 rounded-full">
              {newsEntities.length} relevant articles
            </span>
          </div>

          {newsEntities.length > 0 ? (
            <div className="space-y-4">
              {newsEntities.map((ne, i) => {
                const attrs = ne.attributes || {};
                return (
                  <div key={i} className="group border border-slate-700/50 rounded-lg p-4 bg-slate-900/30 hover:bg-slate-700/30 transition-colors">
                    <div className="flex justify-between items-start gap-4 mb-2">
                      <a
                        href={attrs.url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-medium text-slate-200 group-hover:text-emerald-400 transition-colors leading-tight"
                      >
                        {ne.label}
                      </a>
                      <span className={`text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${
                        attrs.confidence === 'high' ? 'bg-emerald-900/30 text-emerald-400 border border-emerald-900/50' :
                        'bg-yellow-900/30 text-yellow-400 border border-yellow-900/50'
                      }`}>
                        {attrs.confidence} match
                      </span>
                    </div>
                    <div className="flex items-center text-xs text-slate-500 space-x-3">
                      {attrs.publisher && <span>{attrs.publisher}</span>}
                      {attrs.published_at && (
                        <>
                          {attrs.publisher && <span>&bull;</span>}
                          <span>
                            {new Date(attrs.published_at).toLocaleDateString(undefined, {
                              year: 'numeric', month: 'short', day: 'numeric'
                            })}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-slate-500 text-sm">No relevant recent news found.</div>
          )}
        </section>

        {/* 6. Evidence / Collection Notes */}
        <section className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
          <h2 className="text-xl font-bold text-white mb-4 border-b border-slate-700 pb-2">Collection Notes</h2>
          <div className="space-y-3">
            {attrs.discovery_error && (
              <div className="text-sm bg-rose-900/10 text-rose-400 p-3 rounded border border-rose-900/50">
                <strong className="block mb-1">Discovery Warning</strong>
                {attrs.discovery_error}
              </div>
            )}
            {attrs.web_intelligence_error && (
              <div className="text-sm bg-yellow-900/10 text-yellow-400 p-3 rounded border border-yellow-900/50">
                <strong className="block mb-1">Web Collection Warning</strong>
                {attrs.web_intelligence_error}
              </div>
            )}

            {company.evidence && company.evidence.length > 0 ? (
              <div>
                <strong className="text-sm text-slate-400 block mb-2">Evidence Sources</strong>
                <ul className="text-xs text-slate-500 space-y-1">
                  {company.evidence.map((ev, i) => (
                    <li key={i}>
                      {ev.source}: <a href={ev.source_url} target="_blank" rel="noreferrer" className="hover:text-slate-300 truncate">{ev.source_url}</a>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="text-sm text-slate-500">No evidence recorded.</div>
            )}
          </div>
        </section>
      </div>
    )
  }

  const renderTenderContent = () => {
    if (tenderLoading) {
      return (
        <div className="flex flex-col items-center justify-center p-12 space-y-4">
          <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <div className="text-slate-400 font-medium">Searching tenders...</div>
        </div>
      )
    }

    if (tenderError) {
      return (
        <div className="bg-rose-900/20 border border-rose-800 rounded-xl p-6 text-rose-300">
          <h3 className="font-semibold text-rose-400 mb-2">Search Failed</h3>
          <p>{tenderError}</p>
        </div>
      )
    }

    if (!tenderResult) {
      return (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center text-slate-500">
          <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <p className="text-lg">Enter a keyword to search public tenders.</p>
        </div>
      )
    }

    const { query, country_code, status, tenders } = tenderResult

    if (status === 'foundation' || !tenders || tenders.length === 0) {
      return (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center">
          <p className="text-slate-300 text-lg mb-2">No tenders found for "{query}".</p>
          {country_code === 'KW' && (
            <p className="text-slate-400 text-sm mt-4">Search covers up to 40 recent CAPT opening tenders and is not an exhaustive archive search.</p>
          )}
          {country_code === 'SA' && (
            <p className="text-slate-400">Automated Saudi tender collection is not available yet.</p>
          )}
          {country_code === 'AE' && (
            <p className="text-slate-400">UAE federal tender source is temporarily unavailable. GulfScopeIQ support is planned once the official source is operational.</p>
          )}
        </div>
      )
    }

    return (
      <div className="space-y-6">
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Tender Results</h2>
            <p className="text-sm text-slate-400 mt-1">Query: <span className="text-slate-200">"{query}"</span> in {country_code}</p>
          </div>
          <div className="text-right">
            <span className="text-sm font-medium bg-emerald-900/30 text-emerald-400 px-3 py-1 rounded-full border border-emerald-900/50">
              {tenders.length} Found
            </span>
          </div>
        </div>

        {country_code === 'KW' && (
          <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-4 shadow text-slate-300 text-sm">
            <span className="font-semibold text-emerald-400 mr-2">Note:</span>
            {tenders[0]?.attributes?.coverage_note || "Search covers up to 40 recent CAPT opening tenders and is not an exhaustive archive search."}
          </div>
        )}

        <div className="space-y-4">
          {tenders.map((tender, i) => (
            <div key={i} className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg hover:border-slate-600 transition-colors">
              <div className="flex justify-between items-start gap-4 mb-3">
                <a href={tender.source_url} target="_blank" rel="noreferrer" className="text-lg font-semibold text-emerald-400 hover:text-emerald-300 transition-colors">
                  {tender.title}
                </a>
                {tender.status && (
                  <span className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded-full capitalize whitespace-nowrap">
                    {tender.status}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-y-2 gap-x-4 text-sm">
                {tender.reference_number && (
                  <div><span className="text-slate-500">Ref:</span> <span className="text-slate-300">{tender.reference_number}</span></div>
                )}
                {tender.issuing_authority && (
                  <div><span className="text-slate-500">Authority:</span> <span className="text-slate-300">{tender.issuing_authority}</span></div>
                )}
                {tender.attributes?.tender_type && (
                  <div><span className="text-slate-500">Type:</span> <span className="text-slate-300">{tender.attributes.tender_type}</span></div>
                )}
                {tender.published_at && (
                  <div><span className="text-slate-500">Published:</span> <span className="text-slate-300">{tender.published_at}</span></div>
                )}
                {tender.attributes?.purchase_before && (
                  <div><span className="text-slate-500">Purchase Before:</span> <span className="text-slate-300">{tender.attributes.purchase_before}</span></div>
                )}
                {tender.deadline && (
                  <div><span className="text-slate-500">Deadline:</span> <span className="text-slate-300">{tender.deadline}</span></div>
                )}
                {tender.budget && (
                  <div><span className="text-slate-500">Budget/Price:</span> <span className="text-slate-300">{tender.budget}</span></div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col md:flex-row">
      {/* Sidebar / Left column */}
      <div className="w-full md:w-80 bg-slate-800/50 border-r border-slate-700 p-6 flex flex-col">
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight text-white">GulfScopeIQ</h1>
          <h2 className="text-xs text-slate-400 font-medium uppercase tracking-wider mt-1">GCC Intelligence</h2>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-slate-900 rounded-lg p-1 mb-6 border border-slate-700">
          <button
            onClick={() => setActiveTab('company')}
            className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${
              activeTab === 'company' ? 'bg-slate-700 text-white shadow' : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            Companies
          </button>
          <button
            onClick={() => setActiveTab('tender')}
            className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${
              activeTab === 'tender' ? 'bg-slate-700 text-white shadow' : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            Tenders
          </button>
        </div>

        {activeTab === 'company' ? (
          <form onSubmit={handleInvestigate} className="space-y-4 flex-1">
            <div>
              <label htmlFor="companyName" className="block text-sm font-medium text-slate-300 mb-1">Company Name *</label>
              <input
                id="companyName"
                type="text"
                required
                placeholder="e.g. Saudi Aramco"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 outline-none transition-all placeholder:text-slate-600"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="website" className="block text-sm font-medium text-slate-300 mb-1">Official Website <span className="text-slate-500 font-normal">(optional)</span></label>
              <input
                id="website"
                type="text"
                placeholder="e.g. aramco.com"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 outline-none transition-all placeholder:text-slate-600"
                value={website}
                onChange={e => setWebsite(e.target.value)}
              />
              <p className="text-xs text-slate-500 mt-1.5">Leave blank to auto-discover</p>
            </div>

            <button
              type="submit"
              disabled={loading || !companyName.trim()}
              className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium py-2.5 rounded-lg transition-colors focus:ring-4 focus:ring-emerald-500/20"
            >
              {loading ? 'Investigating...' : 'Investigate'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleTenderSearch} className="space-y-4 flex-1">
            <div>
              <label htmlFor="tenderQuery" className="block text-sm font-medium text-slate-300 mb-1">Keyword *</label>
              <input
                id="tenderQuery"
                type="text"
                required
                placeholder="e.g. cybersecurity"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 outline-none transition-all placeholder:text-slate-600"
                value={tenderQuery}
                onChange={e => setTenderQuery(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="tenderCountry" className="block text-sm font-medium text-slate-300 mb-1">Country</label>
              <select
                id="tenderCountry"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 outline-none transition-all"
                value={tenderCountry}
                onChange={e => setTenderCountry(e.target.value)}
              >
                <option value="QA">Qatar (QA)</option>
                <option value="KW">Kuwait (KW)</option>
                <option value="BH">Bahrain (BH)</option>
                <option value="AE">United Arab Emirates (AE) — Source temporarily unavailable</option>
                <option value="SA">Saudi Arabia (SA) - Foundation / not automated yet</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={tenderLoading || !tenderQuery.trim()}
              className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium py-2.5 rounded-lg transition-colors focus:ring-4 focus:ring-emerald-500/20"
            >
              {tenderLoading ? 'Searching...' : 'Search Tenders'}
            </button>
          </form>
        )}

        <div className="mt-8 flex items-center space-x-3 bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
          <div className="text-xs font-medium text-slate-400">API Status</div>
          <div className="flex items-center space-x-2">
            <span className={`h-2 w-2 rounded-full ${apiStatus === 'Online' ? 'bg-emerald-500' : apiStatus === 'Checking...' ? 'bg-yellow-500 animate-pulse' : 'bg-rose-500'}`}></span>
            <span className={`text-xs font-semibold ${apiStatus === 'Online' ? 'text-emerald-400' : apiStatus === 'Checking...' ? 'text-yellow-400' : 'text-rose-400'}`}>
              {apiStatus}
            </span>
          </div>
        </div>
      </div>

      {/* Main Content / Right column */}
      <div className="flex-1 p-6 md:p-8 lg:p-12 overflow-y-auto">
        <div className="max-w-4xl mx-auto">
          {activeTab === 'company' ? renderCompanyContent() : renderTenderContent()}
        </div>
      </div>
    </div>
  )
}

export default App
