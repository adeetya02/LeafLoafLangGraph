# Next Session Prompt for LeafLoaf Real-Time Personalization

## Context
You are continuing work on LeafLoaf after a failed demo. The generic flow wasn't appreciated by stakeholders, especially after talking up the AI/personalization capabilities. We need a production-grade personalization system in 2 days (not 4 weeks).

## Current Status
- **Previous Work**: Created REALTIME_PERSONALIZATION_PLAN.md with complete implementation plan
- **Critical Issue**: Weaviate search taking 699ms (too slow for voice/real-time)
- **Architecture Decided**: Real-time personalization with <10ms response, BigQuery for ML pipeline
- **Tech Stack**: React + Tailwind (NOT HTML), Cloud SQL for sessions/carts, Spanner for graph
- ✅ CI/CD pipeline ready (feature → staging → production)
- 🚀 Ready for Feature #6: Dietary & Cultural Intelligence

## 📚 Key Documents to Reference

### Architecture & Strategy
- `/docs/BDD_CONTEXT_DOCUMENT.md` - Complete BDD testing strategy
- `/docs/ENDPOINT_ANALYSIS.md` - API structure analysis
- `/docs/OPENAPI_V2_SPECIFICATION.md` - Future API design
- `/docs/PERSONALIZATION_IMPLEMENTATION.md` - TDD progress tracker
- `/CLAUDE.md` - Project overview and current status

### Completed Features (Reference for Patterns)
1. `/src/agents/response_compiler.py` - Enhanced with personalization
2. `/src/models/user_preferences.py` - User preference schema
3. `/src/agents/personalized_ranker.py` - Smart search ranking
4. `/src/agents/my_usual_analyzer.py` - My Usual functionality
5. `/src/agents/reorder_intelligence.py` - Reorder Intelligence

## 🔄 Development Flow for Session 3

```
1. Write BDD Scenario (User Story)
   ↓
2. Write TDD Unit Tests (Technical Specs)
   ↓
3. Implement Feature (Red → Green → Refactor)
   ↓
4. Verify BDD Scenario Passes
   ↓
5. Deploy to Feature Branch → Staging
```

## 🥗 Feature #6: Dietary & Cultural Intelligence

### Step 1: BDD Scenarios (Start Here!)

```gherkin
Feature: Dietary & Cultural Intelligence
  As a shopper with dietary needs
  I want LeafLoaf to understand my restrictions
  So that I see only suitable products

  Background:
    Given the dietary intelligence feature is enabled
    And the system has access to purchase history

  Scenario: Auto-detect vegan dietary preference
    Given user "sarah_vegan" has this 3-month purchase history:
      | Product | Category | Count |
      | Oat Milk | Dairy Alternatives | 12 |
      | Almond Yogurt | Dairy Alternatives | 8 |
      | Tofu | Plant Protein | 15 |
      | Tempeh | Plant Protein | 6 |
      | Quinoa | Grains | 10 |
    When sarah_vegan searches for "protein"
    Then the system should detect vegan dietary preference
    And confidence should be > 0.9
    And only plant-based proteins should appear
    And response should include "Showing vegan options"

  Scenario: Cultural cuisine understanding
    Given user "priya_indian" frequently buys:
      | Product | Category | Cultural Tag |
      | Toor Dal | Legumes | Indian |
      | Tamarind | Condiments | Indian |
      | Curry Leaves | Herbs | Indian |
      | Basmati Rice | Rice | Indian |
    When priya_indian searches for "sambar ingredients"
    Then the system should understand Indian cuisine context
    And suggest: dal, tamarind, sambar powder, vegetables
    And rank Indian grocery items higher

  Scenario: Allergen avoidance detection
    Given user "alex_allergic" has never purchased:
      | Allergen | Products Avoided |
      | Nuts | Almonds, Cashews, Peanut Butter |
      | Shellfish | Shrimp, Crab, Lobster |
    When alex_allergic searches for "snacks"
    Then products containing nuts should be filtered out
    And warning should appear for potential allergens
    And confidence in nut allergy should be > 0.8

  Scenario: Smart substitution suggestions
    Given user "emma_lactose" avoids dairy products
    When emma_lactose searches for "milk"
    Then dairy milk should rank lower
    And plant-based alternatives should rank higher
    And system should suggest "Try oat or almond milk instead"

  Scenario: Multiple dietary restrictions
    Given user "david_complex" has:
      | Restriction | Evidence |
      | Gluten-free | No wheat products in 6 months |
      | Vegetarian | No meat products in 1 year |
      | Low-sodium | Consistently buys low-sodium items |
    When david_complex searches for "dinner ideas"
    Then all results should be gluten-free AND vegetarian
    And low-sodium options should rank higher
    And system confidence should reflect all restrictions
```

