# Inter-rater Reliability Feature

## Overview

The inter-rater reliability feature allows multiple users to independently rate the same AI responses to assess the consistency and reliability of feedback. This is crucial for validating the quality of user feedback and improving the overall assessment process.

## Architecture

### Backend Components

1. **InterRaterService** (`backend/services/inter_rater_service.py`)
   - Manages inter-rater functionality
   - Retrieves sessions eligible for inter-rating
   - Handles configuration and user limits

2. **PhoenixAPIClient** (`backend/services/phoenix_client.py`)
   - Interfaces with Phoenix for querying existing sessions
   - Filters sessions based on user and rating criteria
   - Handles authentication with Phoenix API

3. **Enhanced Feedback Models** (`backend/telemetry/feedback.py`)
   - Extended UserFeedback model with inter-rater fields
   - Tracks original span associations
   - Maintains user anonymity while enabling tracking

### Frontend Components

1. **InterRaterButton** (`frontend/src/components/InterRaterButton.vue`)
   - Navigation link in header
   - Shows availability of sessions for rating
   - Only visible when feature is enabled

2. **InterRaterDashboard** (`frontend/src/components/InterRaterDashboard.vue`)
   - Main interface for managing inter-rating sessions
   - Shows progress and statistics
   - Handles session navigation

3. **InterRaterPlayback** (`frontend/src/components/InterRaterPlayback.vue`)
   - Displays original Q&A and feedback
   - Provides interface for new rating
   - Maintains context of original interaction

## Configuration

Add these environment variables to your `.env.*` files:

```bash
# Inter-rater reliability configuration
INTER_RATER_ENABLED=false           # Enable/disable the feature
INTER_RATER_PROJECT=atlas-hansard   # Project name to filter sessions
INTER_RATER_MAX_RATINGS=3          # Maximum ratings per session
INTER_RATER_SESSIONS_PER_USER=5    # Sessions shown to each user
```

## Usage

### Enabling Inter-rater Mode

1. Set `INTER_RATER_ENABLED=true` in your environment configuration
2. Ensure `INTER_RATER_PROJECT` matches your Phoenix project name
3. Configure `INTER_RATER_MAX_RATINGS` (recommended: 2-3)
4. Set `INTER_RATER_SESSIONS_PER_USER` based on your needs

### Workflow

1. **Initial Feedback Phase**: Users provide normal feedback on AI responses
2. **Inter-rater Phase**: 
   - Enable inter-rater mode in configuration
   - "Inter-rating" button appears in navigation for eligible users
   - Users can access sessions they haven't previously rated
   - Each session shows original Q&A, response, and initial feedback
   - Users provide independent ratings using the same criteria

### Data Flow

1. Original feedback is stored in Phoenix with user ID
2. Inter-rater requests query Phoenix for sessions:
   - With existing feedback
   - From current project
   - Not yet rated by requesting user
   - Below maximum rating threshold
3. Inter-rater feedback is submitted as new spans linked to originals
4. Phoenix stores both original and inter-rater feedback for analysis

## Privacy Considerations

- User IDs are anonymous Cognito identifiers
- No personally identifiable information is stored
- Users only see sessions they didn't create
- Original feedback authors cannot be identified
- System maintains research ethics compliance

## API Endpoints

### GET `/api/inter-rater/stats`
Returns availability statistics for current user:
```json
{
  "enabled": true,
  "available_sessions": 3,
  "completed_sessions": 1,
  "max_sessions_per_user": 5,
  "project_name": "atlas-hansard"
}
```

### GET `/api/inter-rater/sessions`
Returns sessions available for inter-rating:
```json
{
  "sessions": [
    {
      "session_id": "session_001",
      "qa_id": "qa_001",
      "span_id": "abcd1234efgh5678",
      "timestamp": "2024-01-15T10:30:00Z",
      "question": "What were the main provisions...",
      "answer": "The Parliamentary Reform Act...",
      "original_feedback": {
        "relevance": 4,
        "clarity": 5,
        "factual_accuracy": 4,
        "user_category": "Digital HASS Researcher"
      },
      "citations": [...],
      "inter_rater_count": 1
    }
  ]
}
```

### POST `/api/feedback` (Enhanced)
Accepts inter-rater feedback with additional fields:
```json
{
  "session_id": "session_001",
  "qa_id": "qa_001",
  "is_inter_rater": true,
  "original_span_id": "abcd1234efgh5678",
  "relevance": 4,
  "clarity": 5,
  "factual_accuracy": 4,
  "source_quality": 4,
  "feedback_text": "Additional inter-rater comments..."
}
```

## Future Enhancements

- **Real Phoenix Integration**: Replace mock data with actual Phoenix GraphQL queries
- **Advanced Filtering**: Add date ranges, user categories, response types
- **Agreement Metrics**: Calculate inter-rater agreement scores (Kappa, ICC)
- **Batch Processing**: Support for rating multiple sessions in sequence
- **Export Functionality**: Download inter-rater data for analysis
- **Admin Dashboard**: Monitor inter-rater progress and statistics

## Troubleshooting

### Inter-rater Button Not Visible
- Check `INTER_RATER_ENABLED=true` in environment
- Verify Phoenix API connectivity
- Ensure user has available sessions

### No Sessions Available
- Check project name configuration
- Verify original feedback exists in Phoenix
- Confirm user hasn't already rated available sessions
- Check maximum ratings threshold

### API Errors
- Verify Phoenix API credentials
- Check Phoenix collector endpoint URL
- Review telemetry configuration
- Monitor backend logs for specific errors
