<template>
	<div class="chat-history">
		<div class="messages">
			<div v-for="(message, index) in chatHistory" :key="message.message_id || index" class="message-container">
				<div :class="['message', 
					message.role === 'assistant' ? 'is-primary' : 'is-info',
					message.is_clarification ? 'is-clarification-question' : '',
					message.is_context_change ? 'is-context-change' : ''
				]">
					<div class="message-content">
						<!-- Special label for clarification questions -->
						<div v-if="message.is_clarification" class="clarification-badge">
							<span class="tag is-warning">Clarification Question</span>
						</div>
						
						<div class="content">
							<div v-html="renderMarkdown(message.content)"></div>
						</div>
						
						<!-- Citations only show if not a clarification question -->
						<div v-if="message.citations && message.citations.length > 0 && !message.is_clarification" class="citations mt-2">
							<ul class="citation-list">
								<li 
									v-for="(citation, cIndex) in message.citations" 
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
												<p v-if="citation.source || citation.title || citation.metadata?.source"><strong>Source:</strong> {{ citation.source || citation.title || citation.metadata?.source }}</p>
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
								<li class="citation-item view-all-item" v-if="message.citations.length > 1">
									<a 
										@click.prevent="showAllCitationsModal(message)" 
										class="view-all-link"
									>
										View all {{ message.allCitations && message.allCitations.length ? message.allCitations.length : message.citations.length }} citations
									</a>
								</li>
							</ul>
						</div>
						
						<!-- Inline Feedback (New) - Only for assistant messages with citations -->
						<InlineFeedback
							v-if="message.role === 'assistant' && message.citations && message.citations.length > 0 && !message.is_clarification"
							:qa-id="message.qa_id"
							:message-id="message.message_id"
							:session-id="sessionId"
							:message-complete="isResponseComplete"
							:citations-visible="true"
							@feedback-workflow-complete="onFeedbackWorkflowComplete"
						/>
						
					</div>
				</div>
			</div>
			
			<!-- Show processing indicator when response is in progress but no content yet -->
			<div v-if="!isResponseComplete && !hasCurrentAssistantResponse" class="message-container">
				<div class="message is-primary">
					<div class="message-content">
						<div class="processing-indicator">
							<span class="processing-dot"></span>
							<span class="processing-text">Processing document chunks (search-k)...</span>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Citation Modal for single citation -->
		<div class="modal" :class="{ 'is-active': selectedCitation }">
			<div class="modal-background" style="background: #fff !important;" @click="selectedCitation = null"></div>
			<div class="modal-card">
				<header class="modal-card-head">
					<p class="modal-card-title">Citation Details</p>
					<button class="delete" aria-label="close" @click="selectedCitation = null"></button>
				</header>
				<section class="modal-card-body" v-if="selectedCitation">
					<div class="citation-full-content">
						<h3 class="title is-5" v-if="selectedCitation.title">{{ selectedCitation.title }}</h3>
						<p class="content">{{ getCitationContent(selectedCitation) }}</p>
						
						<div class="citation-metadata">
							<h4 class="title is-6">Metadata</h4>
							<table class="table is-striped is-fullwidth">
								<tbody>
									<tr v-if="selectedCitation.title">
										<th>Title</th>
										<td>{{ selectedCitation.title }}</td>
									</tr>
									<tr v-if="selectedCitation.source">
										<th>Source</th>
										<td>{{ selectedCitation.source }}</td>
									</tr>
									<tr v-if="selectedCitation.date">
										<th>Date</th>
										<td>{{ selectedCitation.date }}</td>
									</tr>
									<tr v-if="selectedCitation.corpus">
										<th>Corpus</th>
										<td>{{ selectedCitation.corpus }}</td>
									</tr>
									<tr v-if="selectedCitation.page">
										<th>Page</th>
										<td>{{ selectedCitation.page }}</td>
									</tr>
									<tr v-if="selectedCitation.url">
										<th>URL</th>
										<td>
											<a :href="selectedCitation.url" target="_blank" rel="noopener noreferrer" class="citation-link-url">
												 {{ selectedCitation.url }}
											</a>
										</td>
									</tr>
									<tr v-if="selectedCitation.id">
										<th>ID</th>
										<td>{{ selectedCitation.id }}</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>
				</section>
				<footer class="modal-card-foot">
					<button class="button" @click="selectedCitation = null">Close</button>
				</footer>
			</div>
		</div>

		<!-- All Citations Modal using system-prompt-modal styling -->
		<div class="system-prompt-modal" :class="{ 'is-active': showAllCitations }">
			<div class="modal-background" @click="showAllCitations = false"></div>
			<div class="modal-card">
				<header class="modal-card-head">
					<p class="modal-card-title">All Documents Used in Analysis</p>
				</header>
				<section class="modal-card-body">
					<div v-for="(citation, index) in allCitations" :key="index" class="citation-item-full">
						<!-- Metadata section first -->                        
						<div class="citation-metadata-wrapper">
							<div class="metadata-section">
								<!-- Source URL with consistent styling as other metadata -->
								<div class="metadata-item">
									<strong>Source URL:</strong> 
									<a v-if="citation.url && citation.url !== 'None' && citation.url !== ''" 
									   :href="citation.url" 
									   target="_blank" 
									   rel="noopener noreferrer"
									   class="citation-url-link">
										{{ citation.url }}
									</a>
									<span v-else-if="getCitationUrl(citation)" class="citation-url-extracted">
										<a :href="getCitationUrl(citation)" target="_blank" rel="noopener noreferrer">
											{{ getCitationUrl(citation) }}
										</a>
									</span>
									<span v-else-if="citation.corpus" class="no-data-available">
										{{ getCorpusUrlMessage(citation.corpus) }}
									</span>
									<span v-else class="no-data-available">No URL available</span>
								</div>
								
								<!-- Date if available -->
								<div v-if="citation.date || (citation.metadata && citation.metadata.date)" class="metadata-item">
									<strong>Date:</strong> {{ citation.date || citation.metadata?.date }}
								</div>
								
								<!-- Other metadata fields -->
								<div v-if="citation.source || (citation.metadata && citation.metadata.source)" class="metadata-item">
									<strong>Source:</strong> {{ citation.source || citation.metadata?.source }}
								</div>
								
								<div v-if="citation.corpus || (citation.metadata && citation.metadata.corpus)" class="metadata-item">
									<strong>Corpus:</strong> {{ citation.corpus || citation.metadata?.corpus }}
								</div>
								
								<div v-if="citation.page || (citation.metadata && citation.metadata.page)" class="metadata-item">
									<strong>Page:</strong> {{ citation.page || citation.metadata?.page }}
								</div>
								
								<!-- Additional metadata fields -->
								<template v-if="citation.metadata">
									<div v-for="(value, key) in citation.metadata" :key="key" class="metadata-item">
										<template v-if="!['date', 'page', 'corpus', 'source', 'url', 'content', 'text', 'full_content', 'page_content', 'chunk_content'].includes(key) && value">
											<strong>{{ key.charAt(0).toUpperCase() + key.slice(1) }}:</strong> {{ value }}
										</template>
									</div>
								</template>
							</div>
						</div>
						
						<!-- Full chunk content section after metadata -->
						<div class="citation-content-wrapper">
							<h4 class="content-label">Citation Content:</h4>
							<div class="citation-full-text">
								<!-- Use computed function to get the full content -->
								{{ getCitationContent(citation) }}
							</div>
							
							<!-- Citation metadata information -->
							<div class="citation-content-metadata">
								<div class="content-length-info">
									<strong>Content Length:</strong> {{ getCitationContent(citation).length }} characters
								</div>
								<div class="content-note">
									<strong class="note-icon">Note:</strong> Citation content may be partial due to vector store chunking strategy. Please refer to the source URL for complete text.
								</div>
							</div>
						</div>
						
						<div v-if="index < allCitations.length - 1" class="citation-divider"></div>
					</div>
				</section>
				<footer class="modal-card-foot">
					<button class="button" @click="showAllCitations = false">Close</button>
				</footer>
			</div>
		</div>

	</div>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useSessionStore } from '@/stores/session'
