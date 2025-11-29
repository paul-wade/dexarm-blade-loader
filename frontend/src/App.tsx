import { useState } from 'react'
import { useApi } from './hooks/useApi'
import { cn } from './lib/utils'
import {
  Home,
  Plug,
  Power,
  Hand,
  Lock,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Plus,
  Minus,
  Crosshair,
  Play,
  Pause,
  Square,
  Trash2,
  MapPin,
  RefreshCw,
  Grip,
  Wind,
  PowerOff,
} from 'lucide-react'

function App() {
  const { status, ports, logs, log, api, fetchPorts, backendOnline } = useApi()
  const [selectedPort, setSelectedPort] = useState('')
  const [jogDistance, setJogDistance] = useState(10)
  const [selectedHook, setSelectedHook] = useState<number | null>(null)
  const [teachMode, setTeachMode] = useState(false)

  const connected = status?.connected ?? false
  const position = status?.position ?? { x: 0, y: 0, z: 0 }
  const pick = status?.positions?.pick
  const safeZ = status?.positions?.safe_z ?? 0
  const hooks = status?.positions?.hooks ?? []
  const isRunning = status?.is_running ?? false
  const isPaused = status?.is_paused ?? false

  const handleConnect = async () => {
    if (connected) {
      await api('/disconnect')
      log('Disconnected')
    } else {
      if (!selectedPort) return
      const res = await api('/connect', 'POST', { port: selectedPort })
      if (res.success) log('Connected! Press HOME to initialize')
    }
  }

  const handleHome = async () => {
    log('Homing...')
    await api('/home')
    log('At HOME')
  }

  const handleTeachMode = async () => {
    if (teachMode) {
      await api('/teach/disable')
      setTeachMode(false)
      log('Locked')
    } else {
      await api('/teach/enable')
      setTeachMode(true)
      log('FREE - drag arm, then click Set or Lock')
    }
  }

  const handleJog = async (axis: string, direction: number) => {
    await api('/jog', 'POST', { axis, distance: jogDistance * direction })
  }

  const handleSetPick = async () => {
    if (teachMode) {
      await api('/teach/disable')
      setTeachMode(false)
    }
    await api('/pick/set')
    log('Pick location set!')
  }

  const handleSetSafeZ = async () => {
    if (teachMode) {
      await api('/teach/disable')
      setTeachMode(false)
    }
    await api('/safe-z/set')
    log('Safe Z set!')
  }

  const handleAddHook = async () => {
    if (teachMode) {
      await api('/teach/disable')
      setTeachMode(false)
    }
    await api('/suction/off')
    const res = await api('/hooks/add')
    if (res.success) log(`Hook ${res.index} added!`)
  }

  const handleStartCycle = async () => {
    log('Starting cycle...')
    await api('/cycle/start')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Backend offline warning */}
        {!backendOnline && (
          <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
            <span className="text-red-200">
              Backend server is not responding. Please check if the server is running.
            </span>
          </div>
        )}

        {/* Header */}
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
            DexArm Blade Loader
          </h1>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={cn(
                "w-2 h-2 rounded-full",
                backendOnline ? "bg-green-500" : "bg-red-500"
              )} />
              <span className="text-xs text-slate-500">API</span>
            </div>
            <div className="flex items-center gap-2">
              <div className={cn(
                "w-3 h-3 rounded-full",
                connected ? "bg-green-500 animate-pulse" : "bg-red-500"
              )} />
              <span className="text-sm text-slate-400">
                {connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </header>

        {/* Top Row: Connection, Controls, Position, Jog */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Connection */}
          <Card title="Connection" icon={<Plug className="w-4 h-4" />}>
            <div className="space-y-3">
              <div className="flex gap-2">
                <select
                  value={selectedPort}
                  onChange={(e) => setSelectedPort(e.target.value)}
                  aria-label="Select serial port"
                  className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Select port...</option>
                  {ports.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <Button variant="ghost" size="icon" onClick={fetchPorts}>
                  <RefreshCw className="w-4 h-4" />
                </Button>
              </div>
              <Button
                onClick={handleConnect}
                variant={connected ? 'destructive' : 'primary'}
                className="w-full"
                disabled={!selectedPort && !connected}
              >
                <Power className="w-4 h-4 mr-2" />
                {connected ? 'Disconnect' : 'Connect'}
              </Button>
            </div>
          </Card>

          {/* Controls */}
          <Card title="Controls" icon={<Home className="w-4 h-4" />}>
            <div className="space-y-2">
              <Button onClick={handleHome} disabled={!connected} className="w-full">
                <Home className="w-4 h-4 mr-2" /> HOME
              </Button>
              <Button
                onClick={handleTeachMode}
                disabled={!connected}
                variant={teachMode ? 'secondary' : 'default'}
                className="w-full"
              >
                {teachMode ? <Lock className="w-4 h-4 mr-2" /> : <Hand className="w-4 h-4 mr-2" />}
                {teachMode ? 'LOCK' : 'FREE MOVE'}
              </Button>
            </div>
          </Card>

          {/* Position */}
          <Card title="Position" icon={<Crosshair className="w-4 h-4" />}>
            <div className="font-mono text-lg space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">X:</span>
                <span className="text-blue-400">{position.x.toFixed(1)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Y:</span>
                <span className="text-green-400">{position.y.toFixed(1)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Z:</span>
                <span className="text-cyan-400">{position.z.toFixed(1)}</span>
              </div>
            </div>
          </Card>

          {/* Jog */}
          <Card title="Jog Controls" icon={<ArrowUp className="w-4 h-4" />}>
            <div className="space-y-3">
              {/* Step size */}
              <div className="flex gap-1 justify-center">
                {[1, 5, 10, 25].map(d => (
                  <button
                    key={d}
                    onClick={() => setJogDistance(d)}
                    className={cn(
                      "px-3 py-1 rounded text-sm transition-all",
                      jogDistance === d
                        ? "bg-blue-500 text-white"
                        : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                    )}
                  >
                    {d}
                  </button>
                ))}
              </div>
              {/* Jog buttons */}
              <div className="grid grid-cols-4 gap-1">
                <div />
                <Button size="sm" onClick={() => handleJog('y', 1)} disabled={!connected}>
                  <ArrowUp className="w-4 h-4" />
                </Button>
                <div />
                <Button size="sm" onClick={() => handleJog('z', 1)} disabled={!connected}>
                  <Plus className="w-4 h-4" />
                </Button>
                <Button size="sm" onClick={() => handleJog('x', -1)} disabled={!connected}>
                  <ArrowLeft className="w-4 h-4" />
                </Button>
                <div className="flex items-center justify-center text-xs text-slate-500">XY</div>
                <Button size="sm" onClick={() => handleJog('x', 1)} disabled={!connected}>
                  <ArrowRight className="w-4 h-4" />
                </Button>
                <div className="flex items-center justify-center text-xs text-slate-500">Z</div>
                <div />
                <Button size="sm" onClick={() => handleJog('y', -1)} disabled={!connected}>
                  <ArrowDown className="w-4 h-4" />
                </Button>
                <div />
                <Button size="sm" onClick={() => handleJog('z', -1)} disabled={!connected}>
                  <Minus className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Middle Row: Suction, Pick, Safe Z */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Suction */}
          <Card title="Suction" icon={<Wind className="w-4 h-4" />}>
            <div className="flex gap-2">
              <Button onClick={() => api('/suction/grab')} disabled={!connected} className="flex-1">
                <Grip className="w-4 h-4 mr-2" /> GRAB
              </Button>
              <Button onClick={() => api('/suction/release')} disabled={!connected} className="flex-1">
                <Wind className="w-4 h-4 mr-2" /> RELEASE
              </Button>
              <Button onClick={() => api('/suction/off')} disabled={!connected} variant="ghost">
                <PowerOff className="w-4 h-4" />
              </Button>
            </div>
          </Card>

          {/* Pick Location */}
          <Card title="① Pick Location" icon={<MapPin className="w-4 h-4" />}>
            <div className="flex items-center gap-3">
              <div className="flex-1 font-mono text-sm">
                {pick ? (
                  <span>X:{pick.x.toFixed(0)} Y:{pick.y.toFixed(0)} Z:{pick.z.toFixed(0)}</span>
                ) : (
                  <span className="text-slate-500">Not set</span>
                )}
              </div>
              <Button size="sm" onClick={handleSetPick} disabled={!connected}>Set</Button>
              <Button size="sm" variant="ghost" onClick={() => api('/pick/goto')} disabled={!connected || !pick}>Go</Button>
            </div>
          </Card>

          {/* Safe Z */}
          <Card title="② Safe Height" icon={<ArrowUp className="w-4 h-4" />}>
            <div className="flex items-center gap-3">
              <div className="flex-1 font-mono text-sm">
                Z: <span className="text-cyan-400">{safeZ.toFixed(0)}</span>
              </div>
              <Button size="sm" onClick={handleSetSafeZ} disabled={!connected}>Set</Button>
              <Button size="sm" variant="ghost" onClick={() => api('/safe-z/goto')} disabled={!connected}>Go</Button>
            </div>
          </Card>
        </div>

        {/* Hooks + Run + Log */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Hooks */}
          <Card title="③ Hook Drop Points" icon={<MapPin className="w-4 h-4" />} className="md:col-span-2">
            <div className="flex gap-4">
              <div className="flex-1 bg-slate-800 rounded-lg p-2 max-h-48 overflow-y-auto">
                {hooks.length === 0 ? (
                  <p className="text-slate-500 text-sm text-center py-4">No hooks added</p>
                ) : (
                  <div className="space-y-1">
                    {hooks.map((h, i) => (
                      <div
                        key={i}
                        onClick={() => setSelectedHook(i)}
                        className={cn(
                          "px-3 py-2 rounded cursor-pointer font-mono text-sm transition-all",
                          selectedHook === i
                            ? "bg-blue-500/20 border border-blue-500"
                            : "hover:bg-slate-700"
                        )}
                      >
                        Hook {i}: X:{h.x.toFixed(0)} Y:{h.y.toFixed(0)} Z:{h.z.toFixed(0)}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex flex-col gap-2 w-28">
                <Button size="sm" onClick={handleAddHook} disabled={!connected}>
                  <Plus className="w-4 h-4 mr-1" /> Add
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => selectedHook !== null && api(`/hooks/${selectedHook}/goto`)}
                  disabled={!connected || selectedHook === null}
                >
                  Go To
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => selectedHook !== null && api(`/hooks/${selectedHook}/test`)}
                  disabled={!connected || selectedHook === null}
                >
                  Test
                </Button>
                <hr className="border-slate-700" />
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => {
                    if (selectedHook !== null) {
                      api(`/hooks/${selectedHook}`, 'DELETE')
                      setSelectedHook(null)
                    }
                  }}
                  disabled={selectedHook === null}
                >
                  <Trash2 className="w-4 h-4 mr-1" /> Delete
                </Button>
              </div>
            </div>
          </Card>

          {/* Run Cycle */}
          <Card title="Run Cycle" icon={<Play className="w-4 h-4" />}>
            <div className="space-y-4">
              {/* Progress */}
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-300"
                  style={{ width: isRunning ? '50%' : '0%' }}
                />
              </div>
              {/* Controls */}
              <div className="flex gap-2">
                <Button
                  onClick={handleStartCycle}
                  disabled={!connected || isRunning || !pick || hooks.length === 0}
                  className="flex-1"
                  variant="primary"
                >
                  <Play className="w-4 h-4 mr-2" /> START
                </Button>
                <Button
                  onClick={() => api('/cycle/pause')}
                  disabled={!isRunning}
                  variant="secondary"
                >
                  {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                </Button>
                <Button
                  onClick={() => api('/cycle/stop')}
                  disabled={!isRunning}
                  variant="destructive"
                >
                  <Square className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Log */}
        <Card title="Log" className="max-h-48">
          <div className="bg-slate-900 rounded-lg p-3 font-mono text-xs h-32 overflow-y-auto">
            {logs.length === 0 ? (
              <p className="text-slate-600">1. Connect  2. HOME  3. Set Pick  4. Set Safe Z  5. Add Hooks  6. START</p>
            ) : (
              logs.map((l, i) => (
                <div key={i} className="text-slate-400">{l}</div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}

// Reusable Card component
function Card({
  title,
  icon,
  children,
  className,
}: {
  title: string
  icon?: React.ReactNode
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn(
      "bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4",
      className
    )}>
      <div className="flex items-center gap-2 mb-3 text-slate-400">
        {icon}
        <h2 className="text-sm font-medium">{title}</h2>
      </div>
      {children}
    </div>
  )
}

// Reusable Button component
function Button({
  children,
  onClick,
  disabled,
  variant = 'default',
  size = 'default',
  className,
}: {
  children: React.ReactNode
  onClick?: () => void
  disabled?: boolean
  variant?: 'default' | 'primary' | 'secondary' | 'ghost' | 'destructive'
  size?: 'default' | 'sm' | 'icon'
  className?: string
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-medium transition-all",
        "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        {
          'default': "bg-slate-700 hover:bg-slate-600 text-white",
          'primary': "bg-blue-600 hover:bg-blue-500 text-white",
          'secondary': "bg-slate-600 hover:bg-slate-500 text-white",
          'ghost': "bg-transparent hover:bg-slate-700 text-slate-300",
          'destructive': "bg-red-600/20 hover:bg-red-600/30 text-red-400",
        }[variant],
        {
          'default': "px-4 py-2 text-sm",
          'sm': "px-3 py-1.5 text-xs",
          'icon': "p-2",
        }[size],
        className
      )}
    >
      {children}
    </button>
  )
}

export default App
