from .create_users_table import upgrade as create_users_table
from .create_api_configurations_table import upgrade as create_api_configurations_table
from .create_vendor_configurations_tables import (
    upgrade as create_vendor_configurations_tables,
)
from .create_budget_plans_table import upgrade as create_budget_plans_table
from .add_config_name import upgrade as add_config_name
from .create_vendor_metrics_table import upgrade as create_vendor_metrics_table
from .add_updated_at_to_vendor_metrics import (
    upgrade as add_updated_at_to_vendor_metrics,
)
from .add_lineage_to_vendor_metrics import upgrade as add_lineage_to_vendor_metrics
from .create_vendor_metric_ingestion_runs_table import (
    upgrade as create_vendor_metric_ingestion_runs_table,
)

# List of migrations in order of execution
MIGRATIONS = [
    create_users_table,  # Must run first as api_configurations depends on it
    create_api_configurations_table,  # Runs after users table exists
    create_vendor_configurations_tables,
    create_budget_plans_table,  # New migration
    add_config_name,
    create_vendor_metrics_table,  # Add vendor metrics table
    add_updated_at_to_vendor_metrics,  # Add the new migration
    add_lineage_to_vendor_metrics,
    create_vendor_metric_ingestion_runs_table,
]