import { ref, onMounted, computed } from 'vue'
import { marked } from 'marked'
import InlineFeedback from './InlineFeedback.vue'

const emit = defineEmits(['feedback-workflow-complete'])

const sessionStore = useSessionStore()
const { chatHistory, isResponseComplete } = storeToRefs(sessionStore)

// Session ID for feedback
const sessionId = computed(() => sessionStore.sessionId)

// Citation hover and modal state
const hoveredCitation = ref(null)
const selectedCitation = ref(null)
const showAllCitations = ref(false)
const allCitations = ref([])

// Check if there's a current assistant response being streamed
const hasCurrentAssistantResponse = computed(() => {
	// Look for the last message in chat history
	if (chatHistory.value.length === 0) return false;
	const lastMessage = chatHistory.value[chatHistory.value.length - 1];
	// If the last message is from assistant and response is not complete, we have streaming content
	return lastMessage.role === 'assistant' && !isResponseComplete.value;
})

// Configure marked options
marked.setOptions({
	breaks: true,  // Convert line breaks to <br>
	gfm: true,     // Use GitHub Flavored Markdown
	headerIds: false, // Don't add IDs to headers
	mangle: false,  // Don't escape HTML
	sanitize: false // Don't sanitize HTML
})

// Function to render markdown content
function renderMarkdown(content) {
	if (!content) return ''
	return marked(content)
}

