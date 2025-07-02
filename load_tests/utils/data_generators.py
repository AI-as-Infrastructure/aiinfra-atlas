import random
from faker import Faker
from typing import List, Dict, Any

fake = Faker()

class DataGenerator:
    """Generate realistic test data for ATLAS load testing"""
    
    def __init__(self):
        self.parliamentary_questions = [
            "What was the government's position on the Education Act of 1944?",
            "Can you provide details about healthcare reforms discussed in Parliament in the 1960s?",
            "What debates occurred regarding immigration policy in the 1970s?",
            "How did Parliament address economic challenges during the recession?",
            "What was discussed about environmental protection legislation?",
            "Can you find information about social security reforms?",
            "What parliamentary debates covered women's rights in the workplace?",
            "How did MPs discuss infrastructure spending proposals?",
            "What was the government's response to housing shortage concerns?",
            "Can you provide details about taxation policy debates?",
            "What discussions occurred regarding trade union legislation?",
            "How did Parliament address unemployment issues?",
            "What debates covered public transportation funding?",
            "Can you find information about agricultural policy reforms?",
            "What parliamentary discussions addressed child welfare?",
            "How did MPs debate defense spending allocations?",
            "What was discussed about international trade agreements?",
            "Can you provide details about pension reform proposals?",
            "What debates occurred regarding local government funding?",
            "How did Parliament address climate change concerns?"
        ]
        
        self.feedback_comments = [
            "This answer was very helpful and accurate.",
            "The response could be more detailed.",
            "Excellent historical context provided.",
            "The information seems incomplete.",
            "Very relevant to my research needs.",
            "Could include more specific dates.",
            "Great breakdown of the parliamentary process.",
            "The answer was too general.",
            "Perfect for understanding the historical context.",
            "Would benefit from more examples."
        ]
        
        self.corpus_filters = [
            {"corpus": "hansard", "date_range": {"start": "1900", "end": "1950"}},
            {"corpus": "hansard", "date_range": {"start": "1950", "end": "1980"}},
            {"corpus": "hansard", "date_range": {"start": "1980", "end": "2010"}},
            {"corpus": "hansard"},
            {"corpus": "all"}
        ]
    
    def generate_question(self) -> str:
        """Generate a realistic parliamentary question"""
        return random.choice(self.parliamentary_questions)
    
    def generate_custom_question(self) -> str:
        """Generate a more varied question using Faker"""
        topics = ["education", "healthcare", "economy", "environment", "defense", "immigration"]
        topic = random.choice(topics)
        
        patterns = [
            f"What did Parliament discuss about {topic} in the {{year}}s?",
            f"Can you find debates on {topic} policy reforms?",
            f"How did the government address {topic} concerns?",
            f"What was the opposition's stance on {topic} legislation?",
            f"Can you provide details about {topic} spending debates?"
        ]
        
        pattern = random.choice(patterns)
        year = random.randint(1900, 2020) // 10 * 10  # Round to decade
        return pattern.format(year=year)
    
    def generate_session_id(self) -> str:
        """Generate a realistic session ID"""
        return fake.uuid4()
    
    def generate_qa_id(self) -> str:
        """Generate a realistic QA ID"""
        return fake.uuid4()
    
    def generate_corpus_filter(self) -> Dict[str, Any]:
        """Generate corpus filter parameters"""
        return random.choice(self.corpus_filters)
    
    def generate_feedback_data(self, qa_id: str, session_id: str, question: str = None, answer: str = None) -> Dict[str, Any]:
        """Generate feedback submission data matching UI format exactly"""
        
        # Generate realistic LLM response if not provided
        if not answer:
            answer = f"Based on parliamentary records, {random.choice(['the government', 'MPs', 'the opposition'])} discussed this matter extensively. Here are the key points: 1) Policy implementation required careful consideration, 2) Various stakeholders provided input, 3) The outcome reflected balanced decision-making."
        
        if not question:
            question = self.generate_question()
        
        # Generate structured feedback matching UI format
        data = {
            "session_id": session_id,
            "qa_id": qa_id,
            "trace_id": self.generate_qa_id(),
            "relevance": random.randint(1, 5),
            "factual_accuracy": random.choice(["true", "false", "partial"]),
            "source_quality": random.randint(1, 5),
            "clarity": random.randint(1, 5),
            "question_rating": random.randint(1, 5),
            "user_category": random.choice(["General User", "Researcher", "Academic", "Student", "Journalist"]),
            "tags": random.sample(["hallucination", "anachronism", "off-topic", "biased", "well-sourced", "comprehensive", "accurate"], k=random.randint(1, 3)),
            "feedback_text": random.choice(self.feedback_comments),
            "model_answer": answer,
            "test_target": {
                "api_url": "https://staging.atlas.parliament.uk",
                "corpus_type": "hansard",
                "date_range": {"start": "1900", "end": "2024"},
                "provider": "ANTHROPIC",
                "model": "claude-3-sonnet",
                "temperature": 0.1,
                "max_tokens": 4000,
                "stream": True,
                "system_prompt": "You are a helpful AI assistant that provides information about UK Parliamentary proceedings.",
                "embedding_model": "text-embedding-3-large",
                "vector_db": "chroma",
                "reranker": "cross-encoder",
                "chunk_size": 1000,
                "overlap": 200,
                "top_k": 10,
                "score_threshold": 0.7
            },
            "question": question,
            "answer": answer,
            "citations": [
                {
                    "id": f"doc_{random.randint(1000, 9999)}",
                    "title": f"Parliamentary Debate {random.randint(1900, 2024)}",
                    "url": f"https://hansard.parliament.uk/debates/{random.randint(1000, 9999)}",
                    "date": fake.date_between(start_date='-50y', end_date='today').isoformat(),
                    "relevance_score": round(random.uniform(0.7, 0.95), 3),
                    "excerpt": f"During the debate on {random.choice(['education', 'healthcare', 'economy'])}, the Minister stated that comprehensive reforms were necessary..."
                },
                {
                    "id": f"doc_{random.randint(1000, 9999)}",
                    "title": f"Committee Report {random.randint(1900, 2024)}",
                    "url": f"https://committees.parliament.uk/reports/{random.randint(100, 999)}",
                    "date": fake.date_between(start_date='-30y', end_date='today').isoformat(),
                    "relevance_score": round(random.uniform(0.6, 0.9), 3),
                    "excerpt": f"The committee found that {random.choice(['implementation', 'oversight', 'funding'])} required additional attention..."
                }
            ]
        }
        
        return data
    
    def generate_ask_request(self, session_id: str = None) -> Dict[str, Any]:
        """Generate a complete ask request payload matching UI format exactly"""
        if not session_id:
            session_id = self.generate_session_id()
            
        question = self.generate_question()
        qa_id = self.generate_qa_id()
        
        # Match the exact UI request format
        request = {
            "question": question,
            "session_id": session_id,
            "qa_id": qa_id,
            "chat_history": [
                {
                    "role": "user",
                    "content": question
                }
            ],
            "corpus_filter": random.choice(["all", "1901_au", "1901_nz", "1901_uk"]),
            "previous_corpus_filter": "all",
            "provider": "ANTHROPIC"
        }
        
        return request
    
    def generate_async_request(self, session_id: str = None) -> Dict[str, Any]:
        """Generate async processing request"""
        if not session_id:
            session_id = self.generate_session_id()
            
        return {
            "question": self.generate_question(),
            "session_id": session_id,
            "corpus_filter": self.generate_corpus_filter(),
            "priority": random.choice(["normal", "high"]),
            "callback_url": None  # For load testing, we don't need callbacks
        }
    
    def generate_user_scenario(self) -> Dict[str, Any]:
        """Generate a complete user interaction scenario"""
        session_id = self.generate_session_id()
        
        # Generate 1-3 questions per session
        num_questions = random.randint(1, 3)
        questions = []
        
        for _ in range(num_questions):
            qa_id = self.generate_qa_id()
            question_data = self.generate_ask_request(session_id)
            
            # Generate feedback for some questions (70% chance)
            feedback_data = None
            if random.random() < 0.7:
                # Pass question and generated answer for realistic feedback
                question_text = question_data.get("question", "")
                answer_text = f"Based on parliamentary records, this {random.choice(['policy', 'legislation', 'debate'])} involved {random.choice(['extensive', 'careful', 'thorough'])} consideration by {random.choice(['MPs', 'the government', 'committees'])}."
                feedback_data = self.generate_feedback_data(qa_id, session_id, question_text, answer_text)
            
            questions.append({
                "qa_id": qa_id,
                "question_data": question_data,
                "feedback_data": feedback_data
            })
        
        return {
            "session_id": session_id,
            "questions": questions,
            "user_type": random.choice(["researcher", "student", "journalist", "academic"])
        }

# Global instance for easy import
data_generator = DataGenerator()