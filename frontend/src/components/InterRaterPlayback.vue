<template>
  <div class="inter-rater-playback">
    <div class="conversation-container">
      <!-- Prominent Question Display -->
      <div class="question-section">
        <div class="message-style-container">
          <div class="section-header">
            <h4 class="section-title">
              <i class="fas fa-question-circle mr-2"></i>
              Question
            </h4>
          </div>
          <div class="section-content">
            <div class="content-text">
              {{ session.question }}
            </div>
          </div>
        </div>
      </div>

      <!-- Prominent Answer Display -->
      <div class="answer-section">
        <div class="message-style-container">
          <div class="section-header">
            <h4 class="section-title">
              <i class="fas fa-comment-dots mr-2"></i>
              Answer
            </h4>
          </div>
          <div class="section-content">
            <div class="content-text">
              <div class="content" v-html="renderMarkdown(session.answer)"></div>
              
              <div v-if="session.citations && session.citations.length > 0" class="citations-section">
                <hr class="my-4">
                <h6 class="citations-title">
                  <i class="fas fa-book mr-2"></i>
                  Sources Used:
                </h6>
                <ul class="citation-list">
                  <li 
                    v-for="(citation, cIndex) in session.citations" 
                    :key="cIndex" 
                    class="citation-item"
                    @mouseover="hoveredCitation = citation"
                  >
                    <a 
                      href="#" 
                      @click.prevent="showCitationModal(citation)" 
                      class="citation-link"
                    >
                      {{ getCitationLabel(citation) }}
                    </a>
                    <div v-if="hoveredCitation === citation" class="citation-tooltip" @mouseleave="hoveredCitation = null">
                      <div class="citation-tooltip-content">
                        <p class="citation-quote">{{ getCitationText(citation) }}</p>
                        <div class="citation-meta">
                          <p v-if="citation.retrieval_id || citation.source_id || citation.source || citation.title || citation.metadata?.source"><strong>Retrieval ID:</strong> {{ citation.retrieval_id || citation.source_id || citation.source || citation.title || citation.metadata?.source }}</p>
                          <p v-if="citation.date || citation.metadata?.date"><strong>Date:</strong> {{ citation.date || citation.metadata?.date }}</p>
                          <p v-if="citation.page || citation.metadata?.page"><strong>Page:</strong> {{ citation.page || citation.metadata?.page }}</p>
                          <p v-if="citation.url || citation.metadata?.url" class="citation-url">
                            <strong>URL:</strong> 
                            <a :href="citation.url || citation.metadata?.url" target="_blank" rel="noopener noreferrer" @click.stop>
                              View source
                            </a>
                          </p>
                          <p v-if="citation.corpus || citation.metadata?.corpus"><strong>Corpus:</strong> {{ citation.corpus || citation.metadata?.corpus }}</p>
                        </div>
                      </div>
                    </div>
                  </li>
                  <li class="citation-item view-all-item" v-if="session.citations.length > 1">
                    <a 
                      @click.prevent="showAllCitationsModal()" 
                      class="view-all-link"
                    >
                      View all {{ session.citations.length }} citations
                    </a>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Inter-rater Feedback Form -->
    <div class="inter-rater-feedback-section">
      <div class="feedback-container">
        <div class="feedback-header">
          <h4>Inter-rater Assessment</h4>
          <p class="subtitle">Provide an independent evaluation of this LLM response to help us measure inter-rater reliability. Rate each of the following, where 1 is the lowest rating, and 5 is the highest.</p>
        </div>
        <div class="feedback-content">
          
          <!-- Likert-style Rating Grid -->
          <div class="rating-sections">
            <div class="feedback-section">
              <label class="section-label">
                Factual Accuracy
                <span class="tooltip" title="Factual accuracy of LLM output">ⓘ</span>
              </label>
              <div class="likert-scale">
                <div
                  v-for="value in 5"
                  :key="`factual_accuracy-${value}`"
                  class="likert-option"
                  @click="feedback.factual_accuracy = value"
                >
                  <input
                    type="radio"
                    :id="`factual_accuracy-${value}`"
                    :value="value"
                    v-model="feedback.factual_accuracy"
                  />
                  <label :for="`factual_accuracy-${value}`" class="likert-label">
                    <span class="likert-circle" :class="{ active: feedback.factual_accuracy >= value }"></span>
                    <span class="likert-text">{{ value }}</span>
                  </label>
                </div>
              </div>
            </div>
            
            

            <div class="feedback-section">
              <label class="section-label">
                Corpus Fidelity
                <span class="tooltip" title="How well the answer is grounded in the retrieved corpus (citations, quotes, provenance)">ⓘ</span>
              </label>
              <div class="likert-scale">
                <div
                  v-for="value in 5"
                  :key="`corpus_fidelity-${value}`"
                  class="likert-option"
                  @click="feedback.corpus_fidelity = value"
                >
                  <input
                    type="radio"
                    :id="`corpus_fidelity-${value}`"
                    :value="value"
                    v-model="feedback.corpus_fidelity"
                  />
                  <label :for="`corpus_fidelity-${value}`" class="likert-label">
                    <span class="likert-circle" :class="{ active: feedback.corpus_fidelity >= value }"></span>
                    <span class="likert-text">{{ value }}</span>
                  </label>
                </div>
              </div>
            </div>

            <div class="feedback-section">
              <label class="section-label">
                Analysis Quality
                <span class="tooltip" title="Quality of historical analysis">ⓘ</span>
              </label>
              <div class="likert-scale">
                <div
                  v-for="value in 5"
                  :key="`analysis_quality-${value}`"
                  class="likert-option"
                  @click="feedback.analysis_quality = value"
                >
                  <input
                    type="radio"
                    :id="`analysis_quality-${value}`"
                    :value="value"
                    v-model="feedback.analysis_quality"
                  />
                  <label :for="`analysis_quality-${value}`" class="likert-label">
                    <span class="likert-circle" :class="{ active: feedback.analysis_quality >= value }"></span>
                    <span class="likert-text">{{ value }}</span>
                  </label>
                </div>
              </div>
            </div>
            
            <div class="feedback-section">
              <label class="section-label">
                Relevance
                <span class="tooltip" title="Relevance of retrieved sources to query">ⓘ</span>
              </label>
              <div class="likert-scale">
                <div
                  v-for="value in 5"
                  :key="`relevance-${value}`"
                  class="likert-option"
                  @click="feedback.relevance = value"
                >
                  <input
                    type="radio"
                    :id="`relevance-${value}`"
                    :value="value"
                    v-model="feedback.relevance"
                  />
                  <label :for="`relevance-${value}`" class="likert-label">
                    <span class="likert-circle" :class="{ active: feedback.relevance >= value }"></span>
                    <span class="likert-text">{{ value }}</span>
                  </label>
                </div>
              </div>
            </div>
            
            <div class="feedback-section">
              <label class="section-label">
                Difficulty
                <span class="tooltip" title="Difficulty of the query">ⓘ</span>
              </label>
              <div class="likert-scale">
                <div
                  v-for="value in 5"
                  :key="`difficulty-${value}`"
                  class="likert-option"
                  @click="feedback.difficulty = value"
                >
                  <input
                    type="radio"
                    :id="`difficulty-${value}`"
                    :value="value"
                    v-model="feedback.difficulty"
                  />
                  <label :for="`difficulty-${value}`" class="likert-label">
                    <span class="likert-circle" :class="{ active: feedback.difficulty >= value }"></span>
                    <span class="likert-text">{{ value }}</span>
                  </label>
                </div>
              </div>
            </div>
            
            <div class="feedback-section">
              <label class="section-label">
                Clarity
                <span class="tooltip" title="Clarity of the response">ⓘ</span>
              </label>
              <div class="likert-scale">
                <div
                  v-for="value in 5"
                  :key="`clarity-${value}`"
                  class="likert-option"
                  @click="feedback.clarity = value"
                >
                  <input
                    type="radio"
                    :id="`clarity-${value}`"
                    :value="value"
                    v-model="feedback.clarity"
                  />
                  <label :for="`clarity-${value}`" class="likert-label">
                    <span class="likert-circle" :class="{ active: feedback.clarity >= value }"></span>
                    <span class="likert-text">{{ value }}</span>
                  </label>
                </div>
              </div>
            </div>

            
          </div>

          <!-- User Type -->
          <div class="field mt-4">
            <label class="label has-text-weight-bold">User Type</label>
            <div class="control">
              <label class="radio" title="Expert user: you have substantial domain knowledge relevant to this content">
                <input type="radio" value="expert" v-model="feedback.user_type" />
                Expert User
              </label>
              <label class="radio ml-3" title="Non-expert user: you do not have substantial domain expertise for this content">
                <input type="radio" value="non_expert" v-model="feedback.user_type" />
                Non-expert User
              </label>
            </div>
          </div>

          <!-- Comments Section -->
          <div class="field mt-4">
            <label class="label has-text-weight-bold">Additional Comments (Optional)</label>
            <div class="control">
              <textarea 
                class="textarea" 
                v-model="feedback.feedback_text"
                placeholder="Any additional observations about this interaction..."
                rows="3"
              ></textarea>
            </div>

            
          </div>

          <!-- Faults Section -->
          <div class="faults-section">
            <label class="section-label">Faults</label>
            <div class="faults-grid">
              <div class="fault-option">
                <input
                  type="checkbox"
                  id="fault-hallucination"
                  v-model="feedback.faults.hallucination"
                />
                <label for="fault-hallucination">Hallucination</label>
              </div>
              <div class="fault-option">
                <input
                  type="checkbox"
                  id="fault-off-topic"
                  v-model="feedback.faults.off_topic"
                />
                <label for="fault-off-topic">Off-topic</label>
              </div>
              <div class="fault-option">
                <input
                  type="checkbox"
                  id="fault-inappropriate"
                  v-model="feedback.faults.inappropriate"
                />
                <label for="fault-inappropriate">Inappropriate</label>
              </div>
              <div class="fault-option">
                <input
                  type="checkbox"
                  id="fault-bias"
                  v-model="feedback.faults.bias"
                />
                <label for="fault-bias">Bias</label>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="feedback-actions">
            <button
              @click="submitFeedback"
              class="submit-btn"
              :disabled="!isFormValid || isSubmitting"
            >
              <span v-if="isSubmitting">
                <i class="fas fa-spinner fa-spin mr-2"></i>
                Submitting Inter-rating...
              </span>
              <span v-else>Submit Inter-rating</span>
            </button>
          </div>
          
          <!-- Progress Indicator -->
          <div class="has-text-centered mt-4">
            <div v-if="!isFormValid" class="has-text-danger">
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Citation Modal for single citation -->
    <div class="modal" :class="{ 'is-active': selectedCitation }">
      <div class="modal-background" @click="selectedCitation = null"></div>
      <div class="modal-card">
        <header class="modal-card-head">
          <p class="modal-card-title">Citation Details</p>
          <button class="delete" aria-label="close" @click="selectedCitation = null"></button>
        </header>
        <section class="modal-card-body" v-if="selectedCitation">
          <div class="citation-details">
            <div class="citation-content">
              <p class="citation-text">{{ getCitationText(selectedCitation) }}</p>
            </div>
            
            <div class="citation-metadata">
              <div v-if="selectedCitation.title || selectedCitation.metadata?.title" class="metadata-item">
                <strong>Title:</strong> {{ selectedCitation.title || selectedCitation.metadata?.title }}
              </div>
              
              <div v-if="selectedCitation.date || selectedCitation.metadata?.date" class="metadata-item">
                <strong>Date:</strong> {{ selectedCitation.date || selectedCitation.metadata?.date }}
              </div>
              
              <div v-if="selectedCitation.source || selectedCitation.metadata?.source" class="metadata-item">
                <strong>Retrieval ID:</strong> {{ selectedCitation.retrieval_id || selectedCitation.source_id || selectedCitation.source || selectedCitation.metadata?.source }}
              </div>
              
              <div v-if="selectedCitation.corpus || selectedCitation.metadata?.corpus" class="metadata-item">
                <strong>Corpus:</strong> {{ selectedCitation.corpus || selectedCitation.metadata?.corpus }}
              </div>
              
              <div v-if="selectedCitation.page || selectedCitation.metadata?.page" class="metadata-item">
                <strong>Page:</strong> {{ selectedCitation.page || selectedCitation.metadata?.page }}
              </div>
            </div>
            
            <div v-if="selectedCitation.url || selectedCitation.metadata?.url" class="citation-actions">
              <a 
                :href="selectedCitation.url || selectedCitation.metadata?.url" 
                target="_blank" 
                rel="noopener noreferrer" 
                class="button is-primary"
              >
                <span class="icon">
                  <i class="fas fa-external-link-alt"></i>
                </span>
                <span>View Source</span>
              </a>
            </div>
          </div>
        </section>
        <footer class="modal-card-foot">
          <button class="button" @click="selectedCitation = null">Close</button>
        </footer>
      </div>
    </div>

    <!-- All Citations Modal -->
    <div class="modal" :class="{ 'is-active': showAllCitations }">
      <div class="modal-background" @click="showAllCitations = false"></div>
      <div class="modal-card">
        <header class="modal-card-head">
          <p class="modal-card-title">All Citations ({{ session.citations ? session.citations.length : 0 }})</p>
          <button class="delete" aria-label="close" @click="showAllCitations = false"></button>
        </header>
        <section class="modal-card-body">
          <div class="all-citations-list">
            <div 
              v-for="(citation, index) in session.citations" 
              :key="index" 
              class="citation-card"
            >
              <div class="citation-header">
                <h6 class="citation-title">{{ getCitationLabel(citation) }}</h6>
                <span class="citation-index">#{{ index + 1 }}</span>
              </div>
              <div class="citation-content">
                <p>{{ getCitationText(citation) }}</p>
              </div>
              <div class="citation-metadata">
                <p v-if="citation.retrieval_id || citation.source_id || citation.source || citation.metadata?.source"><strong>Retrieval ID:</strong> {{ citation.retrieval_id || citation.source_id || citation.source || citation.metadata?.source }}</p>
                <p v-if="citation.date || citation.metadata?.date"><strong>Date:</strong> {{ citation.date || citation.metadata?.date }}</p>
                <p v-if="citation.url || citation.metadata?.url">
                  <a :href="citation.url || citation.metadata?.url" target="_blank" rel="noopener noreferrer">
                    View Source <i class="fas fa-external-link-alt"></i>
                  </a>
                </p>
              </div>
            </div>
          </div>
        </section>
        <footer class="modal-card-foot">
          <button class="button" @click="showAllCitations = false">Close</button>
        </footer>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Configure marked for consistent markdown rendering
