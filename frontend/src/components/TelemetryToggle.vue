<template>
  <div v-if="isTelemetrySystemEnabled" class="telemetry-toggle">
    <label class="toggle-label">
      <input
        type="checkbox"
        :checked="!isTelemetryEnabled"
        @change="handleToggle"
        class="toggle-checkbox"
      />
      <span class="toggle-slider"></span>
      <span class="toggle-text">Privacy</span>
      <span class="toggle-state">{{ !isTelemetryEnabled ? 'On' : 'Off' }}</span>
      <div class="tooltip-container">
        <span class="info-icon">ⓘ</span>
        <div class="tooltip-text">Controls whether anonymous usage data and feedback are shared for research purposes.</div>
      </div>
    </label>
    <div class="toggle-description">
      {{ !isTelemetryEnabled ? 'Not sharing usage data or feedback' : 'Sharing anonymous usage data and feedback' }}
    </div>
  </div>
</template>

<script setup>
import { usePreferencesStore } from '../stores/preferences'
import { storeToRefs } from 'pinia'

const preferencesStore = usePreferencesStore()
const { isTelemetryEnabled } = storeToRefs(preferencesStore)

const isTelemetrySystemEnabled = import.meta.env.VITE_TELEMETRY_ENABLED === 'true'

const handleToggle = () => {
  preferencesStore.toggleTelemetry()
}
</script>

<style scoped>
.telemetry-toggle {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;
}

.toggle-checkbox {
  display: none;
}

.toggle-slider {
  position: relative;
  width: 44px;
  height: 24px;
  background-color: #ccc;
  border-radius: 12px;
  transition: background-color 0.3s ease;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: white;
  top: 2px;
  left: 2px;
  transition: transform 0.3s ease;
}

.toggle-checkbox:checked + .toggle-slider {
  background-color: #dc3545;
}

.toggle-checkbox:checked + .toggle-slider::before {
  transform: translateX(20px);
}

.toggle-text {
  font-weight: 500;
  color: #333;
}

.toggle-state {
  font-size: 0.9em;
  color: #666;
  margin-left: 8px;
}

.tooltip-container {
  display: inline-block;
  margin-left: 4px;
  position: relative;
  vertical-align: middle;
}

.info-icon {
  cursor: pointer;
}

.tooltip-text {
  display: none;
  position: absolute;
  left: 20px;
  top: -5px;
  background: #333;
  color: #fff;
  padding: 0.5em;
  border-radius: 4px;
  white-space: pre-line;
  z-index: 10;
  width: 250px;
}

.tooltip-container:hover .tooltip-text {
  display: block;
}

.toggle-description {
  font-size: 0.9em;
  color: #666;
  margin-left: 56px;
}
</style>