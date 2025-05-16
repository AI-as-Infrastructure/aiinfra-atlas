import React, { useState, useEffect } from 'react';
import { socket } from '../../socket';

const LikertScale = ({ value, onChange, label }) => (
  <div className="likert-scale">
    <div className="likert-label">{label}</div>
    <div className="likert-options">
      {[1, 2, 3, 4, 5].map((num) => (
        <label key={num} className="likert-option">
          <input
            type="radio"
            name={label}
            value={num}
            checked={value === num}
            onChange={() => onChange(num)}
          />
          <span>{num}</span>
        </label>
      ))}
    </div>
    <div className="likert-labels">
      <span>Poor</span>
      <span>Excellent</span>
    </div>
  </div>
);

const FeedbackForm = ({ onSubmit, onClose, isSubmitting }) => {
  const [answerRating, setAnswerRating] = useState(null);
  const [citationsRating, setCitationsRating] = useState(null);
  const [feedbackText, setFeedbackText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (answerRating && citationsRating) {
      onSubmit({
        answerRating,
        citationsRating,
        feedbackText
      });
    }
  };

  return (
    <form className="feedback-form" onSubmit={handleSubmit}>
      <LikertScale
        value={answerRating}
        onChange={setAnswerRating}
        label="How helpful was this answer?"
      />
      <LikertScale
        value={citationsRating}
        onChange={setCitationsRating}
        label="How relevant were the citations?"
      />
      <textarea
        value={feedbackText}
        onChange={(e) => setFeedbackText(e.target.value)}
        placeholder="Additional comments (optional)"
        rows={3}
      />
      <div className="feedback-actions">
        <button 
          type="submit" 
          disabled={!answerRating || !citationsRating || isSubmitting}
        >
          {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
        </button>
        <button type="button" onClick={onClose} disabled={isSubmitting}>
          Cancel
        </button>
      </div>
    </form>
  );
};

const FeedbackButtons = ({ 
  message, 
  question, 
  sessionId, 
  onComplete, 
  isResponseComplete = false, // New prop to track if response + citations are complete
  isNewQuestionAsked = false  // New prop to track if a new question is being asked
}) => {
  const [showForm, setShowForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [shouldShowButton, setShouldShowButton] = useState(false);

  // Effect to determine when to show the rate button
  useEffect(() => {
    if (isNewQuestionAsked) {
      // Hide button when new question is asked
      setShouldShowButton(false);
      setFeedbackSubmitted(false);
    } else if (isResponseComplete && !feedbackSubmitted) {
      // Show button when response is complete and feedback hasn't been submitted
      setShouldShowButton(true);
    }
  }, [isResponseComplete, isNewQuestionAsked, feedbackSubmitted]);

  // Effect to listen for feedback confirmation
  useEffect(() => {
    const handleFeedbackConfirmed = (data) => {
      if (data.session_id === sessionId) {
        setIsSubmitting(false);
        setShowForm(false);
        setFeedbackSubmitted(true);
        setShouldShowButton(false); // Hide button after feedback submission
        if (onComplete) {
          onComplete();
        }
      }
    };

    const handleFeedbackError = (data) => {
      if (data.session_id === sessionId) {
        setIsSubmitting(false);
        alert('Error submitting feedback: ' + data.error);
      }
    };

    socket.on('feedback_confirmed', handleFeedbackConfirmed);
    socket.on('feedback_error', handleFeedbackError);

    return () => {
      socket.off('feedback_confirmed', handleFeedbackConfirmed);
      socket.off('feedback_error', handleFeedbackError);
    };
  }, [sessionId, onComplete]);

  const handleSubmit = (feedback) => {
    setIsSubmitting(true);
    // Generate a unique ID for this Q&A pair if not already present
    const qa_id = message.qa_id || `qa_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    // Add timestamp for tracing
    const feedback_timestamp = new Date().toISOString();
    
    socket.emit('feedback', {
      session_id: sessionId,
      qa_id: qa_id,  // Include the Q&A pair ID
      question: question,
      answer: message.message,
      sources: message.sources || [],
      answer_rating: feedback.answerRating,
      citations_rating: feedback.citationsRating,
      feedback_text: feedback.feedbackText,
      citations: message.sources || [],
      feedback_timestamp: feedback_timestamp
    });
    
    // Store this qa_id in the message for future reference
    if (!message.qa_id) {
      if (onComplete) {
        onComplete({ ...message, qa_id });
      }
    }
  };

  // Don't render anything if we shouldn't show the button
  if (!shouldShowButton && !showForm) {
    return null;
  }

  return (
    <div className="feedback-container">
      {!showForm ? (
        <button onClick={() => setShowForm(true)} className="feedback-button">
          Rate Answer
        </button>
      ) : (
        <div className="feedback-form">
          <h3>Rate Your Experience</h3>
          <FeedbackForm 
            onSubmit={handleSubmit}
            onClose={() => {
              if (!isSubmitting) {
                setShowForm(false);
                setFeedbackSubmitted(true); // Consider feedback "skipped" if form closed
                setShouldShowButton(false);
              }
            }}
            isSubmitting={isSubmitting}
          />
        </div>
      )}
    </div>
  );
};

export default FeedbackButtons;