marked.setOptions({
  breaks: true,
  gfm: true,
  mangle: false,
  sanitize: false
})

// Function to render markdown content (sanitized to prevent XSS)
function renderMarkdown(content) {
  if (!content) return ''
  return DOMPurify.sanitize(marked(content))
}

// Function to truncate text
function truncateText(text, maxLength) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

// Function to get citation label for display
function getCitationLabel(citation) {
  // Try to find the best label in this order of preference
  if (citation.date) return citation.date
  if (citation.metadata?.date) return citation.metadata.date
  if (citation.title) return truncateText(citation.title, 25)
  if (citation.metadata?.title) return truncateText(citation.metadata.title, 25)
  if (citation.source) return truncateText(citation.source, 25)
  if (citation.metadata?.source) return truncateText(citation.metadata.source, 25)
  if (citation.id) return truncateText(citation.id, 15)
  return "Source"
}

// Function to get citation text (for tooltip and modal display)
function getCitationText(citation) {
  if (!citation) return "View citation"
  
  // Try to get the best text content
  if (citation.text) return citation.text
  if (citation.quote) return citation.quote
  if (citation.content) return citation.content
  if (citation.metadata?.text) return citation.metadata.text
  if (citation.metadata?.content) return citation.metadata.content
  if (citation.metadata?.quote) return citation.metadata.quote
  
  // Fallback to other fields
  if (citation.title) return citation.title
  if (citation.source) return citation.source
  
  return "View citation"
}

