import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface DiffViewerProps {
  patch: string
}

export default function DiffViewer({ patch }: DiffViewerProps) {
  const [showRaw, setShowRaw] = useState(false)

  const parsePatch = (patchContent: string) => {
    const lines = patchContent.split('\n')
    const files: { [key: string]: string[] } = {}
    let currentFile = ''
    
    lines.forEach(line => {
      if (line.startsWith('--- a/') || line.startsWith('+++ b/')) {
        const fileName = line.substring(6) // Remove '--- a/' or '+++ b/'
        if (!files[fileName]) {
          files[fileName] = []
          currentFile = fileName
        }
      } else if (currentFile) {
        files[currentFile].push(line)
      }
    })
    
    return files
  }

  const renderDiffLine = (line: string, index: number) => {
    const className = line.startsWith('+') ? 'text-green-400' : 
                     line.startsWith('-') ? 'text-red-400' : 
                     line.startsWith('@@') ? 'text-yellow-400' : 
                     'text-gray-300'
    
    return (
      <div key={index} className={`font-mono text-sm ${className}`}>
        {line}
      </div>
    )
  }

  if (showRaw) {
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-medium">Raw Patch</h3>
          <button
            onClick={() => setShowRaw(false)}
            className="text-blue-600 hover:text-blue-800"
          >
            Show Parsed View
          </button>
        </div>
        <div className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto">
          <pre className="text-sm whitespace-pre-wrap">{patch}</pre>
        </div>
      </div>
    )
  }

  const parsedFiles = parsePatch(patch)

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">Parsed Diff</h3>
        <button
          onClick={() => setShowRaw(true)}
          className="text-blue-600 hover:text-blue-800"
        >
          Show Raw Patch
        </button>
      </div>
      
      {Object.entries(parsedFiles).map(([fileName, lines]) => (
        <div key={fileName} className="border rounded-lg overflow-hidden">
          <div className="bg-gray-800 text-white px-4 py-2 font-medium">
            {fileName}
          </div>
          <div className="bg-gray-900 text-gray-100 p-4 overflow-x-auto">
            {lines.map((line, index) => renderDiffLine(line, index))}
          </div>
        </div>
      ))}
    </div>
  )
}