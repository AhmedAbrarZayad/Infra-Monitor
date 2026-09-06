# Operational Permissions and Notifications Implementation Plan

## 1. Purpose

This document is the implementation plan for
[Operational Permissions and Notifications](Operational%20Permissions%20and%20Notifications.md).
It covers organization roles, service-scoped Admin access, Engineer work
assignment, role-aware Flutter screens, an in-app notification inbox, and
Firebase Cloud Messaging (FCM).

Analytics is excluded. Firebase Authentication and Google Sign-In are not part
of this design: Django authentication and organization memberships remain the
identity and authorization source of truth. Seeded Django accounts may be used
for end-to-end notification tests once a real app installation has registered
an FCM token.

## 2. Current repository baseline

The repository already provides:

- organization memberships with `OWNER`, `ADMIN`, and `ENGINEER` roles;
- organization-scoped server, incident, anomaly, alert, and AI endpoints;
- incident assignment to a user, status changes, feedback, and update history;
- anomaly listing, detail, and resolution;
- Celery worker, Celery Beat, and Redis infrastructure;
- a global `notifications_enabled` user preference; and
- Flutter organization context, operational pages, and authenticated API access.

The following gaps must be addressed before FCM event routing is safe:

1. `Service` has no Admin-assignment relation.
2. `Incident` identifies a server but not the affected service, so an Admin's
   service scope cannot be determined reliably.
3. `AnomalyDetection` identifies a service but has no Engineer assignee.
4. Current operational list/detail querysets allow every approved organization
   member to read the whole organization.
5. Several writes check only `OWNER`/`ADMIN`, without checking an Admin's
   assigned services.
6. Anomaly resolution currently permits any approved member.
7. Incident acknowledgement and self-assignment currently permit broader
   access than the target policy.
8. The Flutter shell is not role-aware beyond displaying the role name.
9. There is no device-registration, notification-inbox, delivery-attempt, or
   escalation model.
10. Neither the Flutter FCM packages nor the Python Firebase Admin SDK are
    installed or configured.

FCM integration must not begin by sending directly from model signals. Scope,
assignment, event persistence, and execution-time authorization come first.

## 3. Target architecture

```text
Operational transaction
        |
        v
Notification event/outbox row (same database transaction)
        |
        v
Celery delivery task
        |
        +--> revalidate membership, role, service scope and assignment
        +--> create/update in-app recipient records
        +--> apply preferences, severity and deduplication
        +--> send minimal payload to active device registrations through FCM
        +--> persist per-device outcome and deactivate invalid registrations

Flutter notification tap
        |
        v
Select organization -> authenticated API fetch -> authorization recheck
        |
        +--> authorized: show resource
        +--> unauthorized/deleted: show safe unavailable message
```

Django owns recipients and authorization. FCM is an untrusted delivery channel,
not an authorization system. Redis transports jobs but is not the durable
record of a notification.

## 4. Domain and schema changes

### 4.1 Service-to-Admin assignments

Add `ServiceAdminAssignment` under the servers domain:

| Field | Purpose |
| --- | --- |
| `id` | UUID primary key |
| `service` | Assigned `Service` |
| `membership` | Approved organization `ADMIN` membership |
| `assigned_by` | Owner who created the assignment |
| `created_at` | Audit timestamp |

Constraints and validation:

- unique `(service, membership)`;
- membership organization must equal the service's organization;
- membership must be approved and have role `ADMIN`;
- actor must be the organization's Owner;
- an Admin role demotion or membership removal must remove/deactivate their
  service assignments transactionally; and
- service deletion follows the service retention policy and cascades its
  assignments.

Reference `OrganizationMembership`, rather than only `Users`, because roles and
approval are organization-specific.

### 4.2 Incident service identity

Add a nullable `service` foreign key to `Incident`, indexed and using
`SET_NULL`, then make service identity mandatory for newly created
service-originated incidents.

Migration and compatibility rules:

- backfill lifecycle incidents from the service that produced them;
- backfill correlated anomaly incidents from `AnomalyDetection.service_id`;
- leave genuinely server-wide legacy incidents with `service=NULL`;
- only the Owner can access or assign a server-wide incident until an explicit
  server-to-Admin policy is introduced; and
- validate that incident organization, server, and service all agree.

Update every incident creation path, presenter, filter, and test to include
`service_id` and service display information.

