'use client';
import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi } from '@/lib/api';
import { useJobProgress } from '@/hooks/useJobProgress';
import { StatusBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { formatFileSize, formatDate, formatDuration, getStepLabel, downloadJSON, downloadCSV } from '@/lib/utils';
import { JobResult } from '@/types';
import {
  ArrowLeft, RefreshCw, Download, CheckCheck, RotateCcw,
  FileText, Cpu, Clock, BarChart3, Tag, AlignLeft, Edit3,
  Save, X, Wifi, WifiOff, ChevronRight
} from 'lucide-react';

const PROGRESS_STEPS = [
  { key: 'job_queued', label: 'Queued', pct: 0 },
  { key: 'job_started', label: 'Started', pct: 10 },
  { key: 'document_parsing_started', label: 'Parsing', pct: 20 },
  { key: 'document_parsing_completed', label: 'Parsed', pct: 50 },
  { key: 'field_extraction_started', label: 'Extracting', pct: 60 },
  { key: 'field_extraction_completed', label: 'Extracted', pct: 90 },
  { key: 'job_completed', label: 'Done', pct: 100 },
];

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const jobId = parseInt(id);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => documentsApi.detail(jobId).then(r => r.data),
    refetchInterval: (query) => {
      const s = (query.state.data as any)?.status;
      return s === 'processing' || s === 'queued' ? 2000 : false;
    },
  });

  const job = data?.job;
  const doc = data?.document;
  const isActive = job?.status === 'processing' || job?.status === 'queued';

  const { events, latestEvent, isConnected } = useJobProgress(isActive ? jobId : null, isActive);

  // Editing state
  const [editing, setEditing] = useState(false);
  const [editResult, setEditResult] = useState<Partial<JobResult>>({});

  useEffect(() => {
    if (job?.result && !editing) setEditResult(job.reviewed_result || job.result);
  }, [job?.result]);

  useEffect(() => {
    if (latestEvent) refetch();
  }, [latestEvent?.event]);

  const retryMutation = useMutation({
    mutationFn: () => documentsApi.retry(jobId),
    onSuccess: () => refetch(),
  });

  const saveMutation = useMutation({
    mutationFn: () => documentsApi.updateResult(jobId, editResult as Record<string, unknown>),
    onSuccess: () => { setEditing(false); refetch(); },
  });

  const finalizeMutation = useMutation({
    mutationFn: () => documentsApi.finalize(jobId),
    onSuccess: () => refetch(),
  });

  const handleExport = async (format: 'json' | 'csv') => {
    const { data: exp } = await documentsApi.exportDoc(jobId, format);
    if (format === 'json') downloadJSON(exp, `docflow-job-${jobId}.json`);
    else {
      const result = exp.result || {};
      const csv = Object.entries(result).map(([k, v]) =>
        `${k},"${String(v).replace(/"/g, '""')}"`
      ).join('\n');
      downloadCSV(`key,value\n${csv}`, `docflow-job-${jobId}.csv`);
    }
  };

  const currentStepIdx = PROGRESS_STEPS.findIndex(s => s.key === job?.current_step);

  if (isLoading) return (
    <div className="p-6 space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="skeleton h-24 rounded-xl" />
      ))}
    </div>
  );

  if (!job || !doc) return (
    <div className="p-6 text-center py-24">
      <p className="text-ink-muted">Job not found</p>
      <Button variant="secondary" size="sm" className="mt-4" onClick={() => router.push('/dashboard')}>
        Back to dashboard
      </Button>
    </div>
  );

  const displayResult = job.reviewed_result || job.result;

  return (
    <div className="p-6 space-y-5 max-w-4xl animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push('/dashboard')}
            className="text-ink-faint hover:text-ink-muted transition-colors p-1">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold text-ink">{doc.original_filename}</h1>
              <StatusBadge status={job.status} />
              {job.is_finalized && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-400/10 text-emerald-400 border border-emerald-400/20">
                  <CheckCheck className="w-3 h-3" /> Finalized
                </span>
              )}
            </div>
            <p className="text-xs text-ink-faint mt-0.5">
              Job #{job.id} · {formatFileSize(doc.file_size)} · {doc.file_type.toUpperCase()}
            </p>
          </div>
        </div>
        <div className="flex gap-2 items-center">
          {isActive && (
            <div className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border ${
              isConnected ? 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' : 'text-ink-faint border-surface-border'
            }`}>
              {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              {isConnected ? 'Live' : 'Polling'}
            </div>
          )}
          {job.status === 'failed' && (
            <Button variant="secondary" size="sm" loading={retryMutation.isPending}
              onClick={() => retryMutation.mutate()}>
              <RotateCcw className="w-3.5 h-3.5" /> Retry
            </Button>
          )}
          {job.status === 'completed' && !job.is_finalized && (
            <>
              {!editing ? (
                <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
                  <Edit3 className="w-3.5 h-3.5" /> Edit
                </Button>
              ) : (
                <>
                  <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
                    <X className="w-3.5 h-3.5" /> Cancel
                  </Button>
                  <Button variant="secondary" size="sm" loading={saveMutation.isPending}
                    onClick={() => saveMutation.mutate()}>
                    <Save className="w-3.5 h-3.5" /> Save
                  </Button>
                </>
              )}
              <Button variant="primary" size="sm" loading={finalizeMutation.isPending}
                onClick={() => finalizeMutation.mutate()}>
                <CheckCheck className="w-3.5 h-3.5" /> Finalize
              </Button>
            </>
          )}
          {job.status === 'completed' && (
            <div className="flex gap-1">
              <Button variant="secondary" size="sm" onClick={() => handleExport('json')}>
                <Download className="w-3.5 h-3.5" /> JSON
              </Button>
              <Button variant="secondary" size="sm" onClick={() => handleExport('csv')}>
                <Download className="w-3.5 h-3.5" /> CSV
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Progress Timeline */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-ink-faint" />
              <span className="text-sm font-medium text-ink">Processing Pipeline</span>
            </div>
            <span className="text-xs font-mono text-ink-muted">{job.progress.toFixed(0)}%</span>
          </div>
          <ProgressBar value={job.progress} animated={isActive} className="mt-3" />
        </CardHeader>
        <CardBody>
          <div className="flex items-center gap-0">
            {PROGRESS_STEPS.map((step, i) => {
              const done = currentStepIdx >= i;
              const active = currentStepIdx === i && isActive;
              return (
                <div key={step.key} className="flex items-center flex-1">
                  <div className="flex flex-col items-center gap-1">
                    <div className={`w-2.5 h-2.5 rounded-full border transition-all duration-300 ${
                      done ? 'bg-brand border-brand' :
                      active ? 'bg-brand border-brand animate-pulse' :
                      'bg-transparent border-surface-border'
                    }`} />
                    <span className={`text-xs whitespace-nowrap ${
                      done ? 'text-ink-muted' : 'text-ink-faint'
                    }`}>{step.label}</span>
                  </div>
                  {i < PROGRESS_STEPS.length - 1 && (
                    <div className={`flex-1 h-px mb-4 transition-all duration-300 ${
                      done && currentStepIdx > i ? 'bg-brand' : 'bg-surface-border'
                    }`} />
                  )}
                </div>
              );
            })}
          </div>

          {/* Live events feed */}
          {events.length > 0 && (
            <div className="mt-4 pt-4 border-t border-surface-border space-y-1 max-h-32 overflow-y-auto">
              {[...events].reverse().map((evt, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span className="text-ink-faint font-mono w-20 flex-shrink-0">
                    {new Date(evt.timestamp).toLocaleTimeString()}
                  </span>
                  <ChevronRight className="w-3 h-3 text-ink-faint flex-shrink-0" />
                  <span className="text-ink-muted">{evt.message || getStepLabel(evt.event)}</span>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Timestamps */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Queued', value: formatDate(job.queued_at), icon: Clock },
          { label: 'Started', value: job.started_at ? formatDate(job.started_at) : '—', icon: Cpu },
          { label: 'Duration', value: formatDuration(job.queued_at, job.completed_at), icon: BarChart3 },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-surface-raised border border-surface-border rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Icon className="w-3.5 h-3.5 text-ink-faint" />
              <span className="text-xs text-ink-faint">{label}</span>
            </div>
            <p className="text-sm font-mono font-medium text-ink">{value}</p>
          </div>
        ))}
      </div>

      {/* Extracted Result */}
      {displayResult && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-ink-faint" />
              <span className="text-sm font-medium text-ink">Extracted Data</span>
              {job.is_reviewed && !job.is_finalized && (
                <span className="text-xs text-amber-400 bg-amber-400/10 border border-amber-400/20 px-2 py-0.5 rounded-full">
                  Edited
                </span>
              )}
            </div>
          </CardHeader>
          <CardBody className="space-y-4">
            {/* Title & Category */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-ink-faint flex items-center gap-1.5 mb-1.5">
                  <Tag className="w-3 h-3" /> Title
                </label>
                {editing ? (
                  <input value={editResult.title || ''} onChange={e => setEditResult({ ...editResult, title: e.target.value })}
                    className="w-full bg-surface-overlay border border-surface-border rounded-lg px-3 py-2 text-sm text-ink focus:outline-none focus:border-brand/50" />
                ) : (
                  <p className="text-sm font-medium text-ink">{displayResult.title}</p>
                )}
              </div>
              <div>
                <label className="text-xs text-ink-faint flex items-center gap-1.5 mb-1.5">
                  <BarChart3 className="w-3 h-3" /> Category
                </label>
                {editing ? (
                  <input value={editResult.category || ''} onChange={e => setEditResult({ ...editResult, category: e.target.value })}
                    className="w-full bg-surface-overlay border border-surface-border rounded-lg px-3 py-2 text-sm text-ink focus:outline-none focus:border-brand/50" />
                ) : (
                  <p className="text-sm font-medium text-ink">{displayResult.category}</p>
                )}
              </div>
            </div>

            {/* Summary */}
            <div>
              <label className="text-xs text-ink-faint flex items-center gap-1.5 mb-1.5">
                <AlignLeft className="w-3 h-3" /> Summary
              </label>
              {editing ? (
                <textarea value={editResult.summary || ''} rows={3}
                  onChange={e => setEditResult({ ...editResult, summary: e.target.value })}
                  className="w-full bg-surface-overlay border border-surface-border rounded-lg px-3 py-2 text-sm text-ink focus:outline-none focus:border-brand/50 resize-none" />
              ) : (
                <p className="text-sm text-ink-muted leading-relaxed">{displayResult.summary}</p>
              )}
            </div>

            {/* Keywords */}
            <div>
              <label className="text-xs text-ink-faint flex items-center gap-1.5 mb-2">
                <Tag className="w-3 h-3" /> Keywords
              </label>
              <div className="flex flex-wrap gap-1.5">
                {displayResult.keywords?.map((kw) => (
                  <span key={kw} className="px-2 py-0.5 bg-surface-overlay border border-surface-border rounded-md text-xs text-ink-muted font-mono">
                    {kw}
                  </span>
                ))}
              </div>
            </div>

            {/* Metadata */}
            <div className="pt-3 border-t border-surface-border">
              <p className="text-xs text-ink-faint mb-2">Metadata</p>
              <div className="grid grid-cols-3 gap-3">
                {Object.entries(displayResult.metadata || {}).map(([k, v]) => (
                  <div key={k} className="bg-surface-overlay rounded-lg px-3 py-2">
                    <p className="text-xs text-ink-faint capitalize">{k.replace(/_/g, ' ')}</p>
                    <p className="text-xs font-mono text-ink-muted mt-0.5 truncate">{String(v)}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Confidence */}
            <div className="flex items-center justify-between pt-2 border-t border-surface-border">
              <span className="text-xs text-ink-faint">Confidence Score</span>
              <div className="flex items-center gap-2">
                <ProgressBar value={(displayResult.confidence_score || 0) * 100} className="w-24" />
                <span className="text-xs font-mono text-ink-muted">
                  {((displayResult.confidence_score || 0) * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Error state */}
      {job.status === 'failed' && job.error_message && (
        <Card>
          <CardBody>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-red-400/10 border border-red-400/20 flex items-center justify-center flex-shrink-0">
                <X className="w-4 h-4 text-red-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-red-400">Processing Failed</p>
                <p className="text-xs text-ink-muted mt-1 font-mono">{job.error_message}</p>
                <p className="text-xs text-ink-faint mt-2">Retry count: {job.retry_count}</p>
              </div>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
