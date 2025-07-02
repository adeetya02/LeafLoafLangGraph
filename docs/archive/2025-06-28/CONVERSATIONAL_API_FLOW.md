# Conversational API Flow - Multi-Turn Implementation

## 🎯 Overview

This document shows the complete request/response flow for multi-turn conversations, maintaining context and state across interactions.

---

## 🔄 Complete Conversation Flow

### Turn 1: Initial Query

#### Request 1
```json
POST /api/v1/analyze
{
  "input_type": "voice",
  "text": "hey can you get me some rice I need about 20 pounds for my restaurant",
  "voice_metadata": {
    "duration": 4.2,
    "confidence": 0.94
  },
  "user_id": "user123",
  "session_id": "voice_session_789",
  "context": {
    "user_type": "restaurant"
  }
}
```

#### Response 1
```json
{
  "status": "success",
  "data": {
    "extracted_items": [
      {
        "extraction": {
          "raw_text": "rice I need about 20 pounds",
          "normalized_text": "rice",
          "quantity_detected": {
            "amount": 20,
            "unit": "pounds"
          }
        },
        "product_matches": [
          {
            "product": {
              "sku": "LX_RICE_001",
              "product_name": "Laxmi Basmati Rice Premium",
              "size": "20 LB",
              "price": 35.00
            },
            "match_score": 0.98,
            "purchase_history": {
              "previously_purchased": true,
              "times_purchased": 12,
              "typical_quantity": 2
            }
          }
        ]
      }
    ],
    "conversation": {
      "state": "awaiting_selection",
      "message": "You usually order 2 bags of Laxmi Basmati Rice. Want your regular order or just 1 bag this time?",
      "options": [
        {"id": "regular", "text": "2 bags (regular order)", "sku": "LX_RICE_001", "qty": 2},
        {"id": "single", "text": "Just 1 bag", "sku": "LX_RICE_001", "qty": 1},
        {"id": "different", "text": "Show other options"}
      ],
      "context": {
        "pending_items": [
          {
            "type": "rice",
            "status": "selection_needed",
            "top_match": "LX_RICE_001"
          }
        ]
      }
    }
  },
  "meta": {
    "session_id": "voice_session_789",
    "conversation_turn": 1,
    "requires_response": true
  }
}
```

---

### Turn 2: User Selection

#### Request 2
```json
POST /api/v1/analyze
{
  "input_type": "voice",
  "text": "yeah give me the regular 2 bags",
  "voice_metadata": {
    "duration": 2.1,
    "confidence": 0.95
  },
  "user_id": "user123",
  "session_id": "voice_session_789",
  "conversation_context": {
    "previous_turn": 1,
    "previous_state": "awaiting_selection",
    "pending_selection": {
      "options": ["regular", "single", "different"],
      "item_type": "rice"
    }
  }
}
```

#### Response 2
```json
{
  "status": "success",
  "data": {
    "action_result": {
      "type": "item_confirmed",
      "items_added": [
        {
          "sku": "LX_RICE_001",
          "product_name": "Laxmi Basmati Rice Premium",
          "quantity": 2,
          "unit_price": 35.00,
          "total_price": 70.00,
          "status": "confirmed_not_in_cart"
        }
      ]
    },
    "conversation": {
      "state": "item_confirmed_continue",
      "message": "Got it, 2 bags of Basmati rice. What else do you need?",
      "confirmed_items": [
        {
          "name": "Laxmi Basmati Rice",
          "quantity": "2 x 20 LB",
          "price": 70.00
        }
      ],
      "context": {
        "confirmed_not_in_cart": ["LX_RICE_001"],
        "total_so_far": 70.00,
        "awaiting": "more_items_or_checkout"
      }
    }
  },
  "meta": {
    "session_id": "voice_session_789",
    "conversation_turn": 2,
    "requires_response": true
  }
}
```

---

### Turn 3: Adding More Items

#### Request 3
```json
POST /api/v1/analyze
{
  "input_type": "voice",
  "text": "I also need some dal... toor dal and moong dal maybe 5 pounds each",
  "voice_metadata": {
    "duration": 4.8,
    "confidence": 0.88
  },
  "user_id": "user123",
  "session_id": "voice_session_789",
  "conversation_context": {
    "previous_turn": 2,
    "previous_state": "item_confirmed_continue",
    "accumulated_items": [
      {"sku": "LX_RICE_001", "qty": 2, "confirmed": true}
    ]
  }
}
```

