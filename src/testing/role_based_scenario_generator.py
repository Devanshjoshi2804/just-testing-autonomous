"""
Role-Based Test Scenario Generator
Generates test scenarios for different user roles (admin, user, guest, unauthenticated)
Validates role-based access control (RBAC)
"""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
        def debug(self, msg, **kwargs): pass
    logger = MockLogger()


class UserRole(Enum):
    """User roles for access control testing"""
    ADMIN = "admin"           # Full access
    USER = "user"             # Authenticated user with limited access
    GUEST = "guest"           # Limited read-only access
    UNAUTHENTICATED = "unauthenticated"  # No authentication


class AccessLevel(Enum):
    """Expected access level for a role+endpoint combination"""
    ALLOWED = "allowed"       # Should return 2xx
    FORBIDDEN = "forbidden"   # Should return 403
    UNAUTHORIZED = "unauthorized"  # Should return 401


@dataclass
class RolePermission:
    """Represents expected permission for a role on an endpoint"""
    endpoint_key: str
    role: UserRole
    access_level: AccessLevel
    expected_status_codes: List[int]
    description: str


@dataclass
class RoleTestScenario:
    """Test scenario for a specific role on an endpoint"""
    endpoint_key: str
    method: str
    path: str
    role: UserRole
    access_level: AccessLevel
    expected_status_codes: List[int]
    auth_token: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    description: str = ""


