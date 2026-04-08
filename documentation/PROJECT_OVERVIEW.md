# Sentio Smart Doorbell System: Project Overview

## 1. Project Summary

This project is a smart doorbell system that combines a Raspberry Pi edge device, a cloud-connected backend, Supabase services, and a web dashboard into one end-to-end product. The system captures live video locally, records event clips when a user or motion sensor triggers recording, uploads those clips to cloud storage, and allows authenticated users to review activity through a browser-based dashboard.

The current implementation is not just a loose collection of scripts. It is a working multi-part system with:

- a device-side firmware process that manages the camera, microphone, motion sensor, local stream, recording, and upload retry behavior
- a FastAPI backend that handles authentication-aware APIs, file uploads, event records, device pairing, and real-time communication
- a Supabase-backed data and storage layer for users, devices, memberships, event metadata, and uploaded video files
- a browser dashboard that provides sign-in, account creation, device pairing, live preview, manual recording, event history, storage visibility, and device management

## 2. Problem the Project Solves

Traditional doorbell systems often split functionality across proprietary hardware, closed mobile apps, and subscription-based cloud services. This project explores a more transparent and educational alternative: a self-controlled smart doorbell architecture built from commonly available hardware and modern web technologies.

The project solves several practical problems:

- remote awareness of front-door activity
- cloud-backed review of recorded doorbell events
- authenticated account ownership for specific devices
- event-triggered capture using a motion sensor
- a unified interface for monitoring, reviewing, and managing the system

## 3. Intended Users

The primary target user is a homeowner or small household that wants a smart front-door monitoring system with browser access and account-based device ownership.

A second target audience is academic and engineering review. Because this is a senior project, the system is also designed to demonstrate:

- embedded-to-cloud integration
- authentication and account scoping
- multimedia handling on constrained hardware
- web-based product design
- practical tradeoff decisions between reliability, quality, and complexity

## 4. Why the Project Matters

This project matters because it demonstrates a realistic smart-home product architecture rather than a single isolated component. Many student projects stop at a sensor demo or a simple web page. This system goes further by integrating hardware capture, event-driven behavior, cloud persistence, authenticated user ownership, live and recorded media workflows, and an operational dashboard into one coherent product.

It also addresses a real engineering challenge: how to build a responsive smart-doorbell experience on limited hardware such as a Raspberry Pi 3B+ while still preserving acceptable media quality and system reliability.

## 5. High-Level Project Goals

The high-level goals of the project are:

1. Capture front-door activity from a Raspberry Pi device using camera, microphone, and motion sensor inputs.
2. Provide live visibility through a browser-accessible dashboard.
3. Record and upload event clips reliably when triggered manually or by motion.
4. Associate devices with specific user accounts through a pairing workflow.
5. Store event metadata and media in a cloud-backed system.
6. Present a product-like user experience rather than a basic engineering utility.

## 6. Why It Is More Than a Prototype

Although the system still has limitations that would need to be addressed for full commercial deployment, it already demonstrates characteristics that make it more than a proof-of-concept:

- It has a real ownership model for devices, not just an open test feed.
- It includes authentication-backed access control for dashboard actions and event visibility.
- It separates concerns across firmware, backend, storage, and frontend layers.
- It supports operational realities such as upload retry spooling and long-running WebSocket reconnection loops.
- It includes device pairing, multi-device account access, and viewer membership concepts.
- It uses a configurable environment-variable model rather than hardcoded project-only values.
- It presents a refined dashboard and authentication experience suitable for a product demonstration.

## 7. Current Product Framing

The current product branding in the user interface is **Sentio**. Within the UI, Sentio is treated as the product name, while **SentioSmartHome** appears only in a subtle footer/legal-style context.

## 8. Honest Scope Statement

One important academic point is that the repository contains the currently implemented system, not every idea ever considered for the project. For example, the repository README references broader platform ambitions such as React and STM32 firmware, but the code currently present and running is based on:

- Python firmware on Raspberry Pi
- FastAPI backend
- Supabase services
- static HTML, Tailwind, and JavaScript frontend pages

This documentation is intentionally grounded in the real codebase rather than older aspirational descriptions.
