import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Head from 'next/head'
import Link from 'next/link'
import { ArrowLeftIcon, BugAntIcon, CheckCircleIcon, ClipboardDocumentCheckIcon } from '@heroicons/react/24/outline'

interface PytestResult {
  passed: boolean
  total_tests: number
  failed_tests: number
  diagnostics: string[]
  error_details?: string
  execution_time: number
}

interface GeminiAnalysis {
  issue_summary: string
  bugs_detected: string[]
  optimizations: string[]
  patch: string
  deployable_status: string
  confidence_score: number
}

interface Commit {
  sha: string
  message: string
  author: string
  author_email: string
  timestamp: string
  url: string
}

interface Job {
  id: string
  commit_sha: string
  commit_message?: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'ready_for_review' | 'approved'
  pytest_result?: PytestResult
  gemini_analysis?: GeminiAnalysis
  commit?: Commit
  branch_name?: string
  pr_url?: string
  pr_number?: number
}

export default function JobDetails() {
  const router = useRouter()
  const { id } = router.query
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [approving, setApproving] = useState(false)

  useEffect(() => {
    if (id) {
      fetchJob(id as string)
    }
  }, [id])

  const fetchJob = async (jobId: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/jobs/${jobId}`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setJob(data)
      }
    } catch (error) {
      console.error('Error fetching job:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async () => {
    if (!job) return
    
    setApproving(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/jobs/${job.id}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      })
      
      if (response.ok) {
        const result = await response.json()
        alert(`✅ Pull request created successfully!\n\nPR URL: ${result.pr_url || 'Check your repository'}`)
        // Refresh job data
        await fetchJob(job.id)
      } else {
        const error = await response.json()
        alert(`❌ Failed to approve job: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Error approving job:', error)
      alert('❌ Failed to approve job. Please try again.')
    } finally {
      setApproving(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Job not found</h1>
          <Link href="/" className="text-blue-600 hover:text-blue-800">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  return (
    <>
      <Head>
        <title>Job {job.id} - BugSniper Pro</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <Link href="/" className="flex items-center text-gray-600 hover:text-gray-900">
                <ArrowLeftIcon className="h-5 w-5 mr-2" />
                Back to Dashboard
              </Link>
              <div className="flex items-center">
                <BugAntIcon className="h-8 w-8 text-blue-600" />
                <h1 className="ml-2 text-xl font-bold">BugSniper Pro</h1>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="p-6">
              <div className="flex justify-between items-start">
                <div>
                  <h1 className="text-2xl font-bold text-black mb-2">
                    Job {job.id.substring(0, 8)}
                  </h1>
                  <p className="text-black mb-4">
                    Commit: <code className="bg-gray-100 px-2 py-1 rounded text-black">{job.commit_sha.substring(0, 8)}</code>
                  </p>
                  {job.commit_message && (
                    <p className="text-black mb-2">{job.commit_message}</p>
                  )}
                </div>
                <div className="text-right">
                  <div className="flex flex-col items-end space-y-2">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      job.status === 'completed' ? 'bg-green-100 text-green-800' :
                      job.status === 'failed' ? 'bg-red-100 text-red-800' :
                      job.status === 'ready_for_review' ? 'bg-blue-100 text-blue-800' :
                      job.status === 'approved' ? 'bg-purple-100 text-purple-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {job.status.replace('_', ' ').toUpperCase()}
                    </span>
                    
                    {job.status === 'ready_for_review' && job.gemini_analysis?.patch && (
                      <button
                        onClick={handleApprove}
                        disabled={approving}
                        className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {approving ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                            Approving...
                          </>
                        ) : (
                          <>
                            <ClipboardDocumentCheckIcon className="h-4 w-4 mr-2" />
                            Approve & Create PR
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg shadow">
              <div className="p-6">
                <h2 className="text-lg font-semibold mb-4 text-black">Pytest Results</h2>
                {job.pytest_result ? (
                  <div className="space-y-4">
                    {/* Check if pytest requires manual configuration */}
                    {(job.pytest_result as any).requires_manual_config ? (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex items-center mb-3">
                          <span className="text-blue-600 text-lg mr-2">⚙️</span>
                          <h3 className="font-medium text-blue-900">Pytest Configuration Required</h3>
                        </div>
                        <p className="text-blue-800 mb-4">
                          Pytest requires manual configuration to run comprehensive tests. 
                          Click the button below to open the pytest configuration guide.
                        </p>
                        <button 
                          onClick={async () => {
                            try {
                              const response = await fetch(`/api/jobs/${job.id}/configure-pytest`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                credentials: 'include'
                              });
                              const data = await response.json();
                              if (data.config_url) {
                                window.open(data.config_url, '_blank');
                              }
                            } catch (error) {
                              console.error('Failed to configure pytest:', error);
                              // Fallback to direct URL
                              window.open('https://docs.pytest.org/en/stable/getting-started.html', '_blank');
                            }
                          }}
                          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium transition-colors"
                        >
                          Configure Pytest
                        </button>
                        
                        {/* Show static analysis fallback */}
                        {(job.pytest_result as any).static_analysis_fallback && (
                          <div className="mt-4 pt-4 border-t border-blue-200">
                            <h4 className="font-medium text-blue-900 mb-2">Quick Analysis (Static):</h4>
                            <div className="text-sm text-blue-800">
                              <p>Found {(job.pytest_result as any).static_analysis_fallback.failed_tests} issues in {(job.pytest_result as any).static_analysis_fallback.total_tests} files</p>
                              <p className="mt-1 text-xs">For comprehensive testing, please configure pytest above.</p>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      /* Normal pytest results */
                      <div className="space-y-4">
                        <div className="flex items-center">
                          <span className={`text-lg font-medium ${
                            job.pytest_result.passed ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {job.pytest_result.passed ? '✅ PASSED' : '❌ FAILED'}
                          </span>
                          <span className="ml-4 text-black">
                            {job.pytest_result.total_tests} tests, {job.pytest_result.failed_tests} failed
                          </span>
                        </div>
                        {job.pytest_result.diagnostics && job.pytest_result.diagnostics.length > 0 && (
                          <div>
                            <h3 className="font-medium mb-2 text-black">Diagnostics:</h3>
                            <div className="bg-gray-50 rounded p-3 text-sm">
                              <pre className="whitespace-pre-wrap text-black">{job.pytest_result.diagnostics.join('\n')}</pre>
                            </div>
                          </div>
                        )}
                        {job.pytest_result.error_details && (
                          <div>
                            <h3 className="font-medium mb-2 text-black">Error Details:</h3>
                            <div className="bg-red-50 rounded p-3 text-sm text-red-700">
                              {job.pytest_result.error_details}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-black">No test results available</p>
                )}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow">
              <div className="p-6">
                <h2 className="text-lg font-semibold mb-4 text-black">AI Analysis</h2>
                {job.gemini_analysis ? (
                  <div className="space-y-4">
                    <div>
                      <h3 className="font-medium mb-2 text-black">Issue Summary:</h3>
                      <p className="text-black">{job.gemini_analysis.issue_summary}</p>
                    </div>
                    
                    {job.gemini_analysis.bugs_detected && job.gemini_analysis.bugs_detected.length > 0 && (
                      <div>
                        <h3 className="font-medium mb-3 text-black">Bugs Detected ({job.gemini_analysis.bugs_detected.length}):</h3>
                        
                        {/* Scrollable container for bugs */}
                        <div className="max-h-96 overflow-y-auto border border-gray-200 rounded-lg p-4 bg-gray-50">
                          {/* Group bugs by severity */}
                          {(() => {
                            const bugsBySeverity = job.gemini_analysis.bugs_detected.reduce((acc: any, bug: any) => {
                              if (typeof bug === 'string') {
                                if (!acc['other']) acc['other'] = [];
                                acc['other'].push(bug);
                              } else {
                                const severity = bug.severity || 'unknown';
                                if (!acc[severity]) acc[severity] = [];
                                acc[severity].push(bug);
                              }
                              return acc;
                            }, {});

                            const severityOrder = ['critical', 'high', 'medium', 'low', 'other'];
                            const severityLabels = {
                              'critical': '🔴 Critical Issues',
                              'high': '🟠 High Severity',
                              'medium': '🟡 Medium Severity', 
                              'low': '🟢 Low Severity',
                              'other': '📝 Other Issues'
                            };

                            return severityOrder.map(severity => {
                              if (!bugsBySeverity[severity] || bugsBySeverity[severity].length === 0) return null;
                              
                              return (
                                <div key={severity} className="mb-4">
                                  <h4 className="font-medium text-sm mb-2 text-gray-700">
                                    {severityLabels[severity as keyof typeof severityLabels]} ({bugsBySeverity[severity].length})
                                  </h4>
                                  <div className="space-y-2 ml-4">
                                    {bugsBySeverity[severity].map((bug: any, index: number) => {
                                      if (typeof bug === 'string') {
                                        return (
                                          <div key={index} className="flex items-start space-x-2 text-sm">
                                            <span className="text-gray-500 font-bold">•</span>
                                            <span className="text-black">{bug}</span>
                                          </div>
                                        );
                                      } else {
                                        const severityColors = {
                                          'critical': 'border-red-200 bg-red-50',
                                          'high': 'border-orange-200 bg-orange-50',
                                          'medium': 'border-yellow-200 bg-yellow-50',
                                          'low': 'border-blue-200 bg-blue-50'
                                        };
                                        const severityColor = severityColors[bug.severity as keyof typeof severityColors] || 'border-gray-200 bg-gray-50';
                                        
                                        return (
                                          <div key={index} className={`border rounded-lg p-3 ${severityColor}`}>
                                            <div className="flex items-center space-x-2 text-sm mb-1">
                                              <span className="font-semibold text-gray-800">
                                                {bug.type?.replace('_', ' ').toUpperCase()}
                                              </span>
                                              {bug.file && bug.file !== 'unknown' && (
                                                <>
                                                  <span className="text-gray-400">•</span>
                                                  <span className="text-gray-600 font-mono text-xs">
                                                    {bug.file}:{bug.line}
                                                  </span>
                                                </>
                                              )}
                                            </div>
                                            <div className="text-sm text-gray-800 mb-1">
                                              {bug.description}
                                            </div>
                                            {bug.impact && (
                                              <div className="text-xs text-gray-600">
                                                <strong>Impact:</strong> {bug.impact}
                                              </div>
                                            )}
                                            {bug.reproduction && (
                                              <div className="text-xs text-gray-600 mt-1">
                                                <strong>Reproduction:</strong> {bug.reproduction}
                                              </div>
                                            )}
                                          </div>
                                        );
                                      }
                                    })}
                                  </div>
                                </div>
                              );
                            });
                          })()}
                        </div>
                      </div>
                    )}

                    {job.gemini_analysis.optimizations && job.gemini_analysis.optimizations.length > 0 && (
                      <div>
                        <h3 className="font-medium mb-3 text-black">Optimizations ({job.gemini_analysis.optimizations.length}):</h3>
                        
                        {/* Scrollable container for optimizations */}
                        <div className="max-h-80 overflow-y-auto border border-gray-200 rounded-lg p-4 bg-gray-50">
                          <div className="space-y-3">
                            {job.gemini_analysis.optimizations.map((opt: any, index: number) => {
                              // Handle both old string format and new object format
                              if (typeof opt === 'string') {
                                return (
                                  <div key={index} className="flex items-start space-x-2 text-sm">
                                    <span className="text-green-500 font-bold">•</span>
                                    <span className="text-black">{opt}</span>
                                  </div>
                                );
                              } else {
                                return (
                                  <div key={index} className="border border-green-200 bg-green-50 rounded-lg p-3">
                                    <div className="flex items-center space-x-2 text-sm mb-2">
                                      <span className="text-green-600 font-semibold">
                                        {opt.type?.replace('_', ' ').toUpperCase()}
                                      </span>
                                      {opt.file && opt.file !== 'unknown' && (
                                        <>
                                          <span className="text-gray-400">•</span>
                                          <span className="text-gray-600 font-mono text-xs">
                                            {opt.file}:{opt.line}
                                          </span>
                                        </>
                                      )}
                                    </div>
                                    <div className="text-sm text-gray-800">
                                      <div className="font-medium mb-1">
                                        💡 {opt.suggested_approach}
                                      </div>
                                      {opt.current_approach && (
                                        <div className="text-xs text-gray-600 mb-1">
                                          <strong>Current:</strong> {opt.current_approach}
                                        </div>
                                      )}
                                      {opt.benefit && (
                                        <div className="text-xs text-green-700">
                                          <strong>Benefit:</strong> {opt.benefit}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                );
                              }
                            })}
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-between text-sm">
                      <span className="text-black">
                        Deployable: <span className={`font-medium ${
                          job.gemini_analysis.deployable_status === 'deployable' ? 'text-green-600' :
                          job.gemini_analysis.deployable_status === 'not_deployable' ? 'text-red-600' :
                          'text-yellow-600'
                        }`}>
                          {job.gemini_analysis.deployable_status.toUpperCase()}
                        </span>
                      </span>
                      <span className="text-black">
                        Confidence: <span className="font-medium text-black">{Math.round(job.gemini_analysis.confidence_score * 100)}%</span>
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="text-black">No analysis available</p>
                )}
              </div>
            </div>
          </div>

          {job.gemini_analysis?.patch && (
            <div className="mt-6 bg-white rounded-lg shadow">
              <div className="p-6">
                <h2 className="text-lg font-semibold mb-4 text-black">Generated Patch</h2>
                <div className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto">
                  <pre className="text-sm">{job.gemini_analysis.patch}</pre>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </>
  )
}