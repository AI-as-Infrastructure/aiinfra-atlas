import random
from faker import Faker
from typing import List, Dict, Any

fake = Faker()

class DataGenerator:
    """Generate realistic test data for ATLAS load testing"""
    
    def __init__(self):
        # Australian-specific questions optimized for 1901_au filter
        self.australian_questions = [
            "What was discussed about the Australian Federation Act in 1901?",
            "How did Australian Parliament debate the Constitution Act in 1901?",
            "What were the key arguments for and against federation in Australian colonies?",
            "What debates occurred regarding the White Australia Policy in 1901?",
            "How did Australian Parliament justify the Immigration Restriction Act of 1901?",
            "What was discussed about Chinese immigration in Australian parliaments?",
            "How did Australian colonial parliaments respond to calls for South African War volunteers?",
            "How did Australian Parliament address imperial defense obligations?",
            "How did Australian Parliament address tariff policy and trade protection in 1901?",
            "What was the Australian government's response to labor disputes in 1901?",
            "How did Australian Parliament debate the eight-hour working day?",
            "What debates occurred about child labor restrictions in Australian Parliament?",
            "What debates occurred regarding women's suffrage in Australian Parliament in 1901?",
            "What parliamentary discussions addressed Aboriginal affairs in Australian Parliament in 1901?",
            "How did Australian Parliament debate Aboriginal protection and assimilation policies?",
            "How did Australian Parliament debate Australian national identity and culture?",
            "How did Australian Parliament address public health concerns in 1901?",
            "What debates covered education policy in the Australian colonies in 1901?",
            "How did Australian Parliament debate the role of colonial governors?",
            "How did Australian Parliament debate closer settlement policies?",
            "What discussions occurred regarding military defense in Australian Parliament in 1901?",
            "What was discussed about banking and currency in Australian Parliament in 1901?",
            "How did Australian Parliament address the sugar industry protection?",
            "What discussions occurred about mining industry regulation in Australian Parliament?",
            "How did Australian Parliament debate railway construction and transport policy?"
        ]
        
        # New Zealand-specific questions optimized for 1901_nz filter
        self.new_zealand_questions = [
            "What parliamentary debates addressed the Treaty of Waitangi interpretation in New Zealand?",
            "How did New Zealand Parliament discuss Māori land rights around 1900?",
            "What was debated about Māori political representation in New Zealand Parliament?",
            "How did New Zealand Parliament address Māori education and welfare issues?",
            "What debates occurred about Māori customary law versus European law in New Zealand?",
            "How did New Zealand Parliament discuss the Native Land Court system?",
            "How did New Zealand Parliament discuss participation in the South African War?",
            "How did New Zealand Parliament address Asian immigration restrictions?",
            "What debates occurred regarding women's suffrage in New Zealand Parliament?",
            "How did New Zealand Parliament debate land settlement policies?",
            "What was discussed about labor conditions in New Zealand Parliament in 1901?",
            "How did New Zealand Parliament address public works funding?",
            "What debates occurred about education policy in New Zealand Parliament?",
            "How did New Zealand Parliament discuss postal and telegraph services?",
            "What was debated about local government in New Zealand Parliament?",
            "How did New Zealand Parliament address public health measures?",
            "What discussions occurred about temperance in New Zealand Parliament?",
            "How did New Zealand Parliament debate railway development?",
            "What was discussed about agricultural policy in New Zealand Parliament?",
            "How did New Zealand Parliament address military defense in 1901?"
        ]
        
        # UK Parliament questions optimized for 1901_uk filter
        self.uk_questions = [
            "How did UK Parliament debate dominion status for Australia in 1901?",
            "What was the parliamentary response to Emily Hobhouse's reports on South African conditions?",
            "How did UK Parliament debate Britain's conduct in the South African War?",
            "What were the financial implications of the South African War discussed in UK Parliament?",
            "What debates occurred about concentration camps during the South African War in UK Parliament?",
            "How did UK Parliament debate the concept of Greater Britain?",
            "What were the discussions about imperial preference in trade in UK Parliament?",
            "What was debated about the Imperial Conference proposals in UK Parliament?",
            "How did UK Parliament discuss imperial unity versus colonial autonomy?",
            "What debates occurred about the role of the Governor-General in UK Parliament?",
            "How did UK Parliament address imperial defense strategies?",
            "What was discussed about colonial governance in UK Parliament?",
            "How did UK Parliament debate imperial trade policies?",
            "What discussions occurred about imperial citizenship in UK Parliament?",
            "How did UK Parliament address colonial military contributions?",
            "What was debated about imperial communications in UK Parliament?",
            "How did UK Parliament discuss colonial constitutional development?",
            "What debates occurred about imperial federation in UK Parliament?",
            "How did UK Parliament address colonial administrative reform?",
            "What was discussed about imperial economic relations in UK Parliament?"
        ]
        
        # Cross-country questions that work well with "all" filter
        self.general_questions = [
            "What was discussed about Imperial relations with Britain in 1901?",
            "How did parliaments debate imperial preference for British goods?",
            "What debates occurred about free trade versus protection across the Empire?",
            "How did different parliaments discuss strikes and industrial disputes?",
            "What was debated about old-age pensions across different parliaments?",
            "How did parliaments address poverty and social welfare issues?",
            "What discussions occurred about women's legal status and property rights?",
            "How did different parliaments debate university funding and access?",
            "What was discussed about telegraph and postal services across the Empire?",
            "How did parliaments debate quarantine and disease prevention measures?"
        ]
        
        # Intentionally sub-optimal questions for edge case testing (10% of questions)
        self.suboptimal_questions = [
            "What debates occurred about child labor?",  # Generic, no country specified
            "How did Parliament discuss women's suffrage?",  # Could apply to any country
            "What was debated about banking policy?",  # Vague, no country context
            "How did Parliament address education reform?",  # Generic question
            "What discussions occurred about trade policy?",  # No specific country mentioned
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
    
    def generate_question_and_filter(self) -> tuple[str, str]:
        """Generate a question with its optimal filter for better HNSW search results"""
        # 10% chance for sub-optimal questions (for edge case testing)
        if random.random() < 0.1:
            question = random.choice(self.suboptimal_questions)
            # Random filter for sub-optimal questions to test mismatches
            filter_choice = random.choice(["1901_au", "1901_nz", "1901_uk", "all"])
            return question, filter_choice
        
        # 90% optimal question-filter matching
        choice = random.random()
        if choice < 0.3:  # 30% Australian questions
            question = random.choice(self.australian_questions)
            return question, "1901_au"
        elif choice < 0.6:  # 30% New Zealand questions
            question = random.choice(self.new_zealand_questions)
            return question, "1901_nz"
        elif choice < 0.8:  # 20% UK questions
            question = random.choice(self.uk_questions)
            return question, "1901_uk"
        else:  # 20% general questions with "all" filter
            question = random.choice(self.general_questions)
            return question, "all"
    
    def generate_question(self) -> str:
        """Generate a realistic parliamentary question (backward compatibility)"""
        question, _ = self.generate_question_and_filter()
        return question
    
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
    
    def generate_corpus_filter(self) -> str:
        """Generate corpus filter parameters"""
        return random.choice(["all", "1901_au", "1901_nz", "1901_uk"])
    
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
            
        # Use optimized question-filter matching
        question, corpus_filter = self.generate_question_and_filter()
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
            "corpus_filter": corpus_filter,
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