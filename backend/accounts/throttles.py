from rest_framework.throttling import UserRateThrottle


class OrganizationSearchThrottle(UserRateThrottle):
    scope = "organization_search"


class MembershipRequestThrottle(UserRateThrottle):
    scope = "membership_request"
