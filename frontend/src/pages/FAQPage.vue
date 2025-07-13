<template>
  <section class="section">
    <div class="container">
      <h1 class="title faq-title-black">FAQ</h1>
      
      <div class="faq-list">
        <div 
          v-for="(faq, index) in faqs" 
          :key="index" 
          class="faq-item"
        >
          <button 
            class="faq-question" 
            :class="{ 'open': openItems[index] }"
            @click="toggleItem(index)"
          >
            <span>{{ faq.question }}</span>
            <span class="faq-toggle">{{ openItems[index] ? '−' : '+' }}</span>
          </button>
          <div v-if="openItems[index]" class="faq-answer">
            <div v-html="faq.answer"></div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue';

const faqs = [
  {
    question: "What is ATLAS and what is its purpose?",
    answer: `
      <p>
        ATLAS (Analysis and Testing of Language Models for Archival Systems) is a research platform designed to explore how large language models and AI can enhance historical research using parliamentary archives.
      </p>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Core Purpose</h4>

      <ul style="color: black;">
        <li style="color: black;"><strong style="color: black;">Research Tool:</strong> <span style="color: black;">Providing humanities and social science researchers with AI-assisted access to historical parliamentary records</span></li>
        <li style="color: black;"><strong style="color: black;">Educational Framework:</strong> <span style="color: black;">Helping researchers understand the nature of LLM technology and AI product development through direct experience</span></li>
        <li style="color: black;"><strong style="color: black;">Experimental Platform:</strong> <span style="color: black;">Creating a controlled environment to evaluate different AI approaches to historical text analysis</span></li>
        <li style="color: black;"><strong style="color: black;">Methodological Investigation:</strong> <span style="color: black;">Studying how researchers interact with AI systems when conducting historical research</span></li>
        <li style="color: black;"><strong style="color: black;">Technical Framework:</strong> <span style="color: black;">Developing best practices for Retrieval Augmented Generation (RAG) systems in humanities computing</span></li>
        <li style="color: black;"><strong style="color: black;">Open Source Continuation:</strong> <span style="color: black;">Exploring the feasibility of continuing traditions of open source software development enjoyed by previous generations of digital humanities researchers</span></li>
      </ul>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Key Features</h4>
      <ul style="color: black;">
        <li style="color: black;"><strong style="color: black;">Historical Document Access:</strong> <span style="color: black;">Vector search across parliamentary Hansard records from the UK, New Zealand, and Australia from 1901 onward</span></li>
        <li style="color: black;"><strong style="color: black;">Specialized Embeddings:</strong> <span style="color: black;">Using historical language models trained on 19th-century text to better capture period-specific language</span></li>
        <li style="color: black;"><strong style="color: black;">Configurable Architecture:</strong> <span style="color: black;">Test Target system allowing controlled experiments with different models and retrieval settings</span></li>
        <li style="color: black;"><strong style="color: black;">Integrated Analysis:</strong> <span style="color: black;">Comprehensive telemetry and user feedback collection for continuous improvement</span></li>
      </ul>
    `
  },
  {
    question: "What is Retrieval Augmented Generation (RAG)?",
    answer: `
      <p>
        Retrieval Augmented Generation (RAG) is a hybrid AI architecture that combines the knowledge retrieval capabilities of search systems with the reasoning and language generation abilities of large language models (LLMs):
      </p>
      <ul>
        <li><strong>Core Process:</strong> RAG retrieves relevant information from a knowledge base, then passes this information as context to an LLM to generate more accurate and grounded responses</li>
        <li><strong>Vector-Based Retrieval:</strong> Documents are converted into vector embeddings that capture their semantic meaning, allowing for similarity-based search</li>
        <li><strong>Context Enhancement:</strong> The retrieved documents provide the LLM with specific knowledge it may not have learned during its training</li>
      </ul>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Cost and Compute Savings</h4>
      <p>
        RAG offers significant advantages over alternative approaches:
      </p>
      <ul>
        <li><strong>Reduced Model Size:</strong> Using external knowledge allows smaller, more efficient LLMs to achieve similar performance to much larger models</li>
        <li><strong>Lower Inference Costs:</strong> Compared to fully fine-tuned models, RAG systems can be 10-100x less expensive to run at scale</li>
        <li><strong>Minimal Training Requirements:</strong> Unlike full fine-tuning, RAG doesn't require retraining the LLM, only indexing the documents</li>
        <li><strong>Dynamic Knowledge:</strong> Adding new information only requires updating the knowledge base, not retraining the entire model</li>
        <li><strong>Efficient Infrastructure:</strong> Vector search is computationally inexpensive compared to running larger language models or processing full text</li>
      </ul>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Limitations and Challenges</h4>
      <p>
        Despite its benefits, RAG has several important limitations:
      </p>
      <ul>
        <li><strong>Context Window Constraints:</strong> The amount of retrieved information that can be used is limited by the LLM's context window</li>
        <li><strong>Retrieval Quality Dependency:</strong> The system is only as good as its retrieval component; if relevant information isn't retrieved, the LLM cannot use it</li>
        <li><strong>Hallucination Risk:</strong> LLMs may still generate fabricated information when the retrieved context is insufficient or ambiguous</li>
        <li><strong>Reasoning Bottlenecks:</strong> Complex multi-hop reasoning across documents remains challenging for current RAG implementations</li>
        <li><strong>Embedding Limitations:</strong> The quality of vector embeddings affects retrieval performance, and topic drift can occur as concepts evolve over time</li>
        <li><strong>Context Integration:</strong> LLMs sometimes struggle to effectively synthesize information from multiple retrieved documents with conflicting data</li>
      </ul>
      
      <p>
        ATLAS uses RAG as its core architecture, allowing it to generate historically grounded responses by retrieving and citing relevant parliamentary records while maintaining relatively modest computational requirements compared to full-text search or entirely LLM-based approaches.
      </p>
    `
  },
  {
    question: "How does ATLAS manage data privacy?",
    answer: `
      <p>
        ATLAS is designed with privacy considerations at its core, using a stateless architecture that minimizes data retention:
      </p>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Authentication System</h4>
      <ul>
        <li><strong>AWS Cognito Integration:</strong> ATLAS uses AWS Cognito for secure authentication, which handles user credentials without exposing them to the application</li>
        <li><strong>No Stored Login Data:</strong> User login information is validated through Cognito but not stored persistently in ATLAS systems</li>
        <li><strong>Session-Based Access:</strong> Authentication generates temporary session tokens rather than storing persistent user identifiers</li>
      </ul>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Telemetry and Analytics</h4>
      <ul>
        <li><strong>Anonymous Usage Data:</strong> Interaction telemetry is collected without personally identifiable information</li>
        <li><strong>Arize Phoenix Integration:</strong> Data is sent to Arize Phoenix for monitoring system performance, not user behavior</li>
        <li><strong>Observation Identifiers:</strong> Random identifiers are generated for each session without being linked to user accounts</li>
        <li><strong>Limited Retention:</strong> Only minimal data necessary for system improvement is retained</li>
      </ul>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Stateless Architecture</h4>
      <ul>
        <li><strong>No Chat History Storage:</strong> Conversations exist only within the current session and are not persisted after the session ends</li>
        <li><strong>Ephemeral Processing:</strong> Queries and results are processed in memory and not written to permanent storage</li>
        <li><strong>Cache Expiration:</strong> Any temporary caching of responses uses short expiration times</li>
        <li><strong>No User Profiles:</strong> The system does not build or maintain profiles of users or their query patterns</li>
      </ul>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Limitations and Considerations</h4>
      <p>
        While ATLAS prioritizes privacy, users should be aware of certain limitations:
      </p>
      <ul>
        <li><strong>Small User Base:</strong> The limited number of users means that complete anonymization is challenging—specific query patterns could potentially be identifiable in a small group</li>
        <li><strong>Research Context:</strong> As a research platform, some aggregated data about system performance and query types is necessary for research publications</li>
        <li><strong>Third-Party Dependencies:</strong> The system relies on external services (AWS, Arize) that have their own privacy policies and data handling practices</li>
        <li><strong>Administrative Access:</strong> System administrators may have access to logs for troubleshooting purposes, though these are kept to a minimum</li>
      </ul>
      
      <p>
        This privacy-centric approach aligns with ATLAS's research goals while respecting user confidentiality—allowing researchers to interact with historical parliamentary materials without concerns about persistent tracking or data retention.
      </p>
    `
  },
  {
    question: "Why do some questions seem ineffective while others produce high quality results?",
    answer: `
      <p>
        This is probably the biggest limitation of the current LLM RAG (Retrieval Augmented Generation) architecture, which uses HNSW vector search for document retrieval and LLM inferencing for question answering.
      </p>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">The Core Issue</h4>
      <p>
        There's a disconnect between what the LLM understands semantically and what the HNSW search system can find. For example:
      </p>
      <br>
      <ul>
        <li><strong>Query that might produce poor results:</strong> "What parliamentary discussions addressed Aboriginal affairs in 1901?" → No or few results found</li>
        <li><strong>Query that is more liklely to succeed:</strong> "Describe the debates related to Maori and the Treaty of Waitangi in New Zealand" → Rich, detailed results</li>
      </ul>
      <br>
      <p>
        Both queries ask about Indigenous peoples, but the search system performs literal matching rather than leveraging the LLM's semantic understanding that these are related topics. Depending on the specific terms used, the search may fail to retrieve relevant documents, leading to poor or no results. This is similar to the problem of 'prompt engineering', where the way a question is phrased can significantly impact the quality of the answer when quering LLMs, but is compounded by the fact that the LLM cannot communicate back to the search system to suggest alternative terms.
      </p>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Why This Happens</h4>
      <ul>
        <li><strong>Historical Terminology:</strong> Documents use period-specific language that may not match modern search terms</li>
        <li><strong>One-Way Communication:</strong> The LLM cannot communicate back to the search system to suggest alternative terms</li>
        <li><strong>Lexical vs Semantic Search:</strong> The current system relies more on exact word matching than conceptual understanding</li>
      </ul>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Current Status & Roadmap</h4>
      <p>
        While this isn't a major issue for the current phase of the project (which focuses on developing our understanding of testing and evaluation), it is on our roadmap for future improvement. We're tracking this issue and potential solutions on <a href="https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/35" target="_blank" rel="noopener noreferrer">GitHub #35</a>.
      </p>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Tips for Better Results</h4>
      <ul>
        <li><strong>Try historical terminology:</strong> "Aboriginal affairs" → "Native affairs" or "Māori"</li>
        <li><strong>Be specific about countries:</strong> "Australian Parliament" or "New Zealand Parliament"</li>
        <li><strong>Use multiple approaches:</strong> If one query fails, try rephrasing with different terms</li>
        <li><strong>Browse different time periods:</strong> Terminology evolved over time</li>
      </ul>
    `
  },
  {
    question: "How do multi-turn conversations work in ATLAS?",
    answer: `
      <p>
        In ATLAS, each new question in a multi-turn conversation:
      </p>
      <ul>
        <li><strong>Gets Fresh Context:</strong> The system retrieves new document context for each query independently, rather than reusing context from previous turns. This is standard RAG behavior that prioritizes accuracy for each question.</li>
        <li><strong>Maintains Conversation History:</strong> While document context is refreshed, the chat history (previous Q&A pairs) is preserved and sent to the LLM with each new query, allowing it to understand the conversation flow.</li>
      </ul>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Relationship Between Multi-turn Answers, Context, and Citations</h4>
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
    `
  },
  {
    question: "What data sources does ATLAS use?",
    answer: `
      <p>
        ATLAS provides access to parliamentary records from three countries:
      </p>
      <ul>
        <li><strong>United Kingdom:</strong> Hansard parliamentary records from 1901 onward</li>
        <li><strong>New Zealand:</strong> Parliamentary debates from 1901 onward</li>
        <li><strong>Australia:</strong> Federal parliamentary records from 1901 onward</li>
      </ul>
      <p>
        These records have been processed into vector embeddings to enable semantic search. The system automatically identifies which corpus (UK, NZ, or Australia) a document belongs to, allowing for targeted searches across specific parliamentary archives or all available sources.
      </p>
    `
  },
  {
    question: "How does the corpus filter work?",
    answer: `
      <p>
        The corpus filter allows you to limit your search to a specific parliamentary archive:
      </p>
      <ul>
        <li><strong>All Sources:</strong> Searches across all available parliamentary records</li>
        <li><strong>United Kingdom:</strong> Limits search to UK Hansard records only</li>
        <li><strong>New Zealand:</strong> Limits search to NZ parliamentary debates only</li>
        <li><strong>Australia:</strong> Limits search to Australian federal parliamentary records only</li>
      </ul>
      <p>
        The corpus filter is applied at the Redis query level using metadata filtering. The system will only show the corpus selector if:
      </p>
      <ol>
        <li>The backend is configured to support corpus filtering (via the <code>SUPPORTS_CORPUS_FILTERING</code> flag)</li>
        <li>Multiple corpus options are available in the vector store</li>
      </ol>
      <p>
        If corpus filtering is not supported, the UI will automatically hide the selector and search across all available sources.
      </p>

      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Document Counts and Semantic Similarity</h4>
      <p>
        When using corpus filters, you may notice differences in the number of documents retrieved:
      </p>
      <ul>
        <li><strong>Unfiltered Searches:</strong> Will return the maximum number of documents (e.g., 40) from across all corpora, showing the most semantically similar matches regardless of source</li>
        <li><strong>Filtered Searches:</strong> May return fewer documents because the system maintains the same semantic similarity threshold within each corpus</li>
        <li><strong>Quality Over Quantity:</strong> The system prioritizes semantic relevance over reaching the maximum document count, ensuring that only truly relevant documents are included</li>
      </ul>
      <p>
        This behavior ensures that your search results maintain high quality and relevance, even when filtering to specific parliamentary archives.
      </p>
    `
  },
  {
    question: "What is HNSW search and how does it relate to the LLM output?",
    answer: `
      <p>
        HNSW (Hierarchical Navigable Small World) is an advanced vector search algorithm used in ATLAS's retrieval system:
      </p>
      <ul>
        <li><strong>Algorithm Purpose:</strong> HNSW creates a multi-layered graph structure that enables extremely fast approximate nearest neighbor searches in high-dimensional vector spaces</li>
        <li><strong>Speed vs. Accuracy:</strong> It offers an optimal balance between search speed (logarithmic time complexity) and accuracy, making it ideal for real-time RAG systems</li>
        <li><strong>Redis Implementation:</strong> ATLAS uses Chroma as the vector database with HNSW as the primary search algorithm (configured as "ALGORITHM=FLAT" or "ALGORITHM=HNSW")</li>
      </ul>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">How Search Parameters Affect LLM Output</h4>
      <p>
        ATLAS's Test Target configuration controls multiple search parameters that directly impact LLM output quality:
      </p>
      <ul>
        <li><strong>Search K Value:</strong> A configurable parameter that determines how many documents are retrieved from the vector store. Higher values can significantly improve recall, especially for smaller corpora, but must be balanced against potential noise. This value can be adjusted in the Test Target configuration to optimize for different use cases</li>
        <li><strong>Score Threshold:</strong> Sets a minimum similarity score for retrieved documents, ensuring only relevant context is used</li>
        <li><strong>Large Retrieval Size:</strong> For initial retrieval before re-ranking, typically 200+ documents to ensure good candidates are considered</li>
        <li><strong>Citation Limit:</strong> Caps the number of citations shown to users, typically 10-15 sources for readability</li>
      </ul>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Document Enhancement Pipeline</h4>
      <p>
        After initial retrieval, ATLAS applies several enhancements:
      </p>
      <ol>
        <li>Retrieves a large initial set (e.g., 200 documents) using vector similarity</li>
        <li>Applies lightweight re-ranking to prioritize documents with direct term matches</li>
        <li>Filters the best documents (based on citation limit) to send to the LLM</li>
        <li>Formats documents with metadata for the LLM to use as context</li>
      </ol>
      <p>
        This pipeline ensures that the LLM receives the most relevant and diverse set of documents while maintaining reasonable computational costs.
      </p>
    `
  },
  {
    question: "How does fine-tuning improve search quality?",
    answer: `
      <p>
        ATLAS uses fine-tuned embeddings to improve search quality for historical parliamentary records:
      </p>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Fine-tuning Process</h4>
      <ul>
        <li><strong>Base Model:</strong> Starts with a BERT model pre-trained on general text</li>
        <li><strong>Domain Adaptation:</strong> Fine-tunes the model on parliamentary records to better understand historical language and context</li>
        <li><strong>Two-Epoch Training:</strong> Uses a two-epoch fine-tuning process to balance between general language understanding and domain-specific knowledge</li>
      </ul>

      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Vector Store and Model Files</h4>
      <ul>
        <li><strong>Default Vector Store:</strong> The repository includes a pre-generated vector store with fine-tuned embeddings</li>
        <li><strong>Model Files:</strong> The fine-tuned model files are stored in the models directory and are required for optimal search performance</li>
        <li><strong>Fallback Option:</strong> If the fine-tuned model files are not available, the system will use mean pooling as a fallback strategy</li>
      </ul>

      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Benefits of Fine-tuning</h4>
      <ul>
        <li><strong>Better Semantic Understanding:</strong> Improved ability to understand historical language</li>
        <li><strong>Enhanced Recall:</strong> Better at finding relevant documents, especially for complex or historical queries</li>
        <li><strong>Consistent Performance:</strong> More reliable search results across different types of parliamentary records</li>
      </ul>
    `
  },
  {
    question: "How can I get the best search results?",
    answer: `
      <p>
        To get the most relevant and comprehensive search results in ATLAS:
      </p>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Query Formulation</h4>
      <ul>
        <li><strong>Be Specific:</strong> Use clear, focused queries that target specific aspects of parliamentary debates</li>
        <li><strong>Use Historical Context:</strong> Include relevant time periods or historical events in your queries</li>
        <li><strong>Consider Terminology:</strong> Use period-appropriate language when possible, as the system is fine-tuned on historical text</li>
      </ul>

      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Using Corpus Filters</h4>
      <ul>
        <li><strong>Start Broad:</strong> Begin with unfiltered searches to get a comprehensive view across all sources</li>
        <li><strong>Filter Strategically:</strong> Use corpus filters to focus on specific parliamentary records when needed</li>
        <li><strong>Understand Results:</strong> Remember that filtered searches may return fewer documents while maintaining high relevance</li>
      </ul>

      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Interpreting Results</h4>
      <ul>
        <li><strong>Check Citations:</strong> Review the provided citations to verify the source and context of information</li>
        <li><strong>Consider Time Period:</strong> Note the dates of retrieved documents to understand historical context</li>
        <li><strong>Look for Patterns:</strong> Identify common themes or recurring issues across multiple documents</li>
      </ul>

      <p>
        Remember that ATLAS is designed to provide historically grounded responses. The system prioritizes accuracy and relevance over quantity of results, ensuring that you get the most meaningful information for your research.
      </p>
    `
  },
  {
    question: "How do citations work in ATLAS?",
    answer: `
      <p>
        Citations in ATLAS provide transparency about the sources used to generate answers:
      </p>
      <ul>
        <li><strong>Source Retrieval:</strong> When you ask a question, ATLAS retrieves the most relevant documents from the vector store based on semantic similarity</li>
        <li><strong>Context Integration:</strong> These documents are sent as context to the large language model along with your question</li>
        <li><strong>Automatic Citation:</strong> The system displays citations for the sources that informed the answer</li>
        <li><strong>Citation Preview:</strong> You can hover over citation numbers to see a preview of the source content</li>
        <li><strong>Full Content Access:</strong> Clicking a citation opens a modal with the complete source text and metadata</li>
      </ul>
      <p>
        By default, ATLAS shows up to 10 citations per answer, prioritizing the most relevant sources. The exact number is configurable through the target configuration.
      </p>
    `
  },
  {
    question: "What is the feedback system for?",
    answer: `
      <p>
        The feedback system in ATLAS serves multiple important purposes:
      </p>
      <ul>
        <li><strong>Research Value:</strong> Collecting user assessments of answer quality to study how scholars evaluate AI-generated historical analysis</li>
        <li><strong>System Improvement:</strong> Identifying patterns in low-rated answers to improve retrieval and prompting strategies</li>
        <li><strong>Model Comparison:</strong> Gathering comparative data between different LLM configurations and settings</li>
        <li><strong>Educational Tool:</strong> Helping users reflect on the strengths and limitations of AI assistance in historical research</li>
      </ul>
      <p>
        After each answer, you can rate its quality and provide optional written feedback. This data is anonymized and used purely for research and system improvement purposes.
      </p>
    `
  },
  {
    question: "How do embeddings and pooling work in ATLAS?",
    answer: `
      <p>
        ATLAS uses word embeddings and pooling techniques to convert text into numerical vectors that capture semantic meaning:
      </p>
      
      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Word Embeddings</h4>
      <ul>
        <li><strong>Living with Machines Model:</strong> ATLAS defaults to using a BERT model pre-trained on 19th-century text, providing a strong foundation for historical language understanding. You can use a different model by changing the <code>EMBEDDING_MODEL</code> in the Test Target configuration.</li>
        <li><strong>Vector Representation:</strong> Each word or token is converted into a high-dimensional vector that captures its meaning and relationships with other words</li>
        <li><strong>Contextual Understanding:</strong> The model considers the surrounding words to generate context-aware embeddings</li>
      </ul>

      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Pooling Strategies</h4>
      <ul>
        <li><strong>Mean Pooling:</strong> The default strategy that averages all word embeddings in a document to create a single document vector</li>
        <li><strong>Fine-tuned Pooling:</strong> An enhanced approach where the model is fine-tuned on parliamentary records to better capture domain-specific language patterns</li>
        <li><strong>Fallback Mechanism:</strong> If fine-tuned model files aren't available, the system automatically uses mean pooling</li>
      </ul>

      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Role in RAG Chain</h4>
      <ul>
        <li><strong>Document Indexing:</strong> All parliamentary records are converted into embeddings and stored in the vector database</li>
        <li><strong>Query Processing:</strong> User queries are converted into embeddings using the same model</li>
        <li><strong>Semantic Search:</strong> The system finds documents with similar embeddings to the query</li>
        <li><strong>Context Retrieval:</strong> The most semantically similar documents are retrieved and passed to the LLM</li>
      </ul>

      <h4 style="color: black; font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 1.2rem;">Fine-tuning Benefits</h4>
      <ul>
        <li><strong>Historical Language:</strong> Better understanding of historical terminology</li>
        <li><strong>Domain Adaptation:</strong> Improved ability to capture the specific context of parliamentary debates</li>
        <li><strong>Enhanced Retrieval:</strong> More accurate matching of queries to relevant historical documents</li>
      </ul>

      <p>
        The combination of historical language models, effective pooling strategies, and fine-tuning creates a robust foundation for semantic search in ATLAS, enabling accurate retrieval of relevant parliamentary records.
      </p>
    `
  }
];

