import random
from faker import Faker
from typing import List, Dict, Any

fake = Faker()

class DataGenerator:
    """Generate realistic test data for ATLAS load testing"""
    
    def __init__(self):
        self.parliamentary_questions = [
            # Federation and Constitutional Questions
            "What was discussed about the Australian Federation Act in 1901?",
            "How did UK Parliament debate dominion status for Australia in 1901?",
            "What were the key arguments for and against federation in Australian colonies?",
            "How did New Zealand's decision to remain outside federation influence Australian debates?",
            "What constitutional precedents were established during the federation debates?",
            
            # The South African War (1899-1902)
            "How did Parliament debate Britain's conduct in the South African War?",
            "What were the financial implications of the South African War discussed in Parliament?",
            "How did Australian colonial parliaments respond to calls for South African War volunteers?",
            "What debates occurred about concentration camps during the South African War?",
            "How did New Zealand Parliament discuss participation in the South African War?",
            "What was the parliamentary response to Emily Hobhouse's reports on South African conditions?",
            
            # White Australia Policy and Immigration
            "What debates occurred regarding the White Australia Policy in 1901?",
            "How did Parliament justify the Immigration Restriction Act of 1901?",
            "What were the economic arguments for and against the White Australia Policy?",
            "How did Parliament debate the dictation test for immigrants?",
            "What was discussed about Chinese immigration in Australian parliaments?",
            "How did New Zealand Parliament address Asian immigration restrictions?",
            
            # Treaty of Waitangi and Māori Affairs
            "What parliamentary debates addressed the Treaty of Waitangi interpretation?",
            "How did New Zealand Parliament discuss Māori land rights around 1900?",
            "What was debated about Māori political representation in Parliament?",
            "How did Parliament address Māori education and welfare issues?",
            "What debates occurred about Māori customary law versus European law?",
            "How did Parliament discuss the Native Land Court system?",
            
            # Empire and Imperial Relations
            "What was discussed about Imperial relations with Britain in 1901?",
            "How did Parliament debate the concept of Greater Britain?",
            "What were the discussions about imperial preference in trade?",
            "How did Australian Parliament address imperial defense obligations?",
            "What debates occurred about the role of the Governor-General?",
            "How did Parliament discuss imperial unity versus colonial autonomy?",
            "What was debated about the Imperial Conference proposals?",
            
            # Economic and Trade Policy
            "How did Parliament address tariff policy and trade protection in 1901?",
            "What debates occurred about free trade versus protection?",
            "How did Parliament discuss inter-colonial trade barriers?",
            "What was debated about imperial preference for British goods?",
            "How did Parliament address the sugar industry protection?",
            "What discussions occurred about mining industry regulation?",
            "How did Parliament debate railway construction and transport policy?",
            
            # Labor and Industrial Relations
            "What was the government's response to labor disputes in 1901?",
            "How did Parliament debate the eight-hour working day?",
            "What discussions occurred about trade union rights?",
            "How did Parliament address factory conditions and worker safety?",
            "What was debated about arbitration and conciliation courts?",
            "How did Parliament discuss strikes and industrial disputes?",
            "What debates occurred about child labor restrictions?",
            
            # Women's Rights and Gender
            "What debates occurred regarding women's suffrage in 1901?",
            "How did Parliament discuss women's legal status and property rights?",
            "What was debated about women's employment opportunities?",
            "How did Parliament address the marriage and divorce laws?",
            "What discussions occurred about women's education access?",
            "How did Parliament debate women's role in public life?",
            "What was discussed about maternal and child welfare?",
            
            # Social Class and Inequality
            "How did Parliament address poverty and social welfare issues?",
            "What debates occurred about old-age pensions?",
            "How did Parliament discuss class distinctions in colonial society?",
            "What was debated about public education access across social classes?",
            "How did Parliament address housing conditions for the working class?",
            "What discussions occurred about social mobility and opportunity?",
            "How did Parliament debate charity and poor relief systems?",
            
            # Indigenous Affairs and Race Relations
            "What parliamentary discussions addressed Aboriginal affairs in 1901?",
            "How did Parliament debate Aboriginal protection and assimilation policies?",
            "What was discussed about Aboriginal land rights and reserves?",
            "How did Parliament address Aboriginal education and missions?",
            "What debates occurred about Aboriginal voting rights?",
            "How did Parliament discuss half-caste children and removal policies?",
            "What was debated about Aboriginal employment and wages?",
            
            # Culture and National Identity
            "How did Parliament debate Australian national identity and culture?",
            "What discussions occurred about Australian versus British cultural values?",
            "How did Parliament address language policy and English proficiency?",
            "What was debated about Australian literature and arts support?",
            "How did Parliament discuss public holidays and national celebrations?",
            "What debates occurred about Australian symbols and flags?",
            "How did Parliament address cultural institutions and museums?",
            
            # Public Health and Social Issues
            "How did Parliament address public health concerns in 1901?",
            "What debates occurred about quarantine and disease prevention?",
            "How did Parliament discuss alcohol regulation and temperance?",
            "What was debated about sanitation and urban health?",
            "How did Parliament address mental health and asylum conditions?",
            "What discussions occurred about medical education and regulation?",
            "How did Parliament debate pharmaceutical regulation?",
            
            # Education and Knowledge
            "What debates covered education policy in the colonies in 1901?",
            "How did Parliament discuss state versus religious education?",
            "What was debated about university funding and access?",
            "How did Parliament address teacher training and qualifications?",
            "What discussions occurred about technical and vocational education?",
            "How did Parliament debate school curriculum and standards?",
            "What was discussed about education for girls and women?",
            
            # Colonial Governance and Administration
            "Can you provide details about colonial governance reforms in 1901?",
            "How did Parliament debate the role of colonial governors?",
            "What discussions occurred about civil service reform?",
            "How did Parliament address corruption in colonial administration?",
            "What was debated about local government powers and responsibilities?",
            "How did Parliament discuss judicial independence and legal reform?",
            "What debates occurred about police and law enforcement?",
            
            # Infrastructure and Development
            "Can you find information about land settlement schemes in 1901?",
            "How did Parliament debate closer settlement policies?",
            "What discussions occurred about irrigation and water rights?",
            "How did Parliament address telegraph and postal services?",
            "What was debated about port development and shipping?",
            "How did Parliament discuss road construction and maintenance?",
            "What debates occurred about public works funding priorities?",
            
            # Military and Defense
            "What discussions occurred regarding military defense in 1901?",
            "How did Parliament debate colonial military contributions to imperial defense?",
            "What was discussed about military training and conscription?",
            "How did Parliament address coastal defense and fortifications?",
            "What debates occurred about military pensions and veteran affairs?",
            "How did Parliament discuss the role of colonial militias?",
            "What was debated about military equipment and modernization?",
            
            # Financial and Banking
            "What was discussed about banking and currency in 1901?",
            "How did Parliament debate the establishment of a national bank?",
            "What discussions occurred about gold standard and monetary policy?",
            "How did Parliament address government debt and borrowing?",
            "What was debated about taxation and revenue collection?",
            "How did Parliament discuss customs duties and excise taxes?",
            "What debates occurred about colonial financial relations with Britain?"
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