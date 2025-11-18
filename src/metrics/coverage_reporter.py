"""
Coverage Reporter
Generates human-readable coverage reports with visualizations
"""
from typing import Dict, Any, List
from .coverage_tracker import CoverageTracker

try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): pass
        def warning(self, msg, **kwargs): pass
        def error(self, msg, **kwargs): pass
        def debug(self, msg, **kwargs): pass
    logger = MockLogger()


class CoverageReporter:
    """
    Generate coverage reports with visualizations

    Features:
    - Summary statistics
    - ASCII progress bars
    - Endpoint-level details
    - Coverage gap identification
    - Recommendations
    """

    def __init__(self, tracker: CoverageTracker):
        """
        Initialize coverage reporter

        Args:
            tracker: CoverageTracker instance
        """
        self.tracker = tracker

    def generate_report(self) -> str:
        """
        Generate comprehensive coverage report

        Returns:
            Multi-line string report
        """
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("TEST COVERAGE REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Summary
        lines.extend(self._generate_summary())
        lines.append("")

        # Coverage breakdown
        lines.extend(self._generate_coverage_breakdown())
        lines.append("")

        # Endpoint details
        lines.extend(self._generate_endpoint_details())
        lines.append("")

        # Coverage gaps
        lines.extend(self._generate_gaps())
        lines.append("")

        # Recommendations
        lines.extend(self._generate_recommendations())
        lines.append("")

        # Footer
        lines.append("=" * 80)
        lines.append("END OF COVERAGE REPORT")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _generate_summary(self) -> List[str]:
        """Generate summary section"""
        lines = []
        summary = self.tracker.get_coverage_summary()

        lines.append("📊 SUMMARY")
        lines.append("-" * 80)
        lines.append("")

        # Overall coverage with bar
        overall_cov = summary['overall_coverage']
        lines.append(f"Overall Coverage: {overall_cov:.1f}%")
        lines.append(self._create_progress_bar(overall_cov))
        lines.append("")

        # Test statistics
        tests = summary['tests']
        lines.append(f"Total Tests Run: {tests['total']}")
        lines.append(f"   ✅ Passed: {tests['passed']} ({tests['pass_rate']:.1f}%)")
        lines.append(f"   ❌ Failed: {tests['failed']}")
        lines.append("")

        # Endpoint statistics
        endpoints = summary['endpoints']
        lines.append(f"Endpoints: {endpoints['tested']}/{endpoints['total']} tested")
        if endpoints['untested'] > 0:
            lines.append(f"   ⚠️  {endpoints['untested']} untested")

        return lines

    def _generate_coverage_breakdown(self) -> List[str]:
        """Generate coverage breakdown by dimension"""
        lines = []
        summary = self.tracker.get_coverage_summary()

        lines.append("📈 COVERAGE BREAKDOWN")
        lines.append("-" * 80)
        lines.append("")

        # Endpoint coverage
        endpoint_cov = summary['endpoint_coverage']
        lines.append(f"Endpoint Coverage: {endpoint_cov:.1f}%")
        lines.append(self._create_progress_bar(endpoint_cov))
        lines.append("")

        # Parameter coverage
        param_cov = summary['parameter_coverage']
        lines.append(f"Parameter Coverage: {param_cov:.1f}%")
        lines.append(self._create_progress_bar(param_cov))
        lines.append("")

        # Status code coverage
        status_cov = summary['status_code_coverage']
        lines.append(f"Status Code Coverage: {status_cov:.1f}%")
        lines.append(self._create_progress_bar(status_cov))
        lines.append("")

        # Scenario types
        lines.append(f"Scenario Types Tested: {summary['scenario_types']}")

        return lines

    def _generate_endpoint_details(self) -> List[str]:
        """Generate endpoint-level details"""
        lines = []

        lines.append("🔍 ENDPOINT DETAILS")
        lines.append("-" * 80)
        lines.append("")

        tested_endpoints = list(self.tracker.coverage.tested_endpoints)
        tested_endpoints.sort()

        for endpoint_key in tested_endpoints[:10]:  # Show first 10
            details = self.tracker.get_endpoint_details(endpoint_key)

            lines.append(f"• {endpoint_key}")

            # Parameter coverage
            param_cov = details['parameter_coverage']
            params = details['parameters']
            lines.append(f"  Parameters: {len(params['tested'])}/{params['total']} ({param_cov:.0f}%)")

            if params['untested']:
                lines.append(f"     Untested: {', '.join(params['untested'][:5])}")

            # Status code coverage
            status_cov = details['status_code_coverage']
            codes = details['status_codes']
            lines.append(f"  Status Codes: {len(codes['tested'])}/{len(codes['documented'])} ({status_cov:.0f}%)")

            if codes['untested']:
                lines.append(f"     Untested: {codes['untested']}")

            # Scenarios
            scenarios = details['scenarios']
            lines.append(f"  Scenarios: {scenarios['count']} types")

            lines.append("")

        if len(tested_endpoints) > 10:
            lines.append(f"... and {len(tested_endpoints) - 10} more endpoints")
            lines.append("")

        return lines

    def _generate_gaps(self) -> List[str]:
        """Generate coverage gaps section"""
        lines = []
        gaps = self.tracker.get_coverage_gaps()

        lines.append("⚠️  COVERAGE GAPS")
        lines.append("-" * 80)
        lines.append("")

        # Untested endpoints
        if gaps['untested_endpoints']:
            lines.append(f"Untested Endpoints ({len(gaps['untested_endpoints'])}):")
            for endpoint in gaps['untested_endpoints'][:5]:
                lines.append(f"   • {endpoint}")

            if len(gaps['untested_endpoints']) > 5:
                lines.append(f"   ... and {len(gaps['untested_endpoints']) - 5} more")

            lines.append("")

        # Low parameter coverage
        if gaps['low_parameter_coverage']:
            lines.append(f"Low Parameter Coverage ({len(gaps['low_parameter_coverage'])}):")
            for item in gaps['low_parameter_coverage'][:5]:
                lines.append(f"   • {item['endpoint']}: {item['coverage']:.0f}%")

            lines.append("")

        # Missing status codes
        if gaps['missing_status_codes']:
            lines.append(f"Missing Status Codes ({len(gaps['missing_status_codes'])}):")
            for item in gaps['missing_status_codes'][:5]:
                lines.append(f"   • {item['endpoint']}: {item['missing_codes']}")

            lines.append("")

        # Low scenario coverage
        if gaps['low_scenario_coverage']:
            lines.append(f"Low Scenario Coverage ({len(gaps['low_scenario_coverage'])}):")
            for item in gaps['low_scenario_coverage'][:5]:
                lines.append(f"   • {item['endpoint']}: {item['scenario_count']} scenarios")

            lines.append("")

        if not any(gaps.values()):
            lines.append("✅ No significant coverage gaps detected!")
            lines.append("")

        return lines

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations"""
        lines = []
        summary = self.tracker.get_coverage_summary()
        gaps = self.tracker.get_coverage_gaps()

        lines.append("💡 RECOMMENDATIONS")
        lines.append("-" * 80)
        lines.append("")

        recommendations = []

        # Overall coverage recommendation
        overall_cov = summary['overall_coverage']
        if overall_cov < 50:
            recommendations.append("🔴 Critical: Overall coverage is below 50%. Prioritize testing untested endpoints.")
        elif overall_cov < 75:
            recommendations.append("🟡 Warning: Overall coverage is below 75%. Continue expanding test coverage.")
        else:
            recommendations.append("🟢 Good: Overall coverage is above 75%. Focus on filling specific gaps.")

        # Endpoint coverage
        endpoint_cov = summary['endpoint_coverage']
        if endpoint_cov < 100:
            untested_count = summary['endpoints']['untested']
            recommendations.append(f"Test the {untested_count} untested endpoints to improve coverage.")

        # Parameter coverage
        param_cov = summary['parameter_coverage']
        if param_cov < 80:
            recommendations.append("Increase parameter coverage by testing more parameter combinations.")

        # Status code coverage
        status_cov = summary['status_code_coverage']
        if status_cov < 80:
            recommendations.append("Trigger more error scenarios to test documented status codes.")

        # Scenario diversity
        if summary['scenario_types'] < 5:
            recommendations.append("Run more diverse test scenarios (positive, negative, boundary, etc.).")

        # Test failures
        if summary['tests']['failed'] > 0:
            fail_rate = (summary['tests']['failed'] / summary['tests']['total']) * 100
            if fail_rate > 20:
                recommendations.append(f"⚠️  {fail_rate:.1f}% of tests are failing. Investigate and fix failing tests.")

        # Output recommendations
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")

        if not recommendations:
            lines.append("✅ No specific recommendations - coverage looks good!")

        return lines

    def _create_progress_bar(self, percentage: float, width: int = 40) -> str:
        """
        Create ASCII progress bar

        Args:
            percentage: Percentage value (0-100)
            width: Width of progress bar in characters

        Returns:
            ASCII progress bar string
        """
        filled = int(width * percentage / 100)
        empty = width - filled

        # Color indicators
        if percentage >= 80:
            indicator = "🟢"
        elif percentage >= 60:
            indicator = "🟡"
        else:
            indicator = "🔴"

        bar = "█" * filled + "░" * empty
        return f"   {indicator} [{bar}] {percentage:.1f}%"

    def print_report(self):
        """Print coverage report to console"""
        report = self.generate_report()
        print(report)

    def save_report(self, filename: str):
        """
        Save coverage report to file

        Args:
            filename: Path to save report
        """
        report = self.generate_report()

        with open(filename, 'w') as f:
            f.write(report)

        logger.info(f"Coverage report saved to: {filename}")

    def generate_json_report(self) -> Dict[str, Any]:
        """
        Generate coverage report as JSON

        Returns:
            Dict with coverage data
        """
        return self.tracker.export_data()
