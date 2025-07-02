# LeafLoaf BDD Context Document

## Executive Summary

This document defines the Behavior-Driven Development (BDD) approach for testing the **complete LeafLoaf system** - from user input through all agents, personalization features, and final response. BDD tests validate the entire flow, not just individual components.

---

## Part 1: BDD Philosophy for LeafLoaf

### What We're Testing

```
User Story → API Request → Supervisor → Agents → Personalization → Response → User Experience
```

We test the **complete journey**, not isolated parts:
- How a vegan shopper finds suitable products
- How a busy parent reorders weekly essentials
- How the system learns and improves personalization
- How multiple agents coordinate seamlessly

### Why BDD for LeafLoaf

1. **Business-Driven**: Tests written in plain English that stakeholders understand
2. **User-Centric**: Focus on actual shopping behaviors, not technical implementation
3. **Living Documentation**: Tests document system behavior
4. **Regression Prevention**: Catch integration issues early
5. **Confidence in Deployment**: Know the entire system works before production

### Testing Boundaries

| What We Test | What We Don't Test |
|--------------|-------------------|
| Complete user journeys | Individual function logic |
| Agent coordination | Database internals |
| Personalization accuracy | Third-party API reliability |
| Response times (<300ms) | Infrastructure scaling |
| Error recovery flows | Network failures |

---

## Part 2: System Flow Scenarios

### Scenario Category 1: Shopping Journey

```gherkin
Feature: Complete Shopping Experience
  As a grocery shopper
  I want to find and order products quickly
  So that I can save time on weekly shopping

  Background:
    Given the LeafLoaf system is running
    And all agents are healthy
    And personalization features are enabled

  Scenario: First-time shopper becomes regular customer
    # Visit 1: New user
    Given I am a new user "john_doe"
    When I search "organic milk"
    Then I should see standard search results
    And no personalization is applied
    And response time is under 300ms

    # Visit 2: After first purchase
    Given "john_doe" has purchased "Organic Valley Milk" once
    When I search "milk" again
    Then "Organic Valley Milk" should appear in top 3
    And personalization confidence should be 0.45

    # Visit 10: Established patterns
    Given "john_doe" has purchased "Organic Valley Milk" weekly for 2 months
    When I search "milk"
    Then "Organic Valley Milk" should rank #1
    And personalization confidence should be > 0.85
    And suggested quantity should be 2 gallons
    And reorder reminder should show "Due in 2 days"

  Scenario: Multi-intent request handling
    Given I am user "sarah_123" with purchase history
    When I send "I need milk and add 2 bananas to my cart"
    Then the supervisor should identify compound intent
    And route to both product_search and order_agent
    And the response should contain:
      | Section | Content |
      | Products | Milk search results with "Organic Valley" first |
      | Order | "Added 2 bananas to cart" |
      | Personalization | Usual milk quantity: 2 gallons |
    And total processing time < 300ms
```

### Scenario Category 2: Personalization Evolution

```gherkin
Feature: Learning User Preferences Over Time
  As the LeafLoaf system
  I want to learn from user behavior
  So that I can provide better personalization

  Scenario: Dietary preference detection
    Given user "amy_vegan" with this purchase history:
      | Date | Product | Category |
      | -30d | Oat Milk | Dairy Alternatives |
      | -25d | Almond Yogurt | Dairy Alternatives |
      | -20d | Tofu | Plant Protein |
      | -15d | Tempeh | Plant Protein |
      | -10d | Cashew Cheese | Dairy Alternatives |
      | -5d | Soy Milk | Dairy Alternatives |
    When "amy_vegan" searches "protein"
    Then the system should detect vegan dietary preference
    And only show plant-based proteins
    And confidence in dietary preference > 0.9
    And Graphiti should store entity: {type: "dietary_preference", value: "vegan"}

  Scenario: Price sensitivity learning
    Given user "budget_bob" consistently buys items < $5
    And has chosen cheaper alternatives 80% of the time
    When "budget_bob" searches "bread"
    Then budget options should appear in positions 1-2
    And premium items should rank lower
    And personalization should note "high price sensitivity"
```

### Scenario Category 3: Multi-Agent Coordination

```gherkin
Feature: Agent Orchestration
  As the LeafLoaf system
  I want agents to work together seamlessly
  So that users get comprehensive responses

  Scenario: Search with automatic reorder detection
    Given user "mary_weekly" buys milk every 7 days
    And last purchased milk 8 days ago
    When "mary_weekly" searches "breakfast items"
    Then product_search agent returns breakfast products
    And reorder_intelligence detects milk is overdue
    And response_compiler merges both:
      """
      {
        "products": [...breakfast items...],
        "personalization": {
          "reorder_alert": {
            "item": "Organic Valley Milk",
            "message": "You usually order milk every 7 days. Add to cart?",
            "urgency": "overdue"
          }
        }
      }
      """

  Scenario: Order operation with personalization
    Given user "tom_usual" with established patterns
    When "tom_usual" says "add my usual milk"
    Then order_agent should:
      | Step | Action | Result |
      | 1 | Query my_usual_analyzer | Find "Organic Valley 2%" |
      | 2 | Get usual quantity | 2 gallons |
      | 3 | Add to cart | Success |
      | 4 | Check reorder patterns | Next due in 7 days |
    And response includes personalized confirmation:
      """
      Added 2 gallons of Organic Valley 2% Milk to your cart.
      This should last you about a week based on your usual consumption.
      """
```

