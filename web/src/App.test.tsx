import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';
import * as api from './api';

describe('App', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders backend health once loaded', async () => {
    vi.spyOn(api, 'getHealth').mockResolvedValue({
      status: 'ok',
      version: '0.1.0',
      uptime_seconds: 12.34,
    });

    render(<App />);

    expect(await screen.findByText('ok')).toBeInTheDocument();
    expect(screen.getByText('0.1.0')).toBeInTheDocument();
    expect(screen.getByText('12.3s')).toBeInTheDocument();
  });

  it('shows a friendly message when the backend is unreachable', async () => {
    vi.spyOn(api, 'getHealth').mockRejectedValue(new api.ApiError(0, 'Network error: failed'));

    render(<App />);

    expect(
      await screen.findByText(/Cannot reach the backend/i),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('surfaces the API error message for non-network failures', async () => {
    vi.spyOn(api, 'getHealth').mockRejectedValue(new api.ApiError(503, 'Request to /health failed (503)'));

    render(<App />);

    await waitFor(() =>
      expect(screen.getByText(/failed \(503\)/i)).toBeInTheDocument(),
    );
  });
});
