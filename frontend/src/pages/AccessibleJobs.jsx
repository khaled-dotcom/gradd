import { useState, useEffect } from 'react';
import { Heart, RefreshCw } from 'lucide-react';
import JobCard from '../components/JobCard';
import ApplicationModal from '../components/ApplicationModal';
import { jobAPI } from '../api/api';
import { handleAPIError } from '../api/api';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';

const AccessibleJobs = () => {
  const { user } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [showApplicationModal, setShowApplicationModal] = useState(false);

  const loadJobs = async () => {
    setLoading(true);
    try {
      const response = await jobAPI.getAccessibleJobs();
      setJobs(response.data?.results || []);
    } catch (error) {
      handleAPIError(error);
      setJobs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      loadJobs();
    }
  }, [user]);

  if (!user) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Sign in to browse inclusive job listings from Egypt.
        </p>
        <Link to="/login" className="btn-primary">
          Log in
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Heart className="h-8 w-8 text-accent" aria-hidden="true" />
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                Accessible Jobs
              </h1>
            </div>
            <p className="text-gray-600 dark:text-gray-400 max-w-2xl">
              Roles from Egyptian job boards that mention disability inclusion, remote
              flexibility, or accessible workplaces. Apply only through EmpowerWork — we
              never redirect you to external application forms.
            </p>
          </div>
          <button
            type="button"
            onClick={loadJobs}
            className="btn-secondary flex items-center gap-2 self-start"
            aria-label="Refresh job list"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="text-center py-16">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-accent" />
            <p className="mt-4 text-gray-600 dark:text-gray-400">Loading jobs…</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="card text-center py-12">
            <p className="text-gray-600 dark:text-gray-400">
              No accessible-focused jobs yet. The data pipeline imports new listings
              automatically when Azure is running.
            </p>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onApply={(j) => {
                  setSelectedJob(j);
                  setShowApplicationModal(true);
                }}
              />
            ))}
          </div>
        )}
      </div>

      {showApplicationModal && selectedJob && (
        <ApplicationModal
          job={selectedJob}
          onClose={() => {
            setShowApplicationModal(false);
            setSelectedJob(null);
          }}
        />
      )}
    </div>
  );
};

export default AccessibleJobs;