// Corpus configuration
const corpusConfig = ref([])

// Fetch corpus configuration from API
async function fetchCorpusConfig() {
	try {
		// Construct the correct API URL
		const apiUrl = import.meta.env.VITE_API_URL || '';
		const configUrl = apiUrl ? 
			(apiUrl.endsWith('/') ? `${apiUrl}api/config` : `${apiUrl}/api/config`) : 
			'/api/config';
		
		console.log('Fetching configuration from:', configUrl);
		const response = await fetch(configUrl);
		
		if (response.ok) {
			const data = await response.json()
			if (data.CORPUS_OPTIONS && Array.isArray(data.CORPUS_OPTIONS)) {
				corpusConfig.value = data.CORPUS_OPTIONS
			}
		}
	} catch (error) {
		console.error('Error fetching corpus configuration:', error)
		corpusConfig.value = []
	}
}

// Fetch config on component mount
onMounted(() => {
	fetchCorpusConfig()
})

// Function to get URL message for a corpus
function getCorpusUrlMessage(corpusId) {
	if (!corpusId) return 'No URL available';
	
	// Find the matching corpus option
	for (const option of corpusConfig.value) {
		// Check if this corpus ID includes the option value (allowing for partial matches)
		if (option.value && corpusId.includes(option.value) && option.url_message) {
			return option.url_message;
		}
	}
	
	return 'No URL available';
}


// Function to show citation modal
function showCitationModal(citation) {
	selectedCitation.value = citation
}

// Function to get the URL from a citation
function getCitationUrl(citation) {
	// Skip if citation is null or undefined
	if (!citation) return null;
	
	// Try direct url property
	if (citation.url && citation.url !== 'None' && citation.url !== '' && 
		(typeof citation.url !== 'string' || citation.url.toLowerCase() !== 'none')) {
		return citation.url;
	}
	
	// Try url in metadata
	if (citation.metadata && citation.metadata.url && 
		citation.metadata.url !== 'None' && citation.metadata.url !== '' &&
		(typeof citation.metadata.url !== 'string' || citation.metadata.url.toLowerCase() !== 'none')) {
		return citation.metadata.url;
	}
	
	// Try extracting from content
	const contentFields = ['content', 'full_content', 'page_content', 'text', 'chunk_content'];
	for (const field of contentFields) {
		if (citation[field] && typeof citation[field] === 'string' && citation[field].includes('<url>')) {
			const urlMatch = citation[field].match(/<url>(https?:\/\/[^<]+)<\/url>/);
			if (urlMatch && urlMatch[1]) {
				return urlMatch[1];
			}
		}
		
		// Also check in metadata
		if (citation.metadata && citation.metadata[field] && 
			typeof citation.metadata[field] === 'string' && 
			citation.metadata[field].includes('<url>')) {
			const urlMatch = citation.metadata[field].match(/<url>(https?:\/\/[^<]+)<\/url>/);
			if (urlMatch && urlMatch[1]) {
				return urlMatch[1];
			}
		}
	}
	
	return null;
}