class RoleBasedScenarioGenerator:
    """
    Generates test scenarios for role-based access control testing

    Default Permission Model (can be customized):
    - Admin: Full access to all endpoints
    - User: Read own resources, create/update/delete own resources only
    - Guest: Read-only access to public resources
    - Unauthenticated: Access to public endpoints only

    Tests:
    1. Admin can access all endpoints
    2. User can access user-level endpoints
    3. Guest can only read
    4. Unauthenticated gets 401 on protected endpoints
    """

    # Default permission matrix (can be overridden)
    DEFAULT_PERMISSIONS = {
        # Admin has full access
        UserRole.ADMIN: {
            'GET': AccessLevel.ALLOWED,
            'POST': AccessLevel.ALLOWED,
            'PUT': AccessLevel.ALLOWED,
            'PATCH': AccessLevel.ALLOWED,
            'DELETE': AccessLevel.ALLOWED,
        },
        # User has limited access
        UserRole.USER: {
            'GET': AccessLevel.ALLOWED,      # Can read
            'POST': AccessLevel.ALLOWED,     # Can create
            'PUT': AccessLevel.ALLOWED,      # Can update (own resources)
            'PATCH': AccessLevel.ALLOWED,    # Can update (own resources)
            'DELETE': AccessLevel.FORBIDDEN, # Cannot delete (admin only)
        },
        # Guest has read-only access
        UserRole.GUEST: {
            'GET': AccessLevel.ALLOWED,
            'POST': AccessLevel.FORBIDDEN,
            'PUT': AccessLevel.FORBIDDEN,
            'PATCH': AccessLevel.FORBIDDEN,
            'DELETE': AccessLevel.FORBIDDEN,
        },
        # Unauthenticated has no access
        UserRole.UNAUTHENTICATED: {
            'GET': AccessLevel.UNAUTHORIZED,
            'POST': AccessLevel.UNAUTHORIZED,
            'PUT': AccessLevel.UNAUTHORIZED,
            'PATCH': AccessLevel.UNAUTHORIZED,
            'DELETE': AccessLevel.UNAUTHORIZED,
        },
    }

    def __init__(
        self,
        custom_permissions: Optional[Dict[str, Dict[UserRole, AccessLevel]]] = None,
        auth_tokens: Optional[Dict[UserRole, str]] = None
    ):
        """
        Initialize generator

        Args:
            custom_permissions: Custom permission matrix
                               Format: {endpoint_key: {role: access_level}}
            auth_tokens: Authentication tokens for each role
                        Format: {role: token}
        """
        self.custom_permissions = custom_permissions or {}
        self.auth_tokens = auth_tokens or {}

    def generate_role_scenarios(
        self,
        endpoint: Dict[str, Any],
        roles: Optional[List[UserRole]] = None
    ) -> List[RoleTestScenario]:
        """
        Generate test scenarios for all roles on an endpoint

        Args:
            endpoint: Endpoint dict with path, method, parameters
            roles: List of roles to test (defaults to all roles)

        Returns:
            List of role test scenarios
        """
        method = endpoint.get('method', 'GET').upper()
        path = endpoint.get('path', '')
        endpoint_key = f"{method} {path}"

        # Default to all roles if not specified
        if roles is None:
            roles = list(UserRole)

        scenarios = []

        for role in roles:
            # Get expected access level
            access_level = self._get_access_level(endpoint_key, method, role)

            # Get expected status codes
            expected_codes = self._get_expected_status_codes(access_level, method)

            # Get auth token for role
            auth_token = self.auth_tokens.get(role)

            # Generate payload if needed
            payload = None
            if method in ['POST', 'PUT', 'PATCH']:
                payload = self._generate_payload(endpoint, role)

            # Create scenario
            scenario = RoleTestScenario(
                endpoint_key=endpoint_key,
                method=method,
                path=path,
                role=role,
                access_level=access_level,
                expected_status_codes=expected_codes,
                auth_token=auth_token,
                payload=payload,
                description=self._generate_description(endpoint_key, role, access_level)
            )

            scenarios.append(scenario)

        return scenarios

    def _get_access_level(
        self,
        endpoint_key: str,
        method: str,
        role: UserRole
    ) -> AccessLevel:
        """
        Get expected access level for a role on an endpoint

        Args:
            endpoint_key: Endpoint identifier
            method: HTTP method
            role: User role

        Returns:
            Expected access level
        """
        # Check custom permissions first
        if endpoint_key in self.custom_permissions:
            if role in self.custom_permissions[endpoint_key]:
                return self.custom_permissions[endpoint_key][role]

        # Fall back to default permissions
        if role in self.DEFAULT_PERMISSIONS:
            return self.DEFAULT_PERMISSIONS[role].get(method, AccessLevel.FORBIDDEN)

        return AccessLevel.FORBIDDEN

    def _get_expected_status_codes(
        self,
        access_level: AccessLevel,
        method: str
    ) -> List[int]:
        """Get expected status codes for an access level"""
        if access_level == AccessLevel.ALLOWED:
            # Success codes
            if method == 'POST':
                return [200, 201]
            elif method == 'DELETE':
                return [200, 204]
            else:
                return [200]

        elif access_level == AccessLevel.FORBIDDEN:
            return [403]

        elif access_level == AccessLevel.UNAUTHORIZED:
            return [401]

        return [403]  # Default to forbidden

    def _generate_payload(
        self,
        endpoint: Dict[str, Any],
        role: UserRole
    ) -> Dict[str, Any]:
        """Generate test payload for a role"""
        # Simple generic payload
        return {
            'name': f'Test data from {role.value}',
            'description': f'Test resource created by {role.value}',
            'role': role.value
        }

    def _generate_description(
        self,
        endpoint_key: str,
        role: UserRole,
        access_level: AccessLevel
    ) -> str:
        """Generate human-readable description for scenario"""
        if access_level == AccessLevel.ALLOWED:
            return f"{role.value.capitalize()} should be allowed to access {endpoint_key}"
        elif access_level == AccessLevel.FORBIDDEN:
            return f"{role.value.capitalize()} should be forbidden (403) from {endpoint_key}"
        elif access_level == AccessLevel.UNAUTHORIZED:
            return f"{role.value.capitalize()} should be unauthorized (401) for {endpoint_key}"
        return f"Test {role.value} access to {endpoint_key}"

    def generate_all_role_scenarios(
        self,
        endpoints: List[Dict[str, Any]],
        roles: Optional[List[UserRole]] = None
    ) -> List[RoleTestScenario]:
        """
        Generate role test scenarios for all endpoints

        Args:
            endpoints: List of endpoint dicts
            roles: List of roles to test (defaults to all)

        Returns:
            List of all role test scenarios
        """
        all_scenarios = []

        for endpoint in endpoints:
            scenarios = self.generate_role_scenarios(endpoint, roles)
            all_scenarios.extend(scenarios)

        logger.info(
            f"Generated {len(all_scenarios)} role test scenarios "
            f"for {len(endpoints)} endpoints"
        )

        return all_scenarios

    def generate_permission_matrix(
        self,
        endpoints: List[Dict[str, Any]],
        roles: Optional[List[UserRole]] = None
    ) -> Dict[str, Dict[UserRole, AccessLevel]]:
        """
        Generate permission matrix for all endpoints and roles

        Args:
            endpoints: List of endpoint dicts
            roles: List of roles (defaults to all)

        Returns:
            Permission matrix: {endpoint_key: {role: access_level}}
        """
        if roles is None:
            roles = list(UserRole)

        matrix = {}

        for endpoint in endpoints:
            method = endpoint.get('method', 'GET').upper()
            path = endpoint.get('path', '')
            endpoint_key = f"{method} {path}"

            matrix[endpoint_key] = {}

            for role in roles:
                access_level = self._get_access_level(endpoint_key, method, role)
                matrix[endpoint_key][role] = access_level

        return matrix

    def get_scenarios_by_role(
        self,
        scenarios: List[RoleTestScenario],
        role: UserRole
    ) -> List[RoleTestScenario]:
        """Filter scenarios by role"""
        return [s for s in scenarios if s.role == role]

    def get_scenarios_by_access_level(
        self,
        scenarios: List[RoleTestScenario],
        access_level: AccessLevel
    ) -> List[RoleTestScenario]:
        """Filter scenarios by expected access level"""
        return [s for s in scenarios if s.access_level == access_level]

    def get_summary(
        self,
        scenarios: List[RoleTestScenario]
    ) -> Dict[str, Any]:
        """Get summary of scenarios"""
        by_role = {}
        by_access = {}

        for scenario in scenarios:
            # By role
            role = scenario.role.value
            by_role[role] = by_role.get(role, 0) + 1

            # By access level
            access = scenario.access_level.value
            by_access[access] = by_access.get(access, 0) + 1

        return {
            'total_scenarios': len(scenarios),
            'by_role': by_role,
            'by_access_level': by_access,
            'unique_roles': len(by_role),
            'unique_access_levels': len(by_access)
        }

    def set_custom_permission(
        self,
        endpoint_key: str,
        role: UserRole,
        access_level: AccessLevel
    ):
        """
        Set custom permission for an endpoint and role

        Args:
            endpoint_key: Endpoint identifier (e.g., "GET /api/users")
            role: User role
            access_level: Expected access level
        """
        if endpoint_key not in self.custom_permissions:
            self.custom_permissions[endpoint_key] = {}

        self.custom_permissions[endpoint_key][role] = access_level

    def set_auth_token(
        self,
        role: UserRole,
        token: str
    ):
        """
        Set authentication token for a role

        Args:
            role: User role
            token: Authentication token (e.g., JWT, API key)
        """
        self.auth_tokens[role] = token

    def visualize_permission_matrix(
        self,
        endpoints: List[Dict[str, Any]],
        roles: Optional[List[UserRole]] = None
    ) -> str:
        """
        Generate ASCII visualization of permission matrix

        Args:
            endpoints: List of endpoints
            roles: List of roles to include

        Returns:
            ASCII table of permissions
        """
        if roles is None:
            roles = list(UserRole)

        matrix = self.generate_permission_matrix(endpoints, roles)

        lines = []
        lines.append("=" * 100)
        lines.append("PERMISSION MATRIX")
        lines.append("=" * 100)
        lines.append("")

        # Header
        header = "Endpoint".ljust(40)
        for role in roles:
            header += f" | {role.value[:10].ljust(10)}"
        lines.append(header)
        lines.append("-" * 100)

        # Rows
        for endpoint_key, role_permissions in matrix.items():
            row = endpoint_key[:40].ljust(40)

            for role in roles:
                access = role_permissions.get(role, AccessLevel.FORBIDDEN)

                # Icon for access level
                if access == AccessLevel.ALLOWED:
                    icon = "✅ ALLOW "
                elif access == AccessLevel.FORBIDDEN:
                    icon = "🚫 FORBID"
                elif access == AccessLevel.UNAUTHORIZED:
                    icon = "🔒 UNAUTH"
                else:
                    icon = "❓ UNKN "

                row += f" | {icon}"

            lines.append(row)

        lines.append("=" * 100)

        return "\n".join(lines)
