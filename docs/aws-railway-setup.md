# AWS setup for the Railway deployment

Status checked 2026-09-15. This is an operator checklist, not completed AWS provisioning.

## Verified deployment boundary

The live API is Railway service `infraspend` in project `positive-luck`, using
`chaosslabs/infraspend` branch `main`, root `/api`, and Railpack. Its domain is
`api.infraspend.io`. The service configuration lists the database, CORS and
Infisical bootstrap variables; no AWS variables or credential-provider mounts
were listed. Setting a role ARN alone does not authenticate the workload to AWS.

The `platformlabs` AWS CLI profile is verified for company account `682334556539`.
The current session is the account root identity; it is not the Railway workload
identity. IAM lists only AWS service-linked roles, with no OIDC providers.
In `us-east-1`, no Roles Anywhere trust anchors/profiles or ACM private CAs exist.
The old `default` profile is not used for this setup. Do not paste keys or session
tokens into tickets, chat, or committed files.

## Prepared infrastructure

[`infra/aws/railway-identity.yaml`](../infra/aws/railway-identity.yaml) defines the
dedicated trust anchor, `InfraSpendRailwayWorkload` IAM role, and Roles Anywhere
profile. AWS CloudFormation `validate-template` passed. It has not been deployed.

- Supply only the public CA certificate as `CaCertificatePem`.
- Trust requires this exact anchor, AWS account, and certificate subject CN
  `infraspend-railway-production`.
- The profile exposes only that workload role, with one-hour sessions.
- Identity issuance is disabled by default. Enable it only when the certificate
  lifecycle and runtime credential provider are ready.
- The role initially has no permissions policies. Grant `sts:AssumeRole` only
  for individually approved customer role ARNs during onboarding.

Certificate authority selection and signing-key custody are pending. A dedicated
offline CA with 90-day workload certificates is the proposed starting point;
the signing key must remain outside Railway. No keys or certificates have been
generated and no IAM resources have been changed by this preparation.

## Authentication plan

Keep the API on Railway. For a workload outside AWS, use an explicitly configured
temporary-credential provider. A candidate supported by AWS is **IAM Roles Anywhere**:

1. Identify the company AWS account and existing certificate authority/trust
   anchor, if any. Select and document certificate issuance, secure storage,
   rotation, expiration monitoring and revocation before issuing credentials.
2. Create a dedicated InfraSpend workload role trusted by Roles Anywhere,
   restricting the trust anchor and certificate identity. Do not use wildcard
   customer-role access or trust an entire account without the intended boundary.
3. Give that role only `sts:AssumeRole` on the approved customer billing-role ARNs.
4. Install a pinned, verified AWS signing helper in the Railway build and supply
   its certificate/private key through protected runtime files. Configure the
   AWS SDK profile's `credential_process` to run the helper. Private-key files
   must never be committed, baked into the image or printed in logs.
5. Set `AWS_PROFILE`/`AWS_CONFIG_FILE` for that profile and
   `AWS_INFRASPEND_ROLE_ARN` to the dedicated workload IAM role ARN. The default
   boto3 credential chain then supplies credentials for the customer-role STS
   call already implemented in this PR.

This plan requires an approved certificate lifecycle and a runtime bootstrap;
it is not implemented merely by this document. Railway's user-login OAuth/OIDC
integration is not evidence of service workload federation into AWS. If a
verified workload federation option becomes available, assess it before adding
certificate infrastructure. Do not use developer SSO sessions or deploy static
AWS access keys as a substitute for a renewable production credential provider.

References:

- [AWS access for non-AWS workloads](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_common-scenarios_non-aws.html)
- [Roles Anywhere credential helper](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/credential-helper.html)
- [Roles Anywhere deployment planning](https://aws.amazon.com/blogs/security/planning-for-your-iam-roles-anywhere-deployment/)

## Customer role and release checks

After PR #39 is merged/deployed with migrations and the workload identity is
configured, generate the tenant's external ID through `/v1/configuration/aws/setup`.
Use the exact returned trust principal and external-ID condition in the selected
billing account. Grant `ce:GetCostAndUsage`, enable Cost Explorer if necessary,
and scope the workload role's allowlist to that customer role ARN.

Verify, without printing session credentials:

- Local setup operator: `aws sts get-caller-identity --profile <company-profile>`.
- Railway runtime: the default boto3 STS caller identity is the intended workload
  role (a role ARN setting is not identity proof).
- Correct external ID: assume the customer role and query a known completed
  billing month, using `UnblendedCost` in USD or the source's reported currency.
- Incorrect external ID: the same request must be denied by AWS.
- Product flow: authenticated setup, connect, refresh and compare that month to
  AWS using the same account, billing basis, dates and currency.
- Refresh: exercise the integration after temporary credentials renew.
- Failure/revocation: display a failure or stale-data state, never fabricate zero.

Preview sandboxes deliberately refuse real AWS setup and connection requests.
They cannot validate customer IAM trust or real Cost Explorer access. Old
key-based records remain readable; revoke keys/remove legacy secrets only after
the replacement role and cost refresh have been verified.
