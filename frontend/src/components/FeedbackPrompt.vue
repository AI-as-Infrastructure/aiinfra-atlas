<template>
  <div class="feedback-prompt">
    <div class="prompt-content">
      <div class="prompt-text">
        <span class="prompt-message">Submit extended feedback?</span>
        <span class="tooltip" title="Take some time to provide valuable extended feedback">ⓘ</span>
      </div>
      <div class="prompt-buttons">
        <button
          class="prompt-btn yes-btn"
          @click="$emit('response', 'yes')"
        >
          Yes
        </button>
        <button
          class="prompt-btn no-btn"
          @click="$emit('response', 'no')"
        >
          No
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FeedbackPrompt',
  emits: ['response']
}
</script>

<style scoped>
.feedback-prompt {
  margin-top: 1rem;
  width: 100%;
  background-color: #e3f2fd;
  border: 1px solid #90caf9;
  border-radius: 8px;
  padding: 1rem;
}

.prompt-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.prompt-text {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.prompt-message {
  font-size: 16px;
  font-weight: 500;
  color: #1565c0;
}

.tooltip {
  color: #757575;
  cursor: help;
  font-size: 14px;
}

.prompt-buttons {
  display: flex;
  gap: 0.75rem;
}

.prompt-btn {
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.yes-btn {
  background-color: #2196f3;
  color: white;
}

.yes-btn:hover {
  background-color: #1976d2;
}

.no-btn {
  background-color: #f5f5f5;
  color: #757575;
  border: 1px solid #e0e0e0;
}

.no-btn:hover {
  background-color: #eeeeee;
  color: #424242;
}

@media (max-width: 768px) {
  .prompt-content {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }
  
  .prompt-buttons {
    justify-content: center;
  }
}
</style>