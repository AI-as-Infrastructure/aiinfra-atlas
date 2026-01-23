<template>
  <div class="filter-method-selector">
    <h2>Choose Filter Discovery Method</h2>
    <p class="form-description">Select how to organize and filter your corpus</p>

    <div v-if="structureAnalysis" class="structure-summary">
      <h3>Corpus Structure Analysis</h3>
      <div class="stats-grid">
        <div class="stat">
          <span class="label">Total Files:</span>
          <span class="value">{{ structureAnalysis.total_files }}</span>
        </div>
        <div class="stat">
          <span class="label">Directory Depth:</span>
          <span class="value">{{ structureAnalysis.directory_depth }}</span>
        </div>
        <div class="stat">
          <span class="label">File Types:</span>
          <span class="value">
            {{ Object.keys(structureAnalysis.file_types || {}).join(', ') }}
          </span>
        </div>
        <div class="stat">
          <span class="label">Structure Type:</span>
          <span class="value">{{ structureAnalysis.structure_type }}</span>
        </div>
      </div>
    </div>

    <div class="method-selection">
      <div class="form-group">
        <label for="method">Filter Definition Method *</label>
        <select
          id="method"
          v-model="localData.method"
          @change="onMethodChange"
        >
          <option value="directory">Directory Structure</option>
          <option value="xml" :disabled="!hasXmlFiles">XML Structure</option>
        </select>
        <small v-if="!hasXmlFiles && localData.method === 'xml'">
          No XML files detected in your corpus
        </small>
      </div>

      <!-- Directory Method Options -->
      <div v-if="localData.method === 'directory'" class="method-options">
        <div class="form-group">
          <label for="directory-depth">Directory Organization Depth</label>
          <div class="radio-group">
            <label class="radio-option">
              <input
                type="radio"
                v-model.number="localData.directory_depth"
                :value="1"
              />
              <div class="radio-content">
                <strong>Single Layer</strong>
                <p>One level of folders (e.g., countries, topics, years)</p>
                <code>corpus/AU/, corpus/NZ/, corpus/UK/</code>
              </div>
            </label>
            <label class="radio-option">
              <input
                type="radio"
                v-model.number="localData.directory_depth"
                :value="2"
              />
              <div class="radio-content">
                <strong>Two Layers</strong>
                <p>Two levels of folders for hierarchical organization</p>
                <code>corpus/AU/1901/, corpus/AU/1902/, corpus/NZ/1901/</code>
              </div>
            </label>
          </div>
        </div>

        <div class="form-group">
          <label>Filename Pattern for Metadata (optional)</label>
          <input
            v-model="filenamePattern"
            type="text"
            placeholder="e.g., {year}_{month}_{day}_{title}.txt"
          />
          <small>Define pattern to extract metadata from filenames</small>
        </div>

        <div class="preview-section">
          <h4>Example Filters (based on your structure):</h4>
          <div class="filter-examples">
            <div v-if="localData.directory_depth === 1" class="example-list">
              <span class="filter-tag" v-for="dir in topLevelDirs" :key="dir">
                {{ dir }}
              </span>
            </div>
            <div v-else class="example-list">
              <span class="filter-tag" v-for="combo in twoLayerCombos" :key="combo">
                {{ combo }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- XML Method Options -->
      <div v-else-if="localData.method === 'xml'" class="method-options">
        <div class="form-group">
          <label>XML Entities to Extract</label>
          <div class="checkbox-group">
            <label class="checkbox-option">
              <input
                type="checkbox"
                value="person"
                v-model="localData.xml_entities"
              />
              <span>People/Authors</span>
            </label>
            <label class="checkbox-option">
              <input
                type="checkbox"
                value="place"
                v-model="localData.xml_entities"
              />
              <span>Places/Locations</span>
            </label>
            <label class="checkbox-option">
              <input
                type="checkbox"
                value="date"
                v-model="localData.xml_entities"
              />
              <span>Dates/Time Periods</span>
            </label>
            <label class="checkbox-option">
              <input
                type="checkbox"
                value="subject"
                v-model="localData.xml_entities"
              />
              <span>Subjects/Topics</span>
            </label>
            <label class="checkbox-option">
              <input
                type="checkbox"
                value="title"
                v-model="localData.xml_entities"
              />
              <span>Titles</span>
            </label>
          </div>
        </div>

        <div class="form-group">
          <label>Custom XPath Expressions (optional)</label>
          <div class="xpath-input">
            <input
              v-model="xpathInput"
              type="text"
              placeholder="e.g., //teiHeader/titleStmt/title"
              @keypress.enter.prevent="addXPath"
            />
            <button type="button" @click="addXPath">Add</button>
          </div>
          <div class="xpath-list">
            <span
              v-for="(xpath, index) in customXPaths"
              :key="index"
              class="tag"
            >
              {{ xpath }}
              <button type="button" @click="removeXPath(index)" class="remove-tag">×</button>
            </span>
          </div>
        </div>

        <div class="form-group">
          <label>
            <input
              type="checkbox"
              v-model="useDirectoryWithXml"
            />
            Also use top-level directories as filters
          </label>
        </div>
      </div>
    </div>

    <div class="info-box">
      <h4>ℹ️ About Filter Methods</h4>
      <p v-if="localData.method === 'directory'">
        <strong>Directory-based filtering</strong> uses your folder structure to create filters.
        This is ideal for corpora organized by categories like time periods, locations, or topics.
      </p>
      <p v-else>
        <strong>XML-based filtering</strong> extracts entities from XML tags to create dynamic filters.
        This is ideal for structured documents with rich metadata like TEI or custom XML schemas.
      </p>
    </div>

    <div class="form-actions">
      <button @click="$emit('back')" class="btn btn-secondary">Back</button>
      <button @click="handleNext" class="btn btn-primary">Next Step</button>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';

export default {
  name: 'FilterMethodSelector',

  props: {
    modelValue: {
      type: Object,
      required: true
    },
    structureAnalysis: {
      type: Object,
      default: null
    }
  },

  emits: ['update:modelValue', 'next', 'back'],

  setup(props, { emit }) {
    const localData = ref({
      method: 'directory',
      directory_depth: 1,
      xml_entities: [],
      ...props.modelValue
    });

    const filenamePattern = ref('');
    const xpathInput = ref('');
    const customXPaths = ref([]);
    const useDirectoryWithXml = ref(false);

    const hasXmlFiles = computed(() => {
      if (!props.structureAnalysis) return false;
      return props.structureAnalysis.has_xml ||
             (props.structureAnalysis.file_types && props.structureAnalysis.file_types['.xml'] > 0);
    });

    const topLevelDirs = computed(() => {
      if (!props.structureAnalysis) return [];
      return props.structureAnalysis.top_level_dirs || [];
    });

    const twoLayerCombos = computed(() => {
      // Generate example two-layer combinations
      const examples = [];
      const dirs = topLevelDirs.value;
      if (dirs.length > 0) {
        // Show first few combinations as examples
        dirs.slice(0, 3).forEach(dir => {
          examples.push(`${dir}: SubFolder1`);
          examples.push(`${dir}: SubFolder2`);
        });
      }
      return examples;
    });

    const onMethodChange = () => {
      // Reset options when method changes
      if (localData.value.method === 'directory') {
        localData.value.xml_entities = [];
        customXPaths.value = [];
      } else {
        localData.value.directory_depth = 1;
      }
    };

    const addXPath = () => {
      if (xpathInput.value.trim()) {
        customXPaths.value.push(xpathInput.value.trim());
        xpathInput.value = '';
      }
    };

    const removeXPath = (index) => {
      customXPaths.value.splice(index, 1);
    };

    const handleNext = () => {
      // Include additional options in the model
      const updatedData = {
        ...localData.value,
        filename_pattern: filenamePattern.value,
        custom_xpaths: customXPaths.value,
        use_directory_with_xml: useDirectoryWithXml.value
      };
      emit('update:modelValue', updatedData);
      emit('next');
    };

    // Watch for external changes
    watch(
      () => props.modelValue,
      (newValue) => {
        localData.value = { ...localData.value, ...newValue };
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
      filenamePattern,
      xpathInput,
      customXPaths,
      useDirectoryWithXml,
      hasXmlFiles,
      topLevelDirs,
      twoLayerCombos,
      onMethodChange,
      addXPath,
      removeXPath,
      handleNext
    };
  }
};
</script>

<style scoped>
.filter-method-selector {
  max-width: 800px;
  margin: 0 auto;
}

.filter-method-selector h2 {
  color: #333;
  margin-bottom: 0.5rem;
}

.form-description {
  color: #666;
  margin-bottom: 2rem;
}

.structure-summary {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.structure-summary h3 {
  margin-top: 0;
  color: #333;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.stat {
  display: flex;
  flex-direction: column;
}

.stat .label {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.25rem;
}

.stat .value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
}

.method-selection {
  margin-bottom: 2rem;
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

.form-group select,
.form-group input[type="text"] {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group select:focus,
.form-group input[type="text"]:focus {
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

.method-options {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-top: 1rem;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.radio-option {
  display: flex;
  align-items: flex-start;
  padding: 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.radio-option:hover {
  border-color: #3498db;
  background: #f8f9fa;
}

.radio-option input[type="radio"] {
  margin-right: 1rem;
  margin-top: 0.25rem;
}

.radio-content strong {
  display: block;
  margin-bottom: 0.25rem;
  color: #333;
}

.radio-content p {
  margin: 0 0 0.5rem;
  color: #666;
  font-size: 0.9rem;
}

.radio-content code {
  display: block;
  padding: 0.5rem;
  background: #e0e0e0;
  border-radius: 4px;
  font-size: 0.85rem;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.checkbox-option {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.checkbox-option input[type="checkbox"] {
  margin-right: 0.5rem;
}

.preview-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e0e0e0;
}

.preview-section h4 {
  margin: 0 0 1rem;
  color: #333;
}

.filter-examples {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.filter-tag {
  background: #3498db;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.9rem;
}

.xpath-input {
  display: flex;
  gap: 0.5rem;
}

.xpath-input input {
  flex: 1;
}

.xpath-input button {
  padding: 0.5rem 1rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.xpath-list {
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

.info-box {
  background: #e3f2fd;
  border-left: 4px solid #3498db;
  padding: 1rem;
  margin: 2rem 0;
}

.info-box h4 {
  margin: 0 0 0.5rem;
  color: #1976d2;
}

.info-box p {
  margin: 0;
  color: #333;
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

.btn-primary:hover {
  background: #2980b9;
}

.btn-secondary {
  background: #95a5a6;
  color: white;
}

.btn-secondary:hover {
  background: #7f8c8d;
}
</style>