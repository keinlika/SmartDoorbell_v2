# Features and Workflows

## 1. Implemented Features

The current implementation includes the following core features:

- user sign-in
- account creation
- confirm-password validation on sign-up
- persistent light/dark theme toggle
- device pairing by pairing code
- device selector for accessible devices
- device access roles
- live MJPEG preview
- manual recording trigger
- motion-triggered recording
- audio and video clip capture
- cloud upload to Supabase Storage
- event history retrieval
- featured clip viewer
- recent captures queue
- clip deletion
- storage and retention summary
- logout and session recovery

## 2. Login Workflow

### User perspective

The user opens the login page, enters credentials, and signs in to reach the dashboard.

### System perspective

1. The browser calls Supabase `signInWithPassword`.
2. Supabase returns a session token.
3. The dashboard uses that token for backend API calls.
4. The backend validates the token before returning user-scoped data.

## 3. Create Account Workflow

### User perspective

The user selects create-account mode, enters email and password twice, and submits the form.

### System perspective

1. The frontend validates:
   - email format
   - password length/quality expectations
   - password confirmation match
2. The browser calls Supabase `signUp`.
3. If a session is immediately available, the profile is upserted and the user can proceed.
4. If email verification is required, the user is shown a success message and prompted to check email.

## 4. Theme Toggle Workflow

### User perspective

The user can switch between light and dark mode on either the login page or dashboard.

### System perspective

1. The page writes the chosen theme to `localStorage.theme`.
2. The page adds or removes the `dark` class on the document element.
3. Other pages reuse the same stored preference.

## 5. Device Pairing Workflow

### User perspective

The user enters a device pairing code in the dashboard to claim the doorbell.

### System perspective

1. The dashboard sends the code to `/api/pair-device`.
2. The backend verifies the user’s token.
3. The backend looks up the device record by pairing code.
4. If the device is available, the backend assigns ownership to the authenticated user.
5. The backend ensures an owner membership record exists.
6. The dashboard refreshes device state.

## 6. Device Selection Workflow

### User perspective

If the user has access to more than one device, they can choose which device they want to view and manage.

### System perspective

1. The dashboard fetches `/api/device-access`.
2. The frontend renders the available devices.
3. The selected device ID is used in summary and event requests.
4. The manual-record action also targets that selected device ID over WebSocket.

## 7. Live Preview Workflow

### User perspective

The user sees a live preview panel on the dashboard.

### System perspective

1. The dashboard points an image source to the device’s MJPEG endpoint on port `8001`.
2. The device firmware continuously captures and encodes preview frames.
3. The browser updates visually as the MJPEG stream advances.

## 8. Manual Recording Workflow

### User perspective

The user clicks a button to manually record a new clip.

### System perspective

1. The dashboard sends a `manual_record` message over WebSocket.
2. The backend relays the command to the matching device.
3. The firmware acquires the recording lock.
4. The firmware releases the preview camera.
5. FFmpeg records a clip with audio and video.
6. The clip uploads to the backend.
7. The backend stores the file and creates an event record.
8. The dashboard refreshes its history.

## 9. Motion Recording Workflow

### User perspective

The user does not need to do anything. Motion near the sensor automatically creates a recorded event.

### System perspective

1. GPIO motion is detected.
2. The firmware starts the same recording pipeline used for manual recording.
3. The resulting event is stored and later shown in the dashboard history.

## 10. Upload Workflow

### User perspective

After recording, the clip appears in the event history when upload succeeds.

### System perspective

1. The firmware submits the recorded MP4 to `/upload`.
2. The backend validates device context.
3. The backend uploads the file into the Supabase bucket.
4. The backend inserts an event metadata row.
5. If upload fails, the firmware saves the clip in a local retry spool.

## 11. Event History Workflow

### User perspective

The user can review recent motion and manual recordings in the dashboard.

### System perspective

1. The dashboard calls `/api/events`.
2. The backend returns only events for devices the user can access.
3. The frontend sorts and displays those clips in the recent-captures interface.

## 12. Featured Viewer Workflow

### User perspective

The user selects a clip from recent captures and watches it in the larger featured viewer.

### System perspective

1. The dashboard binds the selected event’s video URL to the featured player.
2. The page updates metadata such as event time and type.
3. The selected item remains highlighted in the queue.

## 13. Deletion Workflow

### User perspective

An owner can delete unwanted clips from the dashboard.

### System perspective

1. The dashboard sends `DELETE /api/events/{event_id}`.
2. The backend validates the user and confirms owner access.
3. The backend deletes the storage object.
4. The backend deletes the event row.
5. The dashboard refreshes the event list.

## 14. Storage Summary Workflow

### User perspective

The dashboard shows how much storage is currently used and the retention window in effect.

### System perspective

1. The dashboard calls `/api/dashboard-summary`.
2. The backend computes aggregate storage and clip counts from accessible devices.
3. The frontend renders metrics such as total storage, clips today, and retention days.

## 15. Logout Workflow

### User perspective

The user logs out and is returned to the Sentio login page.

### System perspective

1. The frontend signs out through Supabase JS.
2. Session state is cleared.
3. The browser redirects to `/login.html`.
4. Direct visits to `/static/login.html` also redirect to `/login.html`, keeping one canonical login route.

## 16. Why These Workflows Matter

Taken together, these workflows demonstrate that the project is not only a hardware demo. It supports a complete user journey:

- create account
- sign in
- claim a device
- watch activity
- trigger recording
- review clips
- manage access and storage
- sign out cleanly

That complete journey is one of the strongest parts of the project from a senior-project evaluation perspective.