// Function to get the full content from a citation
function getCitationContent(citation) {
	// Skip if citation is null or undefined
	if (!citation) return "No content available";
	
	// Check direct content fields in priority order
	const contentFields = ['full_content', 'content', 'page_content', 'text', 'chunk_content'];
	
	// Check direct content fields in priority order
	for (const field of contentFields) {
		if (citation[field] && typeof citation[field] === 'string' && citation[field].trim() !== '') {
			// Remove URL tags if present
			let content = citation[field];
			content = content.replace(/<url>.*?<\/url>/g, '');
			return content;
		}
	}
	
	// Check metadata fields
	if (citation.metadata) {
		for (const field of contentFields) {
			if (citation.metadata[field] && 
				typeof citation.metadata[field] === 'string' && 
				citation.metadata[field].trim() !== '') {
				// Remove URL tags if present
				let content = citation.metadata[field];
				content = content.replace(/<url>.*?<\/url>/g, '');
				return content;
			}
		}
	}
	
	// If we get here, no content was found
	return "No content available";
}

// Function to show all citations modal
function showAllCitationsModal(message) {
	// Use allCitations if available, otherwise fall back to regular citations
	const citationsToShow = message.allCitations && message.allCitations.length > 0 ? 
		message.allCitations : message.citations;
	
	if (citationsToShow && citationsToShow.length > 0) {
		// Process citations before display
		citationsToShow.forEach((citation) => {
			// If URL is missing, try to extract it from content
			if (!citation.url || citation.url === '' || citation.url === 'None') {
				// Try to extract URL from content if available
				const content = citation.content || citation.full_content || citation.page_content || '';
				if (content && typeof content === 'string' && content.includes('<url>')) {
					const urlMatch = content.match(/<url>(https?:\/\/[^<]+)<\/url>/);
					if (urlMatch && urlMatch[1]) {
						citation.url = urlMatch[1];
					}
				}
			}
		});
	}
	
	allCitations.value = citationsToShow
	showAllCitations.value = true
}

// Function to get citation text (for tooltip display)
function getCitationText(citation) {
	return citation.text || citation.quote || citation.content || "View citation"
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

// Function to truncate text
function truncateText(text, length) {
	if (!text) return ''
	return text.length > length ? text.substring(0, length) + '...' : text
}


// Handle feedback workflow completion
function onFeedbackWorkflowComplete(messageId) {
	// Emit to parent that feedback workflow is complete for this message ID
	emit('feedback-workflow-complete', messageId)
}


</script>

<style scoped>
.modal .modal-background {
  background: #fff !important;
  opacity: 1 !important;
  box-shadow: none !important;
  filter: none !important;
  backdrop-filter: none !important;
}


.chat-history {
	width: 100%;
	padding: 1rem;
	overflow-y: visible;
}

.messages {
	display: flex;
	flex-direction: column;
	gap: 1rem;
}

.message-container {
	display: flex;
	flex-direction: column;
}

.message {
	max-width: 85%;
	margin: 0;
}

.message.is-primary {
	align-self: flex-end;
	background-color: transparent;
	color: #111 !important;
}

.message.is-info {
	align-self: flex-start;
	background-color: transparent;
	color: #111 !important;
}

/* Both user and assistant responses: transparent background for message content */
.message.is-primary .message-content,
.message.is-info .message-content {
	background: transparent !important;
	color: #111 !important;
	border-radius: 6px;
	padding: 1rem;
}

.message.is-clarification-question {
	background-color: #fffcf4; /* Light yellow background */
	border-left: 3px solid #ffdd57; /* Left border in warning color */
	color: #111 !important;
}

.message-content, .content, .citations, .citation-label, .citation-list, .citation-item {
	color: #111 !important;
}


.message.is-context-change {
	background-color: #f0f0f0; /* Light gray background */
	border-left: 3px solid #ffdd57; /* Left border in warning color */
}

.message-content {
	padding: 1rem;
}

.content {
	margin-bottom: 0.5rem;
}

.citations {
	border-top: 1px solid #dbdbdb;
	padding-top: 0.5rem;
}

.citation-label {
	font-weight: bold;
	margin-bottom: 0.5rem;
	font-family: serif;
}

.citation-list {
	list-style-type: none;
	padding-left: 0;
	margin-top: 0.5rem;
	display: flex;
	flex-wrap: wrap;
	gap: 0 1rem;
}

.citation-item {
	position: relative;
	padding: 0.25rem 0;
	font-family: 'Times New Roman', Times, serif;
	font-size: 0.9rem;
	display: inline-block;
}

.citation-link {
	text-decoration: underline;
	color: #111;
	cursor: pointer;
}

.citation-link:hover {
	color: #666;
}

.view-all-item {
	margin-left: 0.5rem;
}

.view-all-link {
	font-style: italic;
}

.citation-tooltip {
	position: absolute;
	bottom: 100%;
	left: 0;
	width: 320px;
	background-color: white;
	box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
	border-radius: 4px;
	z-index: 10;
	padding: 1rem;
	margin-bottom: 0.5rem;
	pointer-events: auto; /* Ensures the tooltip can receive mouse events */
}

.citation-tooltip::after {
	content: '';
	position: absolute;
	top: 100%;
	left: 15px;
	border-width: 8px;
	border-style: solid;
	border-color: white transparent transparent transparent;
}

.citation-quote {
	font-style: italic;
	margin-bottom: 0.5rem;
	font-size: 0.9rem;
	font-family: 'Times New Roman', Times, serif;
	line-height: 1.4;
	padding-bottom: 0.5rem;
	border-bottom: 1px solid #eee;
}

.citation-meta {
	font-size: 0.85rem;
	margin-top: 0.5rem;
}

.citation-meta p {
	margin-bottom: 0.25rem;
}

.citation-url a {
	color: #0066cc;
	text-decoration: underline;
}

.citation-url a:hover {
	color: #004080;
}

.citation-full-content {
	max-height: 400px;
	overflow-y: auto;
}

.citation-metadata {
	margin-top: 1.5rem;
}

/* All citations modal styles */
.all-citations-modal {
	width: 80vw;
	max-width: 900px;
}

.citation-item-full {
	margin-bottom: 2rem;
	padding-bottom: 1rem;
}

.citation-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 1rem;
}

