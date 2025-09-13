import { useEffect } from 'react'
import { useRouter } from 'next/router'
import Head from 'next/head'
import { CheckCircleIcon, BugAntIcon } from '@heroicons/react/24/outline'

export default function AuthSuccess() {
  const router = useRouter()
  const { user_id } = router.query

  useEffect(() => {
    if (user_id) {
      // Store user ID in localStorage
      localStorage.setItem('user_id', user_id as string)
      
      // Redirect to dashboard after a short delay
      setTimeout(() => {
        router.push('/')
      }, 2000)
    }
  }, [user_id, router])

  return (
    <>
      <Head>
        <title>Authentication Successful - BugSniper Pro</title>
      </Head>

      <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="flex justify-center">
            <CheckCircleIcon className="h-16 w-16 text-green-500" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold text-gray-900">
            Authentication Successful!
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            You have successfully connected your GitHub account to BugSniper Pro.
          </p>
        </div>

        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
            <div className="text-center">
              <BugAntIcon className="h-12 w-12 text-blue-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Welcome to BugSniper Pro!
              </h3>
              <p className="text-sm text-gray-600 mb-6">
                Redirecting you to the dashboard...
              </p>
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
