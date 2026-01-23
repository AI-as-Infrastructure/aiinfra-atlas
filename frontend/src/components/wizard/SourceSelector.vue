<template>
  <div class="source-selector">
    <h2>Select Corpus Source</h2>
    <p class="form-description">Choose where your corpus files are located</p>

    <div class="source-types">
      <div
        class="source-type-card"
        :class="{ active: localData.type === 'local' }"
        @click="selectSourceType('local')"
      >
        <div class="icon">📁</div>
        <h3>Local Directory</h3>
        <p>Files on this server</p>
      </div>

      <div
        class="source-type-card"
        :class="{ active: localData.type === 'github' }"
        @click="selectSourceType('github')"
      >
        <div class="icon">🐙</div>
        <h3>GitHub Repository</h3>
        <p>Files in a GitHub repo</p>
      </div>
    </div>

    <div v-if="localData.type" class="source-config">
      <!-- Local Directory Configuration -->
      <div v-if="localData.type === 'local'" class="config-section">
        <div class="form-group">
          <label for="local-path">Directory Path *</label>
          <div class="path-input">
            <input
              id="local-path"
              v-model="localData.location"
              type="text"
              required
              placeholder="/path/to/corpus/files"
            />
            <button type="button" @click="browsePath" class="browse-btn">Browse</button>
          </div>
          <small>Enter the full path to your corpus directory</small>
        </div>

        <div v-if="localData.location" class="path-preview">
          <h4>Directory Preview</h4>
          <div class="file-tree">
            <div v-for="item in directoryPreview" :key="item" class="tree-item">
              {{ item }}
            </div>
          </div>
        </div>
      </div>

      <!-- GitHub Configuration -->
      <div v-else-if="localData.type === 'github'" class="config-section">
        <div class="form-group">
          <label for="github-url">Repository URL *</label>
          <input
            id="github-url"
            v-model="localData.location"
            type="url"
            required
            placeholder="https://github.com/username/repository"
          />
          <small>Enter the GitHub repository URL</small>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="github-branch">Branch</label>
            <input
              id="github-branch"
              v-model="localData.branch"
              type="text"
              placeholder="main"
            />
          </div>

          <div class="form-group">
            <label for="github-path">Path (optional)</label>
            <input
              id="github-path"
              v-model="repoPath"
              type="text"
              placeholder="docs/corpus"
            />
            <small>Subdirectory within the repository</small>
          </div>
        </div>

        <div class="form-group">
          <label>Sparse Checkout (optional)</label>
          <div class="sparse-input">
            <input
              v-model="sparseInput"
              type="text"
              placeholder="Add path to include..."
              @keypress.enter.prevent="addSparsePath"
            />
            <button type="button" @click="addSparsePath">Add</button>
          </div>
          <div class="sparse-paths">
            <span
              v-for="(path, index) in localData.sparse_checkout"
              :key="index"
              class="tag"
            >
              {{ path }}
              <button type="button" @click="removeSparsePath(index)" class="remove-tag">×</button>
            </span>
          </div>
          <small>Only download specific paths from the repository</small>
        </div>
      </div>
    </div>

    <div class="validation-status" v-if="validationMessage">
      <div :class="['message', validationStatus]">
        {{ validationMessage }}
      </div>
    </div>

    <div class="form-actions">
      <button @click="$emit('back')" class="btn btn-secondary">Back</button>
      <button @click="validateAndNext" class="btn btn-primary" :disabled="!canProceed">
        Next Step
      </button>
    </div>
  </div>
</template>

<script>
import { ref, watch, computed } from 'vue';
import axios from 'axios';

