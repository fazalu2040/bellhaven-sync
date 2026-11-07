# Bellhaven CRM Sync Review App User Guide

This guide explains how to run the local review app and safely approve or reject proposed CRM changes.

## Overview

The app reviews Bellhaven sync proposals generated from the current CRM state and the Bellhaven website data. It gives you a local approval queue before any write-back happens.

The workflow is:
1. Generate pending proposals.
2. Review each proposal.
3. Approve only the changes you want to apply.
4. The app sends the approved write-back to the CRM API.
5. Rejected items remain out of the CRM.

---

## Prerequisites

Before running the app, ensure:
- Python 3.12 is available
- Dependencies are installed in the project virtual environment
- Your CRM token and base URL are set in the environment or `.env`

Typical project setup:

```powershell
cd C:\Projects\bellhaven-sync\bellhaven-sync
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## Run the app

From the repo root:

```powershell
cd C:\Projects\bellhaven-sync\bellhaven-sync
.\.venv\Scripts\python.exe -m streamlit run app/review_app.py --server.headless true --server.port 8503
```

Then open:

```text
http://localhost:8503
```

---

## Generate the review queue

On the page:
- Click the `Load proposals` button.
- The app will compare current CRM accounts to Bellhaven location data and generate pending review items.

Each proposal can be one of these categories:
- `New Account needed`
- `Needs Fix`
- `Inactive`
- `Duplicate`

---

## Review a proposal

For each item, the app shows:
- Proposal id
- CRM account id
- Match score
- Proposed action type
- Evidence and raw details used to justify the recommendation

You can do either of the following:
- `Approve` — writes the proposal back to the CRM
- `Reject` — keeps the proposal out of the CRM and removes it from the queue

---

## Approval rules and safety

The app does not write automatically without your approval.

The approved actions are intentionally limited to the supported CRM operations:

### Create a new account
Use this when no CRM account matches a Bellhaven location closely enough.

### Reparent an account
Use this when the correct Bellhaven parent has changed and the record should move under the correct parent account.

### Mark an account inactive
Use this when the account is no longer active or no matching Bellhaven facility is found.

### Mark a duplicate
Use this when an account is a duplicate of a surviving record.

In that duplicate case, the writeback should:
- set `status` to `Inactive`
- set `active` to `False`
- set `duplicate_of_account` to the surviving account id
- add a clear note explaining the decision

---

## Daily usage pattern

The sync can be run from the CLI when you want to regenerate proposals:

```powershell
cd C:\Projects\bellhaven-sync\bellhaven-sync
.\.venv\Scripts\python.exe -m app.main sync
```

This creates a fresh proposal set that can then be reviewed in the app.

---

## Important notes

- Only approved proposals are written back.
- Rejected proposals are not written.
- The CRM API does not support delete or merge operations.
- The supported pattern is to update status and note fields, and to set `duplicate_of_account` when needed.
- Parent ids must reference valid existing CRM accounts; otherwise the API will reject the request.

---

## Troubleshooting

### App does not start
Check that the project virtual environment is set up and that the dependencies are installed.

### Port already in use
Use an alternate port:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/review_app.py --server.headless true --server.port 8503
```

### Write-back failed with 422
This usually means one of these is wrong:
- required field is missing, such as `name`
- invalid `parent_id`
- invalid field format or unrecognized value
- status is not one of the allowed values

Review the proposal payload in the app and confirm the CRM contract before approving.

---

## Summary

The local app is the controlled review layer between your Bellhaven data and the CRM. It reduces the risk of accidental writes by requiring explicit approval before any update is sent.