export default {
  name: 'InterRaterPlayback',
  props: {
    session: {
      type: Object,
      required: true
    },
    currentIndex: {
      type: Number,
      required: true
    },
    totalSessions: {
      type: Number,
      required: true
    }
  },
  emits: ['submit-feedback'],
  setup(props, { emit }) {
    const feedback = ref({
      factual_accuracy: '',
      corpus_fidelity: '',
      analysis_quality: '',
      relevance: '',
      difficulty: '',
      clarity: '',
      user_type: '',
      feedback_text: '',
      faults: {
        hallucination: false,
        off_topic: false,
        inappropriate: false,
        bias: false
      }
    })
    
    const isSubmitting = ref(false)
    
    // Citation modal states
    const selectedCitation = ref(null)
    const showAllCitations = ref(false)
    const hoveredCitation = ref(null)

    const isFormValid = computed(() => {
      return feedback.value.factual_accuracy && 
             feedback.value.corpus_fidelity && 
             feedback.value.analysis_quality && 
             feedback.value.relevance && 
             feedback.value.difficulty && 
             feedback.value.clarity &&
             feedback.value.user_type
    })

    const formatDate = (dateString) => {
      try {
        const date = new Date(dateString)
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
      } catch (error) {
        return dateString
      }
    }

    const submitFeedback = async () => {
      if (!isFormValid.value || isSubmitting.value) return
      if (!props.session?.span_id) {
        console.error('Cannot submit inter-rater feedback: session missing span_id')
        return
      }

      isSubmitting.value = true

      try {
        const feedbackData = {
          session_id: props.session.session_id,
          qa_id: props.session.qa_id,
          factual_accuracy: parseInt(feedback.value.factual_accuracy),
          corpus_fidelity: parseInt(feedback.value.corpus_fidelity),
          analysis_quality: parseInt(feedback.value.analysis_quality),
          relevance: parseInt(feedback.value.relevance),
          difficulty: parseInt(feedback.value.difficulty),
          clarity: parseInt(feedback.value.clarity),
          user_type: feedback.value.user_type || null,
          feedback_text: feedback.value.feedback_text,
          faults: feedback.value.faults,
          is_inter_rater: true,
          // rater_id is assigned by backend from the authenticated user; do not set on client
          original_span_id: props.session.span_id,
          timestamp: new Date().toISOString(),
          question: props.session.question,
          answer: props.session.answer,
          citations: props.session.citations || [],
          feedback_type: 'inter_rater'
        }

        emit('submit-feedback', feedbackData)
      } catch (error) {
        console.error('Error submitting inter-rater feedback:', error)
      } finally {
        isSubmitting.value = false
      }
    }


    // Citation modal functions
    const showCitationModal = (citation) => {
      selectedCitation.value = citation
    }

    const showAllCitationsModal = () => {
      showAllCitations.value = true
    }

    // Reset form when session changes
    watch(() => props.session, () => {
      // Reset all feedback fields
      feedback.value = {
        factual_accuracy: '',
        corpus_fidelity: '',
        analysis_quality: '',
        relevance: '',
        difficulty: '',
        clarity: '',
        user_type: '',
        feedback_text: '',
        faults: {
          hallucination: false,
          off_topic: false,
          inappropriate: false,
          bias: false
        }
      }
      
      // Reset submission state
      isSubmitting.value = false
      
      // Reset modal states
      selectedCitation.value = null
      showAllCitations.value = false
      hoveredCitation.value = null
    }, { immediate: false })

    return {
      feedback,
      isSubmitting,
      isFormValid,
      formatDate,
      submitFeedback,
      renderMarkdown,
      getCitationLabel,
      getCitationText,
      selectedCitation,
      showAllCitations,
      hoveredCitation,
      showCitationModal,
      showAllCitationsModal
    }
  }
}
</script>

