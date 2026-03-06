/**
 * User Preferences Store for ATLAS
 *
 * This store manages user preferences including telemetry settings and other user-configurable options.
 * Preferences are persisted in localStorage across browser sessions.
 *
 * Design: telemetryEnabled defaults to true (privacy off). Users opt into privacy
 * by toggling it off. The app must work in both states.
 */

import { defineStore } from 'pinia';

// One-time migration: a previous release (fe8370e) incorrectly flipped the
// default to false, which was persisted to localStorage for any user who
// loaded the app during that window. Reset those poisoned values so users
// start with the intended default (telemetry on / privacy off).
const _MIGRATION_KEY = 'atlas-preferences-migrated-v1';
if (!localStorage.getItem(_MIGRATION_KEY)) {
  try {
    const raw = localStorage.getItem('atlas-preferences');
    if (raw) {
      const stored = JSON.parse(raw);
      // Only reset if the stored value is the bad default (false) — don't
      // touch it if the user has explicitly toggled to a different state,
      // but we can't distinguish that, so reset unconditionally this once.
      if (stored.telemetryEnabled === false) {
        stored.telemetryEnabled = true;
        localStorage.setItem('atlas-preferences', JSON.stringify(stored));
      }
    }
  } catch {
    // Corrupt localStorage — remove it so the store re-initialises cleanly
    localStorage.removeItem('atlas-preferences');
  }
  localStorage.setItem(_MIGRATION_KEY, '1');
}

export const usePreferencesStore = defineStore('preferences', {
  state: () => ({
    telemetryEnabled: true,  // Default to enabled (privacy off)
    // Future preferences can be added here
  }),

  getters: {
    /**
     * Check if telemetry is enabled by user preference
     * Note: Privacy toggle shows opposite - when privacy is ON, telemetry is OFF
     */
    isTelemetryEnabled() {
      return this.telemetryEnabled;
    }
  },

  actions: {
    /**
     * Toggle telemetry on/off
     */
    toggleTelemetry() {
      this.telemetryEnabled = !this.telemetryEnabled;
      console.log(`Telemetry ${this.telemetryEnabled ? 'enabled' : 'disabled'} by user`);
    },

    /**
     * Set telemetry preference explicitly
     */
    setTelemetryEnabled(enabled) {
      this.telemetryEnabled = enabled;
      console.log(`Telemetry ${enabled ? 'enabled' : 'disabled'} by user`);
    },

    /**
     * Reset all preferences to defaults
     */
    resetPreferences() {
      this.telemetryEnabled = true;
    }
  },

  // Persist preferences in localStorage
  persist: {
    enabled: true,
    strategies: [
      {
        key: 'atlas-preferences',
        storage: localStorage,
        paths: ['telemetryEnabled']
      }
    ]
  }
});