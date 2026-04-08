# Security and Authentication

## 1. Authentication Model

The project uses **Supabase Auth** as the primary user authentication system.

This means:

- the application does not implement its own password database
- sign-in and sign-up are handled through Supabase
- the browser receives a session token
- the backend verifies that token before serving protected APIs

This is a sound decision for a senior project because it reduces custom security code while still using a real account system.

## 2. User Session Handling

The browser uses the Supabase JavaScript client to manage the user session. The current frontend stores session state in browser storage and uses the access token for backend API calls.

Protected backend routes expect a bearer token and validate it using the Supabase Python client.

If the session is missing or invalid:

- the dashboard redirects to `/login.html`
- logout also returns to `/login.html`

This creates one clear authentication entry point.

## 3. Device Pairing and Ownership

The project distinguishes between **user authentication** and **device identity**.

### User authentication

Handled through Supabase Auth.

### Device ownership

Handled through the `devices` table and pairing code workflow.

### Why ownership matters

Without ownership, the system would effectively behave like a shared demo. With ownership:

- clips are tied to the correct account scope
- device controls only appear for users with access
- one user cannot simply browse another user’s event history

This is one of the most important security-related design decisions in the system.

## 4. Device Membership and Shared Access

The system supports more than a single owner-only model. It also has the concept of `device_members`, which allows viewer-style access relationships.

This matters because real smart-home products often require shared household access. It also shows that the project considers role-based access beyond the simplest possible implementation.

## 5. Device Authentication

The backend supports device-side credentials using:

- `X-Device-ID`
- `X-Device-Token`

The WebSocket connection also supports a `device_auth` message. This allows the backend to associate a real-time connection with a specific hardware device.

The device-auth mode can be configured as:

- `off`
- `shadow`
- `enforce`

### Security significance of these modes

- `off` is weakest and mainly for development
- `shadow` allows compatibility while logging issues
- `enforce` is strongest and appropriate for stricter deployments

The current default is `shadow`, which is reasonable during development but should be tightened for stronger security.

## 6. API Protection Model

Protected routes rely on validated user tokens and account-scoped data lookups.

Examples:

- `/api/device-access` returns only accessible devices
- `/api/events` returns only events for accessible devices
- `/api/dashboard-summary` aggregates only the user’s devices
- `DELETE /api/events/{event_id}` is owner-only

This account scoping is a major security strength.

## 7. Storage Protection Considerations

Uploaded files currently live in Supabase Storage, and the backend stores public URLs in event rows.

### Current strength

- uploaded media is at least organized and associated with account-scoped event metadata

### Current limitation

- public URLs are less private than signed URLs or private-bucket access patterns

For a higher-security production system, the preferred approach would be:

- private bucket access
- signed temporary download URLs
- stronger backend mediation for clip delivery

## 8. Frontend Direct Supabase Usage

The current frontend uses the Supabase JS client not only for sign-in/sign-up, but also for some direct profile and membership operations.

### Benefit

- faster development
- fewer backend routes needed

### Security tradeoff

- authorization logic is split across backend and Supabase policy behavior
- a stricter production model would centralize more write operations behind backend APIs

## 9. Current Security Strengths

The project already includes meaningful security-conscious design choices:

- real user authentication
- canonical login routing
- account-scoped devices and events
- owner and viewer access distinction
- owner-only deletion
- device identity support
- configurable device-auth enforcement modes
- no custom password implementation

## 10. Current Security Limitations

The project also has clear limitations that should be acknowledged honestly:

- default device-auth mode is not strict enforcement
- media access is based on public storage URLs
- the live MJPEG preview is a direct stream, not a brokered private media channel
- some frontend behavior relies on direct Supabase client access
- no full public HTTPS deployment or reverse-proxy hardening is included in the repo
- the sample `test_login.py` contains hardcoded credentials and is not suitable for production

## 11. What Stronger Production Hardening Would Require

To move toward a stronger production-grade security posture, the next phase would include:

1. set device authentication to `enforce`
2. move media storage to private access with signed URLs
3. put the backend behind HTTPS with a reverse proxy
4. centralize more write operations behind backend-owned APIs
5. define and audit Supabase row-level security policies explicitly
6. improve device provisioning and token rotation
7. add audit logging and rate limiting
8. add CSRF-aware patterns where relevant for browser operations
9. implement stronger secret management for deployment

## 12. Security Conclusion

For a senior project, the security model is meaningfully stronger than a simple demo because it includes real user accounts, ownership scoping, membership access, protected APIs, and device identity concepts. At the same time, the project remains honest about the difference between an academic full-stack build and a fully hardened commercial security product.
