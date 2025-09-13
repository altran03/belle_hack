import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Head from 'next/head'
import Link from 'next/link'
import { ArrowLeftIcon, BugAntIcon, CheckCircleIcon, ClipboardDocumentCheckIcon } from '@heroicons/react/24/outline'

interface TestSpriteResult {
  passed: boolean
  total_tests: number
  failed_tests: number
  diagnostics: string[]
  error_details?: string
  execution_time: number
  requires_manual_config?: boolean
  static_analysis_fallback?: TestSpriteResult
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
  testsprite_result?: TestSpriteResult
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
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/jobs/${jobId}`)
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
                <h2 className="text-lg font-semibold mb-4 text-black">TestSprite Results</h2>
                {job.testsprite_result ? (
                  <div className="space-y-4">
                    {/* Display TestSprite results */}
                    {job.testsprite_result.requires_manual_config ? (
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                        <div className="flex items-center mb-3">
                          <span className="text-yellow-600 text-lg mr-2">⏳</span>
                          <h3 className="font-medium text-yellow-900">TestSprite Analysis Running</h3>
                        </div>
                        <p className="text-yellow-800">
                          TestSprite is currently analyzing your code. Results will appear here shortly.
                        </p>
                      </div>
                    ) : (
                      /* Normal TestSprite results */
                      <div className="space-y-4">
                        <div className="flex items-center">
                          <span className={`text-lg font-medium ${
                            job.testsprite_result.passed ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {job.testsprite_result.passed ? '✅ PASSED' : '❌ FAILED'}
                          </span>
                          <span className="ml-4 text-black">
                            {job.testsprite_result.total_tests} tests, {job.testsprite_result.failed_tests} failed
                          </span>
                        </div>
                        {job.testsprite_result.diagnostics && job.testsprite_result.diagnostics.length > 0 && (
                          <div>
                            <h3 className="font-medium mb-2 text-black">Diagnostics:</h3>
                            <div className="bg-gray-50 rounded p-3 text-sm">
                              <pre className="whitespace-pre-wrap text-black">{job.testsprite_result.diagnostics.join('\n')}</pre>
                            </div>
                          </div>
                        )}
                        {job.testsprite_result.error_details && (
                          <div>
                            <h3 className="font-medium mb-2 text-black">Error Details:</h3>
                            <div className="bg-red-50 rounded p-3 text-sm text-red-700">
                              {job.testsprite_result.error_details}
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
                        <h3 className="font-medium mb-2 text-black">Bugs Detected:</h3>
                        <ul className="list-disc list-inside text-sm text-black">
                          {job.gemini_analysis.bugs_detected.map((bug: string, index: number) => (
                            <li key={index}>{bug}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {job.gemini_analysis.optimizations && job.gemini_analysis.optimizations.length > 0 && (
                      <div>
                        <h3 className="font-medium mb-2 text-black">Optimizations:</h3>
                        <ul className="list-disc list-inside text-sm text-black">
                          {job.gemini_analysis.optimizations.map((opt: string, index: number) => (
                            <li key={index}>{opt}</li>
                          ))}
                        </ul>
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