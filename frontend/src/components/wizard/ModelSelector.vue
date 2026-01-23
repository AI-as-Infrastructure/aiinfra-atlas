<template>
  <div class="model-selector">
    <h2>Select Embedding Model</h2>
    <p class="form-description">Choose the embedding model for your vector store</p>

    <div class="model-options">
      <div
        class="model-card"
        :class="{ active: useDefault }"
        @click="selectDefault"
      >
        <div class="model-header">
          <input
            type="radio"
            v-model="useDefault"
            :value="true"
            id="default-model"
          />
          <label for="default-model">
            <h3>Recommended Model</h3>
          </label>
        </div>
        <div class="model-info">
          <div class="model-name">{{ defaultModel.model_id }}</div>
          <p class="model-description">{{ defaultModel.description }}</p>
          <div class="model-specs">
            <span class="spec">
              <strong>Performance:</strong> {{ defaultModel.performance }}
            </span>
            <span class="spec">
              <strong>Size:</strong> {{ defaultModel.size_mb }} MB
            </span>
            <span class="spec">
              <strong>Dimensions:</strong> {{ defaultModel.dimensions }}
            </span>
            <span class="spec">
              <strong>Max Length:</strong> {{ defaultModel.max_seq_length }} tokens
            </span>
          </div>
        </div>
      </div>

      <div
        class="model-card"
        :class="{ active: !useDefault }"
        @click="selectCustom"
      >
        <div class="model-header">
          <input
            type="radio"
            v-model="useDefault"
            :value="false"
            id="custom-model"
          />
          <label for="custom-model">
            <h3>Custom Model</h3>
          </label>
        </div>
        <div class="model-info">
          <p>Use a specific model from HuggingFace</p>
          <div v-if="!useDefault" class="custom-model-input">
            <input
              v-model="customModelId"
              type="text"
              placeholder="e.g., sentence-transformers/all-mpnet-base-v2"
              @blur="validateCustomModel"
            />
            <button @click="validateCustomModel" class="validate-btn">
              Validate
            </button>
          </div>
          <div v-if="customModelInfo" class="model-validation">
            <div v-if="customModelValid" class="validation-success">
              ✅ Model validated successfully
              <div class="model-specs">
                <span class="spec">
                  <strong>Dimensions:</strong> {{ customModelInfo.dimensions }}
                </span>
                <span class="spec">
                  <strong>Max Length:</strong> {{ customModelInfo.max_seq_length }}
                </span>
                <span class="spec">
                  <strong>Est. Size:</strong> {{ customModelInfo.estimated_size_mb }} MB
                </span>
              </div>
            </div>
            <div v-else class="validation-error">
              ❌ {{ customModelError }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="model-testing">
      <h3>Test Model with Sample Text</h3>
      <p>Test how the selected model processes your corpus content</p>

      <div class="test-section">
        <textarea
          v-model="sampleText"
          placeholder="Paste a sample from your corpus here..."
          rows="4"
        ></textarea>
        <button @click="testModel" class="test-btn" :disabled="!canTest">
          Test Embedding
        </button>
      </div>

      <div v-if="testResults" class="test-results">
        <h4>Test Results</h4>
        <div class="results-grid">
          <div class="result-item">
            <span class="label">Processing Time:</span>
            <span class="value">{{ testResults.processing_time }} ms</span>
          </div>
          <div class="result-item">
            <span class="label">Vector Dimensions:</span>
            <span class="value">{{ testResults.dimensions }}</span>
          </div>
          <div class="result-item">
            <span class="label">Token Count:</span>
            <span class="value">{{ testResults.token_count }}</span>
          </div>
          <div class="result-item">
            <span class="label">Memory Used:</span>
            <span class="value">{{ testResults.memory_mb }} MB</span>
          </div>
        </div>
        <div v-if="testResults.similar_chunks" class="similar-chunks">
          <h5>Similar Passages Found:</h5>
          <div
            v-for="(chunk, index) in testResults.similar_chunks"
            :key="index"
            class="chunk-preview"
          >
            <span class="similarity-score">{{ chunk.score }}% similar</span>
            <p>{{ chunk.text }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="embedding-config">
      <h3>Embedding Configuration</h3>
      <div class="config-grid">
        <div class="form-group">
          <label for="chunk-size">Chunk Size (tokens)</label>
          <input
            id="chunk-size"
            v-model.number="localData.chunk_size"
            type="number"
            min="100"
            max="1000"
          />
          <small>Number of tokens per chunk</small>
        </div>
        <div class="form-group">
          <label for="chunk-overlap">Chunk Overlap (tokens)</label>
          <input
            id="chunk-overlap"
            v-model.number="localData.chunk_overlap"
            type="number"
            min="0"
            max="200"
          />
          <small>Overlap between consecutive chunks</small>
        </div>
        <div class="form-group">
          <label for="batch-size">Batch Size</label>
          <input
            id="batch-size"
            v-model.number="localData.batch_size"
            type="number"
            min="1"
            max="128"
          />
          <small>Documents processed per batch</small>
        </div>
      </div>
    </div>

    <div class="form-actions">
      <button @click="$emit('back')" class="btn btn-secondary">Back</button>
      <button @click="handleNext" class="btn btn-primary" :disabled="!canProceed">
        Next Step
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue';
import axios from 'axios';

export default {
  name: 'ModelSelector',

  props: {
    modelValue: {
      type: Object,
      required: true
    },
    corpusMetadata: {
      type: Object,
      default: () => ({})
    }
  },

  emits: ['update:modelValue', 'next', 'back'],

  setup(props, { emit }) {
    const localData = ref({ ...props.modelValue });
    const useDefault = ref(true);
    const defaultModel = ref({});
    const customModelId = ref('');
    const customModelInfo = ref(null);
    const customModelValid = ref(false);
    const customModelError = ref('');
    const sampleText = ref('');
    const testResults = ref(null);

    const canTest = computed(() => {
      return sampleText.value.trim().length > 0 &&
        (useDefault.value || customModelValid.value);
    });

    const canProceed = computed(() => {
      return useDefault.value || customModelValid.value;
    });

    const selectDefault = () => {
      useDefault.value = true;
      localData.value.model_id = defaultModel.value.model_id;
      customModelInfo.value = null;
    };

    const selectCustom = () => {
      useDefault.value = false;
      if (customModelId.value && customModelValid.value) {
        localData.value.model_id = customModelId.value;
      }
    };

    const loadDefaultModel = async () => {
      try {
        const response = await axios.get('/api/corpus-wizard/model-recommendation');
        defaultModel.value = response.data.default;
        if (useDefault.value) {
          localData.value.model_id = defaultModel.value.model_id;
        }
      } catch (error) {
        console.error('Failed to load default model:', error);
        // Fallback
        defaultModel.value = {
          model_id: 'sentence-transformers/all-MiniLM-L6-v2',
          description: 'General-purpose model suitable for most corpora',
          performance: 'Fast processing with good accuracy',
          size_mb: 90,
          dimensions: 384,
          max_seq_length: 512
        };
      }
    };

    const validateCustomModel = async () => {
      if (!customModelId.value.trim()) {
        return;
      }

      try {
        const response = await axios.post('/api/corpus-wizard/validate-model',
          customModelId.value
        );

        if (response.data.valid) {
          customModelValid.value = true;
          customModelInfo.value = response.data.model_info;
          localData.value.model_id = customModelId.value;
          customModelError.value = '';
        } else {
          customModelValid.value = false;
          customModelError.value = response.data.error;
        }
      } catch (error) {
        customModelValid.value = false;
        customModelError.value = 'Failed to validate model';
      }
    };

    const testModel = async () => {
      // Mock test results
      testResults.value = {
        processing_time: Math.floor(Math.random() * 500) + 100,
        dimensions: useDefault.value ? defaultModel.value.dimensions : customModelInfo.value?.dimensions || 384,
        token_count: sampleText.value.split(' ').length,
        memory_mb: 12.5,
        similar_chunks: [
          {
            score: 95,
            text: 'This is a similar passage from the corpus that matches your sample...'
          },
          {
            score: 87,
            text: 'Another relevant passage that was found using the embedding model...'
          }
        ]
      };
    };

    const handleNext = () => {
      emit('update:modelValue', localData.value);
      emit('next');
    };

    // Load default model on mount
    onMounted(() => {
      loadDefaultModel();
    });

    // Watch for external changes
    watch(
      () => props.modelValue,
      (newValue) => {
        localData.value = { ...newValue };
      },
      { deep: true }
    );

    // Emit changes
    watch(
      localData,
      (newValue) => {
        emit('update:modelValue', newValue);
      },
      { deep: true }
    );

    return {
      localData,
      useDefault,
      defaultModel,
      customModelId,
      customModelInfo,
      customModelValid,
      customModelError,
      sampleText,
      testResults,
      canTest,
      canProceed,
      selectDefault,
      selectCustom,
      validateCustomModel,
      testModel,
      handleNext
    };
  }
};
</script>

<style scoped>
.model-selector {
  max-width: 900px;
  margin: 0 auto;
}

.model-selector h2 {
  color: #333;
  margin-bottom: 0.5rem;
}

.form-description {
  color: #666;
  margin-bottom: 2rem;
}

.model-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 2rem;
}

.model-card {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.model-card:hover {
  border-color: #3498db;
  background: #f8f9fa;
}

.model-card.active {
  border-color: #3498db;
  background: #e3f2fd;
}

.model-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.model-header h3 {
  margin: 0;
  color: #333;
}

.model-info {
  color: #666;
}

.model-name {
  font-family: monospace;
  background: #f5f5f5;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.model-description {
  margin: 0.5rem 0;
}

.model-specs {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 0.5rem;
}

.spec {
  font-size: 0.875rem;
}

.custom-model-input {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.custom-model-input input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.validate-btn {
  padding: 0.5rem 1rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.model-validation {
  margin-top: 1rem;
}

.validation-success {
  color: #4caf50;
}

.validation-error {
  color: #f44336;
}

.model-testing {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.model-testing h3 {
  margin-top: 0;
  color: #333;
}

.test-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.test-section textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: vertical;
}

.test-btn {
  padding: 0.75rem 1.5rem;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  align-self: flex-start;
}

.test-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.test-results {
  margin-top: 1.5rem;
  padding: 1rem;
  background: white;
  border-radius: 4px;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.result-item {
  display: flex;
  flex-direction: column;
}

.result-item .label {
  font-size: 0.875rem;
  color: #666;
}

.result-item .value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
}

.similar-chunks {
  margin-top: 1rem;
}

.chunk-preview {
  padding: 0.5rem;
  background: #f5f5f5;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.similarity-score {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  background: #4caf50;
  color: white;
  border-radius: 4px;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.chunk-preview p {
  margin: 0.5rem 0 0;
  color: #666;
  font-size: 0.9rem;
}

.embedding-config {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.form-group input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.form-group small {
  display: block;
  margin-top: 0.25rem;
  color: #666;
  font-size: 0.875rem;
}

.form-actions {
  margin-top: 2rem;
  display: flex;
  justify-content: space-between;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #95a5a6;
  color: white;
}

.btn-secondary:hover {
  background: #7f8c8d;
}

@media (max-width: 768px) {
  .model-options {
    grid-template-columns: 1fr;
  }
}
</style>