<template>
  <div class="corpus-wizard">
    <div class="wizard-header">
      <h1>Corpus Configuration Wizard</h1>
      <p class="subtitle">Configure and build a new corpus for ATLAS</p>
    </div>

    <WizardSteps
      :current-step="currentStep"
      :steps="wizardSteps"
      :step-status="stepStatus"
      @step-click="goToStep"
    />

    <div class="wizard-content">
      <transition name="fade" mode="out-in">
        <!-- Step 1: Metadata -->
        <CorpusMetadataForm
          v-if="currentStep === 1"
          v-model="wizardData.metadata"
          @next="nextStep"
        />

        <!-- Step 2: Source Selection -->
        <SourceSelector
          v-else-if="currentStep === 2"
          v-model="wizardData.source"
          @next="analyzeSource"
          @back="previousStep"
        />

        <!-- Step 3: Filter Method -->
        <FilterMethodSelector
          v-else-if="currentStep === 3"
          v-model="wizardData.filterMethod"
          :structure-analysis="structureAnalysis"
          @next="discoverFilters"
          @back="previousStep"
        />

        <!-- Step 4: Filter Configuration -->
        <FilterConfigurator
          v-else-if="currentStep === 4"
          v-model="wizardData.filters"
          :suggested-filters="suggestedFilters"
          @next="nextStep"
          @back="previousStep"
        />

        <!-- Step 5: Model Selection -->
        <ModelSelector
          v-else-if="currentStep === 5"
          v-model="wizardData.embedding"
          :corpus-metadata="wizardData.metadata"
          @next="validateSample"
          @back="previousStep"
        />

        <!-- Step 6: Validation Preview -->
        <ValidationPreview
          v-else-if="currentStep === 6"
          :validation-results="validationResults"
          :sample-data="sampleData"
          @next="checkRequirements"
          @back="previousStep"
          @fix-issues="fixIssues"
          @revalidate="validateSample"
        />

        <!-- Step 7: System Requirements -->
        <RequirementsChecker
          v-else-if="currentStep === 7"
          :doc-count="structureAnalysis?.total_files || 0"
          v-model="wizardData.processing"
          @next="startBuild"
          @back="previousStep"
        />

        <!-- Step 8: Build Progress -->
        <BuildProgress
          v-else-if="currentStep === 8"
          :build-id="buildId"
          @complete="onBuildComplete"
          @error="onBuildError"
        />

        <!-- Step 9: Testing & Activation -->
        <CorpusTester
          v-else-if="currentStep === 9"
          :corpus-config="wizardData"
          :build-results="buildResults"
          @activate="activateCorpus"
          @back="previousStep"
        />
      </transition>
    </div>

    <!-- Error Dialog -->
    <div v-if="error" class="error-dialog">
      <div class="error-content">
        <h3>Error</h3>
        <p>{{ error }}</p>
        <button @click="error = null">Close</button>
      </div>
    </div>

    <!-- Loading Overlay -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>{{ loadingMessage }}</p>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed } from 'vue';
import { useStore } from 'vuex';
import axios from 'axios';

// Import wizard components
import WizardSteps from '@/components/wizard/WizardSteps.vue';
import CorpusMetadataForm from '@/components/wizard/CorpusMetadataForm.vue';
import SourceSelector from '@/components/wizard/SourceSelector.vue';
import FilterMethodSelector from '@/components/wizard/FilterMethodSelector.vue';
import FilterConfigurator from '@/components/wizard/FilterConfigurator.vue';
import ModelSelector from '@/components/wizard/ModelSelector.vue';
import ValidationPreview from '@/components/wizard/ValidationPreview.vue';
import RequirementsChecker from '@/components/wizard/RequirementsChecker.vue';
import BuildProgress from '@/components/wizard/BuildProgress.vue';
import CorpusTester from '@/components/wizard/CorpusTester.vue';

