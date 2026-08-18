# Backend QA Testing Results

## Authentication Tests

| Test | Expected Result | Actual Result | Status |
|---|---|---|---|
| Signup with missing fields | Request rejected | "Name, email, and password are required" | PASS |
| Signup with existing email | Request rejected | "An account with this email already exists" | PASS |
| Login with wrong password | Request rejected | "Invalid email or password" | PASS |
| Login with missing password | Request rejected | "Email and password are required" | PASS |
| Login with valid credentials | User and token returned | User and JWT token returned | PASS |
| Protected route without token | Request rejected | "No token provided" | PASS |
| Protected route with invalid token | Request rejected | "Invalid or expired token" | PASS |

## Claims API Tests

| Test | Expected Result | Actual Result | Status |
|---|---|---|---|
| Submit claim with missing claim_text | Request rejected | "claim_text is required" | PASS |
| Submit valid claim | Claim created | Claim successfully created | PASS |
| Get user's claims | Claims returned | Claims successfully returned | PASS |
| Check claim verification status | Status returned | "completed" | PASS |
| Get non-existent claim | Request rejected | "Claim not found" | PASS |
| User 2 accesses User 1's claim | Access prevented | "Claim not found" | PASS |

## Summary

Backend authentication, claims API, validation, verification status, and user data isolation were manually tested using PowerShell API requests.

**Overall Result: PASS**
