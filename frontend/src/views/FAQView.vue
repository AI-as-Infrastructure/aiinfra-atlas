<template>
  <div class="faq-page-container">
    <div class="faq-container">
      <section class="about-section">
        <h2>Frequently Asked Questions</h2>
      </section>
      
      <FAQItem question="What is ATLAS and what is its purpose?">
        <div>
          <p>
            ATLAS (Analysis and Testing of Language Models for Archival Systems) is a research platform designed to explore how large language models and AI can enhance historical research using parliamentary archives.
          </p>
          
          <h4>Core Purpose</h4>
          <p>
            ATLAS serves several interconnected research goals:
          </p>
          <ul>
            <li><strong>Research Tool:</strong> Providing humanities and social science researchers with AI-assisted access to historical parliamentary records</li>
            <li><strong>Educational Framework:</strong> Helping researchers understand the nature of LLM technology and AI product development through direct experience</li>
            <li><strong>Experimental Platform:</strong> Creating a controlled environment to evaluate different AI approaches to historical text analysis</li>
            <li><strong>Methodological Investigation:</strong> Studying how researchers interact with AI systems when conducting historical research</li>
            <li><strong>Technical Framework:</strong> Developing best practices for Retrieval Augmented Generation (RAG) systems in humanities computing</li>
            <li><strong>Open Source Continuation:</strong> Exploring the feasibility of continuing traditions of open source software development enjoyed by previous generations of digital humanities researchers</li>
          </ul>
          
          <h4>Key Features</h4>
          <ul>
            <li><strong>Historical Document Access:</strong> Vector search across parliamentary Hansard records from the UK, New Zealand, and Australia from 1901 onward</li>
            <li><strong>Specialized Embeddings:</strong> Using historical language models trained on 19th-century text to better capture period-specific language</li>
            <li><strong>Configurable Architecture:</strong> Test Target system allowing controlled experiments with different models and retrieval settings</li>
            <li><strong>Integrated Analysis:</strong> Comprehensive telemetry and user feedback collection for continuous improvement</li>
          </ul>
        </div>
      </FAQItem>

      <FAQItem question="How do multi-turn conversations work in ATLAS?">
        <div>
          <p>
            In ATLAS, each new question in a multi-turn conversation:
          </p>
          <ul>
            <li><strong>Gets Fresh Context:</strong> The system retrieves new document context for each query independently, rather than reusing context from previous turns. This is standard RAG behavior that prioritizes accuracy for each question.</li>
            <li><strong>Maintains Conversation History:</strong> While document context is refreshed, the chat history (previous Q&A pairs) is preserved and sent to the LLM with each new query, allowing it to understand the conversation flow.</li>
          </ul>
          
          <h4>Relationship Between Multi-turn Answers, Context, and Citations</h4>
          <p>
            The relationship works like this:
          </p>
          <ul>
            <li><strong>Context Retrieval Per Question:</strong> Each new user question triggers a fresh vector search, retrieving documents relevant to the current question only.</li>
            <li><strong>Citations Follow Current Context:</strong> The citations shown to users directly reflect the documents retrieved for the current question, not previous questions.</li>
            <li><strong>LLM Creates Coherent Narrative:</strong> The LLM receives:
              <ul>
                <li>The current question</li>
                <li>The newly retrieved context</li>
                <li>The full conversation history</li>
              </ul>
            </li>
            <li><strong>Contextual Understanding:</strong> The LLM can refer to previous answers when forming responses, but its citations are limited to documents retrieved for the current question.</li>
          </ul>
        </div>
      </FAQItem>

      <FAQItem question="Why do some questions seem ineffective while others produce high quality results?">
        <div>
          <p>
            This is probably the biggest limitation of the current LLM RAG (Retrieval Augmented Generation) architecture, which uses HNSW vector search for document retrieval and LLM inferencing for question answering.
          </p>
          
          <h4>The Core Issue</h4>
          <p>
            There's a disconnect between what the LLM understands semantically and what the HNSW search system can find. For example:
          </p>
          <ul>
            <li><strong>Query that fails:</strong> "What parliamentary discussions addressed Aboriginal affairs in 1901?" → No results found</li>
            <li><strong>Query that succeeds:</strong> "Describe the debates related to Maori and the Treaty of Waitangi in New Zealand" → Rich, detailed results</li>
          </ul>
          <p>
            Both queries ask about Indigenous peoples, but the search system performs literal matching rather than leveraging the LLM's semantic understanding that these are related topics.
          </p>
          
          <h4>Why This Happens</h4>
          <ul>
            <li><strong>Historical Terminology:</strong> Documents use period-specific language that may not match modern search terms</li>
            <li><strong>One-Way Communication:</strong> The LLM cannot communicate back to the search system to suggest alternative terms</li>
            <li><strong>Lexical vs Semantic Search:</strong> The current system relies more on exact word matching than conceptual understanding</li>
          </ul>
          
          <h4>Current Status & Roadmap</h4>
          <p>
            While this isn't a major issue for the current phase of the project (which focuses on developing our understanding of testing and evaluation), it is on our roadmap for future improvement. We're tracking this issue and potential solutions on <a href="https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/35" target="_blank" rel="noopener noreferrer">GitHub #35</a>.
          </p>
          
          <h4>Tips for Better Results</h4>
          <ul>
            <li><strong>Try historical terminology:</strong> "Aboriginal affairs" → "Native affairs" or "Māori"</li>
            <li><strong>Be specific about countries:</strong> "Australian Parliament" or "New Zealand Parliament"</li>
            <li><strong>Use multiple approaches:</strong> If one query fails, try rephrasing with different terms</li>
            <li><strong>Browse different time periods:</strong> Terminology evolved over time</li>
          </ul>
        </div>
      </FAQItem>

      <!-- Add more FAQ items here -->
      
      <div class="faq-bottom-spacer"></div>
    </div>
  </div>
</template>

<script setup>
import FAQItem from '@/components/FAQ/FAQItem.vue'
</script>

<style scoped>
.faq-page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.faq-container {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.about-section {
  padding: 2rem;
  border-bottom: 1px solid #e2e8f0;
}

.about-section h2 {
  color: #1e293b;
  font-size: 1.875rem;
  font-weight: 600;
  margin: 0;
}

.faq-bottom-spacer {
  height: 2rem;
}
</style> 