# Operational Permissions and Notifications

## Purpose

This document defines the planned organization-scoped permissions, visible UI
surfaces, operational assignment rules, and Firebase Cloud Messaging (FCM)
notification routing for Infra Monitor.

The three organization roles are:

- `OWNER`, displayed as **Owner** or **Super admin**;
- `ADMIN`; and
- `ENGINEER`.

Roles belong to an organization membership. A user may have a different role
in another organization. The Analytics page is intentionally excluded from
this product scope.

## Access scopes

- The Owner can access every server, service, incident, anomaly, alert, and
  member in the organization.
- The Owner assigns one or more Admins to specific services.
- An Admin can access only their assigned services, the parent-server context
  required to understand those services, and operational records belonging to
  those services.
- An Owner or an in-scope Admin can assign an incident or anomaly to any
  approved Engineer in the same organization.
- An Engineer can access only work assigned to them and the minimum related
  server and service context required to investigate it.
- An Admin cannot assign, view, or modify work belonging to a service outside
  their assigned scope.
- UI visibility is not authorization. Every API queryset and mutation must
  enforce the same organization, service, and assignment boundaries.

## Permission matrix

| Capability | Owner | Admin | Engineer |
| --- | :---: | :---: | :---: |
| View organization overview | All resources | Assigned services | Assigned work |
| View servers | All | Parents of assigned services | Parents of assigned work |
| View services | All | Assigned services | Services related to assigned work |
| Enroll or add servers | Yes | No | No |
| Disconnect servers | Yes | No | No |
| Rotate monitoring credentials | Yes | No | No |
| Assign services to Admins | Yes | No | No |
| View incidents | All | Assigned services | Assigned incidents |
| View anomalies | All | Assigned services | Assigned anomalies |
| Assign incidents to Engineers | Yes | Within assigned services | No |
| Assign anomalies to Engineers | Yes | Within assigned services | No |
| Reassign or clear an assignee | Yes | Within assigned services | No |
| Acknowledge operational work | Yes | Within assigned services | Assigned work |
| Change incident status | Yes | Within assigned services | Assigned incidents |
| Add investigation or resolution notes | Yes | Within assigned services | Assigned work |
| Resolve incidents | Yes | Within assigned services | Assigned incidents |
| Resolve anomalies | Yes | Within assigned services | Assigned anomalies |
| Use the AI assistant | All resources | Assigned services | Assigned work |
| View organization members | Yes | Yes | Optional read-only access |
| Approve or reject Engineer requests | Yes | Yes | No |
| Remove Engineers | Yes | Yes | No |
| Promote an Engineer to Admin | Yes | No | No |
| Demote or remove an Admin | Yes | No | No |
| Manage organization settings | Yes | No | No |
| View audit history | All | Assigned scope | Own actions |
| Configure escalation policy | Yes | No | No |
| Configure personal notification preferences | Yes | Yes | Yes |
| Register personal notification devices | Yes | Yes | Yes |
| View notification delivery history | All | Assigned services | Own notifications |

No role can modify or remove the Owner through normal membership endpoints.
Ownership transfer and organization deletion require separately designed
workflows.

## Screen visibility

### Owner

Show:

- Overview with organization-wide health and attention items;
- Servers with every server and service;
- Incidents with every incident and anomaly;
- AI Assistant with organization-wide authorized telemetry;
- Team Management, membership requests, and role controls;
- service-to-Admin assignment controls;
- monitoring enrollment, disconnection, and credential controls;
- organization settings, audit history, notification escalation settings; and
- More/Profile and personal notification preferences.

### Admin

Show:

- Overview limited to assigned services;
- Servers limited to assigned services and their parent-server context;
- Incidents and anomalies belonging to assigned services;
- Engineer assignment and reassignment controls for in-scope work;
- AI Assistant limited to assigned services;
- Engineer membership approval and removal controls;
- audit and notification-delivery history limited to assigned services; and
- More/Profile and personal notification preferences.

Hide:

- unassigned services and their operational records;
- server enrollment, disconnection, and monitoring credentials;
- Admin promotion, demotion, removal, and service-assignment controls; and
- organization-wide settings and escalation-policy controls.

### Engineer

Show:

- Overview containing assigned workload;
- read-only server and service context for assigned work;
- assigned incidents and anomalies;
- evidence, acknowledgement, investigation, notes, and resolution controls for
  assigned work;
