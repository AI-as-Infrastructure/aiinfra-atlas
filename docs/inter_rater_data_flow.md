# Inter-rater Data Flow

## When INTER_RATER_ENABLED=true

### User Login/Navigation Flow

```
1. User loads ATLAS homepage
   ↓
2. InterRaterButton component mounts
   ↓
3. Calls GET /api/inter-rater/stats
   ↓
4. Backend checks: InterRaterService.get_inter_rater_stats(user_id)
   ↓
5. If enabled: queries Phoenix for available session count
   ↓
6. Button shows "Inter-rating (2)" if sessions available
```

### Dashboard Population Flow

```
1. User clicks "Inter-rating" button
   ↓
2. Router navigates to /inter-rater
   ↓
3. InterRaterDashboard component mounts
   ↓
4. Calls loadSessions() → GET /api/inter-rater/sessions
   ↓
5. Backend: InterRaterService.get_sessions_for_inter_rating(user_id)
   ↓
6. Check cache first (5min timeout)
   ↓
7. If cache miss: PhoenixAPIClient.query_spans_with_feedback()
   ↓
8. Phoenix returns spans with original feedback
   ↓
9. Filter: exclude user's own sessions + already rated + max ratings reached
   ↓
10. Return filtered sessions to frontend
    ↓
11. Dashboard populates with available sessions
```

### Phoenix Query Details

The Phoenix query (currently mock, but real implementation would):

```sql
-- GraphQL/SQL equivalent of what Phoenix query would do:
SELECT spans.* 
FROM spans 
JOIN span_annotations feedback ON spans.span_id = feedback.span_id
WHERE spans.project_name = 'atlas-hansard'
  AND feedback.annotation_name = 'User Feedback'
  AND spans.attributes.user_id != '{current_user_id}'
  AND spans.span_id NOT IN (
    SELECT original_span_id 
    FROM span_annotations inter_rating 
    WHERE inter_rating.attributes.rater_id = '{current_user_id}'
      AND inter_rating.annotation_name = 'Inter-rater Feedback'
  )
  AND (
    SELECT COUNT(*) 
    FROM span_annotations ir 
    WHERE ir.attributes.original_span_id = spans.span_id
      AND ir.annotation_name = 'Inter-rater Feedback'
  ) < {max_ratings}
ORDER BY spans.start_time DESC
LIMIT {sessions_per_user}
```

### Session Data Structure

```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "qa_id": "uuid", 
      "span_id": "phoenix_span_id",
      "timestamp": "2024-01-15T10:30:00Z",
      "question": "Original user question",
      "answer": "AI response with citations",
      "original_feedback": {
        "relevance": 4,
        "clarity": 5,
        "factual_accuracy": 4,
        "user_category": "Digital HASS Researcher",
        "feedback_text": "Original user comment"
      },
      "citations": [...],
      "inter_rater_count": 1,
      "project_name": "atlas-hansard",
      "original_user_id": "cognito_user_uuid"
    }
  ]
}
```

### Caching Strategy

```
User Cache Key: "inter_rater_sessions_{user_id}"
Cache Timeout: 5 minutes
Cache Invalidation: When user submits inter-rater feedback

Benefits:
- Avoids repeated Phoenix queries
- Faster dashboard loading
- Reduces Phoenix API load
- Automatic refresh every 5 minutes
```

### Real Phoenix Integration (Future)

When connected to real Phoenix, the flow becomes:

```
1. PhoenixAPIClient.query_spans_with_feedback()
   ↓
2. HTTP POST to {phoenix_base_url}/graphql
   Headers: { "api_key": "{phoenix_api_key}" }
   ↓
3. GraphQL query for spans with feedback annotations
   ↓
4. Phoenix returns span data + annotations
   ↓
5. Client filters and formats for frontend
   ↓
6. Dashboard displays real session data
```

## Summary

**Yes, when inter-rater is toggled on:**

1. ✅ **Button appears** in header navigation
2. ✅ **Shows session count** from Phoenix query
3. ✅ **Dashboard populates** from Phoenix when accessed
4. ✅ **Cached for performance** (5min cache)
5. ✅ **Real-time updates** when user submits ratings
6. ✅ **Privacy preserved** (anonymous user IDs only)

The system is designed to be **responsive and efficient** while maintaining **data integrity** and **user privacy**.