export default {
  name: 'SourceSelector',

  props: {
    modelValue: {
      type: Object,
      required: true
    }
  },

  emits: ['update:modelValue', 'next', 'back'],

  setup(props, { emit }) {
    const localData = ref({ ...props.modelValue });
    const directoryPreview = ref([]);
    const sparseInput = ref('');
    const repoPath = ref('');
    const validationStatus = ref('');
    const validationMessage = ref('');

    const canProceed = computed(() => {
      return localData.value.type && localData.value.location && validationStatus.value !== 'error';
    });

    const selectSourceType = (type) => {
      localData.value.type = type;
      localData.value.location = '';
      localData.value.sparse_checkout = [];
      directoryPreview.value = [];
      validationMessage.value = '';
    };

    const browsePath = async () => {
      // In a real implementation, this would open a file browser
      // For now, we'll validate the entered path
      if (localData.value.location) {
        await validatePath();
      }
    };

    const validatePath = async () => {
      try {
        // Mock validation - in reality would check if path exists
        validationStatus.value = 'success';
        validationMessage.value = 'Path is valid';

        // Mock directory preview
        directoryPreview.value = [
          '📁 sources/',
          '  📁 1901/',
          '    📄 hansard_1901_01.txt',
          '    📄 hansard_1901_02.txt',
          '  📁 1902/',
          '    📄 hansard_1902_01.txt',
          '📄 metadata.json'
        ];
      } catch (error) {
        validationStatus.value = 'error';
        validationMessage.value = 'Path does not exist or is not accessible';
      }
    };

    const addSparsePath = () => {
      if (sparseInput.value.trim()) {
        if (!localData.value.sparse_checkout) {
          localData.value.sparse_checkout = [];
        }
        localData.value.sparse_checkout.push(sparseInput.value.trim());
        sparseInput.value = '';
      }
    };

    const removeSparsePath = (index) => {
      localData.value.sparse_checkout.splice(index, 1);
    };

    const validateAndNext = async () => {
      if (localData.value.type === 'local') {
        await validatePath();
        if (validationStatus.value === 'success') {
          emit('next');
        }
      } else if (localData.value.type === 'github') {
        // Validate GitHub URL
        if (localData.value.location.includes('github.com')) {
          emit('next');
        } else {
          validationStatus.value = 'error';
          validationMessage.value = 'Please enter a valid GitHub repository URL';
        }
      }
    };

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
      directoryPreview,
      sparseInput,
      repoPath,
      validationStatus,
      validationMessage,
      canProceed,
      selectSourceType,
      browsePath,
      addSparsePath,
      removeSparsePath,
      validateAndNext
    };
  }
};
</script>

<style scoped>
.source-selector {
  max-width: 800px;
  margin: 0 auto;
}

.source-selector h2 {
  color: #333;
  margin-bottom: 0.5rem;
}

.form-description {
  color: #666;
  margin-bottom: 2rem;
}

.source-types {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 2rem;
}

.source-type-card {
  padding: 2rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.source-type-card:hover {
  border-color: #3498db;
  background: #f8f9fa;
}

.source-type-card.active {
  border-color: #3498db;
  background: #e3f2fd;
}

.source-type-card .icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.source-type-card h3 {
  margin: 0 0 0.5rem;
  color: #333;
}

.source-type-card p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.config-section {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group:last-child {
  margin-bottom: 0;
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
  font-size: 1rem;
}

.form-group input:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.1);
}

.form-group small {
  display: block;
  margin-top: 0.25rem;
  color: #666;
  font-size: 0.875rem;
}

.path-input {
  display: flex;
  gap: 0.5rem;
}

.path-input input {
  flex: 1;
}

.browse-btn {
  padding: 0.5rem 1rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.browse-btn:hover {
  background: #2980b9;
}

.path-preview {
  margin-top: 1rem;
  padding: 1rem;
  background: white;
  border-radius: 4px;
}

.path-preview h4 {
  margin: 0 0 0.5rem;
  color: #333;
}

.file-tree {
  font-family: monospace;
  font-size: 0.9rem;
  color: #666;
}

.tree-item {
  padding: 0.25rem 0;
  white-space: pre;
}

.sparse-input {
  display: flex;
  gap: 0.5rem;
}

.sparse-input input {
  flex: 1;
}

.sparse-input button {
  padding: 0.5rem 1rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.sparse-paths {
  margin-top: 0.5rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag {
  background: #e0e0e0;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.remove-tag {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 1.2rem;
  line-height: 1;
  padding: 0;
}

.validation-status {
  margin: 1rem 0;
}

.validation-status .message {
  padding: 0.75rem;
  border-radius: 4px;
}

.validation-status .message.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.validation-status .message.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
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

@media (max-width: 600px) {
  .source-types {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>