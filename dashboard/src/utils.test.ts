import { CallBackendService } from './utils';

const originalFetch = global.fetch;
afterEach(() => { global.fetch = originalFetch; });

it.each([
  [{ detail: [{ msg: 'Budget months must be unique' }] }, 'Budget months must be unique'],
  [null, 'Request failed (502)'],
])('rejects unsuccessful responses', async (payload, message) => {
  global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 502, json: async () => payload });
  await expect(CallBackendService('/test', async () => 'token')).rejects.toThrow(message);
});

it('handles successful empty responses', async () => {
  global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 204 });
  await expect(CallBackendService('/test', async () => 'token')).resolves.toBeNull();
});
