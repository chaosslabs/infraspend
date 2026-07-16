# InfraSpend - Open Source FinOps Dashboard

InfraSpend is an open-source FinOps dashboard designed to help organizations monitor, analyze, and optimize their cloud spending across multiple vendors.

![InfraSpend Screenshot](dashboard/public/screenshot.png)

## Features

- 📊 **Budget Tracking**: Monitor your cloud spending across multiple vendors
- 📈 **Cost Forecasting**: Predict future cloud costs using common forecasting techniques
- 🤖 **AI-Powered Insights** (Coming Soon): AI-driven forecasts and optimization suggestions

## Supported Integrations

- ✅ **Datadog**: Full support for cost metrics and forecasting
- 🔜 **AWS**: Full support for cost metrics and forecasting

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
    auth0-audience: "https://infraspend.cloudbudget.ai"
    datadog-api-key: "your-datadog-api-key"
    datadog-app-key: "your-datadog-app-key"

ingress:
  enabled: true
  className: nginx  # Adjust based on your cluster
  hosts:
    - host: infraspend.your-domain.com
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
