import { useState, useEffect, useCallback, useRef } from 'react'

const API_BASE = 'http://127.0.0.1:8000/api'
const POLL_INTERVAL = 2000 // 2 seconds instead of 1
const MAX_RETRIES = 3

interface Status {
  connected: boolean
  homed: boolean
  position: { x: number; y: number; z: number }
  carrying_blade: boolean
  suction_active: boolean
  safe_z: number
  is_running: boolean
  is_paused: boolean
  current_cycle: number
  total_cycles: number
  positions: {
    pick: { x: number; y: number; z: number } | null
    safe_z: number | null
    hooks: Array<{ x: number; y: number; z: number }>
  }
}

export function useApi() {
  const [status, setStatus] = useState<Status | null>(null)
  const [ports, setPorts] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const [backendOnline, setBackendOnline] = useState(true)
  const errorCountRef = useRef(0)
  const isMountedRef = useRef(true)

  const log = useCallback((msg: string) => {
    if (isMountedRef.current) {
      setLogs(prev => [...prev.slice(-50), msg])
    }
  }, [])

  const fetchStatus = useCallback(async () => {
    if (!isMountedRef.current) return
    
    try {
      const res = await fetch(`${API_BASE}/status`)
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      
      const data = await res.json()
      if (isMountedRef.current) {
        setStatus(data)
        setBackendOnline(true)
        errorCountRef.current = 0
      }
    } catch (e) {
      errorCountRef.current++
      if (errorCountRef.current >= MAX_RETRIES && isMountedRef.current) {
        setBackendOnline(false)
        console.error('Backend connection lost', e)
      }
    }
  }, [])

  const fetchPorts = useCallback(async () => {
    if (!isMountedRef.current) return
    
    try {
      const res = await fetch(`${API_BASE}/ports`)
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      
      const data = await res.json()
      console.log('Ports response:', data)
      if (isMountedRef.current && Array.isArray(data.ports)) {
        setPorts(data.ports)
      }
    } catch (e) {
      console.error('Failed to fetch ports', e)
    }
  }, [])

  const api = useCallback(async (endpoint: string, method = 'POST', body?: object) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      })
      
      const data = await res.json()
      if (!data.success && data.message) {
        log(`Error: ${data.message}`)
      }
      await fetchStatus()
      return data
    } catch (e) {
      log(`Request failed: ${e}`)
      return { success: false }
    } finally {
      if (isMountedRef.current) {
        setLoading(false)
      }
    }
  }, [fetchStatus, log])

  // Initial fetch and polling
  useEffect(() => {
    isMountedRef.current = true
    
    // Fetch immediately and retry after short delay if empty
    const initPorts = async () => {
      await fetchPorts()
      // Retry after 1 second if ports are empty (backend might not be ready yet)
      setTimeout(fetchPorts, 1000)
    }
    
    initPorts()
    fetchStatus()
    
    // Poll status periodically
    const statusInterval = setInterval(fetchStatus, POLL_INTERVAL)
    // Refresh ports less frequently
    const portsInterval = setInterval(fetchPorts, 10000)
    
    return () => {
      isMountedRef.current = false
      clearInterval(statusInterval)
      clearInterval(portsInterval)
    }
  }, [fetchPorts, fetchStatus])

  return {
    status,
    ports,
    loading,
    logs,
    log,
    api,
    fetchPorts,
    fetchStatus,
    backendOnline,
  }
}