<style scoped>
.inter-rater-playback {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 1rem;
}

.session-header {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #6c757d;
}

.conversation-container {
  margin-bottom: 2rem;
}

/* Question and Answer Sections - Chat Interface Style */
.question-section,
.answer-section,
.original-feedback-section {
  margin-bottom: 1.5rem;
}

.message-style-container {
  background: white;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  width: 100%;
  overflow: hidden;
}

.section-header {
  background: #f8f9fa;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e9ecef;
}

.section-title {
  color: #111;
  font-size: 1.3rem;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  text-align: left;
}

.section-content {
  background: white;
  padding: 1.5rem;
}

.content-text {
  color: #111;
  font-size: 1rem;
  line-height: 1.6;
}

.content-text .content {
  color: #111 !important;
}

/* Markdown styling for rendered content */
.content :deep(h1),
.content :deep(h2),
.content :deep(h3),
.content :deep(h4),
.content :deep(h5),
.content :deep(h6) {
  color: #111;
  font-weight: 600;
  margin-top: 1.5rem;
  margin-bottom: 0.5rem;
}

.content :deep(h1) { font-size: 1.5rem; }
.content :deep(h2) { font-size: 1.3rem; }
.content :deep(h3) { font-size: 1.1rem; }
.content :deep(h4) { font-size: 1rem; }

