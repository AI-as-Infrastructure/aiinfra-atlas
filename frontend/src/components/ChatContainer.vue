<template>
	<div class="chat-container">
		<div class="container">
			<div class="columns">
				<!-- Main Chat Area -->
				<div class="column is-three-quarters main-panel">
					<!-- If no chat history, show input at the top -->
					<div v-if="chatHistory.length === 0" class="mb-4">
						<UserInput @input-active-change="handleInputActiveChange" />
					</div>
					
					<!-- Chat history box only shown when there are messages -->
					<div v-if="chatHistory.length > 0" class="mb-4">
						<ChatHistory @feedback-workflow-complete="onFeedbackWorkflowComplete" />
					</div>
					
					
					<!-- Show input at the bottom when response is complete AND feedback workflow is complete -->
					<div v-if="chatHistory.length > 0 && shouldShowNewQuestionInput" class="mb-4">
						<UserInput @input-active-change="handleInputActiveChange" />
					</div>
				</div>
				<div class="column is-one-quarter sidebar-panel">
					<div class="mb-4">
						<TelemetryToggle />
					</div>
					<div class="mb-4">
						<TestTargetBox />
					</div>
					<div class="export-btn-container">
						<ExportButton />
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import ChatHistory from './ChatHistory.vue'
import UserInput from './UserInput.vue'
import TelemetryToggle from './TelemetryToggle.vue'
import TestTargetBox from './TestTargetBox.vue'
import ExportButton from './ExportButton.vue'
import { storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import { useSessionStore } from '@/stores/session'

const sessionStore = useSessionStore()
const { 
	chatHistory, 
	isResponseComplete,
	qaId 
} = storeToRefs(sessionStore)

// Track feedback workflow completion for current QA ID
const feedbackWorkflowComplete = ref(false)

// Computed property to check if feedback has been submitted for the current response
const feedbackSubmitted = computed(() => {
	if (chatHistory.value.length === 0) return false
	const lastMessage = chatHistory.value[chatHistory.value.length - 1]
	if (lastMessage.role === 'assistant' && lastMessage.message_id) {
		return sessionStore.hasFeedbackBeenSubmitted(lastMessage.message_id)
	}
	return false
});

// Computed property to determine when to show new question input
const shouldShowNewQuestionInput = computed(() => {
	// For responses that need feedback: show input only after feedback workflow is complete
	if (hasAssistantResponseWithCitations.value) {
		return isResponseComplete.value && (feedbackWorkflowComplete.value || feedbackSubmitted.value)
	}
	// For responses without citations (clarifications, etc.): show immediately when complete
	return isResponseComplete.value
})

// Check if the latest assistant response has citations (requires feedback)
const hasAssistantResponseWithCitations = computed(() => {
	if (chatHistory.value.length === 0) return false
	const lastMessage = chatHistory.value[chatHistory.value.length - 1]
	return lastMessage.role === 'assistant' && 
		   lastMessage.citations && 
		   lastMessage.citations.length > 0 && 
		   !lastMessage.is_clarification
})

// Track if user is actively typing in the input field
const userInputActive = ref(false);

// Handle input active change from UserInput component
function handleInputActiveChange(isActive) {
	userInputActive.value = isActive;
}

// Handle feedback workflow completion
function onFeedbackWorkflowComplete(completedMessageId) {
	// Check if this is for the current/latest assistant response
	if (chatHistory.value.length === 0) return
	const lastMessage = chatHistory.value[chatHistory.value.length - 1]
	if (lastMessage.role === 'assistant' && lastMessage.message_id === completedMessageId) {
		feedbackWorkflowComplete.value = true
	}
}

// Watch for QA ID changes to reset feedback workflow state
watch(qaId, (newQaId) => {
	if (newQaId) {
		// Reset feedback workflow state for new QA
		feedbackWorkflowComplete.value = false
		// Check if feedback was already submitted for the latest response
		if (chatHistory.value.length > 0) {
			const lastMessage = chatHistory.value[chatHistory.value.length - 1]
			if (lastMessage.role === 'assistant' && lastMessage.message_id && 
				sessionStore.hasFeedbackBeenSubmitted(lastMessage.message_id)) {
				feedbackWorkflowComplete.value = true
			}
		}
	}
})



</script>

<style scoped>
.chat-container {
	padding: 1.5rem 0;
	min-height: calc(100vh - 52px); /* Subtract navbar height */
	position: relative;
	overflow: visible;
}

.box {
	background-color: white;
	border-radius: 6px;
	box-shadow: 0 2px 3px rgba(10, 10, 10, 0.1);
	padding: 1.5rem;
}

/* Move border and background to the entire right column */
.sidebar-panel {
	background-color: transparent;
	border-radius: 6px;
	padding: 1.5rem 1rem;
	display: flex;
	flex-direction: column;
	gap: 1.5rem;
	min-height: 100%;
	margin-left: 2rem;
}

.main-panel {
	background-color: transparent;
	border-radius: 6px;
	padding: 1.5rem 1rem;
	display: flex;
	flex-direction: column;
	gap: 1.5rem;
	min-height: 100%;
	position: relative;
	overflow: visible;
	z-index: 2;
}

.main-panel > .mb-4 {
	margin-bottom: 1.5rem;
}

.sidebar-panel > .mb-4:first-child {
	margin-bottom: 0;
}

.mb-4 {
	margin-bottom: 1.5rem;
}

.mt-4 {
	margin-top: 1.5rem;
}

.buttons {
	display: flex;
	gap: 0.5rem;
}

.export-btn-container {
	margin-top: 0;
}
.export-btn-container button,
.export-btn-container .button {
	width: 100%;
}

/* Ensure columns have proper spacing */
.columns {
	margin: 0;
}

.column {
	padding: 0.75rem;
}

</style>