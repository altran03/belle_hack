import { useState, useEffect } from 'react'

interface LogStreamProps {
  jobId: string
}

interface LogEntry {
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'success'
  message: string
}

export default function LogStream({ jobId }: LogStreamProps) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    // Mock log entries for now
    const mockLogs: LogEntry[] = [
      {
        timestamp: new Date().toISOString(),
        level: 'info',
        message: 'Starting analysis pipeline...'
      },
      {
        timestamp: new Date().toISOString(),
        level: 'info',
        message: 'Fetching commit details from GitHub...'
      },
      {
        timestamp: new Date().toISOString(),
        level: 'success',
        message: 'Commit downloaded successfully'
      },
      {
        timestamp: new Date().toISOString(),
        level: 'info',
        message: 'Running TestSprite analysis...'
      },
      {
        timestamp: new Date().toISOString(),
        level: 'warning',
        message: 'Found 3 potential issues in the code'
      },
      {
        timestamp: new Date().toISOString(),
        level: 'info',
        message: 'Generating AI-powered patch...'
      },
      {
        timestamp: new Date().toISOString(),
        level: 'success',
        message: 'Analysis completed successfully'
      }
    ]

    setLogs(mockLogs)
    setConnected(true)

    // In a real implementation, you would connect to WebSocket here
    // const ws = new WebSocket(`ws://localhost:8000/ws/${jobId}`)
    // ws.onmessage = (event) => {
    //   const logEntry = JSON.parse(event.data)
    //   setLogs(prev => [...prev, logEntry])
    // }
    // ws.onopen = () => setConnected(true)
    // ws.onclose = () => setConnected(false)

    return () => {
      // ws.close()
    }
  }, [jobId])

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'success':
        return 'text-green-600 bg-green-100'
      case 'warning':
        return 'text-yellow-600 bg-yellow-100'
      case 'error':
        return 'text-red-600 bg-red-100'
      default:
        return 'text-blue-600 bg-blue-100'
    }
  }

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'success':
        return '✅'
      case 'warning':
        return '⚠️'
      case 'error':
        return '❌'
      default:
        return 'ℹ️'
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">Job Logs</h3>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className="text-sm text-gray-500">
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
      
      <div className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-y-auto">
        {logs.length === 0 ? (
          <p className="text-gray-400 text-center py-4">No logs available</p>
        ) : (
          <div className="space-y-2">
            {logs.map((log, index) => (
              <div key={index} className="flex items-start space-x-3">
                <span className="text-gray-500 text-sm font-mono">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${getLevelColor(log.level)}`}>
                  {getLevelIcon(log.level)} {log.level.toUpperCase()}
                </span>
                <span className="text-gray-300 text-sm">{log.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}