### Scenario Category 4: Error Handling & Recovery

```gherkin
Feature: Graceful Error Handling
  As the LeafLoaf system
  I want to handle errors gracefully
  So that users always get helpful responses

  Scenario: Weaviate search failure
    Given Weaviate vector search is unavailable
    When user searches "organic apples"
    Then system should fall back to BM25 search
    And return results using keyword matching
    And log: "Vector search failed, using BM25 fallback"
    And response metadata includes: {"search_method": "bm25_fallback"}

  Scenario: Personalization data unavailable
    Given Redis is down
    And Graphiti memory is inaccessible
    When user "regular_customer" searches "milk"
    Then search should still work
    And return standard results without personalization
    And response includes: {"personalization": {"enabled": false, "reason": "service_unavailable"}}
```

### Scenario Category 5: Performance & Scale

```gherkin
Feature: System Performance Under Load
  As the LeafLoaf system
  I want to maintain performance standards
  So that users have a fast experience

  Scenario: Peak load performance
    Given 100 concurrent users
    When each user sends different search queries
    Then 95th percentile response time < 300ms
    And no requests timeout
    And all personalization features remain active
    And agent coordination works correctly

  Scenario: Complex query performance
    Given a user with 1000+ purchase history items
    When they request "show my usual items"
    Then my_usual_analyzer processes within 50ms
    And total response time < 300ms
    And returns top 20 most frequent items
```

---

## Part 3: Test Implementation Strategy

### Test Structure

```
tests/
├── bdd/
│   ├── features/
│   │   ├── shopping_journey.feature
│   │   ├── personalization.feature
│   │   ├── agent_coordination.feature
│   │   ├── error_handling.feature
│   │   └── performance.feature
│   ├── steps/
│   │   ├── given_steps.py
│   │   ├── when_steps.py
│   │   └── then_steps.py
│   └── environment.py
├── fixtures/
│   ├── users.py
│   ├── products.py
│   └── purchase_history.py
└── simulations/
    ├── user_personas.py
    ├── shopping_patterns.py
    └── load_scenarios.py
```

### Test Data Requirements

#### User Personas
```python
TEST_USERS = {
    "new_shopper": {
        "user_id": "test_new_001",
        "purchase_history": [],
        "preferences": {}
    },
    "vegan_regular": {
        "user_id": "test_vegan_001",
        "purchase_history": [...30 vegan items...],
        "preferences": {"dietary": ["vegan", "organic"]}
    },
    "family_shopper": {
        "user_id": "test_family_001",
        "purchase_history": [...weekly groceries...],
        "preferences": {"household_size": 4}
    },
    "budget_conscious": {
        "user_id": "test_budget_001",
        "purchase_history": [...value items...],
        "preferences": {"price_sensitivity": "high"}
    }
}
```

### BDD Test Implementation Example

```python
# features/shopping_journey.feature implementation

@given('I am a new user "{user_id}"')
async def step_new_user(context, user_id):
    context.user_id = user_id
    context.client = TestClient(app)
    # Clear any existing data
    await clear_test_user_data(user_id)

@when('I search "{query}"')
async def step_search(context, query):
    context.response = await context.client.post("/api/v1/search", json={
        "query": query,
        "user_id": context.user_id
    })
    context.start_time = time.time()

@then('I should see standard search results')
def step_verify_standard_results(context):
    assert context.response.status_code == 200
    data = context.response.json()
    assert data["success"] == True
    assert len(data["products"]) > 0
    # Verify no personalization
    assert "personalization" not in data or data["personalization"]["enabled"] == False

@then('response time is under {time_ms}ms')
def step_verify_response_time(context, time_ms):
    elapsed = (time.time() - context.start_time) * 1000
    assert elapsed < int(time_ms), f"Response took {elapsed}ms, expected < {time_ms}ms"
```

### Performance Validation Framework

```python
class PerformanceValidator:
    def __init__(self):
        self.thresholds = {
            "total_response": 300,  # ms
            "supervisor": 50,
            "product_search": 100,
            "order_agent": 100,
            "response_compiler": 50,
            "personalization": 100
        }
    
    async def validate_response(self, response_data):
        execution = response_data.get("execution", {})
        timings = execution.get("agent_timings", {})
        
        # Check total time
        total_time = execution.get("total_time_ms", 0)
        assert total_time < self.thresholds["total_response"], \
            f"Total time {total_time}ms exceeds threshold"
        
        # Check individual components
        for component, threshold in self.thresholds.items():
            if component in timings:
                assert timings[component] < threshold, \
                    f"{component} took {timings[component]}ms, threshold: {threshold}ms"
```

---

## Part 4: CI/CD Integration

