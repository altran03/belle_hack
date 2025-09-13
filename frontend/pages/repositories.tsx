import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Navigation from '../components/Navigation';

interface Repository {
  id: number;
  name: string;
  full_name: string;
  description: string;
  private: boolean;
  language: string;
  updated_at: string;
  is_monitored: boolean;
}

interface GitHubRepo {
  id: number;
  name: string;
  full_name: string;
  description: string;
  private: boolean;
  language: string;
  updated_at: string;
}

export default function RepositoriesPage() {
  const router = useRouter();
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [monitoredRepos, setMonitoredRepos] = useState<Repository[]>([]);
  const [selectedRepos, setSelectedRepos] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchRepositories();
  }, []);

  const fetchRepositories = async () => {
    try {
      setLoading(true);
      const [githubReposResponse, monitoredReposResponse] = await Promise.all([
        fetch('/api/github/repositories'),
        fetch('/api/repositories')
      ]);

      if (!githubReposResponse.ok || !monitoredReposResponse.ok) {
        throw new Error('Failed to fetch repositories');
      }

      const githubRepos = await githubReposResponse.json();
      const monitored = await monitoredReposResponse.json();

      setRepos(githubRepos);
      setMonitoredRepos(monitored);
      
      // Pre-select already monitored repositories
      const monitoredSet = new Set<string>(monitored.map((repo: Repository) => repo.full_name));
      setSelectedRepos(monitoredSet);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch repositories');
    } finally {
      setLoading(false);
    }
  };

  const handleRepoToggle = (fullName: string) => {
    const newSelected = new Set(selectedRepos);
    if (newSelected.has(fullName)) {
      newSelected.delete(fullName);
    } else {
      newSelected.add(fullName);
    }
    setSelectedRepos(newSelected);
  };

  const handleSaveSelection = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);

      // Get repositories to add and remove
      const currentlyMonitored = new Set(monitoredRepos.map(repo => repo.full_name));
      const toAdd = Array.from(selectedRepos).filter(name => !currentlyMonitored.has(name));
      const toRemove = Array.from(currentlyMonitored).filter(name => !selectedRepos.has(name));

      let addedCount = 0;
      let removedCount = 0;

      // Add new repositories
      for (const fullName of toAdd) {
        const [owner, repoName] = fullName.split('/');
        const response = await fetch('/api/repositories/monitor', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ owner, repo: repoName }),
        });
        
        if (response.ok) {
          addedCount++;
        } else {
          const errorData = await response.json();
          throw new Error(`Failed to add ${fullName}: ${errorData.detail || 'Unknown error'}`);
        }
      }

      // Remove repositories
      for (const fullName of toRemove) {
        const repo = monitoredRepos.find(r => r.full_name === fullName);
        if (repo) {
          const response = await fetch(`/api/repositories/${repo.id}/unmonitor`, {
            method: 'DELETE',
          });
          
          if (response.ok) {
            removedCount++;
          } else {
            const errorData = await response.json();
            throw new Error(`Failed to remove ${fullName}: ${errorData.detail || 'Unknown error'}`);
          }
        }
      }

      // Refresh the page to get updated data
      await fetchRepositories();
      
      // Show success message
      if (addedCount > 0 || removedCount > 0) {
        setSuccessMessage(`Successfully updated monitoring: ${addedCount} repositories added, ${removedCount} repositories removed`);
      } else {
        setSuccessMessage('No changes were made');
      }
      
      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save selection');
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading repositories...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Repository Selection</h1>
              <p className="mt-2 text-gray-600">
                Choose which repositories you want BugSniper to monitor for bugs
              </p>
            </div>
            <button
              onClick={() => router.back()}
              className="px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              ← Back
            </button>
          </div>
        </div>

        {/* Success Message */}
        {successMessage && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-md p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-green-800">Success</h3>
                <div className="mt-2 text-sm text-green-700">{successMessage}</div>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <div className="mt-2 text-sm text-red-700">{error}</div>
              </div>
            </div>
          </div>
        )}

        {/* Stats */}
        <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Total Repositories</p>
                <p className="text-2xl font-semibold text-gray-900">{repos.length}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Selected</p>
                <p className="text-2xl font-semibold text-gray-900">{selectedRepos.size}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Currently Monitored</p>
                <p className="text-2xl font-semibold text-gray-900">{monitoredRepos.length}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Repository List */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">Your Repositories</h3>
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => setSelectedRepos(new Set(repos.map(repo => repo.full_name)))}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  Select All
                </button>
                <button
                  onClick={() => setSelectedRepos(new Set())}
                  className="text-sm text-gray-600 hover:text-gray-800"
                >
                  Clear All
                </button>
              </div>
            </div>
          </div>
          
          <div className="divide-y divide-gray-200">
            {repos.map((repo) => {
              const isSelected = selectedRepos.has(repo.full_name);
              const isMonitored = monitoredRepos.some(r => r.full_name === repo.full_name);
              
              return (
                <div
                  key={repo.id}
                  className={`px-6 py-4 hover:bg-gray-50 transition-colors ${
                    isSelected ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleRepoToggle(repo.full_name)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <h4 className="text-sm font-medium text-gray-900 truncate">
                            {repo.full_name}
                          </h4>
                          {repo.private && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                              Private
                            </span>
                          )}
                          {isMonitored && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                              Monitored
                            </span>
                          )}
                        </div>
                        
                        {repo.description && (
                          <p className="mt-1 text-sm text-gray-500 truncate">
                            {repo.description}
                          </p>
                        )}
                        
                        <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                          {repo.language && (
                            <span className="flex items-center">
                              <div className="w-3 h-3 bg-blue-500 rounded-full mr-1"></div>
                              {repo.language}
                            </span>
                          )}
                          <span>Updated {formatDate(repo.updated_at)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Save Button */}
        <div className="mt-8 flex justify-end">
          <button
            onClick={handleSaveSelection}
            disabled={saving}
            className={`px-6 py-3 rounded-md font-medium transition-colors ${
              saving
                ? 'bg-gray-400 text-white cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500'
            }`}
          >
            {saving ? 'Saving...' : `Save Selection (${selectedRepos.size} repositories)`}
          </button>
        </div>
      </div>
    </div>
  );
}