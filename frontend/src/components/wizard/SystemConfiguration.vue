<template>
  <div class="system-configuration">
    <h2>System Configuration</h2>
    <p class="form-description">Configure how ATLAS collects data and feedback</p>

    <div class="config-section">
      <h3>Telemetry</h3>
      <div class="config-option">
        <label class="toggle-option">
          <input
            type="checkbox"
            v-model="localConfig.telemetryEnabled"
            @change="handleConfigChange"
          />
          <span class="toggle-label">Enable anonymous telemetry</span>
        </label>
        <p class="option-description">
          Helps improve ATLAS by collecting anonymized performance metrics and usage patterns.
          No personal data or query content is collected.
        </p>
      </div>
    </div>

    <div class="config-section">
      <h3>Inter-Rater Feedback</h3>
      <div class="config-option">
        <label class="toggle-option">
          <input
            type="checkbox"
            v-model="localConfig.interRaterEnabled"
            @change="handleConfigChange"
          />
          <span class="toggle-label">Enable feedback collection</span>
        </label>
        <p class="option-description">
          Allows collection of feedback on LLM responses for research purposes.
          All feedback is anonymized.
        </p>
      </div>
    </div>

    <div class="info-box">
      <svg class="info-icon" width="16" height="16" viewBox="0 0 16 16">
        <path fill="currentColor" d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0zm1 12H7V7h2v5zm0-6H7V4h2v2z"/>
      </svg>
      <p>
        These settings can be changed later through the configuration files.
        Your choices here set the initial defaults for this corpus.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({
      telemetryEnabled: false,
      interRaterEnabled: false
    })
  }
})

const emit = defineEmits(['update:modelValue'])

const localConfig = ref({
  telemetryEnabled: false,
  interRaterEnabled: false
})

onMounted(() => {
  // Initialize with provided values or defaults
  localConfig.value = { ...props.modelValue }
})

watch(() => props.modelValue, (newValue) => {
  localConfig.value = { ...newValue }
}, { deep: true })

const handleConfigChange = () => {
  emit('update:modelValue', { ...localConfig.value })
}
</script>

<style scoped>
.system-configuration {
  max-width: 800px;
  margin: 0 auto;
}

.form-description {
  color: #666;
  margin-bottom: 2rem;
}

.config-section {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.config-section h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #333;
  font-size: 1.1rem;
}

.config-option {
  margin-bottom: 1rem;
}

.toggle-option {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.toggle-option input[type="checkbox"] {
  width: 20px;
  height: 20px;
  margin-right: 0.75rem;
  cursor: pointer;
}

.toggle-label {
  font-weight: 500;
  color: #333;
}

.option-description {
  margin-top: 0.5rem;
  margin-left: 2rem;
  color: #666;
  font-size: 0.95rem;
  line-height: 1.5;
}

.info-box {
  display: flex;
  align-items: flex-start;
  padding: 1rem;
  background: #e8f4f8;
  border-radius: 8px;
  margin-top: 2rem;
}

.info-icon {
  margin-right: 0.75rem;
  margin-top: 0.125rem;
  color: #0066cc;
  flex-shrink: 0;
}

.info-box p {
  margin: 0;
  color: #0066cc;
  font-size: 0.95rem;
  line-height: 1.5;
}
</style>