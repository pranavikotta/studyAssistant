// API service for communicating with the backend

const API_BASE_URL = '/search'; // Proxy will forward to http://localhost:8000

/**
 * Send a message to the backend agent and get a response
 * @param {string} message - The user's message
 * @param {string} sessionId - The session ID for conversation continuity
 * @returns {Promise<{answer: string, sessionId: string}>}
 */
export const sendMessage = async (message, sessionId) => {
  try {
    const response = await fetch(API_BASE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: message,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      answer: data.answer,
      sessionId: sessionId, // Return the session ID for continuity
    };
  } catch (error) {
    console.error('API Error:', error);
    throw new Error(error.message || 'Failed to communicate with the backend');
  }
};

/**
 * Generate a new session ID for a new conversation
 * @returns {string}
 */
export const generateSessionId = () => {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Upload files to the backend for RAG processing
 * @param {FileList} files - The files to upload
 * @param {string} sessionId - The session ID to associate files with
 * @returns {Promise<{message: string, files: Array, total_chunks: number}>}
 */
export const uploadFiles = async (files, sessionId) => {
  try {
    const formData = new FormData();
    
    // Add all files to form data
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    
    // Add session ID
    formData.append('session_id', sessionId);
    
    const response = await fetch('/upload', {
      method: 'POST',
      body: formData, // Don't set Content-Type header - browser will set it with boundary
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('File Upload Error:', error);
    throw new Error(error.message || 'Failed to upload files');
  }
};

/**
 * Save conversation to localStorage
 * @param {object} conversation - The conversation object to save
 */
export const saveConversation = (conversation) => {
  try {
    const conversations = getConversations();
    const existingIndex = conversations.findIndex(c => c.id === conversation.id);
    
    if (existingIndex !== -1) {
      conversations[existingIndex] = conversation;
    } else {
      conversations.unshift(conversation); // Add to beginning
    }
    
    localStorage.setItem('conversations', JSON.stringify(conversations));
  } catch (error) {
    console.error('Error saving conversation:', error);
  }
};

/**
 * Get all conversations from localStorage
 * @returns {Array}
 */
export const getConversations = () => {
  try {
    const stored = localStorage.getItem('conversations');
    return stored ? JSON.parse(stored) : [];
  } catch (error) {
    console.error('Error loading conversations:', error);
    return [];
  }
};

/**
 * Delete a conversation from localStorage
 * @param {string} conversationId - The ID of the conversation to delete
 */
export const deleteConversation = (conversationId) => {
  try {
    const conversations = getConversations();
    const filtered = conversations.filter(c => c.id !== conversationId);
    localStorage.setItem('conversations', JSON.stringify(filtered));
  } catch (error) {
    console.error('Error deleting conversation:', error);
  }
};
