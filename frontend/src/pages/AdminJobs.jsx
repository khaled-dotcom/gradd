import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import Table from '../components/Table';
import JobForm from '../components/JobForm';
import { jobAPI } from '../api/api';
import { handleAPIError } from '../api/api';
import toast from 'react-hot-toast';
import { Plus, X, RefreshCw, Database, Briefcase, FileText } from 'lucide-react';

const AdminJobs = () => {
  const { user, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingJob, setEditingJob] = useState(null);
  const [importStatus, setImportStatus] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [importLoading, setImportLoading] = useState(false);

  useEffect(() => {
    if (!user || !isAdmin()) {
      navigate('/');
      return;
    }
    fetchJobs();
    fetchImportData();
  }, [user, isAdmin, navigate]);

  const fetchImportData = async () => {
    if (!user?.id) return;
    try {
      const [statusRes, dashRes] = await Promise.all([
        jobAPI.getImportStatus(user.id),
        jobAPI.getImportDashboard(user.id),
      ]);
      setImportStatus(statusRes.data);
      setDashboard(dashRes.data);
    } catch {
      setImportStatus(null);
      setDashboard(null);
    }
  };

  const handleTriggerImport = async () => {
    if (!user?.id) return;
    setImportLoading(true);
    try {
      await jobAPI.triggerImport(user.id);
      toast.success('Job import pipeline started (admin only)');
      setTimeout(fetchImportData, 5000);
    } catch (error) {
      handleAPIError(error);
    } finally {
      setImportLoading(false);
    }
  };

  const fetchJobs = async () => {
    if (!user?.id) return;
    setLoading(true);
    try {
      const response = await jobAPI.getAllJobs({
        active_only: false,
        admin_user_id: user.id,
        limit: 200,
      });
      setJobs(response.data?.results || []);
    } catch (error) {
      handleAPIError(error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (job) => {
    setEditingJob(job);
    setShowForm(true);
  };

  const handleDelete = async (jobId) => {
    if (!window.confirm('Are you sure you want to delete this job?')) return;
    try {
      await jobAPI.deleteJob(jobId);
      toast.success('Job deleted successfully');
      fetchJobs();
    } catch (error) {
      handleAPIError(error);
    }
  };

  const handleSubmit = async (formData) => {
    try {
      if (editingJob) {
        await jobAPI.updateJob(editingJob.id, formData);
        toast.success('Job updated successfully');
      } else {
        await jobAPI.addJob(formData);
        toast.success('Job created successfully');
      }
      setShowForm(false);
      setEditingJob(null);
      fetchJobs();
    } catch (error) {
      throw error;
    }
  };

  const columns = [
    { key: 'id', label: 'ID' },
    { key: 'title', label: 'Title' },
    {
      key: 'company_name',
      label: 'Company',
      render: (value) => value || '-',
    },
    {
      key: 'location_city',
      label: 'Location',
      render: (value, row) =>
        value
          ? `${value}${row.location_country ? `, ${row.location_country}` : ''}`
          : '-',
    },
    {
      key: 'source',
      label: 'Source',
      render: (value) => value || 'manual',
    },
    {
      key: 'source_url',
      label: 'External URL',
      render: (value) =>
        value ? (
          <a
            href={value}
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent text-xs truncate max-w-[120px] inline-block"
          >
            audit
          </a>
        ) : (
          '—'
        ),
    },
    {
      key: 'is_active',
      label: 'Active',
      render: (value) => (value !== false ? 'Yes' : 'No'),
    },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading jobs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              Manage Jobs
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              استيراد يدوي (أدمن فقط) · تحديث تلقائي كل 8 ساعات عبر Airflow
            </p>
          </div>
          <button
            onClick={() => {
              setEditingJob(null);
              setShowForm(true);
            }}
            className="btn-primary flex items-center space-x-2"
          >
            <Plus className="h-4 w-4" />
            <span>Add Job</span>
          </button>
        </div>

        {dashboard && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="card">
              <Briefcase className="h-5 w-5 text-accent mb-2" />
              <p className="text-sm text-gray-500">وظائف نشطة</p>
              <p className="text-2xl font-bold">{dashboard.total_active_jobs}</p>
            </div>
            <div className="card">
              <FileText className="h-5 w-5 text-accent mb-2" />
              <p className="text-sm text-gray-500">طلبات على موقعنا</p>
              <p className="text-2xl font-bold">{dashboard.total_applications}</p>
              <p className="text-xs text-gray-500">
                {dashboard.pending_applications} pending
              </p>
            </div>
            <div className="card col-span-1 sm:col-span-2">
              <p className="text-sm text-gray-500 mb-1">حسب المصدر</p>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {Object.entries(dashboard.jobs_by_source || {})
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(' · ') || '—'}
              </p>
            </div>
          </div>
        )}

        <div className="card mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-start gap-3">
              <Database className="h-6 w-6 text-accent mt-1" />
              <div>
                <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                  استيراد وظائف السوفتوير (Wuzzuf · Forasna · LinkedIn)
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  التحديث التلقائي: كل 8 ساعات (Airflow). الزر أدناه للأدمن فقط.
                </p>
                {importStatus && importStatus.status !== 'no_runs' && (
                  <p className="text-sm mt-2 text-gray-700 dark:text-gray-300">
                    آخر تشغيل: <strong>{importStatus.status}</strong>
                    {importStatus.added != null && ` · +${importStatus.added}`}
                    {importStatus.updated != null && ` · ${importStatus.updated} محدّث`}
                    {importStatus.finished_at &&
                      ` · ${new Date(importStatus.finished_at).toLocaleString()}`}
                  </p>
                )}
                <Link to="/how-it-works" className="text-sm text-accent hover:underline mt-1 inline-block">
                  كيف يعمل التقديم على الموقع؟
                </Link>
              </div>
            </div>
            <button
              type="button"
              onClick={handleTriggerImport}
              disabled={importLoading}
              className="btn-secondary flex items-center gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${importLoading ? 'animate-spin' : ''}`} />
              Run import now (admin)
            </button>
          </div>
        </div>

        {showForm && (
          <div className="card mb-8">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {editingJob ? 'Edit Job' : 'Add New Job'}
              </h2>
              <button
                onClick={() => {
                  setShowForm(false);
                  setEditingJob(null);
                }}
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <JobForm
              job={editingJob}
              onSubmit={handleSubmit}
              onCancel={() => {
                setShowForm(false);
                setEditingJob(null);
              }}
            />
          </div>
        )}

        <div className="card">
          <Table
            data={jobs}
            columns={columns}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        </div>
      </div>
    </div>
  );
};

export default AdminJobs;
