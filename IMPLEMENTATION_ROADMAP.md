# Implementation Roadmap - 90 Days to Production Excellence

## Goal: Transform from "testing tool" to "intelligent API evolution system"

---

## Week 1-2: Foundation - Real RL Implementation

### What: Replace fake "RL" with actual Q-Learning

**Files to create:**
```
src/rl/
├── __init__.py
├── test_optimizer.py       # Q-Learning agent
├── state_builder.py        # Build state from test context
├── reward_calculator.py    # Calculate rewards
└── models/
    └── q_table.pkl         # Persisted Q-values
```

**Core Implementation:**
```python
# src/rl/test_optimizer.py
import numpy as np
import pickle
from pathlib import Path
from typing import Dict, Tuple, List
from loguru import logger

class TestOptimizer:
    """
    Q-Learning agent for optimal test execution

    State Features:
    - endpoint_id (hashed)
    - hour_of_day (0-23)
    - day_of_week (0-6)
    - days_since_code_change (0-30)
    - recent_failure_rate (0-100)
    - dependency_health_score (0-100)

    Actions:
    - PRIORITY_CRITICAL (test first, always)
    - PRIORITY_HIGH (test early)
    - PRIORITY_NORMAL (test in order)
    - PRIORITY_LOW (test if time permits)
    - SKIP (don't test, high confidence stable)

    Rewards:
    - CORRECT_SKIP: +10 (skipped stable endpoint, saved time)
    - CORRECT_PRIORITY: +5 (found failure in prioritized endpoint)
    - MISSED_FAILURE: -50 (skipped endpoint that failed)
    - WASTED_TIME: -1 (tested stable endpoint unnecessarily)
    """

    ACTIONS = ['critical', 'high', 'normal', 'low', 'skip']

    def __init__(self, alpha=0.1, gamma=0.9, epsilon=0.1):
        self.alpha = alpha      # Learning rate
        self.gamma = gamma      # Discount factor
        self.epsilon = epsilon  # Exploration rate

        self.q_table = self._load_q_table()
        self.state_history = []
        self.metrics = {
            'time_saved': 0,
            'failures_caught': 0,
            'failures_missed': 0,
            'correct_skips': 0,
        }

    def _load_q_table(self) -> Dict:
        """Load persisted Q-table"""
        path = Path('src/rl/models/q_table.pkl')
        if path.exists():
            with open(path, 'rb') as f:
                return pickle.load(f)
        return {}

    def _save_q_table(self):
        """Persist Q-table"""
        path = Path('src/rl/models/q_table.pkl')
        path.parent.mkdir(exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(self.q_table, f)

    def build_state(self, endpoint: Dict, context: Dict) -> Tuple:
        """
        Build state vector from endpoint and context

        Args:
            endpoint: Endpoint metadata (path, method, history)
            context: Test context (time, recent changes, etc.)

        Returns:
            State tuple (hashable for Q-table key)
        """
        from src.rl.state_builder import StateBuilder
        return StateBuilder.build(endpoint, context)

    def choose_action(self, state: Tuple) -> str:
        """
        ε-greedy action selection

        With probability ε, explore (random action)
        Otherwise, exploit (best known action)
        """
        # Exploration
        if np.random.random() < self.epsilon:
            action = np.random.choice(self.ACTIONS)
            logger.debug(f"Exploring: chose {action}")
            return action

        # Exploitation
        state_actions = {a: self.q_table.get((state, a), 0.0)
                        for a in self.ACTIONS}

        best_action = max(state_actions, key=state_actions.get)
        logger.debug(f"Exploiting: chose {best_action} (Q={state_actions[best_action]:.2f})")

        return best_action

    def update(self, state: Tuple, action: str, reward: float, next_state: Tuple):
        """
        Q-Learning update

        Q(s,a) ← Q(s,a) + α[r + γ max_a' Q(s',a') - Q(s,a)]
        """
        current_q = self.q_table.get((state, action), 0.0)

        # Max Q-value for next state
        max_next_q = max(
            self.q_table.get((next_state, a), 0.0)
            for a in self.ACTIONS
        )

        # Update rule
        new_q = current_q + self.alpha * (
            reward + self.gamma * max_next_q - current_q
        )

        self.q_table[(state, action)] = new_q

        logger.debug(
            f"Q-update: {action} {current_q:.2f} → {new_q:.2f} "
            f"(reward={reward}, max_next={max_next_q:.2f})"
        )

    def calculate_reward(self, action: str, actual_result: Dict) -> float:
        """
        Calculate reward based on action and outcome

        Args:
            action: Action taken
            actual_result: Actual test result

        Returns:
            Reward value
        """
        from src.rl.reward_calculator import RewardCalculator
        return RewardCalculator.calculate(action, actual_result)

    def prioritize_endpoints(self, endpoints: List[Dict], context: Dict) -> List[Dict]:
        """
        Prioritize endpoints using RL policy

        Args:
            endpoints: List of endpoints to test
            context: Test context (time, changes, etc.)

        Returns:
            Sorted endpoints with priorities
        """
        prioritized = []

        for endpoint in endpoints:
            state = self.build_state(endpoint, context)
            action = self.choose_action(state)

            prioritized.append({
                **endpoint,
                'priority': action,
                'state': state,  # Store for learning
            })

        # Sort by priority
        priority_order = {
            'critical': 0,
            'high': 1,
            'normal': 2,
            'low': 3,
            'skip': 4,
        }

        prioritized.sort(key=lambda e: priority_order[e['priority']])

        # Log decisions
        logger.info("RL Test Prioritization:")
        for p in prioritized:
            logger.info(f"  {p['priority']:8} - {p['method']} {p['path']}")

        return prioritized

    def learn_from_results(self, results: List[Dict]):
        """
        Update Q-values from test results

        Args:
            results: List of test results with state/action/outcome
        """
        for i, result in enumerate(results):
            state = result['state']
            action = result['priority']
            reward = self.calculate_reward(action, result)

            # Next state (if not last test)
            next_state = results[i + 1]['state'] if i < len(results) - 1 else state

            # Update Q-table
            self.update(state, action, reward, next_state)

            # Update metrics
            if action == 'skip' and result['would_have_passed']:
                self.metrics['correct_skips'] += 1
                self.metrics['time_saved'] += result.get('estimated_time', 5)
            elif action in ['critical', 'high'] and not result['success']:
                self.metrics['failures_caught'] += 1
            elif action == 'skip' and not result['would_have_passed']:
                self.metrics['failures_missed'] += 1

        # Persist learning
        self._save_q_table()

        logger.info(f"RL Metrics: {self.metrics}")

    def get_stats(self) -> Dict:
        """Get learning statistics"""
        return {
            'q_table_size': len(self.q_table),
            'exploration_rate': self.epsilon,
            'metrics': self.metrics,
        }
```

