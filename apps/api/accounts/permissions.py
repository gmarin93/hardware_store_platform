"""Roles and their default permission codes: the single source of truth (ADR 0003).

Services and selectors check permission *codes*, never role names. Splitting
EMPLOYEE later is an additive change here plus matrix/test updates.

Codes marked "reserved" are frozen names for later phases; their owning tasks
enforce them. P1-02A enforces ``branches.*`` and ``staff.manage`` (probe test).
"""

from enum import StrEnum


class Role(StrEnum):
    GUEST = "GUEST"  # unauthenticated principal (or account without a valid role); never stored
    CUSTOMER = "CUSTOMER"
    EMPLOYEE = "EMPLOYEE"
    ADMIN = "ADMIN"


class Perm(StrEnum):
    CATALOG_VIEW_PUBLISHED = "catalog.view_published"
    CATALOG_VIEW_STAFF_FIELDS = "catalog.view_staff_fields"
    BRANCHES_VIEW_ASSIGNED = "branches.view_assigned"
    BRANCHES_VIEW_ALL = "branches.view_all"
    # Reserved (P3+): enforced by the owning quote/order/inventory tasks.
    QUOTES_REQUEST_OWN = "quotes.request_own"
    QUOTES_ACCEPT_OWN = "quotes.accept_own"
    QUOTES_MANAGE = "quotes.manage"
    QUOTES_ISSUE = "quotes.issue"
    QUOTES_RECORD_CONSENT = "quotes.record_customer_consent"
    QUOTES_CONVERT = "quotes.convert"
    INVENTORY_VIEW_INTERNAL = "inventory.view_internal"
    INVENTORY_REPORT_DISCREPANCY = "inventory.report_discrepancy"
    INVENTORY_ADJUST = "inventory.adjust"
    PRICING_MANAGE = "pricing.manage"
    ORDERS_PICK = "orders.pick"
    ORDERS_FULFILL = "orders.fulfill"
    ORDERS_CANCEL = "orders.cancel"
    # Admin-only management.
    STAFF_MANAGE = "staff.manage"
    AUDIT_VIEW = "audit.view"


_GUEST: frozenset[Perm] = frozenset({Perm.CATALOG_VIEW_PUBLISHED})

_CUSTOMER: frozenset[Perm] = _GUEST | {Perm.QUOTES_REQUEST_OWN, Perm.QUOTES_ACCEPT_OWN}

_EMPLOYEE: frozenset[Perm] = _GUEST | {
    Perm.CATALOG_VIEW_STAFF_FIELDS,
    Perm.BRANCHES_VIEW_ASSIGNED,
    Perm.QUOTES_MANAGE,
    Perm.QUOTES_ISSUE,
    Perm.QUOTES_RECORD_CONSENT,
    Perm.QUOTES_CONVERT,
    Perm.INVENTORY_VIEW_INTERNAL,
    Perm.INVENTORY_REPORT_DISCREPANCY,
    Perm.ORDERS_PICK,
    Perm.ORDERS_FULFILL,
    Perm.ORDERS_CANCEL,
}

_ADMIN: frozenset[Perm] = (_EMPLOYEE - {Perm.BRANCHES_VIEW_ASSIGNED}) | {
    Perm.BRANCHES_VIEW_ALL,
    Perm.INVENTORY_ADJUST,
    Perm.PRICING_MANAGE,
    Perm.STAFF_MANAGE,
    Perm.AUDIT_VIEW,
}

ROLE_PERMISSIONS: dict[Role, frozenset[Perm]] = {
    Role.GUEST: _GUEST,
    Role.CUSTOMER: _CUSTOMER,
    Role.EMPLOYEE: _EMPLOYEE,
    Role.ADMIN: _ADMIN,
}


def permissions_for(role: Role) -> frozenset[Perm]:
    return ROLE_PERMISSIONS[role]
