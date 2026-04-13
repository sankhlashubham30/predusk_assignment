import { useEffect, useRef, useState } from 'react';
import { ProgressEvent } from '@/types';
import { getSSEUrl } from '@/lib/api';

export function useJobProgress(jobId: number | null, enabled = true) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [latestEvent, setLatestEvent] = useState<ProgressEvent | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId || !enabled) return;

    const url = getSSEUrl(jobId);
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => setIsConnected(true);

    es.onmessage = (e) => {
      try {
        const data: ProgressEvent = JSON.parse(e.data);
        setLatestEvent(data);
        setEvents((prev) => [...prev, data]);
        if (data.event === 'job_completed' || data.event === 'job_failed') {
          es.close();
          setIsConnected(false);
        }
      } catch {}
    };

    es.onerror = () => {
      setIsConnected(false);
      es.close();
    };

    return () => {
      es.close();
      setIsConnected(false);
    };
  }, [jobId, enabled]);

  return { events, latestEvent, isConnected };
}
