<template>
  <div class="wizard-steps">
    <div class="steps-container">
      <div
        v-for="(step, index) in steps"
        :key="step.id"
        class="step-item"
        :class="{
          'active': currentStep === step.id,
          'completed': stepStatus[step.id] === 'completed',
          'error': stepStatus[step.id] === 'error'
        }"
        @click="$emit('step-click', step.id)"
      >
        <div class="step-number">
          <span v-if="stepStatus[step.id] === 'completed'" class="checkmark">✓</span>
          <span v-else-if="stepStatus[step.id] === 'error'" class="error-mark">✗</span>
          <span v-else>{{ step.id }}</span>
        </div>
        <div class="step-label">{{ step.label }}</div>
        <div v-if="index < steps.length - 1" class="step-line" :class="{ 'completed': stepStatus[step.id] === 'completed' }"></div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'WizardSteps',

  props: {
    currentStep: {
      type: Number,
      required: true
    },
    steps: {
      type: Array,
      required: true
    },
    stepStatus: {
      type: Object,
      required: true
    }
  },

  emits: ['step-click']
};
</script>

<style scoped>
.wizard-steps {
  margin-bottom: 2rem;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.steps-container {
  display: flex;
  justify-content: space-between;
  position: relative;
}

.step-item {
  flex: 1;
  text-align: center;
  position: relative;
  cursor: pointer;
  transition: all 0.3s ease;
}

.step-item:hover {
  opacity: 0.8;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #e0e0e0;
  color: #666;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 0.5rem;
  font-weight: bold;
  transition: all 0.3s ease;
}

.step-item.active .step-number {
  background: #3498db;
  color: white;
  box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3);
}

.step-item.completed .step-number {
  background: #4caf50;
  color: white;
}

.step-item.error .step-number {
  background: #f44336;
  color: white;
}

.checkmark,
.error-mark {
  font-size: 1.2rem;
}

.step-label {
  font-size: 0.9rem;
  color: #666;
}

.step-item.active .step-label {
  color: #3498db;
  font-weight: 500;
}

.step-item.completed .step-label {
  color: #4caf50;
}

.step-line {
  position: absolute;
  top: 20px;
  left: 70%;
  width: calc(100% - 40%);
  height: 2px;
  background: #e0e0e0;
  transition: all 0.3s ease;
}

.step-line.completed {
  background: #4caf50;
}

@media (max-width: 768px) {
  .steps-container {
    flex-direction: column;
  }

  .step-item {
    margin-bottom: 1rem;
  }

  .step-line {
    display: none;
  }
}
</style>