.citation-date {
	font-family: 'Times New Roman', Times, serif;
	font-style: italic;
	color: #666;
}

.citation-content {
	margin-bottom: 1.5rem;
	padding: 0.5rem 0;
}

.content-label, .metadata-label {
	font-size: 1.1rem;
	font-weight: 600;
	margin-bottom: 0.5rem;
	color: #000;
}

.citation-content-wrapper {
	margin-bottom: 1.5rem;
}

.citation-full-text {
	white-space: pre-wrap;
	word-break: break-word;
	line-height: 1.6;
	padding: 0.5rem;
	background-color: #f9f9f9;
	border-radius: 4px;
	border-left: 3px solid #ddd;
	max-height: 300px;
	overflow-y: auto;
	font-family: inherit;
	margin-bottom: 0.5rem;
}

.citation-content-metadata {
	margin-top: 0.5rem;
	font-size: 0.85rem;
	padding: 0.5rem;
	background-color: #f5f5f5;
	border-radius: 4px;
}

.content-length-info {
	color: #666;
}

.content-truncation-warning {
	color: #e65100;
	margin-top: 0.25rem;
}

.content-note {
	margin-top: 0.5rem;
	margin-bottom: 0.5rem;
	padding: 0.5rem;
	background-color: #ffffff;
	border: 1px solid #e0e0e0;
	border-radius: 4px;
	font-size: 0.875rem;
	color: #000000;
}

.note-icon {
	font-weight: bold;
	color: #000000;
	margin-right: 0.25rem;
}

/* url-item class removed for consistent styling */

.citation-link-url {
	color: #000000;
	text-decoration: underline;
	word-break: break-all;
}

.citation-link-url:hover {
	color: #666666;
}

.citation-url-link {
	color: #000000;
	font-weight: 500;
	word-break: break-all;
}

.citation-url-extracted {
	color: #0066cc;
	font-style: italic;
}

.no-data-available {
	color: #999;
	font-style: italic;
}

.citation-divider {
	height: 2px;
	background-color: #e0e0e0;
	margin: 1.5rem 0;
}

.metadata-section {
	margin-top: 1rem;
}

.metadata-item {
	margin-bottom: 0.5rem;
	line-height: 1.4;
}

.metadata-item strong {
	color: #000;
	font-weight: 600;
}

/* System Prompt Modal Styles */
.system-prompt-modal {
	display: none;
}

.system-prompt-modal.is-active {
	display: flex;
	align-items: center;
	justify-content: center;
	position: fixed;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	z-index: 1000;
}

