# Executive Summary

Sentio is a full-stack smart doorbell system built as a senior project to demonstrate modern embedded, backend, cloud, and web-application integration in one coherent product. The system combines a Raspberry Pi edge device, a FastAPI backend, Supabase authentication and storage, and a browser-based dashboard to monitor front-door activity, record event clips, and manage device ownership.

At the hardware level, the Raspberry Pi connects to a camera, microphone, and GPIO motion sensor. At the cloud level, Supabase provides user authentication, relational data storage, and clip storage. At the application level, a FastAPI backend coordinates uploads, device pairing, account-scoped data access, and real-time messaging, while static dashboard and authentication pages present the user-facing experience. Together, these components create a complete smart-doorbell workflow rather than a narrow feature demo.

The central user problem the project solves is front-door awareness and event review. A user can create an account, pair a device, view a live preview, trigger manual recordings, allow motion-triggered recordings, review recent clips, manage device access, and understand storage usage. These workflows matter because they reflect what a real user expects from a smart-home product: secure access, event history, reliable recording, and a usable dashboard.

One of the most important technical design decisions in the project is the camera ownership model. The Raspberry Pi 3B+ is a constrained platform, so the system does not attempt to run one large always-on media pipeline for every job. Instead, the firmware uses a hot-swap approach. OpenCV owns the camera during MJPEG preview, which is served locally to the dashboard. When recording is triggered by motion or manual action, the firmware pauses preview, releases the camera, and allows FFmpeg to take exclusive control for higher-quality video and audio recording. After recording completes, the preview stream is restored. This design prioritizes recording reliability and saved clip quality, which were the most important project goals on this hardware.

The backend is intentionally practical rather than overengineered. FastAPI provides REST endpoints, WebSocket support, and static file serving. Supabase reduces complexity by handling authentication and storage instead of requiring custom implementations of those services. The backend validates browser bearer tokens with Supabase Auth, accepts device uploads, stores event metadata, supports device pairing, and scopes event access to the correct account. This account-scoped ownership model is one of the strongest aspects of the project because it makes the system behave like a real product instead of a globally shared camera feed.

The frontend focuses on delivering a polished product experience. The login page and dashboard share branding, spacing, theme behavior, and interaction patterns. The dashboard includes device management, a pairing flow, a storage summary, a live preview panel, a featured event viewer, recent captures, and empty states. The authentication page includes account creation, password confirmation, inline validation, and clear error handling. These choices are important because they show that the project was designed for usability and product clarity, not just backend correctness.

From an academic perspective, the project demonstrates several core competencies:

- embedded hardware integration through camera, audio, and motion sensor control
- cloud-backed data and media workflows
- authenticated account and ownership models
- asynchronous communication with WebSockets
- practical handling of constrained hardware tradeoffs
- product-oriented frontend design and user workflow thinking

The system also includes operationally meaningful behaviors such as upload retry spooling, WebSocket reconnection loops, configurable environment-driven quality settings, and clip-retention cleanup. These details show that the implementation considered runtime reliability and not just feature demonstration.

At the same time, the project is honest about its current limits. Live preview currently uses a direct MJPEG stream rather than a cloud-relayed media architecture. Device authentication supports strict enforcement but defaults to a development-friendly shadow mode. Stored clip access is based on public storage URLs rather than private signed delivery. Automated testing is limited compared with a mature production system. These are real limitations, but they are also explainable tradeoffs given the goals, hardware, and scope of a senior project.

Overall, Sentio is best understood as a realistic smart-home systems project with a clear technical backbone and a usable product surface. It goes beyond a simple prototype because it integrates hardware, firmware, backend APIs, cloud services, authentication, storage, real-time control, and user interface design into one end-to-end system. It is strong enough to support a technical defense, a product demo, and a discussion of design tradeoffs, limitations, and future work.