#### Response 3
```json
{
  "status": "success",
  "data": {
    "extracted_items": [
      {
        "extraction": {
          "raw_text": "toor dal... 5 pounds",
          "normalized_text": "toor dal",
          "quantity_detected": {
            "amount": 5,
            "unit": "pounds"
          }
        },
        "product_matches": [
          {
            "product": {
              "sku": "LX_TOOR_001",
              "product_name": "Laxmi Toor Dal",
              "size": "4 LB",
              "price": 18.99
            },
            "purchase_history": {
              "previously_purchased": true,
              "times_purchased": 8,
              "typical_quantity": 3
            }
          }
        ]
      },
      {
        "extraction": {
          "raw_text": "moong dal... 5 pounds",
          "normalized_text": "moong dal"
        },
        "product_matches": [
          {
            "product": {
              "sku": "LX_MOONG_001",
              "product_name": "Laxmi Moong Dal",
              "size": "4 LB",
              "price": 16.99
            }
          }
        ]
      }
    ],
    "conversation": {
      "state": "clarification_needed",
      "message": "Both dals come in 4-pound bags. For 5 pounds each, I'd suggest 2 bags of each (8 pounds total). You usually get 3 bags of Toor Dal. Should I go with 2 bags each or your usual 3 bags of Toor?",
      "clarification": {
        "issue": "quantity_adjustment",
        "options": [
          {
            "id": "suggested",
            "text": "2 bags each (8 lbs each)",
            "items": [
              {"sku": "LX_TOOR_001", "qty": 2},
              {"sku": "LX_MOONG_001", "qty": 2}
            ]
          },
          {
            "id": "usual",
            "text": "Your usual (3 Toor, 2 Moong)",
            "items": [
              {"sku": "LX_TOOR_001", "qty": 3},
              {"sku": "LX_MOONG_001", "qty": 2}
            ]
          }
        ]
      },
      "context": {
        "accumulated_items": [
          {"sku": "LX_RICE_001", "qty": 2, "confirmed": true}
        ],
        "pending_clarification": ["dal_quantities"]
      }
    }
  },
  "meta": {
    "session_id": "voice_session_789",
    "conversation_turn": 3,
    "requires_response": true
  }
}
```

---

### Turn 4: Clarification Response

#### Request 4
```json
POST /api/v1/analyze
{
  "input_type": "voice",
  "text": "lets do my usual order",
  "voice_metadata": {
    "duration": 1.8,
    "confidence": 0.96
  },
  "user_id": "user123",
  "session_id": "voice_session_789",
  "conversation_context": {
    "previous_turn": 3,
    "previous_state": "clarification_needed",
    "pending_clarification": "dal_quantities",
    "clarification_options": ["suggested", "usual"]
  }
}
```

#### Response 4
```json
{
  "status": "success",
  "data": {
    "action_result": {
      "type": "items_confirmed",
      "items_added": [
        {
          "sku": "LX_TOOR_001",
          "product_name": "Laxmi Toor Dal",
          "quantity": 3,
          "unit_price": 18.99,
          "total_price": 56.97
        },
        {
          "sku": "LX_MOONG_001",
          "product_name": "Laxmi Moong Dal",
          "quantity": 2,
          "unit_price": 16.99,
          "total_price": 33.98
        }
      ]
    },
    "conversation": {
      "state": "ready_for_cart_or_continue",
      "message": "Perfect! I've added your usual dal order. So far you have rice and dal totaling $160.95. Want to add these to your cart or need anything else?",
      "summary": {
        "confirmed_items": [
          {"name": "Basmati Rice", "qty": "2 x 20 LB", "price": 70.00},
          {"name": "Toor Dal", "qty": "3 x 4 LB", "price": 56.97},
          {"name": "Moong Dal", "qty": "2 x 4 LB", "price": 33.98}
        ],
        "total_items": 7,
        "subtotal": 160.95
      },
      "options": [
        {"id": "add_cart", "text": "Add all to cart"},
        {"id": "continue", "text": "I need more items"},
        {"id": "review", "text": "Review my order"}
      ]
    }
  },
  "meta": {
    "session_id": "voice_session_789",
    "conversation_turn": 4
  }
}
```

---

### Turn 5: Final Action

