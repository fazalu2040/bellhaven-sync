# Bellhaven CRM API writeup

## Verified API conventions

I verified the live CRM contract against the OpenAPI docs at https://analyst-assessment-production.up.railway.app/api/docs and by direct API probes.

### Account endpoints
- `GET /api/v1/accounts`
- `POST /api/v1/accounts`
- `GET /api/v1/accounts/{account_id}`
- `PATCH /api/v1/accounts/{account_id}`

There is no documented DELETE or merge action for accounts. The supported update pattern is a PATCH on the account resource.

### Field conventions
- `name` is required when creating a new account.
- `parent_id` links a facility account to its parent company account.
- `status` uses the allowed values: `Active`, `Inactive`, and `Needs Review`.
- `note` is the free-text explanation field for reviewer reasoning and operational context.
- If an account is a duplicate of a surviving record, the losing copy should keep a `duplicate_of_account` value pointing to the surviving account id and be marked `Inactive`.

### Important business rule
When a record is not a Bellhaven facility or is otherwise not part of the active network, we do not delete or merge it. We represent that outcome through the CRM fields already supported by the API:

- `status` set to either `Inactive` or `Needs Review`
- `note` set with a clear explanation
- `duplicate_of_account` set to the surviving account id when there is a duplicate

## Implementation choices in this project

### 1) Create new account
For a `create_account` proposal, we send a JSON payload like:

```json
{
  "name": "Bellhaven Community Name",
  "status": "Active",
  "care_type": "Assisted Living",
  "address": "123 Main St",
  "city": "Columbus",
  "state": "OH",
  "zip": "43201"
}
```

We do not send a `parent_id` unless the account truly belongs under an existing parent. If the parent does not exist, the API rejects the request with `422` and the error `parent_id does not exist`.

### 2) Update existing account
For instance, when an account is no longer active or is a duplicate, we send a PATCH request to `/api/v1/accounts/{account_id}` with a payload like:

```json
{
  "status": "Inactive",
  "active": false,
  "note": "No matching Bellhaven location found during sync; marked inactive after review."
}
```

This matches the actual CRM behavior that we tested live. PATCH is the method the API accepts; PUT and POST return `405 Method Not Allowed` for update operations.

### 3) Duplicate handling
When a record is a duplicate of another account, we follow the API contract exactly:

```json
{
  "status": "Inactive",
  "active": false,
  "duplicate_of_account": "001SURVIVINGACCOUNTID",
  "note": "Duplicate of surviving account 001SURVIVINGACCOUNTID; retained only the active record."
}
```

This is the supported way to express a duplicate without performing a delete or merge.

### 4) Parent / ownership changes
For situations where the account should belong under a different Bellhaven parent, we update the account via `parent_id` while keeping the record in an operational state consistent with the business decision:

```json
{
  "parent_id": "001PARENTACCOUNTID",
  "status": "Active",
  "note": "Moved under correct parent account after review."
}
```

We only do this when `parent_id` is a valid existing account id. Otherwise the API rejects the request with `422`.

## Why these choices are correct

The CRM API does not support destructive record management. Instead, it expects operational state changes to be expressed using:

- `status` for lifecycle state (`Active`, `Inactive`, `Needs Review`)
- `parent_id` for ownership hierarchy
- `note` for explanation and audit trail
- `duplicate_of_account` for duplicates

This fits the Bellhaven business rules we need to enforce without violating the API contract.