### BDD in the Pipeline

```yaml
# .github/workflows/bdd-tests.yml
name: BDD System Tests

on:
  pull_request:
    branches: [main]
  push:
    branches: [feature/**, staging/**]

jobs:
  bdd-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Test Environment
        run: |
          docker-compose -f docker-compose.test.yml up -d
          python -m pip install behave pytest-bdd
      
      - name: Run BDD Tests - Quick Suite
        run: |
          behave tests/bdd/features \
            --tags=@quick \
            --format=json \
            --outfile=bdd-results.json
      
      - name: Run BDD Tests - Full Suite (staging only)
        if: contains(github.ref, 'staging')
        run: |
          behave tests/bdd/features \
            --tags=~@slow \
            --format=json \
            --outfile=bdd-full-results.json
      
      - name: Performance Validation
        run: |
          python tests/validate_performance.py bdd-results.json
      
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: bdd-test-results
          path: |
            bdd-results.json
            performance-report.html
```

### Staging Environment BDD Tests

```bash
# Run on staging deployment
STAGING_URL=https://leafloaf-staging-feature-xyz.run.app

# Quick smoke tests (< 2 min)
behave tests/bdd/features \
  --tags=@smoke \
  --define base_url=$STAGING_URL

# Full regression suite (< 10 min)
behave tests/bdd/features \
  --tags=~@slow \
  --define base_url=$STAGING_URL \
  --parallel=4

# Load test simulation (< 5 min)
python tests/simulations/realistic_load.py \
  --url=$STAGING_URL \
  --users=50 \
  --duration=300
```

### Production Readiness Gates

```python
# tests/production_readiness.py

class ProductionReadinessGates:
    def __init__(self, test_results):
        self.results = test_results
    
    def check_all_gates(self):
        gates = {
            "functional_tests": self.check_functional_coverage(),
            "performance_tests": self.check_performance_thresholds(),
            "error_handling": self.check_error_scenarios(),
            "personalization": self.check_personalization_accuracy(),
            "scale_tests": self.check_load_handling()
        }
        
        return all(gates.values()), gates
    
    def check_functional_coverage(self):
        # All critical user journeys must pass
        critical_scenarios = [
            "first_time_shopper",
            "search_and_add_to_cart",
            "personalized_recommendations",
            "reorder_detection"
        ]
        return all(self.scenario_passed(s) for s in critical_scenarios)
    
    def check_performance_thresholds(self):
        # 95th percentile must be under 300ms
        p95_latency = self.results.get_percentile(95)
        return p95_latency < 300
```

### Rollback Triggers

```gherkin
Feature: Automatic Rollback Triggers
  As the deployment system
  I want to detect production issues quickly
  So that I can rollback automatically

  Scenario: Performance degradation
    Given new version is deployed to canary (10%)
    When 95th percentile latency > 500ms for 2 minutes
    Then automatically rollback to previous version
    And alert the team
    And create incident report

  Scenario: Error rate spike
    Given new version is deployed to canary
    When error rate > 5% for 1 minute
    Then pause traffic shift
    And run diagnostic tests
    And rollback if diagnostics fail
```

---

## Test Execution Strategy

### Local Development
```bash
# Run specific scenario
behave tests/bdd/features/shopping_journey.feature \
  --name "First-time shopper becomes regular customer"

# Run with specific user
behave tests/bdd/features \
  --define user=test_vegan_001

# Debug mode
behave tests/bdd/features \
  --no-capture \
  --logging-level=DEBUG
```

### Feature Branch Testing
```bash
# Automatically triggered on push
# Runs @quick and @feature tags
# Takes ~3 minutes
# Must pass before PR can be created
```

### Staging Testing
```bash
# Triggered on PR to main
# Runs full test suite
# Takes ~10 minutes
# Must pass before merge allowed
```

### Production Testing
```bash
# Continuous synthetic monitoring
# Runs every 15 minutes
# Key user journeys only
# Alerts on failure
```

---

## Success Metrics

### Test Coverage
- **User Journeys**: 95% of identified user stories have BDD tests
- **Agent Interactions**: All agent combinations tested
- **Error Scenarios**: 20+ error conditions validated
- **Performance**: All endpoints tested under load

### Quality Gates
- **Feature Branch**: 100% of @quick tests must pass
- **Staging**: 100% of @regression tests must pass
- **Production**: 99.9% of @smoke tests must pass

### Business Outcomes
- **Deployment Confidence**: Deploy anytime with confidence
- **Regression Prevention**: Catch issues before users see them
- **Documentation**: Tests serve as living documentation
- **Stakeholder Trust**: Plain English tests build confidence

---

## Next Steps

1. **Implement Core Scenarios**: Start with the 5 shopping journey scenarios
2. **Build Test Data**: Create realistic user personas and purchase histories
3. **Set Up CI Integration**: Add BDD tests to GitHub Actions
4. **Create Dashboards**: Visualize test results and trends
5. **Train Team**: Ensure everyone can write and run BDD tests

---

*This document defines how we test the complete LeafLoaf system using BDD. No code changes required - only test additions.*