### Step 2: TDD Tests to Write

Create `/tests/unit/test_dietary_intelligence.py`:

```python
# Test Categories:
1. test_vegan_preference_detection()
2. test_allergen_pattern_recognition()
3. test_cultural_cuisine_understanding()
4. test_halal_kosher_filtering()
5. test_dietary_confidence_calculation()
6. test_substitution_suggestions()
7. test_multiple_restrictions_handling()
8. test_preference_persistence()
9. test_performance_under_100ms()
10. test_gradual_learning_improvement()
```

### Step 3: Implementation Structure

Create `/src/agents/dietary_intelligence.py`:

```python
class DietaryIntelligence:
    """
    Detects and applies dietary preferences and restrictions
    Integrates with PersonalizedRanker for search filtering
    """
    
    async def analyze_dietary_patterns(self, purchase_history)
    async def detect_allergen_avoidance(self, purchase_history)
    async def understand_cultural_cuisine(self, query, user_profile)
    async def suggest_substitutions(self, product, restrictions)
    async def apply_dietary_filters(self, products, preferences)
    async def calculate_dietary_confidence(self, evidence)
```

### Step 4: Integration Points

1. **Supervisor Integration**
   - Extract dietary context from query
   - Pass to PersonalizedRanker

2. **PersonalizedRanker Enhancement**
   - Call DietaryIntelligence for filtering
   - Apply dietary scores to ranking

3. **Response Compiler Update**
   - Include dietary explanations
   - Show filtered count

4. **Graphiti Memory**
   - Store dietary preferences as entities
   - Track confidence over time

## 🚀 Deployment Strategy

### Feature Branch Testing
```bash
# Create feature branch
git checkout -b feature/dietary-intelligence

# After implementation
git push origin feature/dietary-intelligence
# → Automatic staging deployment
# → URL: leafloaf-staging-feature-dietary-intelligence.run.app
```

### BDD Validation on Staging
```bash
# Run BDD tests against staging
behave tests/bdd/features/dietary_intelligence.feature \
  --define base_url=$STAGING_URL
```

### PR Process
1. All TDD tests passing (10/10)
2. BDD scenarios validated on staging
3. Performance under 100ms
4. Documentation updated
5. Code review approval
6. Merge to main → Production

## 📊 Success Criteria

### TDD Success
- [ ] 10 unit tests written and passing
- [ ] Component performance < 100ms
- [ ] 100% code coverage
- [ ] Handles edge cases

### BDD Success
- [ ] All 5 scenarios passing
- [ ] End-to-end flow working
- [ ] Staging deployment successful
- [ ] User experience validated

### Business Value
- [ ] Vegans see only vegan products
- [ ] Allergens automatically avoided
- [ ] Cultural cuisines understood
- [ ] Substitutions suggested
- [ ] Multiple restrictions handled

## 💡 Implementation Tips

1. **Start with BDD** - Write the scenario first
2. **Break down to TDD** - Each step needs unit tests
3. **Use existing patterns** - Copy from completed features
4. **Test on staging** - Validate before production
5. **Document as you go** - Update progress tracker

## 🎯 Session Goals

1. ✅ Write 5 BDD scenarios for Dietary Intelligence
2. ✅ Write 10 TDD unit tests
3. ✅ Implement DietaryIntelligence class
4. ✅ Integrate with existing agents
5. ✅ Deploy to staging and validate
6. ✅ Update documentation
7. ✅ Create PR for review

## 📈 Progress Tracking

After this session:
- Features completed: 6/10 (60%)
- Tests written: 59 total
- BDD scenarios: 5 new dietary scenarios
- Performance: Maintaining <300ms total

Remember: **BDD for the "what"**, **TDD for the "how"**!

Good luck! 🚀