#### Request 5
```json
POST /api/v1/analyze
{
  "input_type": "voice",
  "text": "add everything to my cart please",
  "voice_metadata": {
    "duration": 2.2,
    "confidence": 0.97
  },
  "user_id": "user123",
  "session_id": "voice_session_789",
  "conversation_context": {
    "previous_turn": 4,
    "previous_state": "ready_for_cart_or_continue",
    "confirmed_items": [
      {"sku": "LX_RICE_001", "qty": 2},
      {"sku": "LX_TOOR_001", "qty": 3},
      {"sku": "LX_MOONG_001", "qty": 2}
    ]
  }
}
```

#### Response 5
```json
{
  "status": "success",
  "data": {
    "action_result": {
      "type": "added_to_cart",
      "cart_operation": {
        "status": "success",
        "items_added": 7,
        "cart_id": "cart_abc123",
        "timestamp": "2025-06-26T14:30:00Z"
      }
    },
    "cart": {
      "cart_id": "cart_abc123",
      "items": [
        {
          "sku": "LX_RICE_001",
          "name": "Laxmi Basmati Rice Premium",
          "quantity": 2,
          "unit_price": 35.00,
          "line_total": 70.00
        },
        {
          "sku": "LX_TOOR_001",
          "name": "Laxmi Toor Dal",
          "quantity": 3,
          "unit_price": 18.99,
          "line_total": 56.97
        },
        {
          "sku": "LX_MOONG_001",
          "name": "Laxmi Moong Dal",
          "quantity": 2,
          "unit_price": 16.99,
          "line_total": 33.98
        }
      ],
      "summary": {
        "total_items": 7,
        "unique_products": 3,
        "subtotal": 160.95,
        "tax": 13.28,
        "total": 174.23
      }
    },
    "conversation": {
      "state": "cart_updated_complete",
      "message": "Great! I've added all 7 items to your cart. Your total is $174.23. Would you like to checkout now or continue shopping?",
      "options": [
        {"id": "checkout", "text": "Proceed to checkout"},
        {"id": "continue", "text": "Continue shopping"},
        {"id": "done", "text": "I'm done for now"}
      ],
      "session_summary": {
        "total_turns": 5,
        "items_discussed": 3,
        "items_in_cart": 7,
        "used_purchase_history": true,
        "clarifications_needed": 1,
        "clarifications_resolved": 1
      }
    }
  },
  "meta": {
    "session_id": "voice_session_789",
    "conversation_turn": 5,
    "conversation_complete": false
  }
}
```

---

## 🔑 Key Conversation Patterns

### 1. State Management
```json
"conversation": {
  "state": "awaiting_selection" | "clarification_needed" | "ready_for_cart",
  "context": {
    "accumulated_items": [],
    "pending_actions": [],
    "clarifications": []
  }
}
```

### 2. Context Propagation
Each request includes:
- `session_id`: Links all turns
- `conversation_context`: Previous state
- `previous_turn`: Turn number
- `accumulated_items`: Running list

### 3. Intelligent Responses
- **Selection needed**: Present options
- **Clarification needed**: Ask specific questions
- **Confirmation**: Summarize before action
- **Completion**: Clear next steps

### 4. Purchase History Integration
- "You usually order..."
- "Your typical quantity is..."
- Smart defaults based on history

### 5. Error Recovery
```json
{
  "conversation": {
    "state": "error_recovery",
    "message": "I didn't catch that. Did you want 2 bags or 3 bags?",
    "retry_context": {
      "last_question": "quantity_selection",
      "valid_responses": ["2", "3", "two", "three"]
    }
  }
}
```

---

## 📊 Session Tracking

### BigQuery Events for Each Turn
```json
{
  "event_type": "conversation_turn",
  "session_id": "voice_session_789",
  "user_id": "user123",
  "turn_number": 3,
  "state_transition": "item_confirmed -> clarification_needed",
  "items_extracted": 2,
  "clarifications_needed": 1,
  "response_time_ms": 380,
  "llm_confidence": 0.88,
  "purchase_history_used": true
}
```

---

## 🎯 Implementation Notes

1. **Session Storage**: Redis with 1-hour TTL
2. **State Machine**: Clear states and transitions
3. **Context Window**: Keep last 3 turns
4. **Graceful Degradation**: Can recover from lost context
5. **Analytics**: Track conversation quality metrics