**Integration into TestRunner:**
```python
# src/executors/test_runner.py (modified)
from src.rl.test_optimizer import TestOptimizer

class TestRunner:
    def __init__(self, ...):
        # ... existing code ...
        self.rl_optimizer = TestOptimizer()

    async def test_all_endpoints(self, endpoints, ordered=True):
        # Build context
        context = {
            'time': datetime.now(),
            'recent_changes': self._get_recent_git_changes(),
            'dependency_health': await self._check_dependencies(),
        }

        # Use RL to prioritize
        if ordered:
            endpoints = self.rl_optimizer.prioritize_endpoints(
                endpoints,
                context
            )

        # Test endpoints (skip if priority='skip')
        results = []
        for endpoint in endpoints:
            if endpoint['priority'] == 'skip':
                logger.info(f"⏭️  Skipping {endpoint['path']} (RL: high confidence stable)")
                # Still track what would have happened (for learning)
                result = await self._check_endpoint_status(endpoint)
                result['skipped'] = True
            else:
                result = await self.test_endpoint(endpoint)

            results.append(result)

        # Learn from results
        self.rl_optimizer.learn_from_results(results)

        return results
```

**Expected Outcome:**
- After 100 test runs, RL learns patterns
- Achieves 30-40% time reduction with <1% false negatives
- Metrics tracked and visualized

