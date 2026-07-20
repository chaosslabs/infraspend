import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import VendorMetrics from '../VendorMetrics';
import { deriveSourceHealth, STALE_AFTER_HOURS } from '../SourceHealth';
import { useAuth0 } from '@auth0/auth0-react';
import '@testing-library/jest-dom';

const NOW = new Date('2026-07-20T12:00:00Z').getTime();
const hoursAgo = (h: number) => new Date(NOW - h * 3_600_000).toISOString();

// Mock Auth0
jest.mock('@auth0/auth0-react');

// Mock the chart component since we don't need to test its internals
jest.mock('components/charts/BarChart', () => {
  return function DummyChart() {
    return <div data-testid="bar-chart">Chart</div>;
  };
});

const renderWithRouter = (ui: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {ui}
    </BrowserRouter>
  );
};

describe('VendorMetrics', () => {
  beforeEach(() => {
    // Mock Auth0 hook
    (useAuth0 as jest.Mock).mockReturnValue({
      getAccessTokenSilently: jest.fn(),
      isAuthenticated: true,
      user: { sub: 'test-user' }
    });

    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: { pathname: '/' },
      writable: true
    });
  });

  it('renders the component title', () => {
    renderWithRouter(
      <VendorMetrics
        vendor="aws"
        identifier="Default Configuration"
        title="AWS Costs"
        demo={true}
      />
    );

    expect(screen.getByText('AWS Costs')).toBeInTheDocument();
  });

  it('shows demo data when demo prop is true', () => {
    renderWithRouter(
      <VendorMetrics
        vendor="aws"
        identifier="Default Configuration"
        title="AWS Costs"
        demo={true}
      />
    );

    // The chart should be rendered
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('surfaces a source-health label in demo mode', () => {
    renderWithRouter(
      <VendorMetrics
        vendor="datadog"
        identifier="Default Configuration"
        title="Datadog Costs"
        demo={true}
      />
    );

    // Datadog demo data is fresh; the freshness badge must be present.
    expect(screen.getByText('Fresh')).toBeInTheDocument();
  });

  it('labels demo data as cached when the latest refresh failed', () => {
    renderWithRouter(
      <VendorMetrics
        vendor="aws"
        identifier="Default Configuration"
        title="AWS Costs"
        demo={true}
      />
    );

    // AWS demo data has a failed latest attempt over cached data.
    expect(
      screen.getByText('Cached — last refresh failed')
    ).toBeInTheDocument();
  });
});

describe('deriveSourceHealth', () => {
  it('returns unknown when no ingestion fields are present', () => {
    expect(deriveSourceHealth(undefined, NOW).state).toBe('unknown');
    expect(deriveSourceHealth({}, NOW).state).toBe('unknown');
  });

  it('returns never when there is an attempt but no success', () => {
    const result = deriveSourceHealth(
      { last_attempt_at: hoursAgo(1), last_attempt_status: 'failed' },
      NOW
    );
    expect(result.state).toBe('never');
  });

  it('returns failed (cached) when the latest attempt failed over prior success', () => {
    const result = deriveSourceHealth(
      {
        last_success_at: hoursAgo(26),
        last_attempt_at: hoursAgo(1),
        last_attempt_status: 'failed',
      },
      NOW
    );
    expect(result.state).toBe('failed');
    expect(result.label).toMatch(/cached/i);
  });

  it('returns partial when the latest attempt only partially refreshed', () => {
    const result = deriveSourceHealth(
      {
        last_success_at: hoursAgo(2),
        last_attempt_at: hoursAgo(1),
        last_attempt_status: 'partial',
      },
      NOW
    );
    expect(result.state).toBe('partial');
  });

  it('returns stale when the last success is older than the threshold', () => {
    const result = deriveSourceHealth(
      {
        last_success_at: hoursAgo(STALE_AFTER_HOURS + 1),
        last_attempt_at: hoursAgo(STALE_AFTER_HOURS + 1),
        last_attempt_status: 'success',
      },
      NOW
    );
    expect(result.state).toBe('stale');
  });

  it('returns fresh for a recent success', () => {
    const result = deriveSourceHealth(
      {
        last_success_at: hoursAgo(2),
        last_attempt_at: hoursAgo(2),
        last_attempt_status: 'success',
      },
      NOW
    );
    expect(result.state).toBe('fresh');
  });
});
