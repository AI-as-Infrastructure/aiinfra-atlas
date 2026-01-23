<template>
  <div class="metadata-form">
    <h2>Corpus Metadata</h2>
    <p class="form-description">Provide basic information about your corpus</p>

    <form @submit.prevent="handleSubmit">
      <div class="form-row">
        <div class="form-group">
          <label for="name">Corpus Name *</label>
          <input
            id="name"
            v-model="localData.name"
            type="text"
            required
            pattern="[a-z0-9_-]+"
            placeholder="my_corpus"
            @input="updateDisplayName"
          />
          <small>Lowercase letters, numbers, underscores, and hyphens only</small>
        </div>

        <div class="form-group">
          <label for="display_name">Display Name *</label>
          <input
            id="display_name"
            v-model="localData.display_name"
            type="text"
            required
            placeholder="My Corpus"
          />
        </div>
      </div>

      <div class="form-group">
        <label for="description">Description *</label>
        <textarea
          id="description"
          v-model="localData.description"
          required
          rows="3"
          placeholder="Describe your corpus and its contents..."
        ></textarea>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="version">Version</label>
          <input
            id="version"
            v-model="localData.version"
            type="text"
            placeholder="1.0.0"
          />
        </div>

        <div class="form-group">
          <label>Time Period</label>
          <div class="time-period">
            <input
              v-model.number="timePeriodStart"
              type="number"
              min="1000"
              max="2024"
              placeholder="Start year"
            />
            <span>to</span>
            <input
              v-model.number="timePeriodEnd"
              type="number"
              min="1000"
              max="2024"
              placeholder="End year"
            />
          </div>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="copyright_status">Copyright Status</label>
          <select id="copyright_status" v-model="localData.copyright_status">
            <option value="">Select status...</option>
            <option value="public_domain">Public Domain</option>
            <option value="cc0">CC0 - No Rights Reserved</option>
            <option value="cc_by">CC BY - Attribution</option>
            <option value="cc_by_sa">CC BY-SA - Attribution ShareAlike</option>
            <option value="cc_by_nc">CC BY-NC - Attribution NonCommercial</option>
            <option value="copyright">Under Copyright</option>
            <option value="mixed">Mixed</option>
          </select>
        </div>

        <div class="form-group">
          <label for="doi">DOI</label>
          <input
            id="doi"
            v-model="localData.doi"
            type="text"
            placeholder="10.1234/example"
          />
        </div>
      </div>

      <div class="form-group">
        <label for="copyright_statement">Copyright Statement</label>
        <textarea
          id="copyright_statement"
          v-model="localData.copyright_statement"
          rows="2"
          placeholder="Copyright notice or license information..."
        ></textarea>
      </div>

      <div class="form-group">
        <label for="source_repository">Source Repository</label>
        <input
          id="source_repository"
          v-model="localData.source_repository"
          type="url"
          placeholder="https://github.com/organization/repository"
        />
      </div>

      <div class="form-group">
        <label>Key Entities</label>
        <div class="entity-input">
          <input
            v-model="entityInput"
            type="text"
            placeholder="Add people, places, or topics..."
            @keypress.enter.prevent="addEntity"
          />
          <button type="button" @click="addEntity">Add</button>
        </div>
        <div class="entity-tags">
          <span
            v-for="(entity, index) in localData.entities"
            :key="index"
            class="tag"
          >
            {{ entity }}
            <button type="button" @click="removeEntity(index)" class="remove-tag">×</button>
          </span>
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary">Next Step</button>
      </div>
    </form>
  </div>
</template>

<script>
import { ref, watch, computed } from 'vue';

export default {
  name: 'CorpusMetadataForm',

  props: {
    modelValue: {
      type: Object,
      required: true
    }
  },

  emits: ['update:modelValue', 'next'],

  setup(props, { emit }) {
    const localData = ref({ ...props.modelValue });
    const entityInput = ref('');

    const timePeriodStart = computed({
      get: () => localData.value.time_period?.start,
      set: (value) => {
        if (!localData.value.time_period) {
          localData.value.time_period = {};
        }
        localData.value.time_period.start = value;
      }
    });

    const timePeriodEnd = computed({
      get: () => localData.value.time_period?.end,
      set: (value) => {
        if (!localData.value.time_period) {
          localData.value.time_period = {};
        }
        localData.value.time_period.end = value;
      }
    });

    const updateDisplayName = () => {
      if (!localData.value.display_name || localData.value.display_name === '') {
        // Auto-generate display name from name
        localData.value.display_name = localData.value.name
          .replace(/[_-]/g, ' ')
          .replace(/\b\w/g, c => c.toUpperCase());
      }
    };

    const addEntity = () => {
      if (entityInput.value.trim()) {
        if (!localData.value.entities) {
          localData.value.entities = [];
        }
        localData.value.entities.push(entityInput.value.trim());
        entityInput.value = '';
      }
    };

    const removeEntity = (index) => {
      localData.value.entities.splice(index, 1);
    };

    const handleSubmit = () => {
      emit('update:modelValue', localData.value);
      emit('next');
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
      entityInput,
      timePeriodStart,
      timePeriodEnd,
      updateDisplayName,
      addEntity,
      removeEntity,
      handleSubmit
    };
  }
};
</script>

<style scoped>
.metadata-form {
  max-width: 800px;
  margin: 0 auto;
}

.metadata-form h2 {
  color: #333;
  margin-bottom: 0.5rem;
}

.form-description {
  color: #666;
  margin-bottom: 2rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
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

.time-period {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.time-period input {
  flex: 1;
}

.entity-input {
  display: flex;
  gap: 0.5rem;
}

.entity-input input {
  flex: 1;
}

.entity-input button {
  padding: 0.5rem 1rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.entity-input button:hover {
  background: #2980b9;
}

.entity-tags {
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

.remove-tag:hover {
  color: #333;
}

.form-actions {
  margin-top: 2rem;
  display: flex;
  justify-content: flex-end;
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

.btn-primary:hover {
  background: #2980b9;
}

@media (max-width: 600px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>