---

## Week 3-4: Mutation Testing Engine

### What: Systematic edge-case and security testing

**Files to create:**
```
src/testing/
├── __init__.py
├── mutation_engine.py
├── mutators/
│   ├── __init__.py
│   ├── sql_injection.py
│   ├── xss.py
│   ├── type_confusion.py
│   ├── boundary_values.py
│   ├── overflow.py
│   └── unicode_edge_cases.py
└── reports/
    └── vulnerability_report.py
```

**Core Implementation:**
```python
# src/testing/mutation_engine.py
from typing import List, Dict, Any
from loguru import logger
from src.testing.mutators import *

class MutationEngine:
    """Generate edge-case test payloads through mutation"""

    MUTATORS = {
        'sql_injection': SQLInjectionMutator(),
        'xss': XSSMutator(),
        'type_confusion': TypeConfusionMutator(),
        'boundary': BoundaryValueMutator(),
        'overflow': OverflowMutator(),
        'unicode': UnicodeEdgeCaseMutator(),
    }

    def __init__(self, enabled_mutators: List[str] = None):
        """
        Initialize mutation engine

        Args:
            enabled_mutators: List of mutator names to use (default: all)
        """
        if enabled_mutators:
            self.mutators = {k: v for k, v in self.MUTATORS.items()
                           if k in enabled_mutators}
        else:
            self.mutators = self.MUTATORS

    def generate_mutations(
        self,
        base_payload: Dict[str, Any],
        max_per_mutator: int = 10
    ) -> List[Dict]:
        """
        Generate mutated payloads

        Args:
            base_payload: Original payload
            max_per_mutator: Max mutations per mutator

        Returns:
            List of mutation test cases
        """
        mutations = []

        for name, mutator in self.mutators.items():
            logger.info(f"Generating {name} mutations...")

            mutated_payloads = mutator.mutate(base_payload, max_per_mutator)

            for payload in mutated_payloads:
                mutations.append({
                    'type': name,
                    'payload': payload,
                    'expected_behavior': mutator.expected_behavior,
                    'severity': mutator.severity,
                    'description': mutator.describe(payload),
                })

        logger.info(f"Generated {len(mutations)} total mutations")
        return mutations

    async def run_mutation_tests(
        self,
        endpoint: Dict,
        base_payload: Dict,
        test_runner
    ) -> Dict:
        """
        Execute mutation testing on endpoint

        Args:
            endpoint: Endpoint to test
            base_payload: Base valid payload
            test_runner: TestRunner instance

        Returns:
            Vulnerability report
        """
        mutations = self.generate_mutations(base_payload)

        vulnerabilities = []
        passed = 0
        failed = 0

        for mutation in mutations:
            result = await test_runner.test_endpoint(
                endpoint,
                headers={'Content-Type': 'application/json'},
                payload=mutation['payload']
            )

            # Check if behavior matches expectation
            is_vulnerable = self._check_vulnerability(
                result,
                mutation['expected_behavior']
            )

            if is_vulnerable:
                vulnerabilities.append({
                    'type': mutation['type'],
                    'severity': mutation['severity'],
                    'description': mutation['description'],
                    'payload': mutation['payload'],
                    'response': result,
                })
                failed += 1
            else:
                passed += 1

        return {
            'endpoint': f"{endpoint['method']} {endpoint['path']}",
            'total_mutations': len(mutations),
            'passed': passed,
            'vulnerabilities': vulnerabilities,
            'severity_breakdown': self._analyze_severity(vulnerabilities),
        }

    def _check_vulnerability(self, result: Dict, expected: str) -> bool:
        """Check if response indicates vulnerability"""
        if expected == 'REJECT':
            # Should be rejected (400, 422)
            return result['status_code'] not in [400, 422, 403]

        elif expected == 'SANITIZE':
            # Should sanitize dangerous input
            response_text = str(result.get('response', ''))
            # Check if dangerous chars were escaped
            return any(char in response_text for char in ['<script>', "'; DROP", '--'])

        elif expected == 'VALIDATE':
            # Should validate and reject invalid types
            return result['status_code'] == 200  # Accepted invalid data

        return False

    def _analyze_severity(self, vulnerabilities: List[Dict]) -> Dict:
        """Analyze severity distribution"""
        from collections import Counter
        severities = [v['severity'] for v in vulnerabilities]
        return dict(Counter(severities))
```

