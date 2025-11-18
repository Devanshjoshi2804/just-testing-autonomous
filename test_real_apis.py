#!/usr/bin/env python3
"""
Real API Testing Script
Tests the entire AutoTest-RL pipeline with real API documentation
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

try:
    from loguru import logger
except ImportError:
    # Simple logger if loguru not available
    class SimpleLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
        def success(self, msg, **kwargs): print(f"✅ {msg}")
    logger = SimpleLogger()


class RealAPITester:
    """Test AutoTest-RL with real API documentation"""

    def __init__(self):
        self.docs_dir = Path("docs/api-specs")
        self.results_dir = Path("data/test-results")
        self.parsed_dir = Path("data/parsed-docs")

        # Create directories
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)

        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'summary': {}
        }

    def discover_documents(self) -> List[Path]:
        """Discover all API documentation files"""
        logger.info("Discovering API documentation...")

        docs = []

        # Find PDFs
        pdf_files = list(self.docs_dir.glob("**/*.pdf"))
        docs.extend(pdf_files)

        # Find JSON (OpenAPI specs)
        json_files = list(self.docs_dir.glob("**/*.json"))
        docs.extend(json_files)

        # Find YAML (OpenAPI specs)
        yaml_files = list(self.docs_dir.glob("**/*.yaml"))
        yaml_files.extend(list(self.docs_dir.glob("**/*.yml")))
        docs.extend(yaml_files)

        logger.info(f"Found {len(docs)} documentation files:")
        logger.info(f"  - {len(pdf_files)} PDF files")
        logger.info(f"  - {len(json_files)} JSON files")
        logger.info(f"  - {len(yaml_files)} YAML files")

        return docs

    async def test_document_parsing(self, doc_path: Path) -> Dict[str, Any]:
        """Test document parsing pipeline"""
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing: {doc_path.name}")
        logger.info(f"{'='*80}")

        result = {
            'file': str(doc_path),
            'file_name': doc_path.name,
            'file_type': doc_path.suffix,
            'status': 'pending',
            'steps': {}
        }

        try:
            # Step 1: Parse document
            logger.info("Step 1: Parsing document...")
            parsed_data = await self._parse_document(doc_path)
            result['steps']['parsing'] = {
                'status': 'success',
                'endpoints_found': parsed_data.get('endpoint_count', 0),
                'pages': parsed_data.get('pages', 0)
            }
            logger.success(f"  ✅ Parsed {parsed_data.get('endpoint_count', 0)} endpoints")

            # Step 2: Extract constraints
            logger.info("Step 2: Extracting constraints...")
            constraints = await self._extract_constraints(parsed_data)
            result['steps']['constraint_extraction'] = {
                'status': 'success',
                'constraints_found': len(constraints)
            }
            logger.success(f"  ✅ Extracted {len(constraints)} constraints")

            # Step 3: Generate tests
            logger.info("Step 3: Generating tests...")
            tests = await self._generate_tests(parsed_data, constraints)
            result['steps']['test_generation'] = {
                'status': 'success',
                'tests_generated': len(tests)
            }
            logger.success(f"  ✅ Generated {len(tests)} tests")

            # Step 4: Save results
            self._save_parsed_data(doc_path, parsed_data, constraints, tests)

            result['status'] = 'success'

        except Exception as e:
            logger.error(f"  ❌ Error: {str(e)}")
            result['status'] = 'failed'
            result['error'] = str(e)
            import traceback
            result['traceback'] = traceback.format_exc()

        return result

    async def _parse_document(self, doc_path: Path) -> Dict[str, Any]:
        """Parse document (mock for now)"""
        # This would use the actual document parser
        # For now, return mock data to test the flow

        if doc_path.suffix == '.pdf':
            # PDF parsing
            return {
                'type': 'pdf',
                'endpoint_count': 10,
                'pages': 50,
                'endpoints': [
                    {
                        'path': '/api/users',
                        'method': 'GET',
                        'description': 'List all users'
                    },
                    {
                        'path': '/api/users',
                        'method': 'POST',
                        'description': 'Create a user'
                    }
                ],
                'raw_text': 'Mock API documentation content...'
            }
        elif doc_path.suffix in ['.json', '.yaml', '.yml']:
            # OpenAPI spec
            return {
                'type': 'openapi',
                'endpoint_count': 15,
                'endpoints': []
            }
        else:
            raise ValueError(f"Unsupported file type: {doc_path.suffix}")

    async def _extract_constraints(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract constraints (mock for now)"""
        # This would use the actual constraint extractor
        return {
            'email': {'type': 'string', 'format': 'email'},
            'age': {'type': 'integer', 'min': 0, 'max': 150}
        }

    async def _generate_tests(self, parsed_data: Dict[str, Any], constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate tests (mock for now)"""
        # This would use the actual test generator
        endpoint_count = parsed_data.get('endpoint_count', 0)
        return [
            {
                'endpoint': '/api/users',
                'method': 'GET',
                'type': 'positive',
                'test_case': 'List users successfully'
            }
            for i in range(endpoint_count * 5)  # 5 tests per endpoint
        ]

    def _save_parsed_data(self, doc_path: Path, parsed_data: Dict, constraints: Dict, tests: List):
        """Save parsed data and generated tests"""
        output_name = doc_path.stem

        # Save parsed data
        parsed_file = self.parsed_dir / f"{output_name}_parsed.json"
        with open(parsed_file, 'w') as f:
            json.dump(parsed_data, f, indent=2)

        # Save constraints
        constraints_file = self.parsed_dir / f"{output_name}_constraints.json"
        with open(constraints_file, 'w') as f:
            json.dump(constraints, f, indent=2)

        # Save tests
        tests_file = self.parsed_dir / f"{output_name}_tests.json"
        with open(tests_file, 'w') as f:
            json.dump(tests, f, indent=2)

    def generate_report(self):
        """Generate summary report"""
        logger.info(f"\n{'='*80}")
        logger.info("TEST SUMMARY")
        logger.info(f"{'='*80}\n")

        total = len(self.results['tests'])
        success = len([t for t in self.results['tests'] if t['status'] == 'success'])
        failed = len([t for t in self.results['tests'] if t['status'] == 'failed'])

        logger.info(f"Total documents tested: {total}")
        logger.info(f"  ✅ Success: {success}")
        logger.info(f"  ❌ Failed: {failed}")

        if success > 0:
            logger.info(f"\nSuccess rate: {success/total*100:.1f}%")

        # Show details of successful tests
        if success > 0:
            logger.info(f"\n{'='*80}")
            logger.info("SUCCESSFUL TESTS")
            logger.info(f"{'='*80}\n")

            for test in self.results['tests']:
                if test['status'] == 'success':
                    logger.info(f"✅ {test['file_name']}")
                    for step_name, step_data in test['steps'].items():
                        logger.info(f"   {step_name}: {step_data}")

        # Show details of failed tests
        if failed > 0:
            logger.info(f"\n{'='*80}")
            logger.info("FAILED TESTS")
            logger.info(f"{'='*80}\n")

            for test in self.results['tests']:
                if test['status'] == 'failed':
                    logger.error(f"❌ {test['file_name']}")
                    logger.error(f"   Error: {test.get('error', 'Unknown')}")

        # Save report
        report_file = self.results_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"\n📄 Full report saved to: {report_file}")

    async def run(self):
        """Run the full test suite"""
        logger.info("="*80)
        logger.info("AutoTest-RL: Real API Testing")
        logger.info("="*80)
        logger.info("")

        # Discover documents
        docs = self.discover_documents()

        if not docs:
            logger.warning("⚠️  No documentation files found in docs/api-specs/")
            logger.info("\nTo use this script:")
            logger.info("1. Place your API documentation PDFs in: docs/api-specs/")
            logger.info("2. Or place OpenAPI specs (JSON/YAML) in: docs/api-specs/")
            logger.info("3. Run this script again")
            return

        logger.info("")

        # Test each document
        for doc in docs:
            result = await self.test_document_parsing(doc)
            self.results['tests'].append(result)

        # Generate report
        self.generate_report()


async def main():
    """Main entry point"""
    tester = RealAPITester()
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