### 4.3 Engineer assignment for anomalies

Add these fields to `AnomalyDetection`:

- `assigned_to`, nullable `AUTH_USER_MODEL`, `SET_NULL`, indexed;
- `assigned_at`, nullable timestamp; and
- `assigned_by`, nullable `AUTH_USER_MODEL`, `SET_NULL`.

The assigned user must have an approved `ENGINEER` membership in the anomaly's
organization. Resolution fields remain separate from assignment fields.

Add anomaly assignment history rather than relying only on the current row.
Either introduce `AnomalyUpdate`, matching `IncidentUpdate`, or introduce a
shared immutable operational-work audit event with resource type and resource
UUID. Assignment, reassignment, resolution, and comments must be reconstructable.

### 4.4 Device registrations

Add a notifications app with `DeviceRegistration`:

| Field | Purpose |
| --- | --- |
| `id` | UUID primary key |
| `user` | Django user who currently owns the app installation |
| `token` | Send-capable FCM registration value, protected as sensitive data |
| `token_fingerprint` | SHA-256 fingerprint for lookup/logging without disclosure |
| `installation_id` | Firebase Installation ID when available |
| `platform` | `ANDROID`, `IOS`, or `WEB` |
| `device_name` | Optional user-visible label |
| `app_version` | Diagnostic metadata |
| `notifications_authorized` | Last client-reported OS permission state |
| `active` | Whether sends are allowed |
| `last_registered_at` | Last authenticated token upload |
| `last_seen_at` | Last app synchronization |
| `invalidated_at` | When FCM or logout invalidated the registration |
| timestamps | Creation and update audit fields |

Requirements:

- support multiple installations per user;
- make the active token/fingerprint unique;
- atomically transfer a reused installation token to the currently
  authenticated user after login, preventing delivery to a previous account on
  the same device;
- deactivate the current user's registration on logout when the client can
  reach Django;
- never return another user's raw token;
- never log raw tokens; and
- prune stale and FCM-invalid registrations.

The database must retain a send-capable token, so a one-way hash alone is not
sufficient. Protect the field through application/database encryption and
restrict operational access.

### 4.5 Durable notification records

Add the following models:

#### `NotificationEvent`

- organization;
- stable event type;
- resource type and UUID;
- service and severity where applicable;
- safe template variables, without secrets or full evidence;
- deduplication key with a database uniqueness constraint;
- creation time; and
- dispatch state and timestamps.

#### `UserNotification`

- event and recipient user;
- title/body suitable for the in-app inbox;
- `read_at`, `archived_at`, and creation time;
- recipient-reason code such as `SERVICE_ADMIN`, `ASSIGNEE`, or `ESCALATED_OWNER`;
- unique `(event, user)`.

This is the durable inbox and must exist independently of push success.

#### `NotificationDelivery`

- user notification and device registration;
- attempt number;
- state: `PENDING`, `SENT`, `FAILED_RETRYABLE`, `FAILED_PERMANENT`, or `SKIPPED`;
- FCM message ID where available;
- sanitized provider error code;
- attempted/sent timestamps; and
- uniqueness/idempotency protection for a logical delivery attempt.

Do not store provider credentials or raw access tokens in any notification row.

### 4.6 Preferences and escalation policy

Keep the existing global `notifications_enabled` switch and add structured
preferences for at least:

- incident created;
- anomaly created;
- assignment/reassignment;
- status and feedback changes;
- recovery/resolution;
- minimum severity; and
- push versus in-app delivery.

In-app critical records should not disappear merely because push is disabled.

Add one organization-level escalation policy managed by the Owner:

- acknowledgement timeout;
- severity levels that escalate;
- whether the Owner receives all critical events; and
- enabled/disabled state.

## 5. Central authorization layer

Do not duplicate role checks across views. Add reusable scoped-query and
capability functions in the common/authorization layer.

Required primitives include:

- `services_visible_to(membership)`;
- `servers_visible_to(membership)`;
- `incidents_visible_to(membership)`;
- `anomalies_visible_to(membership)`;
- `can_manage_service(membership, service)`;
- `can_assign_work(membership, service)`;
- `can_operate_incident(membership, incident)`;
- `can_operate_anomaly(membership, anomaly)`; and
- `eligible_engineers(organization)`.