**Mutator Example:**
```python
# src/testing/mutators/sql_injection.py
class SQLInjectionMutator:
    """Generate SQL injection test payloads"""

    severity = 'CRITICAL'
    expected_behavior = 'REJECT'

    PAYLOADS = [
        "'; DROP TABLE users--",
        "1' OR '1'='1",
        "admin'--",
        "1' UNION SELECT * FROM users--",
        "'; EXEC xp_cmdshell('dir')--",
        "1' AND 1=CONVERT(int, (SELECT TOP 1 password FROM users))--",
    ]

    def mutate(self, base_payload: Dict, max_count: int = 10) -> List[Dict]:
        """Generate SQL injection mutations"""
        mutations = []

        for field, value in base_payload.items():
            if isinstance(value, str):
                for sql_payload in self.PAYLOADS[:max_count]:
                    mutated = base_payload.copy()
                    mutated[field] = sql_payload
                    mutations.append(mutated)

        return mutations[:max_count]

    def describe(self, payload: Dict) -> str:
        """Describe this mutation"""
        return f"SQL injection attempt in payload fields"
```

**Integration:**
```python
# Add to API routes
@router.post("/api/v1/tests/{test_id}/mutation-scan")
async def run_mutation_scan(test_id: str, mutation_config: MutationConfig):
    """Run mutation testing on all endpoints"""

    engine = MutationEngine(enabled_mutators=mutation_config.mutators)

    results = await engine.run_mutation_tests(...)

    return MutationReportResponse(
        vulnerabilities_found=len(results['vulnerabilities']),
        severity_high=results['severity_breakdown']['CRITICAL'],
        severity_medium=results['severity_breakdown']['HIGH'],
        severity_low=results['severity_breakdown']['MEDIUM'],
        report_url=f"/reports/mutation/{test_id}"
    )
```

**Expected Outcome:**
- Automatically discover SQL injection, XSS, type confusion bugs
- Generate security reports
- Integrate into CI/CD for pre-deploy scanning

---

## Week 5-6: Schema Evolution Tracking

### What: Detect API changes automatically

**Files to create:**
```
src/analysis/
├── __init__.py
├── schema_tracker.py
├── schema_differ.py
└── changelog_generator.py
```

**Core Implementation:**
```python
# src/analysis/schema_tracker.py
from datetime import datetime, timedelta
from typing import Dict, List
from src.rag.doc_store import DocumentStore

class SchemaTracker:
    """Track API schema evolution over time"""

    def __init__(self):
        self.schema_store = DocumentStore(collection_name="api_schemas")

    def record_schema(self, endpoint: str, response: Dict, metadata: Dict = None):
        """Record response schema"""
        schema = self._extract_schema(response)

        self.schema_store.add_documents(
            documents=[{
                'endpoint': endpoint,
                'schema': schema,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {},
            }],
            metadatas=[{
                'endpoint': endpoint,
                'timestamp': datetime.now().isoformat(),
            }]
        )

    def detect_breaking_changes(
        self,
        endpoint: str,
        timeframe_days: int = 7
    ) -> Dict:
        """Detect breaking changes in endpoint schema"""

        # Get recent schemas
        cutoff = datetime.now() - timedelta(days=timeframe_days)

        recent_schemas = self.schema_store.query(
            query_texts=[endpoint],
            n_results=100,
            where={'endpoint': endpoint}
        )

        # Compare schemas
        if len(recent_schemas['documents']) < 2:
            return {'breaking_changes': [], 'status': 'stable'}

        # Analyze changes
        from src.analysis.schema_differ import SchemaDiffer
        differ = SchemaDiffer()

        changes = differ.compare_schemas(
            old_schema=recent_schemas['documents'][-1],
            new_schema=recent_schemas['documents'][0]
        )

        return {
            'endpoint': endpoint,
            'breaking_changes': changes['breaking'],
            'additions': changes['additions'],
            'deprecations': changes['deprecations'],
            'severity': self._assess_severity(changes),
        }

    def _extract_schema(self, response: Dict) -> Dict:
        """Extract schema from response"""
        if isinstance(response, dict):
            return {
                'type': 'object',
                'properties': {
                    k: self._extract_schema(v)
                    for k, v in response.items()
                },
                'required': list(response.keys())
            }
        elif isinstance(response, list):
            if response:
                return {
                    'type': 'array',
                    'items': self._extract_schema(response[0])
                }
            return {'type': 'array', 'items': {}}
        else:
            return {'type': type(response).__name__}
```