.content :deep(p) {
  margin-bottom: 1rem;
  color: #111;
  line-height: 1.6;
}

.content :deep(ul),
.content :deep(ol) {
  margin-bottom: 1rem;
  padding-left: 1.5rem;
  color: #111;
}

.content :deep(li) {
  margin-bottom: 0.25rem;
  color: #111;
}

.content :deep(strong) {
  font-weight: 600;
  color: #111;
}

.content :deep(em) {
  font-style: italic;
  color: #111;
}

.content :deep(blockquote) {
  border-left: 3px solid #ddd;
  padding-left: 1rem;
  margin: 1rem 0;
  color: #666;
  font-style: italic;
}

.content :deep(code) {
  background-color: #f5f5f5;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-size: 0.9em;
  color: #111;
}

.content :deep(pre) {
  background-color: #f5f5f5;
  padding: 1em;
  border-radius: 4px;
  overflow-x: auto;
  margin: 1rem 0;
}

.content :deep(pre code) {
  background-color: transparent;
  padding: 0;
  font-size: 0.9em;
  color: #111;
}

.citations-title {
  color: #111;
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
}

.citations-section {
  background-color: transparent;
  border-radius: 6px;
  padding: 0;
  margin-top: 1rem;
}

/* Citation List Styling (matching ChatHistory.vue) */
.citation-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.citation-item {
  position: relative;
  padding: 0.25rem 0;
  font-family: 'Times New Roman', Times, serif;
  font-size: 0.9rem;
  display: inline-block;
  vertical-align: top;
}

