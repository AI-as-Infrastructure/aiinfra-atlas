// Helper function to deduplicate text by removing repeated segments
export function deduplicateText(text) {
  if (!text || text.length < 200) return text;
  
  // Split into paragraphs for easier processing
  const paragraphs = text.split(/\n\n+/).filter(p => p.trim().length > 0);
  
  // If there's only one paragraph, look for repeated sentences
  if (paragraphs.length <= 1) {
    // Try to split on sentence boundaries
    const sentences = text.split(/(?<=[.!?])\s+/);
    if (sentences.length > 3) {
      // Check for duplicated sentences
      const uniqueSentences = [];
      const seen = new Set();
      
      for (const sentence of sentences) {
        if (!seen.has(sentence) && sentence.trim().length > 5) {
          uniqueSentences.push(sentence);
          seen.add(sentence);
        }
      }
      
      // If we found duplicates
      if (uniqueSentences.length < sentences.length) {
        return uniqueSentences.join(' ');
      }
    }
    
    return text;
  }
  
  // Check for duplicated paragraphs or content
  const uniqueParagraphs = [];
  const seen = new Set();
  
  // First pass: remove exact duplicates
  for (const paragraph of paragraphs) {
    if (!seen.has(paragraph) && paragraph.trim().length > 0) {
      uniqueParagraphs.push(paragraph);
      seen.add(paragraph);
    }
  }
  
  // If there were duplicates, rebuild the text
  if (uniqueParagraphs.length < paragraphs.length) {
    return uniqueParagraphs.join('\n\n');
  }
  
  // Second pass: check for partial duplicates or repeated themes
  // This is more challenging and might result in false positives,
  // so we're more conservative
  
  // Check if the whole text is duplicated (first half == second half)
  const halfLength = Math.floor(text.length / 2);
  const firstHalf = text.substring(0, halfLength).trim();
  const secondHalf = text.substring(halfLength).trim();
  
  // If the two halves are similar enough, just keep the first half
  if (firstHalf.length > 100 && 
    (secondHalf.includes(firstHalf.substring(0, 50)) || 
     firstHalf.includes(secondHalf.substring(0, 50)))) {
    return firstHalf;
  }
  
  // No obvious duplication found
  return text;
} 