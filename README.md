# InfraSpend - Open Source FinOps Dashboard

InfraSpend is an open-source FinOps dashboard designed to help organizations monitor, analyze, and optimize their cloud spending across multiple vendors.

![InfraSpend Screenshot](dashboard/public/screenshot.png)

## Features

- 📊 **Budget Tracking**: Monitor your cloud spending across multiple vendors
- 📈 **Cost Forecasting**: Predict future cloud costs using common forecasting techniques
- 🤖 **AI-Powered Insights** (Coming Soon): AI-driven forecasts and optimization suggestions

## Supported Integrations

- ✅ **Datadog**: Full support for cost metrics and forecasting
- ✅ **AWS**: Full support for cost metrics and forecasting
- ✅ **Heroku**: Full support for invoice cost metrics and forecasting
- ✅ **Claude / Anthropic API**: Organization cost reports and forecasting
- ✅ **OpenAI API**: Organization API costs and forecasting
- ✅ **Claude and ChatGPT subscriptions**: Manual monthly subscription totals and forecasting

### Claude and ChatGPT billing setup

Run the normal backend migrations (`cd api && python -m app.migrations.run_all`)
before using the new sources. In **Integrations / Source setup**, choose:

- **Claude API (Anthropic)**: Enter a Claude Console organization Admin API key.
  InfraSpend reads the [Anthropic Cost API](https://platform.claude.com/docs/en/manage-claude/usage-cost-api),
  follows pagination and converts cents to USD before aggregating monthly totals.
  The endpoint excludes Priority Tier costs and is unavailable for individual accounts.
- **OpenAI API**: Enter an organization Admin API key with permission to read
  [organization costs](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/costs).
  This imports API spending, not ChatGPT subscriptions; ordinary project inference keys are insufficient.
- **Claude subscription / ChatGPT subscription**: Enter an account name, billing
  month and actual monthly total from your bill in USD. Use Edit to add another
  month or correct an existing total. Saving a month replaces that month's total
  for that account; other months remain unchanged. Missing months stay unknown.
  These sources show **Manual entry**, with no automatic subscription billing sync.
  Non-USD subscription bills and automatic enterprise subscription imports are not supported.

API credentials use the existing Infisical customer-secrets integration, with
separate secret references for each account. No new environment variables are
required. Reports retain provider and source-period metadata; the current month's
API total includes completed UTC days and may lag provider billing. Empty or failed reports
are not converted into invented zero-cost months. API sources participate in the
existing refresh job, cache/failure indicators, forecasts and budget views.
Forecasts require at least two recorded months; they are estimates, not bills.
The demo includes illustrative AI costs, not live account data.

## Budgets, forecasts, and existing accounts

Account detail budgets now support all seven listed sources and apply to the named
account. Run backend migrations before deploying this version. The additive
`add_budget_account_scope` migration preserves previous vendor-wide plans with a
null account identifier; they remain readable through the existing API and are
shown separately in the UI. They are never silently assigned to one account.
Omitting `identifier` from budget API writes retains the vendor-wide contract;
new UI writes include the account identifier. Saving an account budget does not
overwrite a legacy vendor-wide plan.

Forecasts use the most recent consecutive completed UTC months, excluding partial
periods and the current month. At least two completed months, including the last
closed month, are required. Missing months and zero-to-positive growth produce an
explicit unavailable state rather than invented growth. Best/worst scenarios are
illustrative estimates, not confidence intervals. Simulations use the same
completed-month baseline as the forecast.

AWS, Datadog and Heroku saves now use independent secret references per user,
provider and account. Existing references remain readable; re-save each legacy
account with its correct credentials to move it to an independent reference.
Previously shared credentials cannot be reconstructed automatically. If multiple
accounts previously shared a secret, verify their provider identity and historical
totals before relying on those records. This update does not contact providers,
rotate live credentials or rewrite historical costs during migration.

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- Python 3.8+
- uv (Python package installer)
- Kubernetes cluster
- Helm v3

### Installation

#### Local Development

1. Clone the repository:
```bash
git clone https://github.com/chaosslabs/infraspend.git
cd infraspend
```

2. Install frontend dependencies:
```bash
cd dashboard
npm install
```

3. Install backend dependencies:
```bash
cd api
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a new virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

#### Kubernetes Deployment

1. Add the Bitnami repository for PostgreSQL dependency:
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

2. Create a values file (`values.yaml`):
```yaml
secrets:
  infraspendSecrets:
    auth0-domain: "your-auth0-domain"
    auth0-client-id: "your-auth0-client-id"
    auth0-audience: "your-auth0-audience"
    datadog-api-key: "your-datadog-api-key"
    datadog-app-key: "your-datadog-app-key"

ingress:
  enabled: true
  className: nginx  # Adjust based on your cluster
  hosts:
    - host: infraspend.io
      paths:
        - path: /api
          pathType: Prefix
          service: infraspend-api
          port: 8000
        - path: /
          pathType: Prefix
          service: infraspend-dashboard
          port: 3000
```

3. Install the chart:
```bash
# Update dependencies
helm dependency update ./helm/infraspend/infraspend

# Install the chart
helm install infraspend ./helm/infraspend/infraspend -f values.yaml -n your-namespace
```

4. Verify the installation:
```bash
kubectl get pods -n your-namespace
kubectl get ingress -n your-namespace
```

5. Upgrading:
```bash
helm upgrade infraspend ./helm/infraspend/infraspend -f values.yaml -n your-namespace
```

6. Uninstalling:
```bash
helm uninstall infraspend -n your-namespace
```

### Configuration

The following table lists the configurable parameters for the Helm chart:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Global container registry | `ghcr.io` |
| `api.replicaCount` | Number of API replicas | `1` |
| `api.resources` | API resource requests/limits | See values.yaml |
| `dashboard.replicaCount` | Number of dashboard replicas | `1` |
| `dashboard.resources` | Dashboard resource requests/limits | See values.yaml |
| `postgresql.enabled` | Enable PostgreSQL deployment | `true` |
| `ingress.enabled` | Enable ingress creation | `false` |
| `secrets.create` | Create Kubernetes secrets | `true` |

For a complete list of parameters, see the [values.yaml](helm/infraspend/infraspend/values.yaml) file.

4. Set up environment variables:

For the api, check the [api/.env.example](api/.env.example) file.
For the dashboard, check the [dashboard/.env.example](dashboard/.env.example) file.

5. Start the development servers:
```bash
# Start backend (from /api directory)
uvicorn app.main:app --reload

# Start frontend (from /dashboard directory)
npm start
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to:
- Set up your development environment
- Submit pull requests
- Report issues
- Propose new features

## Architecture

InfraSpend consists of two main components:

1. **Frontend** (`/dashboard`):
   - React with TypeScript
   - TailwindCSS for styling
   - Auth0 for authentication
   - ApexCharts for data visualization

2. **Backend** (`/api`):
   - FastAPI (Python)
   - Integration with cloud vendor APIs
   - Cost analysis and forecasting algorithms
   - uv for dependency management

## License

See the [LICENSE](LICENSE) file for details.

## Support

If you need help or have questions:
- Open an issue
- Join our community discussions
- Check out our documentation

## Roadmap

- [x] Datadog Integration
- [ ] AWS Integration
- [ ] GCP Integration
- [ ] Azure Integration
- [ ] AI-powered cost optimization suggestions
- [ ] Custom alerting rules
- [ ] Budget management
- [ ] Team collaboration features

## Acknowledgments

- Thanks to all our contributors
- Built with [React](https://reactjs.org/) and [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [Auth0](https://auth0.com/) for authentication

## Auth0 login setup

1. Create an Auth0 **Single Page Application** and use **Universal Login**.
   Enable the connections your users should see (for example email/password or
   Google) for that application. Password reset is handled by Universal Login
   for database connections. Customize its logo, colors, and application name
   in Auth0 Branding to match InfraSpend.
2. For local development, add `http://localhost:3000` to **Allowed Callback
   URLs** and **Allowed Web Origins**, and `http://localhost:3000/` to **Allowed
   Logout URLs**. Add the equivalent HTTPS origin for each deployed environment.
   The callback uses the origin, not `/auth/sign-in`.
3. Register an Auth0 API using RS256. Copy its Identifier into
   `REACT_APP_AUTH0_AUDIENCE`; configure the backend `AUTH0_AUDIENCE` to the same
   value and `AUTH0_DOMAIN` to the same tenant hostname.
4. Copy `dashboard/.env.example` to `dashboard/.env.local` and fill in the tenant
   hostname (without `https://`), SPA client ID, and API audience. Restart the
   development server or rebuild the frontend after changing these values:
   Create React App embeds them at build time. Never put a client secret in
   `REACT_APP_*` variables.

Private workspace routes now require authentication. Sign-in restores the
requested workspace path, including filters and fragments. Failed sign-in can
be retried; the demo and support remain accessible while authentication loads,
when it fails, or when configuration is absent. Tokens use the SDK's default
in-memory cache. API authorization must still be enforced by the backend.

Verify against your tenant: open a private deep link in a signed-out browser,
complete Universal Login, confirm the original route and API data load, refresh,
and sign out. Also cancel a login and verify retry and public demo access.
See the [Auth0 React SDK documentation](https://auth0.com/docs/libraries/auth0-react)
for tenant settings and session behavior.