.citation-link {
  text-decoration: underline;
  color: #111;
  cursor: pointer;
  font-family: 'Times New Roman', Times, serif;
  font-size: 0.9rem;
}

.citation-link:hover {
  color: #666;
  text-decoration: underline;
}

.view-all-link {
  text-decoration: underline;
  color: #111;
  cursor: pointer;
  font-family: 'Times New Roman', Times, serif;
  font-size: 0.9rem;
  margin-left: 0.5rem;
}

.view-all-link:hover {
  color: #666;
  text-decoration: underline;
}

/* Citation Tooltip */
.citation-tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 0.5rem;
  z-index: 1000;
  min-width: 300px;
  max-width: 400px;
}

.citation-tooltip-content {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  padding: 1rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.citation-quote {
  font-style: italic;
  color: #495057;
  margin-bottom: 0.75rem;
  padding: 0.5rem;
  background-color: #f8f9fa;
  border-radius: 4px;
  border-left: 3px solid #6c757d;
}

.citation-meta p {
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
}

.citation-url a {
  color: #495057;
  text-decoration: underline;
}

.citation-url a:hover {
  color: #212529;
}

/* Modal Styling */
.citation-details {
  max-width: 100%;
}

.citation-text {
  font-style: italic;
  color: #495057;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #6c757d;
  line-height: 1.6;
}

.citation-metadata {
  margin-bottom: 1.5rem;
}

.metadata-item {
  margin-bottom: 0.75rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f1f3f4;
}

.metadata-item:last-child {
  border-bottom: none;
}

.citation-actions {
  text-align: center;
}

/* All Citations Modal */
.all-citations-list {
  max-height: 60vh;
  overflow-y: auto;
}

.citation-card {
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  background-color: white;
}

.citation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #f1f3f4;
}

