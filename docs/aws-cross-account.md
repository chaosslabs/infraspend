# AWS cross-account connections

New AWS connections use STS AssumeRole, a server-generated external ID per user,
and the customer role's `ce:GetCostAndUsage` permission. The external ID is not a
password; it binds requests to the authenticated tenant. Customers cannot choose
or submit another tenant's external ID. Temporary credentials stay in memory and
refresh before expiration. The SDK uses bounded timeouts and standard retries.

## Operator setup

1. Run the API migrations before deploying the new API. The additive migration
   preserves existing key-based configurations.
2. Give the API an AWS workload role (EKS IRSA/Pod Identity, ECS task role, or EC2
   instance profile). For local development, use an AWS profile with temporary
   credentials. Do not deploy static AWS access keys.
3. Set `AWS_INFRASPEND_ROLE_ARN` to that workload's IAM role ARN (not an STS
   assumed-role session ARN). This becomes the exact trusted principal.
4. Grant that workload role `sts:AssumeRole` on the approved customer role ARNs:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "sts:AssumeRole",
    "Resource": ["arn:aws:iam::CUSTOMER_ACCOUNT_ID:role/InfraspendCosts"]
  }]
}
```

Use real account IDs in the deployed policy. Keep the resource list scoped to
approved customer roles. For Helm, set `serviceAccount.annotations.eks.amazonaws.com/role-arn`
for IRSA (or configure an EKS Pod Identity association), and add the principal ARN
to `api.env`. The API deployment now uses the chart's configured service account.
Configure the workload's own trust policy for the selected AWS compute service.

## Customer onboarding

Open AWS Configuration and choose **Generate AWS role policies**. Create an IAM
role in the account whose billing data should be read, using the displayed trust
policy and inline permissions policy. Enable Cost Explorer in that account; AWS
may need time to prepare its initial data. Paste the role ARN and connect.
Infraspend verifies actual Cost Explorer access before changing the saved
configuration. Failed verification preserves the old connection.

This implementation supports the standard AWS partition and Cost Explorer in
`us-east-1`. A billing management account can expose linked-account costs; choose
the account according to the intended billing visibility.

## Migration and revocation

Existing access-key connections continue working until replaced through the UI.
After successfully connecting the replacement role and verifying a cost refresh,
revoke the old IAM access key in AWS and remove its old Infisical secret. This
release clears key references on the migrated database record but does not delete
old secrets automatically. Back up the database before production migration.

To revoke cross-account access, remove the customer role's trust or the operator's
AssumeRole permission. Already-issued sessions can remain usable until expiry
(up to one hour); use AWS's role-session revocation procedure when immediate
revocation is needed. A denied or unavailable API remains an error, never zero cost.

Deployments need a live end-to-end check: connect the intended account, fetch a
known billing period and compare it to AWS, verify a wrong external ID is denied,
and exercise the connection again after session refresh. Local mocked tests do
not establish deployed IAM correctness.

AWS reference: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_common-scenarios_third-party.html
