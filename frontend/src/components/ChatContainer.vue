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
						<ChatHistory />
					</div>
					
					<!-- Show input at the bottom when response is complete -->
					<div v-if="chatHistory.length > 0 && (isResponseComplete || feedbackSubmitted)" class="mb-4">
						<UserInput @input-active-change="handleInputActiveChange" />
					</div>
				</div>
				<div class="column is-one-quarter sidebar-panel">
					<!-- Feedback component with simplified visibility logic -->
					<div v-if="shouldShowFeedback" class="mb-4">
						<FeedbackBox 
							@feedback-submitted="handleFeedbackSubmitted"
						/>
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
import FeedbackBox from './FeedbackBox.vue'
import TestTargetBox from './TestTargetBox.vue'
import ExportButton from './ExportButton.vue'
import { storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import { useSessionStore } from '@/stores/session'

const sessionStore = useSessionStore()
const { 
	chatHistory, 
	isResponseComplete, 
	isNewQuestionAsked,
	qaId 
} = storeToRefs(sessionStore)

// Simplified computed property to determine if feedback box should be shown
const shouldShowFeedback = computed(() => {
	// Only show feedback when we have a valid QA ID, the response is complete, 
	// no new question has been asked, and feedback hasn't been submitted yet
	return qaId.value && 
		isResponseComplete.value && 
		!isNewQuestionAsked.value && 
		!sessionStore.hasFeedbackBeenSubmitted(qaId.value);
});

// Computed property to check if feedback has been submitted
const feedbackSubmitted = computed(() => {
	return qaId.value ? sessionStore.hasFeedbackBeenSubmitted(qaId.value) : false;
});

// Track if user is actively typing in the input field
const userInputActive = ref(false);

// Handle input active change from UserInput component
function handleInputActiveChange(isActive) {
	userInputActive.value = isActive;
}

// Keep these computed properties for other components that might need them
const lastAssistantAnswer = computed(() => {
	// Find the last assistant message
	const last = [...chatHistory.value].reverse().find(m => m.role === 'assistant')
	return last ? last.content : ''
})

const lastAssistantCitations = computed(() => {
	// Find the last assistant message and get its citations
	const last = [...chatHistory.value].reverse().find(m => m.role === 'assistant')
	return last && last.citations ? last.citations : []
})

// Handle feedback submission
const handleFeedbackSubmit = () => {
	// Any additional handling after feedback is submitted can go here
}

function handleFeedbackSubmitted() {
	if (qaId.value) {
		sessionStore.markFeedbackSubmitted(qaId.value)
	}
}

// At the top of your component setup function
watch(() => sessionStore.corpusFilter, (newFilter, oldFilter) => {
	// Removed excessive logging
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