.citation-title {
  font-weight: 600;
  color: #495057;
  margin: 0;
}

.citation-index {
  background-color: #6c757d;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.citation-card .citation-content {
  margin-bottom: 0.75rem;
}

.citation-card .citation-content p {
  font-style: italic;
  color: #495057;
  line-height: 1.5;
  margin: 0;
}

.citation-card .citation-metadata p {
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
}

.citation-card .citation-metadata a {
  color: #495057;
  text-decoration: none;
}

.citation-card .citation-metadata a:hover {
  text-decoration: underline;
}

/* Original Feedback Metrics */
.feedback-metric {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.metric-label {
  font-weight: 600;
  min-width: 120px;
}

.metric-value {
  font-weight: bold;
  color: #495057;
}

.metric-stars {
  display: flex;
  gap: 2px;
}

.star {
  font-size: 1rem;
}

.star.filled {
  color: #6c757d;
}

.star.empty {
  color: #ddd;
}

/* Inter-rater Feedback Form - Chat Interface Style */
.inter-rater-feedback-section {
  margin-top: 3rem;
}

.feedback-container {
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 0;
}

.feedback-header {
  margin-bottom: 1.5rem;
  text-align: center;
  padding: 1.5rem 1.5rem 0 1.5rem;
}

.feedback-header h4 {
  margin: 0 0 0.5rem 0;
  color: #495057;
  font-size: 18px;
}

.feedback-header .subtitle {
  margin: 0;
  color: #6c757d;
  font-size: 14px;
  line-height: 1.4;
}

.feedback-content {
  padding: 0 1.5rem 1.5rem 1.5rem;
}

/* Likert Scale Styling (matching ExtendedFeedback.vue) */
.rating-sections {
  margin-bottom: 2rem;
}

.feedback-section {
  margin-bottom: 1.5rem;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.75rem;
  font-size: 14px;
}

.tooltip {
  color: #6c757d;
  cursor: help;
  font-size: 12px;
  margin-left: 0.25rem;
}

.likert-scale {
  display: flex;
  justify-content: space-between;
  max-width: 300px;
  margin: 0 auto;
}

.likert-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
}

.likert-option input[type="radio"] {
  display: none;
}

.likert-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  padding: 0.25rem;
}

.likert-circle {
  width: 20px;
  height: 20px;
  border: 2px solid #dee2e6;
  border-radius: 50%;
  background-color: white;
  transition: all 0.2s ease;
  margin-bottom: 0.25rem;
}

.likert-circle.active {
  background-color: #363636;
  border-color: #363636;
}

.likert-text {
  font-size: 12px;
  color: #6c757d;
}

/* Action Buttons (matching ExtendedFeedback.vue) */
.feedback-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  border-top: 1px solid #e9ecef;
  padding-top: 1rem;
  margin-top: 1.5rem;
}

.cancel-btn {
  background-color: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s ease;
}

.cancel-btn:hover:not(:disabled) {
  background-color: #545b62;
}

.submit-btn {
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s ease;
}

.submit-btn:hover:not(:disabled) {
  background-color: #218838;
}

.submit-btn:disabled,
.cancel-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

/* Responsive Design */
@media (max-width: 768px) {
  .inter-rater-playback {
    padding: 0 0.5rem;
  }
  
  .session-header {
    padding: 1rem;
  }
  
  .likert-scale {
    max-width: 250px;
  }
  
  .feedback-actions {
    flex-direction: column;
  }
}

/* Faults Section (matching ExtendedFeedback.vue) */
.faults-section {
  border-top: 1px solid #e9ecef;
  padding-top: 1.5rem;
  margin-top: 1.5rem;
}

.faults-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
  margin-top: 0.75rem;
}

.fault-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.fault-option input[type="checkbox"] {
  margin: 0;
}

.fault-option label {
  font-size: 14px;
  color: #495057;
  cursor: pointer;
}

@media (max-width: 768px) {
  .faults-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Visual Improvements */
.card {
  transition: box-shadow 0.3s ease;
}

.card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.notification.is-info.is-light {
  border-left: 4px solid #209cee;
}
</style>