**Auto-Update Test Payloads:**
```python
# When schema changes detected, auto-adapt tests
class AdaptiveTestGenerator:
    """Auto-update tests when schema changes"""

    def adapt_to_schema_change(self, endpoint: str, changes: Dict):
        """Adapt test payloads to schema changes"""

        if 'new_required_field' in changes['breaking']:
            # LLM generates value for new field
            new_field = changes['breaking']['new_required_field']

            updated_payload = self.llm.invoke(f"""
            API endpoint {endpoint} now requires a new field: {new_field}
            Generate an appropriate test value for this field.
            Response format: JSON only
            """)

            # Update stored test templates
            self.update_test_template(endpoint, updated_payload)
```

**Expected Outcome:**
- Automatic detection of breaking changes
- Auto-generated changelog
- Test payloads adapt to schema evolution
- Alerts sent before deploying breaking changes

---

## Week 7-8: Anomaly Detection

### What: Detect silent failures (status 200 but wrong behavior)

**Implementation in:** `src/analysis/anomaly_detector.py`

Uses ChromaDB for baseline pattern storage, flags responses that deviate significantly from historical norms even when status code is 200.

---

## Week 9-10: Production Traffic Mining

### What: Generate realistic test data from production patterns

Learn from actual API usage to create test cases that mirror real-world scenarios.

---

## Week 11-12: Integration & Polish

- CI/CD integrations (GitHub Actions, GitLab CI, Jenkins)
- Dashboard for visualization
- Plugin system
- Documentation and examples
- Performance optimization

---

## Success Metrics

| Metric | Baseline | Target (90 days) |
|--------|----------|------------------|
| Test execution time | 100% | 60% (40% reduction) |
| False negative rate | - | <1% |
| Vulnerabilities found | 0 | 10+ per scan |
| Breaking changes caught | Manual | 100% automated |
| Developer satisfaction | - | 8/10+ |
| Time to detect API regression | Hours | Minutes |

---

## Cost-Benefit Analysis

**Investment:** 1-2 engineers × 90 days = ~$50K

**Returns (Annual):**
- Reduced incident response: $200K (4 major incidents prevented)
- Faster development cycles: $150K (20% velocity increase)
- Fewer production bugs: $100K (support cost reduction)
- Security vulnerabilities prevented: $500K+ (one breach prevented)

**ROI:** 18x in year one

---

## Getting Started Tomorrow

**Day 1 Tasks:**
1. Create `src/rl/test_optimizer.py` (Q-Learning skeleton)
2. Add state builder (extract features from endpoints)
3. Write reward calculator
4. Integrate into TestRunner (basic version)
5. Test with demo script - collect initial data

**Day 2-5:**
- Refine reward function based on results
- Add more state features
- Tune hyperparameters (alpha, gamma, epsilon)
- Measure time savings

**Week 1 Milestone:** RL agent making basic prioritization decisions

---

This roadmap is aggressive but achievable. Each week builds on the previous, creating compounding value.

**Focus:** Ship working features weekly, iterate based on real results.