export default {
  name: 'CorpusWizard',

  components: {
    WizardSteps,
    CorpusMetadataForm,
    SourceSelector,
    FilterMethodSelector,
    FilterConfigurator,
    ModelSelector,
    ValidationPreview,
    RequirementsChecker,
    BuildProgress,
    CorpusTester
  },

  setup() {
    const store = useStore();
    const currentStep = ref(1);
    const loading = ref(false);
    const loadingMessage = ref('');
    const error = ref(null);

    // Wizard data
    const wizardData = reactive({
      metadata: {
        name: '',
        display_name: '',
        description: '',
        version: '1.0.0',
        time_period: null,
        copyright_status: '',
        copyright_statement: '',
        doi: '',
        source_repository: '',
        entities: []
      },
      source: {
        type: 'local',
        location: '',
        branch: 'main',
        sparse_checkout: []
      },
      filterMethod: {
        method: 'directory',
        directory_depth: 1,
        xml_entities: []
      },
      filters: [],
      citation: {
        template: '{author}. {title}. {date}. {source}.',
        url_pattern: '',
        metadata_patterns: {},
        source_name: '',
        source_url: ''
      },
      embedding: {
        model_id: 'sentence-transformers/all-MiniLM-L6-v2',
        chunk_size: 500,
        chunk_overlap: 50,
        batch_size: 32
      },
      processing: {
        mode: 'cpu',
        max_workers: 4,
        memory_limit_gb: null,
        sample_size: null
      }
    });

    // Analysis results
    const structureAnalysis = ref(null);
    const suggestedFilters = ref([]);
    const validationResults = ref(null);
    const sampleData = ref(null);
    const buildId = ref(null);
    const buildResults = ref(null);

    // Wizard steps configuration
    const wizardSteps = [
      { id: 1, label: 'Metadata', icon: 'info' },
      { id: 2, label: 'Source', icon: 'folder' },
      { id: 3, label: 'Filter Method', icon: 'filter' },
      { id: 4, label: 'Filters', icon: 'list' },
      { id: 5, label: 'Model', icon: 'cpu' },
      { id: 6, label: 'Validation', icon: 'check' },
      { id: 7, label: 'Requirements', icon: 'server' },
      { id: 8, label: 'Build', icon: 'build' },
      { id: 9, label: 'Test & Activate', icon: 'play' }
    ];

    const stepStatus = reactive({
      1: 'active',
      2: 'pending',
      3: 'pending',
      4: 'pending',
      5: 'pending',
      6: 'pending',
      7: 'pending',
      8: 'pending',
      9: 'pending'
    });

    // Navigation methods
    const nextStep = () => {
      if (currentStep.value < wizardSteps.length) {
        stepStatus[currentStep.value] = 'completed';
        currentStep.value++;
        stepStatus[currentStep.value] = 'active';
      }
    };

    const previousStep = () => {
      if (currentStep.value > 1) {
        stepStatus[currentStep.value] = 'pending';
        currentStep.value--;
        stepStatus[currentStep.value] = 'active';
      }
    };

    const goToStep = (step) => {
      // Only allow going to completed steps or the next step
      if (step <= currentStep.value || step === currentStep.value + 1) {
        currentStep.value = step;
        updateStepStatuses();
      }
    };

    const updateStepStatuses = () => {
      for (let i = 1; i <= wizardSteps.length; i++) {
        if (i < currentStep.value) {
          stepStatus[i] = 'completed';
        } else if (i === currentStep.value) {
          stepStatus[i] = 'active';
        } else {
          stepStatus[i] = 'pending';
        }
      }
    };

    // API calls
    const analyzeSource = async () => {
      loading.value = true;
      loadingMessage.value = 'Analyzing corpus structure...';

      try {
        const response = await axios.post('/api/corpus-wizard/analyze', {
          source_type: wizardData.source.type,
          source_location: wizardData.source.location,
          file_types: ['txt', 'xml'],
          metadata: wizardData.metadata
        });

        structureAnalysis.value = response.data;
        nextStep();
      } catch (err) {
        error.value = `Failed to analyze source: ${err.message}`;
      } finally {
        loading.value = false;
      }
    };

    const discoverFilters = async () => {
      loading.value = true;
      loadingMessage.value = 'Discovering filters...';

      try {
        const response = await axios.post('/api/corpus-wizard/suggest-filters', {
          metadata: wizardData.metadata,
          structure_analysis: structureAnalysis.value,
          method: wizardData.filterMethod
        });

        suggestedFilters.value = response.data.filters;
        wizardData.filters = response.data.filters; // Pre-populate
        nextStep();
      } catch (err) {
        error.value = `Failed to discover filters: ${err.message}`;
      } finally {
        loading.value = false;
      }
    };

    const validateSample = async () => {
      loading.value = true;
      loadingMessage.value = 'Validating corpus sample...';

      try {
        const config = {
          metadata: wizardData.metadata,
          source: wizardData.source,
          filters: {
            method: wizardData.filterMethod.method,
            directory_depth: wizardData.filterMethod.directory_depth,
            xml_entities: wizardData.filterMethod.xml_entities,
            filters: wizardData.filters
          },
          citation: wizardData.citation,
          embedding: wizardData.embedding,
          processing: wizardData.processing
        };

        const response = await axios.post('/api/corpus-wizard/validate-sample', {
          source_path: wizardData.source.location,
          config: config
        });

        validationResults.value = response.data.validation;
        sampleData.value = response.data.sample;

        if (currentStep.value === 5) {
          nextStep();
        }
      } catch (err) {
        error.value = `Validation failed: ${err.message}`;
      } finally {
        loading.value = false;
      }
    };

    const fixIssues = async (issues) => {
      loading.value = true;
      loadingMessage.value = 'Applying fixes...';

      try {
        const response = await axios.post('/api/corpus-wizard/fix-issues', {
          issues: issues,
          auto_fix: true
        });

        // Re-validate after fixing
        await validateSample();
      } catch (err) {
        error.value = `Failed to fix issues: ${err.message}`;
      } finally {
        loading.value = false;
      }
    };

    const checkRequirements = async () => {
      // Requirements are checked in the component itself
      nextStep();
    };

    const startBuild = async () => {
      loading.value = true;
      loadingMessage.value = 'Starting corpus build...';

      try {
        const config = {
          metadata: wizardData.metadata,
          source: wizardData.source,
          filters: {
            method: wizardData.filterMethod.method,
            directory_depth: wizardData.filterMethod.directory_depth,
            xml_entities: wizardData.filterMethod.xml_entities,
            filters: wizardData.filters
          },
          citation: wizardData.citation,
          embedding: wizardData.embedding,
          processing: wizardData.processing
        };

        const response = await axios.post('/api/corpus-wizard/build', {
          config: config,
          mode: wizardData.processing.mode
        });

        buildId.value = response.data.build_id;
        nextStep();
      } catch (err) {
        error.value = `Failed to start build: ${err.message}`;
      } finally {
        loading.value = false;
      }
    };

    const onBuildComplete = (results) => {
      buildResults.value = results;
      nextStep();
    };

    const onBuildError = (err) => {
      error.value = `Build failed: ${err}`;
      stepStatus[8] = 'error';
    };

    const activateCorpus = async () => {
      loading.value = true;
      loadingMessage.value = 'Activating corpus...';

      try {
        const response = await axios.post(
          `/api/corpus-wizard/activate/${wizardData.metadata.name}`,
          null,
          { params: { backup: true } }
        );

        // Success - redirect or show success message
        alert('Corpus activated successfully! Please restart the server.');
        window.location.href = '/';
      } catch (err) {
        error.value = `Failed to activate corpus: ${err.message}`;
      } finally {
        loading.value = false;
      }
    };

    return {
      currentStep,
      loading,
      loadingMessage,
      error,
      wizardData,
      wizardSteps,
      stepStatus,
      structureAnalysis,
      suggestedFilters,
      validationResults,
      sampleData,
      buildId,
      buildResults,
      nextStep,
      previousStep,
      goToStep,
      analyzeSource,
      discoverFilters,
      validateSample,
      fixIssues,
      checkRequirements,
      startBuild,
      onBuildComplete,
      onBuildError,
      activateCorpus
    };
  }
};
</script>

<style scoped>
.corpus-wizard {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.wizard-header {
  text-align: center;
  margin-bottom: 3rem;
}

.wizard-header h1 {
  font-size: 2.5rem;
  color: #333;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  font-size: 1.1rem;
}

.wizard-content {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  min-height: 400px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.error-dialog {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.error-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  max-width: 500px;
}

.error-content h3 {
  color: #d32f2f;
  margin-bottom: 1rem;
}

.error-content button {
  background: #d32f2f;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 5px solid #f3f3f3;
  border-top: 5px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>