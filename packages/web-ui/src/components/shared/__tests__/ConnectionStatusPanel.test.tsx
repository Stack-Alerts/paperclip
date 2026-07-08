import { render, screen, fireEvent } from '@testing-library/react';
import { ConnectionStatusPanel } from '../ConnectionStatusPanel';

const mockUseBackendHealth = jest.fn();
const mockUseNextCandleCountdown = jest.fn();

jest.mock('@/hooks/useBackendHealth', () => ({
  useBackendHealth: () => mockUseBackendHealth(),
}));
jest.mock('@/hooks/useNextCandleCountdown', () => ({
  useNextCandleCountdown: () => mockUseNextCandleCountdown(),
}));

describe('ConnectionStatusPanel', () => {
  beforeEach(() => {
    mockUseNextCandleCountdown.mockReturnValue(42);
  });

  it('does not show a retry button while connected', () => {
    mockUseBackendHealth.mockReturnValue({
      connectionState: 'connected',
      health: { status: 'ok', redis: true, uptime_seconds: 60, branch: 'main' },
      lastChecked: new Date(),
      error: null,
    });
    render(<ConnectionStatusPanel collapsed={false} />);
    expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument();
  });

  it('shows a retry button when disconnected and calls recheck on click', () => {
    const recheck = jest.fn();
    mockUseBackendHealth.mockReturnValue({
      connectionState: 'disconnected',
      health: null,
      lastChecked: new Date(),
      error: 'NetworkError: fetch failed',
      recheck,
    });
    render(<ConnectionStatusPanel collapsed={false} />);
    const btn = screen.getByRole('button', { name: /retry connection/i });
    fireEvent.click(btn);
    expect(recheck).toHaveBeenCalledTimes(1);
  });

  it('disables the retry button while checking', () => {
    const recheck = jest.fn();
    mockUseBackendHealth.mockReturnValue({
      connectionState: 'checking',
      health: null,
      lastChecked: null,
      error: null,
      recheck,
    });
    render(<ConnectionStatusPanel collapsed={false} />);
    const btn = screen.getByRole('button', { name: /checking/i });
    expect(btn).toBeDisabled();
  });

  it('shows the API base URL so the user knows which port to check', () => {
    mockUseBackendHealth.mockReturnValue({
      connectionState: 'disconnected',
      health: null,
      lastChecked: new Date(),
      error: 'NetworkError: fetch failed',
      recheck: jest.fn(),
    });
    render(<ConnectionStatusPanel collapsed={false} />);
    expect(screen.getByText(/localhost:8765/)).toBeInTheDocument();
  });
});