Expected scope behavior:

| Role | Services | Incidents/anomalies | Mutations |
| --- | --- | --- | --- |
| Owner | Organization-wide | Organization-wide | All authorized operational actions |
| Admin | Explicit assignments | Records for assigned services | In-scope assignment and operations |
| Engineer | Related to assigned work | Assigned records only | Assigned-work actions only |

Apply these primitives to overview counts, server/service list and detail,
metric ranges, alerts, incidents, anomalies, AI evidence, conversations, and
audit/notification history. Parent server visibility must not grant visibility
to sibling services.

Return `404` for an out-of-scope resource to avoid confirming its existence.
Use `403` only when the resource is visible but the requested action is not
allowed.

## 6. API implementation

### 6.1 Service Admin assignments

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/organizations/{org}/services/{service}/admins/` | Owner; assigned Admin read-only | List assignments |
| `PUT` | `/api/organizations/{org}/services/{service}/admins/` | Owner | Replace assignment set atomically |
| `POST` | `/api/organizations/{org}/services/{service}/admins/{membership}/` | Owner | Add one Admin |
| `DELETE` | `/api/organizations/{org}/services/{service}/admins/{membership}/` | Owner | Remove one Admin |

Replacement must validate every membership before making any change.

### 6.2 Work assignment

Keep the incident assignment endpoint and add the equivalent anomaly endpoint:

| Method | Endpoint | Permission |
| --- | --- | --- |
| `PATCH` | `/api/organizations/{org}/incidents/{incident}/assignment/` | Owner or in-scope Admin |
| `PATCH` | `/api/organizations/{org}/anomalies/{detection}/assignment/` | Owner or in-scope Admin |

Use one request contract:

```json
{
  "user_id": 123
}
```

`user_id: null` clears the assignment. Return `409` for stale reassignment when
an optional expected-assignee precondition does not match.

Remove unrestricted Engineer self-assignment unless product requirements add a
separate visible work queue. Engineers must not use self-assignment to bypass
service scope.

### 6.3 Device registration

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `PUT` | `/api/auth/me/devices/{installation_id}/` | Register or refresh the current installation |
| `DELETE` | `/api/auth/me/devices/{installation_id}/` | Deactivate it for the current user |
| `GET` | `/api/auth/me/devices/` | List sanitized current-user devices |

Token upload requires normal Django authentication. It does not require a real
email address, Google Sign-In, or Firebase Authentication.

### 6.4 Notification inbox and preferences

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/organizations/{org}/notifications/` | Scoped current-user inbox |
| `GET` | `/api/organizations/{org}/notifications/unread-count/` | Badge count |
| `PATCH` | `/api/organizations/{org}/notifications/{id}/read/` | Mark one read/unread |
| `POST` | `/api/organizations/{org}/notifications/mark-all-read/` | Mark visible inbox read |
| `GET/PATCH` | `/api/auth/me/notification-preferences/` | Personal preferences |
| `GET/PATCH` | `/api/organizations/{org}/notification-policy/` | Owner escalation policy |
| `GET` | `/api/organizations/{org}/notification-deliveries/` | Owner/all, Admin/scoped, Engineer/own |

Every notification lookup is recipient- and organization-scoped.

## 7. Event production and routing

Create notification events inside the same transaction as the authoritative
operational change. Enqueue delivery with `transaction.on_commit`; never send
before the transaction commits.

Use explicit domain service calls rather than broad Django signals, which hide
causality and can send during fixtures, migrations, or partial transactions.

### 7.1 Initial event catalog

| Event | Trigger | Initial recipients |
| --- | --- | --- |
| `INCIDENT_CREATED` | New service incident | Assigned service Admins; Owner fallback |
| `ANOMALY_CREATED` | New `is_anomaly=true` detection | Assigned service Admins; Owner fallback |
| `INCIDENT_ASSIGNED` | Engineer assigned/reassigned | New Engineer; previous Engineer on removal |
| `ANOMALY_ASSIGNED` | Engineer assigned/reassigned | New Engineer; previous Engineer on removal |
| `INCIDENT_STATUS_CHANGED` | Material status transition | Assignee and service Admins as applicable |
| `WORK_FEEDBACK_ADDED` | Investigation/resolution comment | Assignee/service Admins except actor |
| `SERVICE_RECOVERED` | Lifecycle recovery | Assignee and service Admins |
| `INCIDENT_RESOLVED` | Manual or automatic resolution | Assignee and service Admins |
| `ANOMALY_RESOLVED` | Manual resolution | Assignee and service Admins |
| `WORK_ESCALATED` | Acknowledgement deadline exceeded | Owner |

