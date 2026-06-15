import { useCallback, useEffect, useState } from 'react';
import { ApiError, getHealth, type Health } from './api';

type Status =
  | { kind: 'loading' }
  | { kind: 'ok'; health: Health }
  | { kind: 'error'; message: string };

/**
 * WebHawk dashboard shell.
 *
 * Phase 0 skeleton: confirms the front end can reach the FastAPI backend by
 * rendering its health/version, with explicit loading and error states. Real
 * scan UI (targets, findings, reports) is built in later phases.
 */
export default function App(): JSX.Element {
  const [status, setStatus] = useState<Status>({ kind: 'loading' });

  const load = useCallback((signal?: AbortSignal) => {
    setStatus({ kind: 'loading' });
    getHealth(signal)
      .then((health) => setStatus({ kind: 'ok', health }))
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const message =
          err instanceof ApiError
            ? err.status === 0
              ? 'Cannot reach the backend. Is the API running on :8000?'
              : err.message
            : 'Unexpected error loading backend status.';
        setStatus({ kind: 'error', message });
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return (
    <main className="app">
      <header className="app__header">
        <h1>
          Web<span className="app__accent">Hawk</span>
        </h1>
        <p className="app__tagline">Authorized web-application vulnerability scanner</p>
      </header>

      <section className="card" aria-live="polite">
        <h2 className="card__title">Backend status</h2>
        {status.kind === 'loading' && <p className="muted">Checking backend…</p>}

        {status.kind === 'ok' && (
          <dl className="kv">
            <dt>Status</dt>
            <dd>
              <span className="badge badge--ok">{status.health.status}</span>
            </dd>
            <dt>Version</dt>
            <dd>{status.health.version}</dd>
            <dt>Uptime</dt>
            <dd>{status.health.uptime_seconds.toFixed(1)}s</dd>
          </dl>
        )}

        {status.kind === 'error' && (
          <div className="error" role="alert">
            <p>{status.message}</p>
            <button type="button" onClick={() => load()}>
              Retry
            </button>
          </div>
        )}
      </section>

      <footer className="app__footer muted">
        Authorized testing only — every scan requires proof of target ownership.
      </footer>
    </main>
  );
}
