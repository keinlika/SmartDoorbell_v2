# Testing and Validation

## 1. Testing Philosophy

This project should be evaluated as a complete integrated system: hardware, backend, cloud, and UI. Because of that, testing is not only about unit tests. It also includes:

- functional workflow testing
- reliability testing
- user-interface validation
- hardware-trigger validation
- operational recovery behavior

The current repository does not contain a full automated test suite, so validation relies heavily on integration and scenario testing.

## 2. What Has Clearly Been Tested Through the Current Implementation

Based on the code and current feature set, the following workflows have clearly been implemented and exercised during development:

- sign in and sign up through Supabase
- dashboard load after authentication
- logout redirect to canonical login route
- device pairing by pairing code
- live MJPEG preview display
- manual recording trigger through WebSocket
- motion-triggered recording through GPIO monitoring
- clip upload to backend and Supabase Storage
- event history retrieval and display
- featured clip viewing
- clip deletion by owner
- storage and retention summary rendering
- theme persistence between login and dashboard

## 3. Completed Technical Validation Evidence Available from the Codebase

Even without a full test suite, the codebase itself provides evidence of validation-focused implementation:

- firmware includes recording locks to prevent overlap
- firmware includes upload retry spooling for network failures
- backend includes retention cleanup logic
- backend uses account-scoped event and device queries
- frontend includes empty states and session-failure handling
- login page includes inline validation and confirm-password logic

These are signs that the system was built with real operational behavior in mind.

## 4. Tests Worth Demonstrating to a Professor

The following tests provide strong evidence during a live demo or project defense.

### Authentication tests

- create a new account
- sign in with an existing account
- show password mismatch validation during sign-up
- log out and show redirect to `/login.html`

### Device ownership tests

- pair a device using a valid pairing code
- show that the device appears in the selector afterward
- demonstrate that events shown are scoped to the signed-in account

### Recording tests

- trigger a manual recording from the dashboard
- demonstrate motion-triggered recording using the sensor
- show the new event appearing in recent captures
- open the clip in the featured viewer

### Storage tests

- show storage summary values updating after new captures
- delete a clip and show the event list changing accordingly

### Theme/UI tests

- toggle dark mode on login
- sign in
- show that the theme persists on the dashboard

## 5. Functional Test Cases

The following functional test cases should be explicitly documented for evaluation.

### F1. Sign-in success

- Precondition: valid Supabase user exists
- Action: enter valid credentials
- Expected result: dashboard loads successfully

### F2. Sign-up password mismatch

- Precondition: user on create-account mode
- Action: enter non-matching passwords
- Expected result: form blocks submission and shows inline validation

### F3. Pair valid device

- Precondition: authenticated user and unclaimed device with known pairing code
- Action: submit pairing code
- Expected result: device becomes visible under account

### F4. Manual record

- Precondition: backend and device connected by WebSocket
- Action: click record
- Expected result: clip records, uploads, and appears in history

### F5. Motion record

- Precondition: sensor armed and device running
- Action: trigger sensor
- Expected result: motion clip records and appears in history

### F6. Delete clip

- Precondition: owner user and existing clip
- Action: delete selected event
- Expected result: clip disappears from history and storage object is removed

## 6. Reliability Test Cases

### R1. Backend restart recovery

- Action: restart the FastAPI backend while the device is running
- Expected result: firmware reconnect loop restores WebSocket connection

### R2. Temporary upload failure

- Action: disconnect backend or network during upload
- Expected result: clip is preserved locally in spool and retried later

### R3. Repeated motion triggers

- Action: trigger motion repeatedly during an active recording
- Expected result: recording lock prevents overlapping FFmpeg sessions

### R4. Camera reinitialization after recording

- Action: trigger a recording, then wait for preview to return
- Expected result: MJPEG preview resumes after FFmpeg finishes

## 7. UI Test Cases

### U1. Empty-state quality

- Precondition: no recent events
- Expected result: dashboard shows deliberate empty states, not broken placeholders

### U2. Mobile layout

- Action: view login and dashboard on a narrow browser width
- Expected result: text wraps cleanly and controls remain usable

### U3. Theme persistence

- Action: toggle theme on one page and move to the other page
- Expected result: selected theme persists

## 8. Suggested Evidence to Show a Professor

Useful evidence includes:

- a live manual recording
- a motion-triggered event
- the event appearing in the dashboard
- a paired-device view showing account scoping
- clip deletion behavior
- a quick look at the firmware console showing recording/upload status
- a quick look at Supabase tables or storage bucket entries

## 9. Recommended Validation Checklist for Demo Day

Before the demo:

1. confirm backend starts successfully with `uvicorn app.main:app`
2. confirm device firmware connects to backend
3. confirm MJPEG stream loads in browser
4. confirm test account can sign in
5. confirm one valid pairing code is available
6. confirm at least one stored clip exists as a backup demo artifact
7. confirm theme toggle and logout behavior work

During the demo:

1. show login
2. show dashboard
3. show paired device
4. show manual or motion recording
5. show clip upload and playback

## 10. Recommended Tests Still Worth Doing

The following additional tests would strengthen the project further:

- formal API tests for protected routes
- explicit device-auth enforcement testing in `enforce` mode
- storage-access hardening tests with signed or private URLs
- longer-duration soak testing on the Raspberry Pi
- browser compatibility checks across multiple devices
- more structured sensor false-positive testing

## 11. Honest Testing Assessment

The project demonstrates substantial integration testing value, but it does not yet have a deep automated test harness. In a senior-project defense, the strongest framing is:

- the system has been validated as a real integrated workflow
- core user and hardware behaviors are implemented and testable
- the next maturity step would be broader automated and long-duration testing
