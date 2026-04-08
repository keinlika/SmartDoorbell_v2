# Limitations and Future Work

## 1. Current Limitations

The current system is functional and coherent, but it still has limitations that should be presented honestly.

### 1.1 Live preview architecture is simple

The dashboard preview uses the device’s direct MJPEG stream on port `8001`. This works well for a controlled environment, but it is not a full cloud-relayed streaming architecture.

### 1.2 Device authentication is not strict by default

The backend supports strict device authentication, but the default mode is `shadow` rather than `enforce`.

### 1.3 Storage delivery is not fully hardened

Clips are represented through public storage URLs rather than private signed delivery.

### 1.4 Frontend writes are not fully backend-centralized

Some profile and device-membership interactions are performed directly through the Supabase JS client.

### 1.5 Limited automated testing

The repository does not currently include a complete automated test suite for backend, frontend, and device behavior.

### 1.6 Hardware constraints

The Raspberry Pi 3B+ limits how aggressive video quality and always-on processing can be.

### 1.7 Single-process simplicity

The current WebSocket relay and backend model are intentionally simple. They are suitable for the project’s scale, but not yet for large-scale multi-tenant deployment.

## 2. Why These Constraints Exist

These constraints exist for understandable engineering reasons:

- the project balances scope against senior-project timelines
- the hardware platform is intentionally low-cost and modest
- the architecture prioritizes reliability and explainability over maximum feature complexity
- cloud services were chosen to reduce reinvented infrastructure

In other words, most limitations are the result of deliberate tradeoffs rather than oversight.

## 3. Prototype-Stage Limitations

The following are best described as prototype-stage limitations:

- simplified live streaming model
- limited automated testing
- partial direct frontend-to-Supabase write behavior
- development-friendly device-auth defaults

These do not prevent the system from functioning, but they do mark the difference between a strong academic system and a fully hardened commercial platform.

## 4. Product-Grade Future Roadmap

The following improvements would be appropriate in a next phase.

### Security and privacy

- move all clip access to private storage with signed URLs
- enforce device authentication by default
- add more backend-owned write APIs
- define stronger audit logging and rate limiting

### Streaming and media

- evaluate a more scalable remote preview path
- support stronger multi-device live-view routing
- consider hardware-accelerated encoding where available

### Operations

- add systemd services or containers for easier startup
- add monitoring, structured logs, and alerting
- add more robust secret and configuration management

### Testing

- add backend API tests
- add UI end-to-end tests
- add repeated long-duration device soak tests

### Product features

- richer notifications
- better user invitations and household management
- clip search and filtering
- event labels and thumbnails
- configurable retention policies per device or plan

## 5. Why Hot-Swap Still Makes Sense Today

One likely question is why the project does not already use a more advanced single-pipeline recording/preview architecture.

The answer is that on Raspberry Pi 3B+, the current hot-swap model is still the best tradeoff for the present goals:

- better recording reliability
- better saved clip quality
- lower CPU pressure
- smaller implementation risk

It is a limitation in one sense, but also a deliberate optimization for the hardware actually used.

## 6. Realistic Next Phase

If the project continued into a second phase, the most realistic sequence would be:

1. harden security and storage access
2. improve test coverage
3. improve operational deployment and HTTPS
4. then revisit more advanced streaming architecture

This order matters because there is more value in making the current system secure and dependable than in adding technically flashy features first.

## 7. Conclusion

The current project is beyond a toy prototype, but it is not yet a full commercial product. That is the honest and academically defensible position. Its limitations are clear, explainable, and paired with realistic next steps.
