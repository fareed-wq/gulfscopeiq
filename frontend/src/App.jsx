import { useState, useEffect } from 'react'

function App() {
  const [apiStatus, setApiStatus] = useState('Checking...')

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'ok') {
          setApiStatus('Online')
        } else {
          setApiStatus('Offline')
        }
      })
      .catch(() => {
        setApiStatus('Offline')
      })
  }, [])

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-slate-800 rounded-xl shadow-2xl p-8 border border-slate-700">
        <h1 className="text-4xl font-bold tracking-tight text-white mb-2">GulfScopeIQ</h1>
        <h2 className="text-xl text-slate-300 font-medium mb-4">GCC Company & Market Intelligence</h2>
        <p className="text-slate-400 mb-8">Public intelligence, connected.</p>
        
        <div className="flex items-center space-x-3 bg-slate-900/50 p-4 rounded-lg border border-slate-700/50">
          <div className="text-sm font-medium text-slate-300">API Status:</div>
          <div className="flex items-center space-x-2">
            <span className={`h-2.5 w-2.5 rounded-full ${apiStatus === 'Online' ? 'bg-emerald-500' : apiStatus === 'Checking...' ? 'bg-yellow-500 animate-pulse' : 'bg-rose-500'}`}></span>
            <span className={`text-sm font-semibold ${apiStatus === 'Online' ? 'text-emerald-400' : apiStatus === 'Checking...' ? 'text-yellow-400' : 'text-rose-400'}`}>
              {apiStatus}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
