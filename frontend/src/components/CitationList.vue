<template>
	<div v-if="displayedCitations.length">
	  <h5 class="title is-6">Citations</h5>
	  <ul>
		<li v-for="(c, idx) in displayedCitations" :key="idx" style="margin-bottom: 0.5em;">
		  <span
			class="has-tooltip-arrow"
			:title="c.tooltip || c.quote"
		  >
			<a v-if="c.url" :href="c.url" target="_blank">[{{ idx + 1 }}]</a>
			<span v-else>[{{ idx + 1 }}]</span>
		  </span>
		  <span style="margin-left: 0.5em;">{{ c.text || c.quote }}</span>
		</li>
	  </ul>
	  <div v-if="displayedCitations.length > 3">
		<a @click="showAll = true" style="cursor:pointer;">
		  See all {{ displayedCitations.length }} citations
		</a>
	  </div>
	  <div v-if="showAll" class="modal is-active">
		<div class="modal-background" @click="showAll = false"></div>
		<div class="modal-content">
		  <div class="box">
			<h5 class="title is-6">All Citations</h5>
			<ul>
			  <li v-for="(c, idx) in displayedCitations" :key="idx">
				<a v-if="c.url" :href="c.url" target="_blank">[{{ idx + 1 }}] {{ c.text || c.quote }}</a>
				<span v-else>[{{ idx + 1 }}] {{ c.text || c.quote }}</span>
				<div v-if="c.meta || c.source_id"><small>{{ c.meta || c.source_id }}</small></div>
				<div v-if="c.full_content" style="white-space: pre-wrap; font-size: 0.95em;">
				  {{ c.full_content }}
				</div>
				<hr>
			  </li>
			</ul>
			<button class="button" @click="showAll = false">Close</button>
		  </div>
		</div>
	  </div>
	</div>
  </template>
  
  <script setup>
  import { ref, computed } from 'vue'
  const props = defineProps({
	answer: { type: String, required: false },
	citations: { type: Array, required: false, default: () => [] }
  })
  const showAll = ref(false)
  
  // If we have structured citations, use those directly
  // Otherwise, parse citations from text
  const displayedCitations = computed(() => {
	// If structured citations are provided, use them
	if (props.citations && props.citations.length > 0) {
	  return props.citations.map((citation, index) => ({
		number: index + 1,
		text: citation.quote || citation.text,
		url: citation.url,
		meta: citation.source_id || citation.meta,
		tooltip: citation.quote || citation.text,
		full_content: citation.full_content
	  }));
	}
	
	// Otherwise, fall back to parsing from text
	if (!props.answer) return [];
	
	// Split answer into main answer and citation lines
	const citationRegex = /^\[(\d+)\]\s*(.*)$/;
	const lines = props.answer.split('\n');
	
	return lines
	  .map(line => {
		const match = line.match(citationRegex);
		if (match) {
		  // Try to extract metadata (URL, etc.) from the text if present
		  const number = match[1];
		  const text = match[2];
		  // Simple URL extraction (optional, can be improved)
		  const urlMatch = text.match(/https?:\/\/\S+/);
		  const url = urlMatch ? urlMatch[0] : null;
		  // Tooltip/meta extraction (optional, can be improved)
		  const meta = text.replace(url || '', '').trim();
		  return {
			number,
			text,
			url,
			meta,
			tooltip: meta,
			full_content: null // Could be filled if you parse more
		  };
		}
		return null;
	  })
	  .filter(Boolean);
  });
  </script>