Suppress notifying the actor unless the event is a requested confirmation.

### 7.2 Deduplication examples

- incident creation: `incident:{incident_id}:created`;
- anomaly creation: `anomaly:{detection_id}:created`;
- assignment: `{resource}:{id}:assignee:{assignment_version}`;
- status: `incident:{id}:status:{transition_version}`;
- recovery: `service:{id}:recovery:{lifecycle_transition_id}`; and
- escalation: `{resource}:{id}:escalation:{policy_version}:{deadline}`.

The internal anomaly endpoint uses `update_or_create`; emit
`ANOMALY_CREATED` only when a new anomalous record is created or when a defined
state transition warrants a new event. Retries for the same model window must
not notify again.

### 7.3 Recipient revalidation

The delivery worker must resolve recipients again immediately before creating
push deliveries:

- service Admin still assigned and approved;
- Engineer still assigned and approved;
- Owner membership still authoritative;
- recipient preference allows the optional push type;
- device registration remains active and fresh; and
- resource remains accessible.

When no service Admin exists, create an Owner fallback notification. If every
Admin push delivery permanently fails, enqueue a deduplicated Owner escalation
without removing the Admins' in-app notifications.

## 8. FCM backend integration

1. Add a pinned compatible `firebase-admin` dependency to the backend.
2. Initialize one Firebase app lazily in the notification transport, not at
   Django module-import time.
3. Use Application Default Credentials. For local/on-premises Compose, mount a
   service-account JSON file read-only outside the repository and set
   `GOOGLE_APPLICATION_CREDENTIALS` in the backend and Celery worker.
4. Add `FIREBASE_PROJECT_ID`, `FCM_ENABLED`, timeouts, retry limits, and stale
   registration age to environment examples.
5. Never bake the service-account file into an image, commit it, expose it to
   Flutter, or print it in logs.
6. Send individual device messages with minimal data payloads and platform-safe
   notification fields.
7. Treat provider throttling and transient network errors as retryable with
   bounded exponential backoff.
8. Mark `UNREGISTERED` tokens inactive. Treat `INVALID_ARGUMENT` as an invalid
   token only after validating that the payload itself is valid.
9. Persist the provider message ID and sanitized result for operations support.
10. When `FCM_ENABLED=false`, continue creating inbox records and mark push
    delivery as skipped; local development must remain functional.

Official setup references:

