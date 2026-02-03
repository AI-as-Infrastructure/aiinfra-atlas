# Add System Configuration Settings to Corpus Wizard

## Summary

Add a new configuration step to the corpus wizard that allows users to toggle system-wide settings including inter-rater feedback and telemetry during initial setup. This provides users with transparent control over data collection and feedback mechanisms from the first interaction with the system.

## Motivation

Currently, inter-rater feedback and telemetry settings are controlled via environment variables that must be set before deployment. This approach:
- Lacks transparency for end users about data collection
- Requires technical knowledge to modify settings
- Cannot be adjusted through the UI after deployment
- Creates friction for users who want to opt-out of telemetry or feedback collection

Adding these configuration options to the corpus wizard ensures:
- Users have immediate visibility and control over data collection
- Settings can be adjusted without technical intervention
- Compliance with privacy best practices by making opt-in/opt-out explicit
- Better user experience through centralized configuration

## Detailed Design

### 1. New Configuration Step in Wizard

Add a new step between "Metadata" (Step 1) and "Source" (Step 2) called "System Configuration":
- Position: Step 2 (all subsequent steps shift +1)
- Component: `SystemConfiguration.vue`
- Purpose: Configure telemetry and feedback settings before corpus creation

### 2. Configuration Options

The new configuration step will present:

**Telemetry Settings:**
- Toggle: Enable/Disable Phoenix telemetry
- Description: Explain what data is collected (anonymized performance metrics, LLM interactions)
- Default: Disabled (opt-in approach for privacy)

**Inter-Rater Feedback:**
- Toggle: Enable/Disable inter-rater feedback system
- Description: Explain the feedback collection for research purposes
- Default: Disabled (opt-in approach)

### 3. Backend Integration

**New Endpoint:** `POST /api/system/configuration`
- Updates runtime configuration without restart
- Persists settings to a configuration file
- Returns success/failure status

**Configuration Storage:**
- Create `config/system_settings.json` for runtime settings
- Backend reads this file on startup and applies settings
- Environment variables remain as deployment-time overrides

### 4. UI Components

**SystemConfiguration.vue:**
```vue
<template>
  <div class="system-configuration">
    <h2>System Configuration</h2>
    <p>Configure how ATLAS collects data and feedback</p>

    <div class="config-section">
      <h3>Telemetry</h3>
      <label>
        <input type="checkbox" v-model="config.telemetryEnabled">
        Enable anonymous telemetry
      </label>
      <p class="description">
        Helps improve ATLAS by collecting anonymized performance metrics and usage patterns.
        No personal data or query content is collected.
      </p>
    </div>

    <div class="config-section">
      <h3>Inter-Rater Feedback</h3>
      <label>
        <input type="checkbox" v-model="config.interRaterEnabled">
        Enable feedback collection
      </label>
      <p class="description">
        Allows collection of feedback on LLM responses for research purposes.
        All feedback is anonymized.
      </p>
    </div>
  </div>
</template>
```

## Breaking Changes

None. This is an additive change that:
- Maintains backward compatibility with environment variables
- Does not modify existing APIs
- Preserves current default behaviors

## Alternatives Considered

1. **Separate Settings Page:** Add a dedicated settings page outside the wizard
   - Pros: More discoverable for existing users
   - Cons: Users might miss it during initial setup

2. **Environment Variables Only:** Keep current approach
   - Pros: Simple, no UI changes needed
   - Cons: Poor user experience, lacks transparency

3. **First-Run Modal:** Show configuration modal on first application load
   - Pros: Ensures all users see it
   - Cons: Interrupts user flow, feels intrusive

## Security Considerations

- Configuration endpoint requires appropriate authentication
- Settings file should have restricted permissions (backend-only access)
- Validation of boolean values to prevent injection
- Audit logging for configuration changes

## Testing Strategy

1. Unit tests for new Vue component
2. Integration tests for configuration endpoint
3. E2E tests for wizard flow with new step
4. Manual testing of setting persistence across restarts

## Implementation Priority

High - This addresses privacy concerns and improves user trust by providing transparent control over data collection from the first interaction with the system.