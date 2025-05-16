// src/components/about/AboutPage.js
import React from 'react';
import Header from '../layout/Header';

const AboutPage = ({ onLogout, onRefresh, showSessionMessage }) => {
  return (
    <div className="container">
      <Header 
        title="ATLAS: Analysis and Testing of Language Models for Archival Systems"
        onLogout={onLogout}
        onRefresh={onRefresh}
        showSessionMessage={showSessionMessage}
        showAbout={false}
        isAboutPage={true}
      />
      <div className="about-page-layout">
        <div className="about-container">
          
          <section className="about-section">
            <h2>About</h2>
            <p>
              ATLAS (Analysis and Testing of Language Models for Archival Systems) is a test harness for the 
              evaluation of Large Language Model (LLM) Retrieval Augmented Generation (RAG) for Humanities & 
              Social Science (HASS) research. ATLAS is a deliverable of the 
              <a href="https://aiinfra.anu.edu.au" target="_blank" rel="noreferrer"> AI as Infrastructure (AIINFRA)</a> project.
            </p>
            <p>
              AIINFRA's primary goal is to develop an evaluation framework for LLM RAG systems designed for 
              historical research.
            </p>
          </section>
          
          <section className="about-section">
            <h2>Data Privacy</h2>
            <p>
              ATLAS is designed with privacy in mind. User authentication is implemented through AWS Cognito
              to protect user data. All chat sessions are associated with a unique session ID rather than 
              personally identifiable information.
            </p>
            <p>
              While feedback and metrics are collected to improve the system, they are anonymized and stored
              securely. No personally identifiable information is shared with third parties.
            </p>
          </section>
          
          <section className="about-section">
            <h2>Roadmap</h2>
            <p>
              Future development plans for ATLAS include:
            </p>
            <ul>
              <li>Enhanced model evaluation frameworks</li>
              <li>Support for additional language models</li>
              <li>More extensive citation analysis tools</li>
              <li>Improved feedback mechanisms</li>
              <li>Offline version with default test user</li>
            </ul>
          </section>
          
          <section className="about-section">
            <h2>Contact</h2>
            <p>
              For questions, feedback, or collaboration inquiries, please contact the <a href="mailto://james.smithies@anu.edu.au" target="_blank" rel="noreferrer">lead developer</a>.
            </p>
          </section>
        </div>
        <div className="about-sidebar">
          <div className="info-box">
            <h3>Version Information</h3>
            <p>ATLAS Version: 0.1.0</p>
            <p>Last Updated: March 2025</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AboutPage;