import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Head from 'next/head'
import Link from 'next/link'
import { ArrowLeftIcon, BugAntIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'

interface Repository {
  id: number
  github_id: number
  name: string
  full_name: string
  default_branch: string
  clone_url: string
  is_active: boolean
}

export default function Repositories() {
  const router = useRouter()
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [loading, setLoading] = useState(true)
  const [monitoring, setMonitoring] = useState<number | null>(null)

  useEffect(() => {
    const userId = localStorage.getItem('user_id')
    if (!userId) {
      router.push('/auth/login')
      return
    }
    fetchRepositories(parseInt(userId))
  }, [router])

  const fetchRepositories = async (userId: number) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/repositories?user_id=${userId}`)
      if (response.ok) {
        const data = await response.json()
        setRepositories(data)
      }
    } catch (error) {
      console.error('Error fetching repositories:', error)
    } finally {
      setLoading(false)
    }
  }

  const startMonitoring = async (repoId: number) => {
    setMonitoring(repoId)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/repositories/${repoId}/monitor`, {
        method: 'POST'
      })
      if (response.ok) {
        // Refresh repositories to show updated status
        const userId = localStorage.getItem('user_id')
        if (userId) {
          await fetchRepositories(parseInt(userId))
        }
        // Redirect to dashboard
        router.push('/')
      } else {
        console.error('Failed to start monitoring')
      }
    } catch (error) {
      console.error('Error starting monitoring:', error)
    } finally {
      setMonitoring(null)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('user_id')
    router.push('/auth/login')
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
        <title>Connect Repositories - BugSniper Pro</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <Link href="/" className="flex items-center text-gray-600 hover:text-gray-900">
                <ArrowLeftIcon className="h-5 w-5 mr-2" />
                Back to Dashboard
              </Link>
              <div className="flex items-center space-x-4">
                <div className="flex items-center">
                  <BugAntIcon className="h-8 w-8 text-blue-600" />
                  <h1 className="ml-2 text-xl font-bold">BugSniper Pro</h1>
                </div>
                <button
                  onClick={handleLogout}
                  className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-4">Connect Your Repositories</h1>
            <p className="text-gray-600">
              Select the repositories you want BugSniper Pro to monitor for bugs and issues.
            </p>
          </div>

          {repositories.length === 0 ? (
            <div className="text-center py-12">
              <BugAntIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">No repositories found</h3>
              <p className="text-gray-500 mb-4">
                Make sure you have repositories in your GitHub account and try again.
              </p>
              <button
                onClick={() => fetchRepositories(parseInt(localStorage.getItem('user_id') || '1'))}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg"
              >
                Refresh Repositories
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {repositories.map((repo) => (
                <div key={repo.id} className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 mb-1">
                        {repo.name}
                      </h3>
                      <p className="text-sm text-gray-500 mb-2">
                        {repo.full_name}
                      </p>
                      <p className="text-xs text-gray-400">
                        Default branch: {repo.default_branch}
                      </p>
                    </div>
                    {repo.is_active && (
                      <CheckCircleIcon className="h-6 w-6 text-green-500" />
                    )}
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      repo.is_active 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {repo.is_active ? 'Monitoring' : 'Not Monitoring'}
                    </span>
                    
                    {!repo.is_active && (
                      <button
                        onClick={() => startMonitoring(repo.id)}
                        disabled={monitoring === repo.id}
                        className={`px-4 py-2 rounded-lg text-sm font-medium ${
                          monitoring === repo.id
                            ? 'bg-gray-400 text-white cursor-not-allowed'
                            : 'bg-blue-600 text-white hover:bg-blue-700'
                        }`}
                      >
                        {monitoring === repo.id ? 'Starting...' : 'Start Monitoring'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {repositories.length > 0 && (
            <div className="mt-8 text-center">
              <Link
                href="/"
                className="bg-green-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-green-700"
              >
                Go to Dashboard
              </Link>
            </div>
          )}
        </main>
      </div>
    </>
  )
}