// Initialize all items as closed
const openItems = ref(faqs.map(() => false));

// Toggle function to open/close FAQ items
const toggleItem = (index) => {
  openItems.value[index] = !openItems.value[index];
};
</script>

<style scoped>
.title, .faq-title-black {
  color: black !important;
}

.faq-list {
  margin-top: 2rem;
}

.faq-item {
  margin-bottom: 1rem;
  background: white;
  border-radius: 0.5rem;
  border: 1px solid #e0e0e0;
  overflow: hidden;
}

.faq-question {
  width: 100%;
  padding: 1.5rem;
  background: white !important;
  border: none;
  color: black !important;
  font-size: 1.25rem;
  font-weight: 600;
  text-align: left;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: background-color 0.2s;
}

.faq-question:hover {
  background: rgba(0, 0, 0, 0.05);
}


.faq-question.open {
  background: white;
  border-bottom: 1px solid #cbd5e1;
}

.faq-toggle {
  font-size: 1.5rem;
  color: black;
  transition: transform 0.2s;
}

.faq-answer {
  padding: 1.5rem;
  color: black !important;
  background-color: white;
}

.faq-answer * {
  color: black !important;
}

.faq-answer h4 {
  color: black !important;
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-size: 1.25rem;
  font-weight: 600;
}

.faq-answer p {
  margin-bottom: 1rem;
}

.faq-answer ul, .faq-answer ol {
  margin-bottom: 1rem;
  padding-left: 1.5rem;
}

.faq-answer li {
  margin-bottom: 0.5rem;
}

.faq-answer strong {
  color: black !important;
  font-weight: bold;
}

.faq-answer code {
  background-color: #f8f8f8;
  padding: 0.2rem 0.4rem;
  border-radius: 0.25rem;
  font-family: monospace;
  font-size: 0.9em;
  color: black;
}
</style> 