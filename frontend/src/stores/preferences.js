/**
 * User Preferences Store for ATLAS
 * 
 * This store manages user preferences including telemetry settings and other user-configurable options.
 * Preferences are persisted in localStorage across browser sessions.
 */

import { defineStore } from 'pinia';

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