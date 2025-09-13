import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Head from 'next/head'
import Link from 'next/link'
import { ArrowLeftIcon, BugAntIcon, CheckCircleIcon } from '@heroicons/react/24/outline'

interface Job {
  id: string
  commit_sha: string
  commit_message?: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  testsprite_total_tests?: number
  testsprite_passed?: boolean
  testsprite_failed_tests?: number
  testsprite_diagnostics?: string
  gemini_issue_summary?: string
  gemini_bugs_detected?: string
  gemini_patch?: string
}

export default function JobDetails() {
  const router = useRouter()
  const { id } = router.query
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)

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
                  <h1 className="text-2xl font-bold text-gray-900 mb-2">
                    Job {job.id.substring(0, 8)}
                  </h1>
                  <p className="text-gray-600 mb-4">
                    Commit: <code className="bg-gray-100 px-2 py-1 rounded">{job.commit_sha.substring(0, 8)}</code>
                  </p>
                  {job.commit_message && (
                    <p className="text-gray-700 mb-2">{job.commit_message}</p>
                  )}
                </div>
                <div className="text-right">
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    job.status === 'completed' ? 'bg-green-100 text-green-800' :
                    job.status === 'failed' ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {job.status}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg shadow">
              <div className="p-6">
                <h2 className="text-lg font-semibold mb-4">TestSprite Results</h2>
                {job.testsprite_total_tests !== undefined ? (
                  <div className="space-y-4">
                    <div className="flex items-center">
                      <span className={`text-lg font-medium ${
                        job.testsprite_passed ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {job.testsprite_passed ? '✅ PASSED' : '❌ FAILED'}
                      </span>
                      <span className="ml-4 text-gray-600">
                        {job.testsprite_total_tests} tests, {job.testsprite_failed_tests} failed
                      </span>
                    </div>
                    {job.testsprite_diagnostics && (
                      <div>
                        <h3 className="font-medium mb-2">Diagnostics:</h3>
                        <div className="bg-gray-50 rounded p-3 text-sm">
                          <pre className="whitespace-pre-wrap">{job.testsprite_diagnostics}</pre>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-gray-500">No test results available</p>
                )}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow">
              <div className="p-6">
                <h2 className="text-lg font-semibold mb-4">AI Analysis</h2>
                {job.gemini_issue_summary ? (
                  <div className="space-y-4">
                    <div>
                      <h3 className="font-medium mb-2">Issue Summary:</h3>
                      <p className="text-gray-700">{job.gemini_issue_summary}</p>
                    </div>
                    
                    {job.gemini_bugs_detected && (
                      <div>
                        <h3 className="font-medium mb-2">Bugs Detected:</h3>
                        <ul className="list-disc list-inside text-sm text-gray-700">
                          {(() => {
                            try {
                              const bugs = JSON.parse(job.gemini_bugs_detected)
                              return Array.isArray(bugs) ? bugs.map((bug: string, index: number) => (
                                <li key={index}>{bug}</li>
                              )) : <li>{job.gemini_bugs_detected}</li>
                            } catch {
                              return <li>{job.gemini_bugs_detected}</li>
                            }
                          })()}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-gray-500">No analysis available</p>
                )}
              </div>
            </div>
          </div>

          {job.gemini_patch && (
            <div className="mt-6 bg-white rounded-lg shadow">
              <div className="p-6">
                <h2 className="text-lg font-semibold mb-4">Generated Patch</h2>
                <div className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto">
                  <pre className="text-sm">{job.gemini_patch}</pre>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </>
  )
}