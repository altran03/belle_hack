import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Head from 'next/head'
import Link from 'next/link'
import { BugAntIcon, CheckCircleIcon, ExclamationTriangleIcon, ClockIcon, TrashIcon } from '@heroicons/react/24/outline'
import Navigation from '../components/Navigation'

export default function Dashboard() {
  const router = useRouter()
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [clearing, setClearing] = useState(false)

  useEffect(() => {
    const userId = localStorage.getItem('user_id')
    if (!userId) {
      router.push('/auth/login')
      return
    }
    fetchData(parseInt(userId))
  }, [router])

  const fetchData = async (userId: number) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/jobs?user_id=${userId}`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setJobs(data)
      }
    } catch (error) {
      console.error('Error fetching data:', error)
    } finally {
      setLoading(false)
    }
  }


  const handleClearHistory = async () => {
    const userId = localStorage.getItem('user_id')
    if (!userId) return

    if (!confirm('Are you sure you want to clear all job history? This action cannot be undone.')) {
      return
    }

    setClearing(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/jobs?user_id=${userId}`, {
        method: 'DELETE',
        credentials: 'include'
      })
      
      if (response.ok) {
        const result = await response.json()
        alert(`✅ Successfully cleared ${result.deleted_count} jobs from history`)
        // Refresh the jobs list
        await fetchData(parseInt(userId))
      } else {
        const error = await response.json()
        alert(`❌ Failed to clear job history: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Error clearing job history:', error)
      alert('❌ Failed to clear job history. Please try again.')
    } finally {
      setClearing(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <>
      <Head>
        <title>BugSniper Pro - Dashboard</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        <Navigation />
        
        {/* Clear History Button - positioned below navigation */}
        {jobs.length > 0 && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex justify-end">
              <button
                onClick={handleClearHistory}
                disabled={clearing}
                className="flex items-center bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {clearing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Clearing...
                  </>
                ) : (
                  <>
                    <TrashIcon className="h-4 w-4 mr-2" />
                    Clear History
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <svg className="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Total Jobs</p>
                  <p className="text-2xl font-semibold">{jobs.length}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow">
            <div className="p-6">
              <h2 className="text-lg font-semibold mb-4">Recent Jobs</h2>
              {jobs.length === 0 ? (
                <div className="text-center py-12">
                  <div className="h-12 w-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-medium mb-2">No jobs yet</h3>
                  <p className="text-gray-500 mb-4">
                    Connect your GitHub repositories to start monitoring.
                  </p>
                  <button
                    onClick={() => router.push('/repositories')}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg"
                  >
                    Connect Repositories
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {jobs.slice(0, 5).map((job: any) => (
                    <Link key={job.id} href={`/jobs/${job.id}`} className="block">
                      <div className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium">{job.commit_sha.substring(0, 8)}</p>
                            <p className="text-sm text-gray-500">{job.commit_message}</p>
                          </div>
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            job.status === 'completed' ? 'bg-green-100 text-green-800' :
                            job.status === 'failed' ? 'bg-red-100 text-red-800' :
                            job.status === 'ready_for_review' ? 'bg-blue-100 text-blue-800' :
                            job.status === 'approved' ? 'bg-purple-100 text-purple-800' :
                            'bg-yellow-100 text-yellow-800'
                          }`}>
                            {job.status.replace('_', ' ').toUpperCase()}
                          </span>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </>
  )
}