- AI Assistant limited to assigned resources;
- personal notification history; and
- More/Profile and personal notification preferences.

Hide:

- unassigned servers, services, incidents, and anomalies;
- Team Management and membership requests;
- infrastructure enrollment, disconnection, and credentials;
- assignment and reassignment controls;
- organization settings, audit history, and escalation configuration.

## Assignment rules

1. The assignee must be an approved Engineer in the same organization.
2. Owners may assign or clear any incident or anomaly in the organization.
3. Admins may assign or clear work only for their assigned services.
4. Engineers cannot assign or reassign work.
5. Assignment is independent of lifecycle status. It does not make an
   unhealthy service healthy or resolve an anomaly.
6. Removing an Admin's service assignment immediately removes that Admin's
   access to the service and its operational records.
7. Removing an Engineer requires review or reassignment of their unresolved
   work.
8. Assignment, reassignment, unassignment, acknowledgement, status, feedback,
   and resolution changes must be recorded in the audit trail.

## Notification routing

FCM is the notification transport. Django remains authoritative for identity,
authorization, resource state, assignments, recipient selection, preferences,
deduplication, and audit history.

### Incident or anomaly created

Notify all Admins currently assigned to the affected service.

Notify the Owner when:

- the service has no assigned Admin;
- delivery to every assigned Admin fails;
- the item remains unacknowledged beyond its configured escalation threshold;
  or
- an organization-wide critical-event preference explicitly requires it.

Do not notify unrelated Admins or unassigned Engineers.

### Engineer assignment

When an Owner or Admin assigns work:

- notify the newly assigned Engineer;
- notify the previous Engineer when the work is reassigned or cleared;
- show the assigning user an in-app success confirmation; and
- notify the service's assigned Admins when required by their preferences.

### Status and feedback changes

- Notify the assigned Engineer when an Owner or Admin materially updates the
  assigned item.
- Notify the service's assigned Admins when the Engineer acknowledges,
  investigates, comments on, or resolves the item.
- Notify the Owner only for configured critical events or escalation failures.

### Recovery and resolution

Notify the assigned Engineer and the service's assigned Admins when:

- service telemetry recovers;
- an incident is automatically resolved by recovery;
- an incident is manually resolved; or
- an anomaly is manually resolved.

Notification preferences may suppress optional recovery messages, but required
critical escalation notifications must follow the organization's escalation
policy.

## Notification authorization

Immediately before enqueueing or sending a notification, the backend must
confirm that:

- the recipient still has an approved membership in the organization;
- an Admin is still assigned to the affected service;
- an Engineer is still assigned to the incident or anomaly;
- the device token belongs to the intended user;
- the resource still exists and remains within the recipient's access scope;
  and
- the event has not already been delivered under the same deduplication key.

Permission changes must affect future notifications immediately. Previously
issued notifications do not authorize access: opening a notification must
fetch the resource again through an authenticated, scoped API.

## FCM payload policy

Push payloads must contain only the identifiers and small amount of routing
information needed to open the correct screen. For example:

```json
{
  "type": "INCIDENT_ASSIGNED",
  "organization_id": "ORGANIZATION_UUID",
  "incident_id": "INCIDENT_UUID",
  "severity": "CRITICAL"
}
```

Do not include metric evidence, AI reports, credentials, server addresses,
access tokens, private investigation notes, or other sensitive operational
details in an FCM payload. The app retrieves authorized details after opening.

## Device and delivery requirements

- Support multiple devices per user.
- Associate each FCM registration token with its authenticated user and device.
- Rotate tokens and remove invalid or unregistered tokens reported by FCM.
- Allow personal preferences by notification type and severity.
- Use stable event deduplication keys so repeated ML windows or retries do not
  spam recipients.
- Maintain an in-app notification inbox independent of push delivery success.
- Record send attempts, delivery failures where available, recipient selection,
  and related assignment changes in the audit trail.
- Deep links must select the correct organization and then reauthorize access
  before displaying the target resource.

## Out of scope

- Analytics page and analytics-specific permissions;
- ownership transfer;
- organization deletion;
- cross-organization assignments;
- assigning incidents or anomalies to users who are not approved Engineers;
  and
- using Firebase claims or FCM topics as the source of authorization truth.