.system-prompt-modal .modal-background {
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	background-color: rgba(255, 255, 255, 0.9);
}

.system-prompt-modal .modal-card {
	position: relative;
	width: 80%;
	max-width: 800px;
	max-height: 80vh;
	display: flex;
	flex-direction: column;
	background-color: white;
	border-radius: 6px;
	box-shadow: 0 2px 15px rgba(0, 0, 0, 0.1);
}

.system-prompt-modal .modal-card-head {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 1.25rem;
	border-bottom: 1px solid #dbdbdb;
	background-color: white;
	border-top-left-radius: 6px;
	border-top-right-radius: 6px;
}

.system-prompt-modal .modal-card-title {
	color: black;
	font-size: 1.5rem;
	font-weight: 600;
	margin: 0;
}

.system-prompt-modal .modal-card-body {
	flex-grow: 1;
	overflow-y: auto;
	padding: 1.25rem;
	background-color: white;
}

.system-prompt-modal .modal-card-foot {
	display: flex;
	justify-content: flex-end;
	padding: 1.25rem;
	background-color: white;
	border-top: 1px solid #dbdbdb;
	border-bottom-left-radius: 6px;
	border-bottom-right-radius: 6px;
}

.system-prompt-modal .button {
	background-color: #f5f5f5;
	border: 1px solid #dbdbdb;
	border-radius: 4px;
	color: #363636;
	cursor: pointer;
	padding: 0.5em 1em;
	font-size: 1rem;
}

.system-prompt-modal .button:hover {
	background-color: #e8e8e8;
}

.clarification-badge {
	margin-bottom: 0.5rem;
}

.citations-loading {
	font-style: italic;
	color: #666;
	padding: 0.5rem 0;
	border-top: 1px solid #dbdbdb;
}


.ml-2 {
	margin-left: 0.5rem;
}

pre {
  background-color: #f5f5f5;
  color: #333;
  font-size: 0.8rem;
  padding: 0.25rem;
  border-radius: 3px;
  overflow-x: auto;
  max-height: 150px;
  white-space: pre-wrap;
}

/* Add styles for markdown content */
.content :deep(h1),
.content :deep(h2),
.content :deep(h3),
.content :deep(h4),
.content :deep(h5),
.content :deep(h6) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
  line-height: 1.25;
}

.content :deep(p) {
  margin-bottom: 1em;
}

.content :deep(ul),
.content :deep(ol) {
  margin-bottom: 1em;
  padding-left: 2em;
}

.content :deep(li) {
  margin-bottom: 0.5em;
}

.content :deep(strong) {
  font-weight: 600;
}

.content :deep(em) {
  font-style: italic;
}

.content :deep(code) {
  background-color: #f5f5f5;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-size: 0.9em;
}

.content :deep(pre) {
  background-color: #f5f5f5;
  padding: 1em;
  border-radius: 4px;
  overflow-x: auto;
  margin-bottom: 1em;
}

.content :deep(pre code) {
  background-color: transparent;
  padding: 0;
  font-size: 0.9em;
}

.content :deep(blockquote) {
  border-left: 4px solid #dbdbdb;
  padding-left: 1em;
  margin-left: 0;
  margin-bottom: 1em;
  color: #666;
}

.content :deep(hr) {
  border: none;
  border-top: 1px solid #dbdbdb;
  margin: 1em 0;
}

.content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1em;
}

.content :deep(th),
.content :deep(td) {
  border: 1px solid #dbdbdb;
  padding: 0.5em;
  text-align: left;
}

.content :deep(th) {
  background-color: #f5f5f5;
  font-weight: 600;
}

.content :deep(a) {
  color: #3273dc;
  text-decoration: none;
}

.content :deep(a:hover) {
  text-decoration: underline;
}

/* Processing indicator styles */
.processing-indicator {
  display: flex;
  align-items: center;
  color: #666;
  font-size: 0.9rem;
}

.processing-dot {
  width: 8px;
  height: 8px;
  background-color: #999;
  border-radius: 50%;
  margin-right: 0.5rem;
  animation: pulse 1.5s ease-in-out infinite;
}

.processing-text {
  color: #666;
}

@keyframes pulse {
  0% {
    opacity: 0.4;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0.4;
  }
}
</style>