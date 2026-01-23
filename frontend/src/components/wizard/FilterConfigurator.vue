<template>
  <div class="filter-configurator">
    <h2>Configure Corpus Filters</h2>
    <p class="form-description">Review and customize the discovered filters for your corpus</p>

    <div class="filters-summary">
      <div class="summary-stats">
        <span>{{ localFilters.length }} filters discovered</span>
        <span v-if="enabledCount > 0" class="enabled-count">
          ({{ enabledCount }} enabled)
        </span>
      </div>
    </div>

    <div class="filter-list">
      <div
        v-for="(filter, index) in localFilters"
        :key="filter.id"
        class="filter-item"
        :class="{ disabled: !filter.enabled }"
      >
        <div class="filter-header">
          <input
            type="checkbox"
            v-model="filter.enabled"
            :id="`filter-${filter.id}`"
          />
          <label :for="`filter-${filter.id}`" class="filter-label">
            {{ filter.label }}
          </label>
          <span class="filter-stats" v-if="filter.file_count">
            ({{ filter.file_count }} files)
          </span>
          <button
            type="button"
            @click="editFilter(index)"
            class="edit-btn"
          >
            Edit
          </button>
        </div>

        <div class="filter-details">
          <span class="detail-item">
            <strong>ID:</strong> {{ filter.id }}
          </span>
          <span class="detail-item">
            <strong>Type:</strong> {{ filter.type }}
          </span>
          <span class="detail-item">
            <strong>Pattern:</strong> <code>{{ filter.pattern }}</code>
          </span>
        </div>

        <div v-if="editingIndex === index" class="filter-edit">
          <div class="edit-group">
            <label>Filter Label:</label>
            <input
              v-model="filter.label"
              type="text"
              placeholder="Display name for this filter"
            />
          </div>
          <div class="edit-group">
            <label>Filter Pattern:</label>
            <input
              v-model="filter.pattern"
              type="text"
              placeholder="File pattern or XPath"
            />
          </div>
          <div class="edit-actions">
            <button @click="saveEdit(index)" class="save-btn">Save</button>
            <button @click="cancelEdit" class="cancel-btn">Cancel</button>
          </div>
        </div>
      </div>
    </div>

    <div class="add-filter-section">
      <h3>Add Custom Filter</h3>
      <div class="add-filter-form">
        <div class="form-row">
          <input
            v-model="newFilter.id"
            type="text"
            placeholder="Filter ID (lowercase, no spaces)"
            pattern="[a-z0-9_-]+"
          />
          <input
            v-model="newFilter.label"
            type="text"
            placeholder="Filter Label"
          />
        </div>
        <div class="form-row">
          <input
            v-model="newFilter.pattern"
            type="text"
            placeholder="Pattern (e.g., docs/**/*.txt)"
          />
          <select v-model="newFilter.type">
            <option value="directory">Directory</option>
            <option value="xml">XML</option>
            <option value="custom">Custom</option>
          </select>
          <button @click="addCustomFilter" class="add-btn">Add Filter</button>
        </div>
      </div>
    </div>

    <div class="filter-testing">
      <h3>Test Filters</h3>
      <p>Enter a file path to see which filters would match:</p>
      <div class="test-input">
        <input
          v-model="testPath"
          type="text"
          placeholder="e.g., AU/1901/hansard_1901_01.txt"
          @input="testFilters"
        />
      </div>
      <div v-if="testResults.length > 0" class="test-results">
        <h4>Matching Filters:</h4>
        <div class="matching-filters">
          <span
            v-for="result in testResults"
            :key="result"
            class="filter-tag"
          >
            {{ result }}
          </span>
        </div>
      </div>
    </div>

    <div class="hierarchy-view" v-if="hasHierarchy">
      <h3>Filter Hierarchy</h3>
      <div class="hierarchy-tree">
        <div v-for="parent in parentFilters" :key="parent.id" class="parent-node">
          <div class="node-header">
            <span class="node-icon">📁</span>
            {{ parent.label }}
          </div>
          <div class="child-nodes">
            <div v-for="child in getChildFilters(parent.id)" :key="child.id" class="child-node">
              <span class="node-icon">📄</span>
              {{ child.label }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="form-actions">
      <button @click="$emit('back')" class="btn btn-secondary">Back</button>
      <button @click="handleNext" class="btn btn-primary" :disabled="enabledCount === 0">
        Next Step
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';

export default {
  name: 'FilterConfigurator',

  props: {
    modelValue: {
      type: Array,
      default: () => []
    },
    suggestedFilters: {
      type: Array,
      default: () => []
    }
  },

  emits: ['update:modelValue', 'next', 'back'],

  setup(props, { emit }) {
    const localFilters = ref(
      props.suggestedFilters.map(f => ({ ...f, enabled: true }))
    );
    const editingIndex = ref(null);
    const testPath = ref('');
    const testResults = ref([]);

    const newFilter = ref({
      id: '',
      label: '',
      pattern: '',
      type: 'directory'
    });

    const enabledCount = computed(() => {
      return localFilters.value.filter(f => f.enabled).length;
    });

    const hasHierarchy = computed(() => {
      return localFilters.value.some(f => f.parent_id);
    });

    const parentFilters = computed(() => {
      return localFilters.value.filter(f => !f.parent_id && f.enabled);
    });

    const getChildFilters = (parentId) => {
      return localFilters.value.filter(f => f.parent_id === parentId && f.enabled);
    };

    const editFilter = (index) => {
      editingIndex.value = index;
    };

    const saveEdit = (index) => {
      editingIndex.value = null;
    };

    const cancelEdit = () => {
      editingIndex.value = null;
    };

    const addCustomFilter = () => {
      if (newFilter.value.id && newFilter.value.label && newFilter.value.pattern) {
        localFilters.value.push({
          ...newFilter.value,
          enabled: true,
          custom: true
        });
        newFilter.value = {
          id: '',
          label: '',
          pattern: '',
          type: 'directory'
        };
      }
    };

    const testFilters = () => {
      if (!testPath.value) {
        testResults.value = [];
        return;
      }

      const matching = [];
      localFilters.value.forEach(filter => {
        if (filter.enabled) {
          // Simple pattern matching
          const pattern = filter.pattern.replace(/\*\*/g, '.*').replace(/\*/g, '[^/]*');
          const regex = new RegExp(pattern);
          if (regex.test(testPath.value)) {
            matching.push(filter.label);
          }
        }
      });
      testResults.value = matching;
    };

    const handleNext = () => {
      // Only emit enabled filters
      const enabledFilters = localFilters.value.filter(f => f.enabled);
      emit('update:modelValue', enabledFilters);
      emit('next');
    };

    // Watch for external changes
    watch(
      () => props.suggestedFilters,
      (newValue) => {
        if (newValue && newValue.length > 0) {
          localFilters.value = newValue.map(f => ({ ...f, enabled: true }));
        }
      },
      { deep: true }
    );

    return {
      localFilters,
      editingIndex,
      testPath,
      testResults,
      newFilter,
      enabledCount,
      hasHierarchy,
      parentFilters,
      getChildFilters,
      editFilter,
      saveEdit,
      cancelEdit,
      addCustomFilter,
      testFilters,
      handleNext
    };
  }
};
</script>

<style scoped>
.filter-configurator {
  max-width: 900px;
  margin: 0 auto;
}

.filter-configurator h2 {
  color: #333;
  margin-bottom: 0.5rem;
}

.form-description {
  color: #666;
  margin-bottom: 2rem;
}

.filters-summary {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.summary-stats {
  font-size: 1.1rem;
  color: #333;
}

.enabled-count {
  color: #4caf50;
  font-weight: 500;
}

.filter-list {
  margin-bottom: 2rem;
}

.filter-item {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  margin-bottom: 1rem;
  padding: 1rem;
  transition: all 0.3s ease;
}

.filter-item.disabled {
  opacity: 0.6;
}

.filter-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.filter-header input[type="checkbox"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.filter-label {
  font-weight: 500;
  color: #333;
  flex: 1;
  cursor: pointer;
}

.filter-stats {
  color: #666;
  font-size: 0.9rem;
}

.edit-btn {
  padding: 0.25rem 0.75rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.edit-btn:hover {
  background: #2980b9;
}

.filter-details {
  display: flex;
  gap: 2rem;
  margin-left: 2rem;
  font-size: 0.9rem;
  color: #666;
}

.detail-item code {
  background: #f5f5f5;
  padding: 0.125rem 0.25rem;
  border-radius: 2px;
}

.filter-edit {
  margin: 1rem 0 0 2rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.edit-group {
  margin-bottom: 1rem;
}

.edit-group label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 500;
  color: #333;
}

.edit-group input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.edit-actions {
  display: flex;
  gap: 0.5rem;
}

.save-btn,
.cancel-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.save-btn {
  background: #4caf50;
  color: white;
}

.cancel-btn {
  background: #f44336;
  color: white;
}

.add-filter-section {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.add-filter-section h3 {
  margin-top: 0;
  color: #333;
}

.add-filter-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: flex;
  gap: 0.5rem;
}

.form-row input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.form-row select {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.add-btn {
  padding: 0.5rem 1rem;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.filter-testing {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.filter-testing h3 {
  margin-top: 0;
  color: #333;
}

.test-input input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.test-results {
  margin-top: 1rem;
}

.matching-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.filter-tag {
  background: #3498db;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.9rem;
}

.hierarchy-view {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.hierarchy-tree {
  margin-top: 1rem;
}

.parent-node {
  margin-bottom: 1rem;
}

.node-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  color: #333;
  margin-bottom: 0.5rem;
}

.child-nodes {
  margin-left: 2rem;
}

.child-node {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
  color: #666;
}

.node-icon {
  font-size: 1.2rem;
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
</style>