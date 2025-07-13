<template>
  <section class="section">
    <div class="container">
      <div class="about-container">
        <div class="about-content">
          <h1 class="title">About</h1>
          <p>
            ATLAS (Analysis and Testing of Language Models for Archival Systems) is a test harness for the 
            evaluation of Large Language Model (LLM) Retrieval Augmented Generation (RAG) for Humanities & 
            Social Science (HASS) research. ATLAS is a deliverable of the 
            <a href="https://aiinfra.anu.edu.au" target="_blank" rel="noreferrer"> AI as Infrastructure (AIINFRA)</a> project. AIINFRA's primary goal is to develop an evaluation framework for LLM RAG systems designed for 
            historical research. 
          </p> 
          <h1 class="title">Code</h1>
          <p>
            This code was developed with assistance from AI tools. It is available on <a href="https://github.com/AI-as-Infrastructure/aiinfra-atlas" target="_blank" rel="noreferrer">GitHub</a>. The code is made available under the <a href="https://mit-license.org/" target="_blank" rel="noreferrer">MIT License</a>.
          </p>
          <h1 class="title">ATLAS Hansard Data Sources</h1>
          <p>
            ATLAS is designed to process historical parliamentary debates (Hansard) from 1901 by default, although it can be updated to process other sources. These sources are freely available. They are included in the default ATLAS vector store but have different licensing terms. If you choose to access and use these data sources, either through the vector store supplied with ATLAS or independently, please respect their respective licensing terms.
          </p>
          <br>
          <div class="hansard-item">
            <strong>Australian Hansard</strong>: Available at the <a href="https://www.aph.gov.au/parliamentary_business/hansard/hansreps_2011" target="_blank" rel="noreferrer">Parliament of Australia</a> and <a href="https://www.historichansard.net/" target="_blank" rel="noreferrer">Historic Hansard</a>. They are licensed by the Parliament of Australia under a <a href="https://creativecommons.org/licenses/by-nc-nd/4.0/" target="_blank" rel="noreferrer">CC-BY-NC-ND license</a>. Specialist advice on their use to generate vector stores for the <a href="https://aiinfra.anu.edu.au" target="_blank" rel="noreferrer">AI as Infrastructure</a> project was obtained.
          </div>
          <br>
          <div class="hansard-item">
            <strong>Aotearoa New Zealand Hansard</strong>: Available at the <a href="https://babel.hathitrust.org/cgi/mb?a=listis;c=71329709" target="_blank" rel="noreferrer">HathiTrust Digital Library</a> and licensed as <a href="https://creativecommons.org/publicdomain/zero/1.0/" target="_blank" rel="noreferrer">CC0</a> (public domain). Code used to transcribe and clean the Google Books pdfs is available <a href="https://github.com/AI-as-Infrastructure/aiinfra-nzhansard-preparation" target="_blank" rel="noreferrer">here</a>.
          </div>
          <br>
          <div class="hansard-item">
            <strong>United Kingdom Hansard</strong>: Available at the <a href="https://api.parliament.uk/historic-hansard/index.html" target="_blank" rel="noreferrer">History of Parliament Project</a> under <a href="https://en.wikipedia.org/wiki/Parliamentary_copyright#Terms" target="_blank" rel="noreferrer">UK Parliamentary Copyright</a>.
          </div>

        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
// No script needed after removing version info
</script>

<style scoped>
.about-container {
  display: flex;
  justify-content: center;
}

.about-content {
  width: 75%; /* Same width as the previous is-three-quarters column */
  max-width: 800px;
}

.title {
  color: black;
  margin-top: 2rem;
  margin-bottom: 1rem;
}

.hansard-item {
  margin-left: 0;
  text-indent: 0;
  padding-left: 0;
}

.hansard-item strong {
  color: black;
  font-weight: bold;
}
</style>