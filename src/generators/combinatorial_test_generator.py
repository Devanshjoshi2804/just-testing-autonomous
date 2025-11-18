"""
Combinatorial Test Generator
Generates test combinations for optional parameters
Tests all meaningful combinations instead of just all-or-nothing
"""
from typing import Dict, Any, List, Set
from itertools import combinations


class CombinatorialTestGenerator:
    """
    Generates combinatorial test cases for optional parameters

    Example:
        Endpoint with params: a (required), b (optional), c (optional), d (optional)

        Traditional testing: 2 tests
        - All params: {a, b, c, d}
        - Required only: {a}

        Combinatorial testing: 8 tests
        - {a}           (required only)
        - {a, b}        (b only)
        - {a, c}        (c only)
        - {a, d}        (d only)
        - {a, b, c}     (b + c)
        - {a, b, d}     (b + d)
        - {a, c, d}     (c + d)
        - {a, b, c, d}  (all)

    This finds bugs that only occur with specific parameter combinations.
    """

    def __init__(self, max_combinations: int = 100):
        """
        Initialize Combinatorial Test Generator

        Args:
            max_combinations: Maximum number of combinations to generate
                             (prevents explosion with many optional params)
        """
        self.max_combinations = max_combinations

    def generate_parameter_combinations(
        self,
        endpoint: Dict[str, Any],
        include_required: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate all meaningful parameter combinations

        Args:
            endpoint: Endpoint definition with parameters
            include_required: Whether to include required params in all combinations

        Returns:
            List of parameter combination dicts, each describing which params to include
        """
        parameters = endpoint.get('parameters', [])

        # Separate required and optional parameters
        required_params = [p for p in parameters if p.get('required', False)]
        optional_params = [p for p in parameters if not p.get('required', False)]

        # If no optional params, return just the base case
        if not optional_params:
            return [{'description': 'Required parameters only', 'params': required_params}]

        # Generate all combinations of optional parameters
        all_combinations = []

        # Combination 1: Required params only (baseline)
        all_combinations.append({
            'description': 'Required parameters only',
            'params': required_params,
            'optional_params_included': []
        })

        # Generate combinations of optional params
        num_optional = len(optional_params)

        # For small number of optional params (<=5), test all combinations
        # For larger numbers, use smart sampling
        if num_optional <= 5:
            # Test all 2^n combinations
            for r in range(1, num_optional + 1):
                for combo in combinations(optional_params, r):
                    combo_params = list(required_params) + list(combo)
                    optional_names = [p['name'] for p in combo]

                    all_combinations.append({
                        'description': f"With optional params: {', '.join(optional_names)}",
                        'params': combo_params,
                        'optional_params_included': optional_names
                    })
        else:
            # Smart sampling for large number of optional params
            # 1. Test each optional param individually
            for param in optional_params:
                combo_params = required_params + [param]
                all_combinations.append({
                    'description': f"With optional param: {param['name']}",
                    'params': combo_params,
                    'optional_params_included': [param['name']]
                })

            # 2. Test pairs of optional params (pairwise testing)
            for combo in combinations(optional_params, 2):
                combo_params = list(required_params) + list(combo)
                optional_names = [p['name'] for p in combo]
                all_combinations.append({
                    'description': f"With optional params: {', '.join(optional_names)}",
                    'params': combo_params,
                    'optional_params_included': optional_names
                })

            # 3. Test all optional params
            all_combinations.append({
                'description': 'With all optional parameters',
                'params': parameters,
                'optional_params_included': [p['name'] for p in optional_params]
            })

        # Limit to max_combinations
        if len(all_combinations) > self.max_combinations:
            # Keep first (required only), last (all params), and sample the middle
            sampled = [all_combinations[0]]  # Required only

            # Sample from middle
            step = len(all_combinations) // (self.max_combinations - 2)
            for i in range(1, len(all_combinations) - 1, step):
                if len(sampled) < self.max_combinations - 1:
                    sampled.append(all_combinations[i])

            sampled.append(all_combinations[-1])  # All params
            all_combinations = sampled

        return all_combinations

    def generate_combinatorial_test_suite(
        self,
        endpoint: Dict[str, Any],
        base_payload_generator,
        parameter_constraints: Dict[str, Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate complete combinatorial test suite with payloads

        Args:
            endpoint: Endpoint definition
            base_payload_generator: Function to generate payload for given params
                                   Signature: func(endpoint, params_to_include) -> payload
            parameter_constraints: Optional constraints for parameters

        Returns:
            List of test cases with payloads
        """
        # Generate parameter combinations
        combinations = self.generate_parameter_combinations(endpoint)

        test_suite = []

        for i, combo in enumerate(combinations, 1):
            # Create modified endpoint with only these params
            modified_endpoint = {
                **endpoint,
                'parameters': combo['params']
            }

            # Generate payload for this combination
            payload = base_payload_generator(modified_endpoint, parameter_constraints)

            test_case = {
                'test_number': i,
                'total_tests': len(combinations),
                'description': combo['description'],
                'params_included': [p['name'] for p in combo['params']],
                'optional_params_included': combo.get('optional_params_included', []),
                'payload': payload,
                'expected_status': 200,  # Assume success for valid combinations
                'test_type': 'combinatorial'
            }

            test_suite.append(test_case)

        return test_suite

    def get_combination_coverage_stats(
        self,
        endpoint: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get statistics about combinatorial coverage

        Args:
            endpoint: Endpoint definition

        Returns:
            Coverage statistics dict
        """
        parameters = endpoint.get('parameters', [])
        required_params = [p for p in parameters if p.get('required', False)]
        optional_params = [p for p in parameters if not p.get('required', False)]

        num_optional = len(optional_params)

        # Calculate total possible combinations
        total_possible = 2 ** num_optional if num_optional > 0 else 1

        # Calculate actual combinations to test
        combinations = self.generate_parameter_combinations(endpoint)
        actual_combinations = len(combinations)

        return {
            'total_parameters': len(parameters),
            'required_parameters': len(required_params),
            'optional_parameters': num_optional,
            'total_possible_combinations': total_possible,
            'combinations_to_test': actual_combinations,
            'coverage_percentage': (actual_combinations / total_possible * 100) if total_possible > 0 else 100,
            'sampling_strategy': 'exhaustive' if num_optional <= 5 else 'pairwise + all',
            'max_combinations_limit': self.max_combinations
        }

    def should_use_combinatorial_testing(
        self,
        endpoint: Dict[str, Any],
        min_optional_params: int = 2
    ) -> bool:
        """
        Determine if combinatorial testing is worthwhile for this endpoint

        Args:
            endpoint: Endpoint definition
            min_optional_params: Minimum number of optional params to trigger combinatorial testing

        Returns:
            True if combinatorial testing should be used
        """
        parameters = endpoint.get('parameters', [])
        optional_params = [p for p in parameters if not p.get('required', False)]

        # Use combinatorial testing if:
        # 1. Has at least min_optional_params optional parameters
        # 2. Is not a simple GET with only query params
        # 3. Method is not DELETE (usually simple)

        has_enough_optional = len(optional_params) >= min_optional_params
        method = endpoint.get('method', 'GET').upper()
        is_complex = method in ['POST', 'PUT', 'PATCH', 'GET']

        return has_enough_optional and is_complex

    def explain_combinatorial_strategy(
        self,
        endpoint: Dict[str, Any]
    ) -> str:
        """
        Explain the combinatorial testing strategy for this endpoint

        Args:
            endpoint: Endpoint definition

        Returns:
            Human-readable explanation
        """
        stats = self.get_combination_coverage_stats(endpoint)

        optional = stats['optional_parameters']
        total = stats['total_possible_combinations']
        actual = stats['combinations_to_test']

        if optional == 0:
            return "No optional parameters - combinatorial testing not needed"

        if optional <= 5:
            return (
                f"Testing all {actual} combinations of {optional} optional parameters "
                f"(exhaustive coverage: {stats['coverage_percentage']:.0f}%)"
            )
        else:
            return (
                f"Using pairwise testing strategy for {optional} optional parameters:\n"
                f"  - Testing {actual} combinations out of {total} possible\n"
                f"  - Strategy: Each param individually + all pairs + all params\n"
                f"  - Coverage: {stats['coverage_percentage']:.1f}% of combinations"
            )
