import random
from faker import Faker
from typing import List, Dict, Any

fake = Faker()

class DataGenerator:
    """Generate realistic test data for ATLAS load testing"""
    
    def __init__(self):
        self.parliamentary_questions = [
            "What was discussed about the Australian Federation Act in 1901?",
            "Can you provide details about colonial governance reforms in 1901?",
            "What debates occurred regarding the White Australia Policy in 1901?",
            "How did Parliament address tariff policy and trade protection in 1901?",
            "What was discussed about Imperial relations with Britain in 1901?",
            "Can you find information about land settlement schemes in 1901?",
            "What parliamentary debates covered mining regulations in 1901?",
            "How did MPs discuss railway construction and transport in 1901?",
            "What was the government's response to labor disputes in 1901?",
            "Can you provide details about public works funding in 1901?",
            "What discussions occurred regarding military defense in 1901?",
            "How did Parliament address public health concerns in 1901?",
            "What debates covered education policy in the colonies in 1901?",
            "Can you find information about postal and telegraph services in 1901?",
            "What parliamentary discussions addressed Aboriginal affairs in 1901?",
            "How did MPs debate agricultural development in 1901?",
            "What was discussed about banking and currency in 1901?",
            "Can you provide details about public service appointments in 1901?",
            "What debates occurred regarding women's suffrage in 1901?",
            "How did Parliament address immigration and settlement in 1901?"
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
        topics = ["federation", "colonial administration", "tariff policy", "imperial relations", "land settlement", "mining", "railway construction", "labor disputes", "public works", "military defense", "public health", "education", "postal services", "Aboriginal affairs", "agricultural development", "banking", "women's suffrage", "immigration"]
        topic = random.choice(topics)
        
        patterns = [
            f"What did Parliament discuss about {topic} in 1901?",
            f"Can you find debates on {topic} policy in 1901?",
            f"How did the government address {topic} concerns in 1901?",
            f"What was the opposition's stance on {topic} legislation in 1901?",
            f"Can you provide details about {topic} discussions in 1901?"
        ]
        
        pattern = random.choice(patterns)
        return pattern
    
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
        """Generate feedback submission data matching actual UI format exactly"""
        
        # Generate realistic LLM response if not provided
        if not answer:
            answer = f"Based on parliamentary records, {random.choice(['the government', 'MPs', 'the opposition'])} discussed this matter extensively. Here are the key points: 1) Policy implementation required careful consideration, 2) Various stakeholders provided input, 3) The outcome reflected balanced decision-making."
        
        if not question:
            question = self.generate_question()
        
        # Match the EXACT UI feedback format from actual payload you provided
        data = {
            "session_id": session_id,
            "qa_id": qa_id,
            "trace_id": self.generate_qa_id(),
            "relevance": random.randint(1, 5),
            "factual_accuracy": random.choice(["true", "false", "mixed"]),  # UI uses "mixed" not just true/false
            "source_quality": random.randint(1, 5),
            "clarity": random.randint(1, 5),
            "question_rating": random.randint(1, 5),
            "user_category": random.choice(["General User", "Hansard Expert", "Digital HASS Researcher", "GLAM Practitioner"]),
            "tags": random.sample(["hallucination", "anachronism", "biased", "off-topic", "well-sourced"], k=random.randint(0, 3)),  # Can be empty
            "feedback_text": random.choice(self.feedback_comments),
            "model_answer": answer or "",
            "test_target": {},  # UI often sends empty object
            "question": question,
            "answer": answer,
            "citations": [],
            "timestamp": fake.iso8601()
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