- [Firebase Admin SDK setup](https://firebase.google.com/docs/admin/setup)
- [Flutter FCM setup](https://firebase.google.com/docs/cloud-messaging/flutter/get-started)
- [FCM registration management](https://firebase.google.com/docs/cloud-messaging/manage-tokens)

## 9. Flutter implementation

### 9.1 Firebase bootstrap

- Add `firebase_core` and `firebase_messaging`.
- Configure only the intended platforms with FlutterFire CLI.
- Initialize Firebase before `runApp`.
- Register a top-level background-message handler where required.
- Request notification permission contextually on Android 13+, iOS, and web.
- Retrieve the installation/token after Django login and upload it through the
  authenticated device endpoint.
- Listen for token refresh and re-upload it with a fresh timestamp.
- Deactivate the registration during logout when possible; backend ownership
  transfer on the next login is still required for crash/offline cases.

### 9.2 Foreground, background, and terminated behavior

- Foreground: show an in-app banner and refresh unread count.
- Background/terminated tap: parse only allowlisted event types and UUIDs.
- Select the referenced organization if it remains available to the user.
- Navigate to incident or anomaly detail only after the API fetch succeeds.
- Show a generic unavailable message on `403/404`, never cached sensitive
  details from the push payload.

Do not use Firebase Dynamic Links. Use app routing driven by the notification
data and authenticated resource lookup.

### 9.3 Role-aware screens

Implement server-driven scope plus client-side affordance checks:

- Owner sees all operational screens, service Admin assignment, enrollment,
  credentials, Team Management, audit, basic notification status, and
  notification policy.
- Admin sees assigned services and their work, Engineer assignment controls,
  member approval/removal, scoped history, and personal preferences.
- Engineer sees assigned work, related read-only context, permitted workflow
  actions, personal inbox, and personal preferences.

Remove Analytics imports/page slots and ensure navigation title/page/destination
arrays have the same length. Route guards must protect direct navigation to
Owner/Admin pages, while the API remains the final enforcement point.

### 9.4 Required UI additions

- Owner service-detail Admin assignment control;
- Owner/Admin incident Engineer assignment control;
- Owner/Admin anomaly Engineer assignment control;
- anomaly resolution control on both Overview and server detail where allowed;
- notification inbox and unread badge;
- per-user notification settings;
- Owner escalation-policy screen;
- basic notification delivery/acknowledgement status on the relevant detail
  screen; and
- safe notification deep-link handling.

UI completeness rule: if any implemented user-facing capability in this plan
has no existing Flutter screen or control, add the smallest usable UI for it.
Do not consider an API-only implementation complete when an Owner, Admin, or
Engineer must interact with or inspect that capability. This includes device
registration state when troubleshooting is necessary, the inbox, notification
preferences, acknowledgement, basic delivery status, Owner fallback/escalation
policy, and unavailable deep-link feedback. Follow the existing design system
and role/capability guards; do not add a production-scale operations dashboard.

## 10. Escalation and maintenance tasks

Add Celery tasks for:

- dispatching a notification event;
- sending/retrying a device delivery;
- finding unacknowledged eligible incidents/anomalies past their deadline;
- escalating to the Owner with a stable deduplication key; and
- pruning stale or invalid device registrations.

Run escalation checks frequently enough to meet the policy, for example once
per minute. Use database deadlines and idempotency constraints so duplicate
Celery Beat delivery or worker restarts cannot create duplicate notifications.

## 11. Testing strategy

### 11.1 Authorization matrix tests

For every scoped collection, detail, and mutation, test:

- Owner in the same organization;
- assigned Admin;
- unassigned Admin;
- assigned Engineer;
- unassigned Engineer;
- pending member;
- member from another organization; and
- removed/demoted member after a previously valid assignment.

Assert both response status and queryset contents. Include sibling services on
the same server to prove parent-server visibility does not leak their data.

### 11.2 Model and migration tests

- assignment uniqueness and cross-organization rejection;
- only approved Admin memberships can receive services;
- only approved Engineers can receive work;
- incident service/server/organization consistency;
- legacy server-wide incident handling;
- role demotion/removal cleanup;
- device-token ownership transfer; and
- deduplication constraints under concurrent event creation.

### 11.3 Notification routing tests

- assigned Admin recipients only;
- Owner fallback when no Admin exists;
- new and previous Engineer behavior on reassignment;
- actor suppression;
- preference and severity filtering;
- automatic recovery and manual resolution;
- execution-time permission revalidation;
- repeated anomaly callback deduplication;
- all-device failure escalation; and
- in-app notification creation when FCM is disabled or unavailable.

Mock the Firebase transport in normal test suites. Do not contact FCM from unit
or CI tests.

### 11.4 Flutter tests

- navigation and controls for each role/scope;
- token upload only after authenticated session establishment;
- token refresh and logout handling;
- foreground notification refresh;
- background deep-link organization selection;
- unauthorized/deleted target handling;
- inbox unread/read behavior; and
- Analytics remains absent from navigation.

### 11.5 Manual seeded-account test

Use an Owner, an Admin, and an Engineer seed account. Real email delivery is not
required. Use separate devices/emulators where possible; otherwise log out and
log in carefully so device-token ownership transfer is exercised.

1. Register the Owner device and enable notifications.
2. Assign an Admin to one service but not a sibling service.
3. Register the Admin device.
4. Create an incident/anomaly for the assigned service and confirm only that
   Admin receives it.
5. Create work for the unassigned sibling and confirm the Admin receives
   nothing while the Owner receives fallback/escalation behavior.
6. Assign the first item to the seeded Engineer and confirm the Engineer device
   receives it.
7. Resolve/recover the item and verify scoped follow-up notifications and inbox
   records.
8. Remove the Admin service assignment and confirm future access and delivery
   stop immediately.

## 12. Delivery phases

### 12.1 Developer and AI handoff context

This plan is intended to be executable by another developer or coding agent.
Before changing code, inspect the current backend and Flutter implementation,
existing migrations, tests, API conventions, authorization helpers, Celery
configuration, and organization-context state. Treat the repository as the
source of truth when a class, field, route, or filename differs from this plan;
adapt the implementation without weakening tenant isolation or role checks.

Assume Phases 1 and 2 provide service-scoped authorization and Owner -> Admin
-> Engineer assignment. Phases 3 through 5 build notification behavior on top
of that foundation. Django and organization memberships remain the identity
and authorization authority. Firebase Authentication is not required. FCM is
only a delivery channel: every notification must remain available through the
durable Django-backed inbox even when FCM is disabled or unavailable.

Implementation rules for Phases 3 through 5:

- preserve existing user changes and follow repository conventions;
- create additive, reversible migrations and do not rewrite old migrations;
- keep all queries organization-scoped and recheck access at send and open
  time;
- enqueue Celery work only after the database transaction commits;
- make event creation, delivery, and escalation idempotent with database
  constraints, not only application checks;
- never place secrets, raw device tokens, evidence, or sensitive incident data
  in logs or FCM payloads;
- mock Firebase in automated tests; real FCM is only for a controlled manual
  test;
- keep the Phase 5 scope minimal; and
- add the smallest role-appropriate Flutter UI whenever required functionality
  has no existing UI. API completion alone is not sufficient for user-facing
  behavior.

Before starting each phase, run the relevant existing test suites and record
the baseline. After implementation, run focused backend tests, Flutter tests,
formatters/static analysis, and any repository-required checks. If a test
cannot run because credentials or external infrastructure are unavailable,
document that limitation and verify the local/fake-transport path instead.

### Phase 1: Authorization foundation

- Add service-to-Admin assignments and central scoped-query helpers.
- Add incident service identity and anomaly Engineer assignment.
- Backfill compatible records.
- Enforce role/scope on all backend reads and writes.
- Add the full authorization matrix test suite.

Exit criterion: an unassigned Admin or Engineer cannot retrieve an out-of-scope
resource by list, detail, metric, AI, alert, or audit endpoint.

### Phase 2: Assignment APIs and role-aware Flutter UI

- Implement Owner service-to-Admin assignment.
- Implement consistent incident/anomaly Engineer assignment.
- Add assignment history.
- Scope Flutter data and controls by capabilities.
- Remove the Analytics slot cleanly.

Exit criterion: Owner -> Admin -> Engineer assignment works end to end without
notifications and survives refresh/relogin.

### Phase 3: Durable notification core

Goal: build and verify the complete notification workflow without depending on
Firebase.

Backend implementation:

1. Create the notifications app, or extend the existing one, with
   `DeviceRegistration`, `NotificationEvent`, `UserNotification`,
   `NotificationDelivery`, structured user preferences, and the organization
   escalation policy described in Section 4. Use migrations and database
   uniqueness constraints for deduplication.
2. Add serializers/services for device registration, inbox listing, unread
   count, mark-read/mark-all-read, preferences, policy, and the minimal delivery
   status required by the UI. Raw FCM tokens must never be returned by an API.
3. Implement the authenticated endpoints in Sections 6.3 and 6.4 with
   organization and recipient scoping. If a separate delivery-history endpoint
   is retained internally, do not build the deferred full history UI; expose
   only the basic status needed by the relevant detail screen.
4. Produce `NotificationEvent` inside the same transaction as each supported
   operational change. Schedule dispatch with `transaction.on_commit`.
5. Implement recipient routing for assigned service Admins and assigned
   Engineers, preference/severity filtering, actor suppression, and durable
   `UserNotification` creation. Owner fallback and timeout escalation may be
   completed in Phase 5, but routing must provide a clean extension point.
6. Add Celery dispatch/delivery tasks and a fake transport selected when FCM is
   disabled. The fake transport must create deterministic delivery outcomes so
   tests can verify `PENDING`, `SENT`, `FAILED`, and `SKIPPED` behavior.
7. Revalidate membership, role, service scope, assignment, and resource access
   immediately before delivery. A permission change must prevent a pending
   unauthorized send.

Flutter implementation:

1. Add the notification inbox, unread badge, read/unread actions, and personal
   preference controls using the existing app architecture and design system.
2. Add an Owner-only minimal notification-policy form if no policy UI exists.
3. Add loading, empty, failure, and unauthorized states. Hide controls the
   current role cannot use, while keeping backend authorization authoritative.
4. If any Phase 3 API represents behavior a user must view or change and no UI
   exists, add the smallest usable role-aware screen or control for it.

Tests:

- model validation, migration compatibility, uniqueness, and tenant isolation;
- endpoint authorization and recipient-only inbox access;
- transaction rollback produces no dispatched notification;
- repeated event production creates one logical event/recipient;
- permission changes before task execution prevent delivery;
- preferences, severity filtering, and FCM-disabled/fake-transport behavior;
  and
- Flutter inbox, unread count, preferences, policy permissions, and UI states.

Exit criterion: all events create correct durable recipients and delivery
records with FCM disabled, and users can access the inbox and required settings
through role-appropriate Flutter UI.

### Phase 4: FCM and Flutter messaging

Goal: replace the fake push transport with FCM while keeping the durable inbox
and authorization behavior unchanged.

Backend implementation:

1. Add and pin the Firebase Admin SDK, environment settings, feature flag,
   credential documentation, timeouts, and bounded retry settings. Initialize
   Firebase lazily in the transport layer.
2. Implement one-device-at-a-time sends with minimal allowlisted payload data.
   Persist the provider message ID and sanitized outcome; never log the raw
   token or credentials.
3. Classify provider responses into sent, retryable failure, permanent failure,
   and invalid registration. Use bounded exponential backoff and preserve
   Celery idempotency.
4. Deactivate invalid/unregistered tokens immediately. Keep periodic age-based
   pruning optional until Phase 5 and do not let push failure remove the inbox
   notification.

Flutter implementation:

1. Configure Firebase only for the supported demo platforms and initialize it
   before the application starts.
2. After Django login, request notification permission contextually, obtain the
   installation/token, register it through the authenticated API, listen for
   refresh, and deactivate it on logout when possible.
3. Handle foreground messages, background/terminated notification taps, and
   unread-count refresh. Fetch the referenced resource from Django before
   displaying its details.
4. Add safe deep-link routing with allowlisted event/resource types,
   organization selection, and a generic unavailable message for deleted or
   unauthorized targets.
5. Add any missing user-facing permission prompt, notification settings entry,
   inbox entry point, status indicator, or unavailable-state UI needed to make
   this flow demonstrable end to end.

Tests and verification:

- backend transport tests with mocked Firebase success, transient failure,
  permanent failure, invalid token, and retry exhaustion;
- token ownership transfer, refresh, logout, and cross-user isolation tests;
- Flutter foreground/background routing and unauthorized/deleted-target tests;
- confirm FCM-disabled mode still works entirely through the durable inbox; and
- manually test seeded Owner, Admin, and Engineer accounts on registered demo
  devices/emulators without using real FCM in CI.

Exit criterion: seeded Admin and Engineer accounts receive the correct push on
their registered devices, unauthorized accounts receive nothing, and every
push remains represented in the durable inbox and basic status UI.

### Phase 5: Essential reliability

Keep this phase intentionally small for the varsity-project scope. It includes
only the reliability behavior needed to demonstrate that notifications are
reasonably safe and useful:

- **Owner fallback:** when an incident or anomaly has no eligible assigned
  responder, notify the organization Owner.
- **One-step acknowledgement timeout:** if the original responder does not
  acknowledge a notification within the configured time, send one
  deduplicated reminder or escalate it once to the Owner. Do not implement
  multi-level escalation chains.
- **Basic delivery status:** expose only `SENT`, `FAILED`, and `ACKNOWLEDGED` on
  the related incident/anomaly or notification detail. A separate operational
  metrics dashboard and a full delivery-history screen are deferred.
- **Stale-token cleanup:** when FCM reports that a device token is invalid,
  deactivate it so later notifications do not repeatedly fail. Periodic,
  production-scale token-maintenance jobs may be deferred.
- **Focused safety tests:** verify tenant isolation, role permissions,
  permission changes before delivery, and that duplicate or concurrent
  escalation processing creates only one logical escalation.

Implementation steps:

1. Define exactly which incident/anomaly states require acknowledgement and
   what existing action counts as acknowledgement. Reuse an existing
   acknowledgement field/action where available; otherwise add the smallest
   timestamp, actor field, authenticated endpoint, and role-appropriate Flutter
   button/status needed to support it.
2. Store an acknowledgement deadline when an eligible notification is created.
   Add one periodic Celery task that finds expired, unacknowledged work and
   creates one Owner escalation using a stable database-backed deduplication
   key. Do not build multi-level escalation chains.
3. When no eligible assigned responder/service Admin exists at initial routing,
   create the Owner fallback notification. Clearly record the recipient reason
   as `ESCALATED_OWNER` or the equivalent repository convention.
4. Map detailed internal delivery states to the three user-facing values:
   `SENT`, `FAILED`, and `ACKNOWLEDGED`. Show this on the relevant notification,
   incident, or anomaly detail screen. Add the UI if it does not already exist.
5. On an FCM invalid/unregistered response, deactivate the device registration
   and exclude it from later sends. A simple optional scheduled cleanup based
   on `last_seen_at` is acceptable, but a complex pruning system is not needed.
6. Add focused tests for cross-tenant access, role permissions, revocation
   before delivery, Owner fallback, timeout behavior, and concurrent duplicate
   escalation. Use transaction/concurrency tests supported by the repository's
   test database.

Dashboards, detailed operational metrics, advanced retry tuning, formal outage
testing, and extensive runbooks are outside the current project scope and may
be added later if the system is prepared for production use.

Exit criterion: Owner fallback and the single acknowledgement escalation work,
users can see the basic delivery state, invalid FCM tokens are deactivated, and
the focused authorization and duplicate-escalation tests pass.

## 13. Suggested repository work map

Backend areas:

- `backend/common/`: centralized capabilities and scoped querysets;
- `backend/servers/`: service Admin assignment model, service APIs, lifecycle
  notification events;
- `backend/incident/`: service identity, scoped workflow and assignment events;
- `backend/ml_model/`: anomaly assignment, scoped resolution and creation events;
- `backend/accounts/`: structured preferences and membership cleanup hooks;
- `backend/notifications/`: device registrations, inbox, delivery, policy,
  routing, FCM transport, Celery tasks, APIs, and tests;
- `backend/infra_monitor/settings.py`: Firebase, retry, pruning and escalation
  configuration; and
- `docker-compose.yml`: read-only credential mount and matching worker
  environment.

Flutter areas:

- `frontend/pubspec.yaml` and generated Firebase platform configuration;
- `frontend/lib/core/`: Firebase bootstrap, authenticated token registration,
  message handling and routing;
- organization context/capability providers;
- server/service Admin assignment UI;
- incident/anomaly Engineer assignment and workflow controls;
- notification inbox, preferences, and basic delivery status; and
- role-aware navigation and route guards.

## 14. Rollout and compatibility

Use feature flags for `SCOPED_OPERATIONAL_ACCESS` and `FCM_ENABLED`.

Recommended rollout:

1. deploy additive schema migrations;
2. backfill incident service identity and create initial service assignments;
3. audit records that cannot be safely scoped;
4. deploy scoped APIs in report-only logging mode if necessary;
5. enable backend scope enforcement before exposing role-specific UI;
6. enable durable inbox/event production with FCM disabled;
7. register test devices and enable FCM for a test organization;
8. validate recipient isolation and failure behavior; and
9. expand rollout while monitoring delivery, deduplication, and authorization
   denial metrics.

Do not enable Admin scoping before every production service has an intentional
assignment or a documented Owner-only fallback. Do not send pushes before the
durable event and execution-time permission checks are active.

## 15. Definition of done

The implementation is complete when:

- all operational APIs enforce the documented Owner/Admin/Engineer scopes;
- the Owner can assign Admins to services;
- Owners and in-scope Admins can assign incidents and anomalies to approved
  Engineers;
- Engineers can operate only their assigned work;
- Flutter shows only authorized screens, records, and controls;
- every notification has a durable event and in-app recipient record;
- FCM payloads contain identifiers and safe routing metadata only;
- recipient authorization is checked again at send and open time;
- device token refresh, reuse, logout, invalidation, and pruning are handled;
- retries and repeated event callbacks cannot create duplicate logical pushes;
- Owner fallback and escalation behavior is tested;
- seeded Django users can complete the full device-notification workflow
  without Google Sign-In or real email delivery; and
- Analytics is absent from the implemented navigation and permission surface.
