# Professor Q&A Preparation

## 1. Why did you choose this architecture?

**Answer:**  
I chose an edge-to-cloud architecture because a smart doorbell naturally spans hardware capture, cloud persistence, and user-facing review. The Raspberry Pi handles sensing and media capture, the FastAPI backend coordinates uploads and access control, Supabase provides authentication and storage, and the dashboard gives the user a complete interface. This division kept responsibilities clear and made the system easier to defend technically.

## 2. Why did you use a Raspberry Pi instead of a microcontroller only?

**Answer:**  
The project needed camera capture, microphone capture, FFmpeg recording, local streaming, HTTP upload, and WebSocket communication. A Raspberry Pi is much better suited for those multimedia and networking workloads than a small microcontroller alone. It also gave me a Linux environment with access to OpenCV, FFmpeg, GPIO, and Python libraries, which made full-system integration practical.

## 3. Why did you use the hot-swap camera architecture?

**Answer:**  
Because the hardware is a Raspberry Pi 3B+, my top priority was reliable recording. A single always-on pipeline or simultaneous preview/record ownership model would increase complexity and steady-state CPU load. The hot-swap approach gives OpenCV the camera during preview, then releases it so FFmpeg can take exclusive control during recording. That reduces camera-access conflicts and improves the reliability of saved clips, which was the highest priority.

## 4. Why not build the frontend in React or another SPA framework?

**Answer:**  
The current product goals did not require a large component framework. A static HTML and JavaScript frontend was enough to deliver sign-in, pairing, history, live preview, theme persistence, and dashboard state. That kept deployment simpler and let me focus on full-system behavior instead of adding extra frontend build complexity.

## 5. Why did you choose FastAPI?

**Answer:**  
FastAPI gave me straightforward REST routes, async support, WebSocket support, and static file serving in one Python framework. Since the firmware was also in Python, using FastAPI kept the project consistent and reduced development friction.

## 6. Why did you choose Supabase?

**Answer:**  
Supabase let me avoid building authentication, storage, and data persistence from scratch. It gave me a real user-authentication model, relational tables for devices and events, and storage for recorded clips. That allowed me to focus the project on smart-doorbell logic and product integration rather than rebuilding common cloud services.

## 7. How does account security work?

**Answer:**  
Users authenticate with Supabase Auth. The dashboard then sends the bearer token to the FastAPI backend, which validates it server-side. Device and event access are scoped to the authenticated user through device ownership and membership relationships. That means clips are not globally visible just because someone can open the dashboard.

## 8. How are devices associated with a user account?

**Answer:**  
Through a pairing-code workflow. A signed-in user submits a pairing code, the backend looks up the matching device, and if it is available it assigns ownership to that user. The system also creates or verifies the owner membership relationship so the user can manage and view that device consistently.

## 9. Why does the system use both a backend and direct Supabase access from the frontend?

**Answer:**  
The backend handles the core protected system logic, especially user-scoped data and device events. The frontend also uses the Supabase JavaScript client for authentication and some account-related operations to reduce backend code and speed development. It is a pragmatic choice for a senior project, although in a stricter production model I would centralize more of those writes behind backend-owned APIs.

## 10. How scalable is the current architecture?

**Answer:**  
It is scalable enough for a small number of devices and users, but it is not yet designed for large-scale deployment. The WebSocket relay is simple, the live preview is direct MJPEG from the device, and media is stored using a straightforward event model. For larger scale, I would need stronger streaming infrastructure, more formal background-job handling, and more operational hardening.

## 11. What are the strongest technical parts of the project?

**Answer:**  
The strongest parts are the complete end-to-end integration, the account-scoped device ownership model, the practical hot-swap media pipeline on constrained hardware, the upload retry behavior, and the product-like dashboard and authentication flow. It behaves like a real system rather than a set of isolated demos.

## 12. What are the main limitations?

**Answer:**  
The biggest limitations are the direct MJPEG preview approach, public clip URLs instead of private signed delivery, development-friendly device-auth defaults, and limited automated testing. Those are the main areas I would improve next for a more production-grade system.

## 13. Why is the live preview not the same quality as the recorded clip?

**Answer:**  
That is intentional. On Raspberry Pi 3B+, trying to make preview and recording both high quality all the time would hurt performance and reliability. I deliberately prioritized saved clip quality over preview quality because recorded evidence is more important than a perfect live stream in this system.

## 14. How do you prevent overlapping recordings?

**Answer:**  
The firmware uses an `asyncio.Lock` and an internal recording state. That ensures only one FFmpeg recording session can own the capture pipeline at a time, which reduces resource conflicts and race conditions when multiple triggers occur close together.

## 15. What happens if upload fails?

**Answer:**  
The firmware keeps the clip locally in a spool directory and retries later. That makes the system more reliable in real conditions where the backend or network may not always be available.

## 16. How does real-time communication work?

**Answer:**  
The browser and device both connect to the backend over a WebSocket route. The browser can send manual-record commands, and the backend relays those commands to the correct device connection. The device can also send event-style messages back through the same real-time channel.

## 17. Why does privacy matter in this project?

**Answer:**  
Doorbell footage concerns home entry and potentially visitors, so privacy and access control are important. That is why I designed the system around authenticated accounts and ownership scoping instead of a shared public view. The current implementation still needs stronger storage hardening, but privacy was considered as a core design concern.

## 18. How would you harden this for real-world deployment?

**Answer:**  
I would enforce device authentication, move media delivery to private or signed URLs, place the backend behind HTTPS and a reverse proxy, centralize more operations behind backend APIs, define stronger row-level security policies, and add monitoring and audit logging.

## 19. Why is this more than just a prototype?

**Answer:**  
Because it already integrates hardware triggers, cloud upload, user accounts, ownership control, dashboard review, deletion, storage visibility, retry behavior, and real-time commands into one working system. It still has product-grade gaps, but it goes well beyond a one-off concept demo.

## 20. If you had more time, what would you improve first?

**Answer:**  
First I would harden security and media privacy, then improve deployment and testing, and only after that revisit more advanced streaming architecture. That order gives the biggest product value without destabilizing the current reliable core.
