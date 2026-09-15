import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom';
import VendorDetails from '../VendorDetails';

const mockToken = jest.fn().mockResolvedValue('test-token');
jest.mock('@auth0/auth0-react', () => ({ useAuth0: () => ({ getAccessTokenSilently: mockToken }) }));

const originalFetch = global.fetch;
let plans: any[];
let failSave: boolean;
let failLoad: boolean;
let requests: any[];

beforeEach(() => {
  plans = [];
  failSave = false;
  failLoad = false;
  requests = [];
  global.fetch = jest.fn(async (url: string, options: RequestInit) => {
    let status = 200;
    let body: any;
    if (url.includes('budget-plans')) {
      if (options.method === 'POST') {
        const payload = JSON.parse(options.body as string);
        requests.push(payload);
        if (failSave) { status = 400; body = { detail: 'Budget save rejected' }; }
        else {
          const plan = { ...payload, id: 10, budgets: { budgets: payload.budgets } };
          plans = [...plans.filter(p => p.identifier !== payload.identifier), plan];
          body = { data: plan, status: 'success' };
        }
      } else if (failLoad) { status = 503; body = { message: 'Budget service unavailable' }; }
      else body = { data: plans, status: 'success' };
    } else if (url.includes('vendors-forecast')) {
      body = {
        forecast: [{ month: '09-2026', cost: 100, best_case: 90, worst_case: 110 }],
        growth_rates: { trend_based: 0, best_case: -10, worst_case: 10 },
        sums: { total_forecast: 100, total_best_case: 90, total_worst_case: 110 },
        basis: { status: 'ready', message: 'Completed months only', base_cost: 100, base_month: '08-2026' },
      };
    } else body = { data: [{ month: '08-2026', cost: 100 }, { month: '09-2026', cost: 5 }] };
    return { ok: status < 400, status, json: async () => body } as Response;
  }) as jest.Mock;
});
afterEach(() => { global.fetch = originalFetch; });

const show = () => render(
  <MemoryRouter initialEntries={['/admin/vendors/openai?identifier=Research%20%26%20Finance']}>
    <Link to="/admin/vendors/openai?identifier=Other">Switch account</Link>
    <Routes><Route path="/admin/vendors/:vendor" element={<VendorDetails />} /></Routes>
  </MemoryRouter>,
);

it('saves, reloads and edits an AI account budget through the real response contract', async () => {
  const first = show();
  fireEvent.click(await screen.findByRole('button', { name: 'Set up budget plan' }));
  fireEvent.change(await screen.findByLabelText('Budget for 09-2026'), { target: { value: '123.45' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save Budgets' }));
  await waitFor(() => expect(requests).toHaveLength(1));
  expect(requests[0]).toEqual({ vendor: 'openai', identifier: 'Research & Finance', budgets: [{ month: '09-2026', amount: 123.45 }] });
  await screen.findByText('Budget plan saved successfully');
  first.unmount();
  show();
  expect(await screen.findByLabelText('Budget for 09-2026')).toHaveValue(123.45);
  fireEvent.change(screen.getByLabelText('Budget for 09-2026'), { target: { value: '140' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save Budgets' }));
  await waitFor(() => expect(plans[0].budgets.budgets[0].amount).toBe(140));
});

it('shows rejected saves without success and allows retry', async () => {
  failSave = true;
  show();
  fireEvent.click(await screen.findByRole('button', { name: 'Set up budget plan' }));
  await screen.findByLabelText('Budget for 09-2026');
  fireEvent.click(screen.getByRole('button', { name: 'Save Budgets' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Budget save rejected');
  expect(screen.queryByText('Budget plan saved successfully')).not.toBeInTheDocument();
  failSave = false;
  fireEvent.click(screen.getByRole('button', { name: 'Save Budgets' }));
  await screen.findByText('Budget plan saved successfully');
});

it('keeps legacy vendor-wide and other-account budgets out of the account editor', async () => {
  plans = [
    { id: 1, identifier: null, budgets: { budgets: [{ month: '01-2026', amount: 500 }] } },
    { id: 2, identifier: 'Other', budgets: { budgets: [{ month: '02-2026', amount: 300 }] } },
  ];
  show();
  expect(await screen.findByText('Previous vendor-wide budget (preserved separately)')).toBeInTheDocument();
  expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
  expect(screen.getByText('01-2026: $500.00')).toBeInTheDocument();
});

it('uses the completed-month baseline for simulated budgets', async () => {
  show();
  fireEvent.change(await screen.findByRole('slider'), { target: { value: '10' } });
  fireEvent.click(screen.getByRole('button', { name: 'Set up budget plan' }));
  expect(await screen.findByLabelText('Budget for 09-2026')).toHaveValue(110);
});

it('shows load errors and prevents overwriting an unread budget', async () => {
  failLoad = true;
  show();
  expect(await screen.findByRole('alert')).toHaveTextContent('Budget service unavailable');
  expect(screen.getByRole('button', { name: 'Save Budgets' })).toBeDisabled();
});


it('discards unsaved editor state when switching accounts', async () => {
  plans = [
    { id: 1, identifier: 'Research & Finance', budgets: { budgets: [{ month: '09-2026', amount: 100 }] } },
    { id: 2, identifier: 'Other', budgets: { budgets: [{ month: '09-2026', amount: 300 }] } },
  ];
  show();
  fireEvent.change(await screen.findByLabelText('Budget for 09-2026'), { target: { value: '999' } });
  fireEvent.click(screen.getByRole('link', { name: 'Switch account' }));
  await waitFor(() => expect(screen.getByLabelText('Budget for 09-2026')).toHaveValue(300));
  fireEvent.click(screen.getByRole('button', { name: 'Save Budgets' }));
  await waitFor(() => expect(requests[0].identifier).toBe('Other'));
  expect(plans.find(plan => plan.identifier === 'Research & Finance').budgets.budgets[0].amount).toBe(100);
});
