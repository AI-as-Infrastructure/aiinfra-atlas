#!/usr/bin/env python3
"""
Enhanced Data Generators for ATLAS Load Testing
Optimized for 15 concurrent users with expanded question pool, random parameters, and cache-busting
"""

import random
import time
import uuid
from datetime import datetime, timedelta
from faker import Faker
from typing import List, Dict, Any, Optional

fake = Faker()

class EnhancedDataGenerator:
    """Enhanced data generator with cache-busting and expanded question diversity"""
    
    def __init__(self):
        # Expanded question pool with 100+ diverse questions
        self.base_questions = [
            # Federation and Constitution
            "What was discussed about the Australian Federation Act in 1901?",
            "How did Parliament debate the new Constitution in 1901?",
            "What concerns were raised about federation implementation in 1901?",
            "Can you find discussions about constitutional powers in 1901?",
            "What was the opposition's view on federation in 1901?",
            
            # Colonial Governance
            "Can you provide details about colonial governance reforms in 1901?",
            "How did MPs address colonial administration changes in 1901?",
            "What debates occurred about colonial representation in 1901?",
            "How was the transition from colonial to federal government discussed?",
            "What concerns were raised about colonial autonomy in 1901?",
            
            # Immigration and Race Policy
            "What debates occurred regarding the White Australia Policy in 1901?",
            "How did Parliament discuss immigration restrictions in 1901?",
            "What was said about Asian immigration in 1901?",
            "Can you find debates about naturalization laws in 1901?",
            "How did MPs address racial discrimination in 1901?",
            
            # Trade and Economy
            "How did Parliament address tariff policy and trade protection in 1901?",
            "What was discussed about free trade versus protection in 1901?",
            "Can you find debates about international trade agreements in 1901?",
            "How did MPs discuss economic development in 1901?",
            "What concerns were raised about colonial trade preferences in 1901?",
            
            # Imperial Relations
            "What was discussed about Imperial relations with Britain in 1901?",
            "How did Parliament address ties with the British Empire in 1901?",
            "What debates occurred about imperial defense in 1901?",
            "Can you find discussions about colonial representation in London in 1901?",
            "How did MPs view imperial federation proposals in 1901?",
            
            # Land and Agriculture
            "Can you find information about land settlement schemes in 1901?",
            "How did Parliament discuss agricultural development in 1901?",
            "What debates occurred about land ownership in 1901?",
            "How did MPs address rural development in 1901?",
            "What was discussed about agricultural tariffs in 1901?",
            
            # Mining and Resources
            "What parliamentary debates covered mining regulations in 1901?",
            "How did MPs discuss gold mining policy in 1901?",
            "What was said about mineral rights in 1901?",
            "Can you find debates about mining taxation in 1901?",
            "How did Parliament address mining disputes in 1901?",
            
            # Transport and Infrastructure
            "How did MPs discuss railway construction and transport in 1901?",
            "What debates occurred about interstate railways in 1901?",
            "Can you find discussions about shipping and ports in 1901?",
            "How did Parliament address road construction in 1901?",
            "What was discussed about transport subsidies in 1901?",
            
            # Labor and Employment
            "What was the government's response to labor disputes in 1901?",
            "How did Parliament discuss working conditions in 1901?",
            "What debates occurred about industrial relations in 1901?",
            "Can you find discussions about wages and hours in 1901?",
            "How did MPs address unemployment in 1901?",
            
            # Public Works and Services
            "Can you provide details about public works funding in 1901?",
            "How did Parliament discuss infrastructure spending in 1901?",
            "What debates occurred about public buildings in 1901?",
            "How did MPs address water and sewerage in 1901?",
            "What was discussed about public service efficiency in 1901?",
        ]
        
        # Question variations for cache-busting
        self.question_variations = [
            "What did Parliament say about {topic} in 1901?",
            "How did MPs discuss {topic} during 1901?",
            "Can you find debates about {topic} policy in 1901?",
            "What was the government's position on {topic} in 1901?",
            "How did the opposition respond to {topic} legislation in 1901?",
            "What concerns were raised about {topic} in Parliament in 1901?",
            "How did different parties view {topic} in 1901?",
            "What specific measures were proposed for {topic} in 1901?",
            "How did public opinion influence {topic} debates in 1901?",
            "What were the main arguments for and against {topic} in 1901?",
        ]
        
        # Topics for generating variations
        self.topics = [
            "federation", "colonial administration", "tariff policy", "imperial relations", 
            "land settlement", "mining regulations", "railway construction", "labor disputes",
            "public works", "military defense", "public health", "education policy",
            "postal services", "Aboriginal affairs", "agricultural development", "banking",
            "women's suffrage", "immigration", "trade protection", "constitutional powers",
            "industrial relations", "natural resources", "infrastructure", "taxation",
            "electoral reform", "judicial appointments", "diplomatic relations", "maritime law",
            "rural development", "urban planning", "environmental conservation", "cultural policy"
        ]
        
        # Cache-busting parameters
        self.cache_busters = [
            "context", "perspective", "analysis", "summary", "details", "overview",
            "implications", "consequences", "background", "history", "evolution",
            "comparison", "contrast", "significance", "importance", "relevance"
        ]
        
        # Corpus filters with weights (realistic distribution)
        self.corpus_options = [
            ("all", 40),           # 40% - most common
            ("1901_au", 25),       # 25% - Australia focus
            ("1901_uk", 20),       # 20% - UK focus  
            ("1901_nz", 15),       # 15% - New Zealand focus
        ]
        
        # Realistic user patterns
        self.user_categories = [
            ("General User", 40),
            ("Digital HASS Researcher", 25),
            ("Hansard Expert", 20),
            ("GLAM Practitioner", 15),
        ]
        
        # Feedback patterns
        self.feedback_comments = [
            "This answer provided excellent historical context for my research.",
            "The response could include more specific parliamentary references.",
            "Very comprehensive overview of the debates from this period.",
            "The information seems to miss some key perspectives from the time.",
            "Exactly what I needed for understanding the legislative process.",
            "Could benefit from more direct quotes from the parliamentary records.",
            "Great breakdown of the different political positions involved.",
            "The answer was somewhat general - more specific details would help.",
            "Perfect for contextualizing the historical significance of these debates.",
            "Would be useful to include more information about the outcomes.",
            "The response effectively explains the complexity of the issue.",
            "I was hoping for more analysis of the political motivations involved.",
            "This gives a good sense of the parliamentary atmosphere at the time.",
            "The historical connections could be explained more clearly.",
            "Excellent use of primary sources from the parliamentary records.",
        ]
        
        # Session tracking for realistic user behavior
        self.session_questions = {}
        self.session_start_times = {}
        
    def generate_diverse_question(self, session_id: str = None, cache_bust: bool = True) -> str:
        """Generate a diverse question with cache-busting parameters"""
        
        # Track questions per session for realistic behavior
        if session_id:
            if session_id not in self.session_questions:
                self.session_questions[session_id] = []
                self.session_start_times[session_id] = time.time()
        
        # Choose question generation method
        if random.random() < 0.6:  # 60% from base questions
            question = random.choice(self.base_questions)
        else:  # 40% generated variations
            topic = random.choice(self.topics)
            pattern = random.choice(self.question_variations)
            question = pattern.format(topic=topic)
        
        # Add cache-busting parameters
        if cache_bust:
            question = self._add_cache_busting_params(question, session_id)
        
        # Track question for session
        if session_id:
            self.session_questions[session_id].append(question)
        
        return question
    
    def _add_cache_busting_params(self, question: str, session_id: str = None) -> str:
        """Add cache-busting parameters to questions"""
        cache_busters = []
        
        # Add random context request (30% chance)
        if random.random() < 0.3:
            context_type = random.choice(self.cache_busters)
            cache_busters.append(f"Please provide {context_type}")
        
        # Add temporal variation (20% chance)
        if random.random() < 0.2:
            time_contexts = [
                "in the early months of 1901",
                "during the first parliamentary sessions of 1901",
                "in the context of the federation transition",
                "from the perspective of the time",
                "considering the political climate of 1901"
            ]
            cache_busters.append(random.choice(time_contexts))
        
        # Add random session-specific element (15% chance)
        if random.random() < 0.15 and session_id:
            session_hash = hash(session_id) % 1000
            cache_busters.append(f"(session context: {session_hash})")
        
        # Add timestamp-based variation (10% chance)
        if random.random() < 0.1:
            timestamp = int(time.time() * 1000) % 10000
            cache_busters.append(f"[query: {timestamp}]")
        
        # Combine question with cache busters
        if cache_busters:
            question = f"{question} {' '.join(cache_busters)}"
        
        return question
    
    def generate_realistic_corpus_filter(self, session_id: str = None) -> str:
        """Generate realistic corpus filter based on user behavior patterns"""
        
        # Track user's corpus preferences within session
        if session_id and session_id in self.session_questions:
            questions_in_session = len(self.session_questions[session_id])
            
            # Users tend to stick with one corpus for first few questions
            if questions_in_session <= 2:
                if random.random() < 0.7:  # 70% chance to use specific corpus
                    return self._weighted_choice(self.corpus_options[1:])  # Skip "all"
            
            # Later questions more likely to use "all" or explore other corpora
            if questions_in_session > 3:
                if random.random() < 0.5:  # 50% chance for "all"
                    return "all"
        
        return self._weighted_choice(self.corpus_options)
    
    def _weighted_choice(self, choices: List[tuple]) -> str:
        """Make weighted random choice from (item, weight) tuples"""
        total = sum(weight for _, weight in choices)
        r = random.uniform(0, total)
        upto = 0
        for choice, weight in choices:
            if upto + weight >= r:
                return choice
            upto += weight
        return choices[-1][0]  # fallback
    
    def generate_session_id(self) -> str:
        """Generate a unique session ID with timestamp"""
        timestamp = int(time.time() * 1000)
        return f"session_{timestamp}_{uuid.uuid4().hex[:8]}"
    
    def generate_qa_id(self) -> str:
        """Generate a unique QA ID with timestamp"""
        timestamp = int(time.time() * 1000)
        return f"qa_{timestamp}_{uuid.uuid4().hex[:8]}"
    
    def generate_optimized_ask_request(self, session_id: str = None) -> Dict[str, Any]:
        """Generate optimized ask request with cache-busting and realistic parameters"""
        if not session_id:
            session_id = self.generate_session_id()
        
        question = self.generate_diverse_question(session_id, cache_bust=True)
        qa_id = self.generate_qa_id()
        corpus_filter = self.generate_realistic_corpus_filter(session_id)
        
        # Realistic provider distribution (based on your config)
        providers = [
            ("GOOGLE", 60),    # Primary provider (Gemini)
            ("ANTHROPIC", 25), # Secondary
            ("OPENAI", 15),    # Tertiary
        ]
        provider = self._weighted_choice(providers)
        
        # Generate realistic chat history (some sessions have context)
        chat_history = [{"role": "user", "content": question}]
        
        # Add previous context for ongoing sessions (30% chance)
        if (session_id in self.session_questions and 
            len(self.session_questions[session_id]) > 1 and 
            random.random() < 0.3):
            
            prev_question = self.session_questions[session_id][-2]
            chat_history.insert(0, {"role": "user", "content": prev_question})
            chat_history.insert(1, {"role": "assistant", "content": "Based on parliamentary records..."})
        
        request = {
            "question": question,
            "session_id": session_id,
            "qa_id": qa_id,
            "chat_history": chat_history,
            "corpus_filter": corpus_filter,
            "previous_corpus_filter": "all",  # Default
            "provider": provider,
            # Add cache-busting metadata
            "timestamp": int(time.time() * 1000),
            "request_id": uuid.uuid4().hex[:8],
        }
        
        return request
    
    def generate_realistic_feedback(self, qa_id: str, session_id: str, 
                                  question: str = None, answer: str = None) -> Dict[str, Any]:
        """Generate realistic feedback with varied parameters"""
        
        if not question:
            question = self.generate_diverse_question(session_id, cache_bust=False)
        
        if not answer:
            answer = self._generate_realistic_answer(question)
        
        # Realistic rating distributions
        relevance_weights = [(5, 30), (4, 35), (3, 20), (2, 10), (1, 5)]
        clarity_weights = [(5, 25), (4, 40), (3, 25), (2, 8), (1, 2)]
        source_weights = [(5, 35), (4, 30), (3, 25), (2, 8), (1, 2)]
        
        # User category based on session behavior
        user_category = self._weighted_choice(self.user_categories)
        
        # Realistic tag distribution
        all_tags = ["hallucination", "anachronism", "biased", "off-topic", "well-sourced", 
                   "comprehensive", "needs-more-detail", "excellent-sources", "clear-explanation"]
        tags = random.sample(all_tags, k=random.randint(0, 3))
        
        feedback = {
            "session_id": session_id,
            "qa_id": qa_id,
            "trace_id": self.generate_qa_id(),
            "relevance": self._weighted_choice(relevance_weights),
            "factual_accuracy": random.choice(["true", "false", "mixed"]),
            "source_quality": self._weighted_choice(source_weights),
            "clarity": self._weighted_choice(clarity_weights),
            "question_rating": self._weighted_choice([(5, 40), (4, 35), (3, 20), (2, 4), (1, 1)]),
            "user_category": user_category,
            "tags": tags,
            "feedback_text": random.choice(self.feedback_comments),
            "model_answer": answer,
            "test_target": {},
            "question": question,
            "answer": answer,
            "citations": [],
            "timestamp": fake.iso8601(),
            # Cache-busting elements
            "feedback_id": uuid.uuid4().hex[:8],
            "submission_timestamp": int(time.time() * 1000),
        }
        
        return feedback
    
    def _generate_realistic_answer(self, question: str) -> str:
        """Generate realistic answer content"""
        answer_templates = [
            "Based on parliamentary records from 1901, {topic} was extensively debated. The key points discussed included: {point1}, {point2}, and {point3}. The government's position was {position}, while the opposition argued {opposition_view}.",
            "The parliamentary debates of 1901 reveal significant discussion about {topic}. MPs from different parties presented {perspective1} and {perspective2}. The final outcome reflected {outcome}.",
            "Parliamentary records show that {topic} was a contentious issue in 1901. The debates centered around {issue1}, {issue2}, and {issue3}. Various stakeholders provided input, ultimately leading to {resolution}.",
        ]
        
        template = random.choice(answer_templates)
        
        # Fill in template variables
        variables = {
            "topic": "this matter",
            "point1": "policy implementation concerns",
            "point2": "financial implications",
            "point3": "administrative challenges",
            "position": "generally supportive with reservations",
            "opposition_view": "for stronger oversight measures",
            "perspective1": "detailed technical analysis",
            "perspective2": "broader policy implications",
            "outcome": "a balanced compromise",
            "issue1": "constitutional implications",
            "issue2": "practical implementation",
            "issue3": "long-term consequences",
            "resolution": "a carefully crafted solution",
        }
        
        for key, value in variables.items():
            template = template.replace(f"{{{key}}}", value)
        
        return template
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        if session_id not in self.session_questions:
            return {}
        
        session_time = time.time() - self.session_start_times.get(session_id, time.time())
        
        return {
            "session_id": session_id,
            "questions_asked": len(self.session_questions[session_id]),
            "session_duration": session_time,
            "questions_per_minute": len(self.session_questions[session_id]) / (session_time / 60) if session_time > 0 else 0,
        }
    
    def cleanup_old_sessions(self, max_age_seconds: int = 3600):
        """Clean up old session data"""
        current_time = time.time()
        old_sessions = [
            sid for sid, start_time in self.session_start_times.items()
            if current_time - start_time > max_age_seconds
        ]
        
        for session_id in old_sessions:
            self.session_questions.pop(session_id, None)
            self.session_start_times.pop(session_id, None)

# Global instance
enhanced_data_generator = EnhancedDataGenerator()