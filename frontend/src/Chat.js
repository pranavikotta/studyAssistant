import React from 'react';
import * as api from './services/api';
import ReactMarkdown from 'react-markdown';
import {Prism as SyntaxHighlighter} from 'react-syntax-highlighter';
import {vscDarkPlus} from 'react-syntax-highlighter/dist/esm/styles/prism';

// Component to render structured content (quiz, flashcards, todo lists, etc.)
function StructuredContent({ content }) {
    // Try JSON first, then fallback to parsing Markdown quizzes
    try {
        const data = JSON.parse(content);

        // Render To-Do List
        if (data.list_title && data.tasks) {
            return (
                <div className='structured-content todo-list'>
                    <h3>{data.list_title}</h3>
                    <ul>
                        {data.tasks.map((task, idx) => (
                            <li key={idx} className='todo-item'>
                                <div className='task-description'>{task.task_description}</div>
                                {task.priority !== 'Not specified' && (
                                    <span className='task-priority'>Priority: {task.priority}</span>
                                )}
                                {task.due_date !== 'No due date' && (
                                    <span className='task-due-date'>Due: {task.due_date}</span>
                                )}
                            </li>
                        ))}
                    </ul>
                </div>
            );
        }

        // Render Quiz (JSON schema)
        if (data.quiz_title && data.questions) {
            return (
                <div className='structured-content quiz'>
                    <h3>{data.quiz_title}</h3>
                    {data.questions.map((q, idx) => (
                        <div key={idx} className='quiz-question'>
                            <p className='question-text'><strong>Q{idx + 1}:</strong> {q.question_text}</p>
                            {q.options && q.options.length > 0 && (
                                <ul className='quiz-options'>
                                    {q.options.map((opt, optIdx) => (
                                        <li key={optIdx}>{opt}</li>
                                    ))}
                                </ul>
                            )}
                            {q.correct_answer && (
                                <p className='answer'><strong>Answer:</strong> {q.correct_answer}</p>
                            )}
                            {q.explanation && (
                                <p className='explanation'><em>{q.explanation}</em></p>
                            )}
                        </div>
                    ))}
                </div>
            );
        }

        // Render Flashcards
        if (data.deck_title && data.cards) {
            return (
                <div className='structured-content flashcards'>
                    <h3>{data.deck_title}</h3>
                    {data.cards.map((card, idx) => (
                        <div key={idx} className='flashcard'>
                            <div className='card-term'><strong>{card.term}</strong></div>
                            <div className='card-definition'>{card.definition}</div>
                        </div>
                    ))}
                </div>
            );
        }

        // Render Schedule
        if (data.schedule_title && data.activities) {
            return (
                <div className='structured-content schedule'>
                    <h3>{data.schedule_title}</h3>
                    <p className='schedule-day'>{data.day}</p>
                    {data.activities.map((activity, idx) => (
                        <div key={idx} className='schedule-item'>
                            <span className='time-slot'>{activity.time_slot}</span>
                            <span className='activity'>{activity.activity_description}</span>
                        </div>
                    ))}
                </div>
            );
        }

        // Fallback: display as formatted JSON
        return <pre>{JSON.stringify(data, null, 2)}</pre>;
    } catch (e) {
        // Not JSON - attempt to parse Markdown quiz format
        const parsed = parseMarkdownQuiz(content);
        if (parsed && parsed.questions && parsed.questions.length > 0) {
            return (
                <div className='structured-content quiz'>
                    <h3>{parsed.title || 'Quiz'}</h3>
                    {parsed.questions.map((q, idx) => (
                        <div key={idx} className='quiz-question'>
                            <p className='question-text'><strong>Q{idx + 1}:</strong> {q.question}</p>
                            {q.options && q.options.length > 0 && (
                                <ul className='quiz-options'>
                                    {q.options.map((opt, optIdx) => (
                                        <li key={optIdx}>{opt}</li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    ))}
                </div>
            );
        }

        // Not structured - render nothing here and let markdown renderer handle it
        return null;
    }
}

// Simple Markdown quiz parser (falls back when tool returned Markdown)
function parseMarkdownQuiz(content) {
    if (!content || typeof content !== 'string') return null;
    const lines = content.split('\n');
    let title = null;
    const questions = [];
    let currentQ = null;

    const optionRegex = /^\s*([a-dA-D])[).]\s*(.+)$/;
    const questionRegex = /^\s*(\d+)\.\s*(.+)$/;

    for (let raw of lines) {
        const line = raw.replace(/\r/g, '').trim();
        if (!line) continue;

        // Detect title like '**Myopia Quiz**' or line containing 'Quiz'
        if (!title) {
            const stripped = line.replace(/^[*\s]+|[*\s]+$/g, '');
            if (/quiz/i.test(stripped)) {
                title = stripped;
                continue;
            }
        }

        const qMatch = line.match(questionRegex);
        if (qMatch) {
            if (currentQ) questions.push(currentQ);
            currentQ = { question: qMatch[2].trim(), options: [] };
            continue;
        }

        const oMatch = line.match(optionRegex);
        if (oMatch && currentQ) {
            // store option text only
            currentQ.options.push(oMatch[2].trim());
            continue;
        }

        // Some quizzes use 'a) text' without numbering - catch those
        const alphaOption = line.match(/^\s*([a-dA-D])[).]\s*(.+)$/);
        if (alphaOption && currentQ) {
            currentQ.options.push(alphaOption[2].trim());
            continue;
        }

        // If line starts with a bullet like '-' and we're in a question, take as option
        if (/^[-*]\s+/.test(line) && currentQ) {
            currentQ.options.push(line.replace(/^[-*]\s+/, '').trim());
            continue;
        }

        // Otherwise, treat as continuation of the previous question text
        if (currentQ && !/^Answer:/i.test(line)) {
            // append to question
            currentQ.question += ' ' + line;
        }
    }

    if (currentQ) questions.push(currentQ);
    if (questions.length === 0) return null;
    return { title, questions };
}

function Chat() {
    return <Chats />;
}

function Chats() {
    const [conversations, setConversations] = React.useState([]);
    const [activeConversation, setActiveConversation] = React.useState(null);
    const [messages, setMessages] = React.useState([]);
    const [inputMessage, setInputMessage] = React.useState('');
    const [sessionId, setSessionId] = React.useState(null);
    const [isLoading, setIsLoading] = React.useState(false);
    const [error, setError] = React.useState('');
    const [uploadedFiles, setUploadedFiles] = React.useState([]);
    const messagesEndRef = React.useRef(null);

    // Load conversations from localStorage on mount
    React.useEffect(() => {
        const savedConversations = api.getConversations();
        setConversations(savedConversations);
    }, []);

    // Auto-scroll to bottom when messages change
    React.useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    const startNewChat = () => {
        setActiveConversation(null);
        setMessages([]);
        setSessionId(api.generateSessionId());
        setError('');
        setUploadedFiles([]);
    };

    const selectConversation = (conv) => {
        setActiveConversation(conv);
        setSessionId(conv.sessionId);
        setMessages(conv.messages || []);
        setError('');
        setUploadedFiles(conv.files || []);
    };

    const deleteConversation = (convId, event) => {
        event.stopPropagation(); // Prevent triggering selectConversation
        
        // Delete from localStorage
        api.deleteConversation(convId);
        
        // Update state
        const updatedConversations = api.getConversations();
        setConversations(updatedConversations);
        
        // If deleting active conversation, clear it
        if (activeConversation?.id === convId) {
            startNewChat();
        }
    };

    const sendMessage = async () => {
        if (inputMessage.trim() === '' || isLoading) return;
        
        const userMessage = inputMessage.trim();
        setInputMessage('');
        setError('');
        
        // Add user message immediately
        const newUserMessage = { role: 'user', content: userMessage };
        setMessages(prev => [...prev, newUserMessage]);
        
        setIsLoading(true);
        
        try {
            // Use existing sessionId or generate new one
            const currentSessionId = sessionId || api.generateSessionId();
            if (!sessionId) {
                setSessionId(currentSessionId);
            }
            
            // Call backend API
            const response = await api.sendMessage(userMessage, currentSessionId);
            
            // Add assistant response
            const assistantMessage = { 
                role: 'assistant', 
                content: response.answer
            };
            const updatedMessages = [...messages, newUserMessage, assistantMessage];
            setMessages(prev => [...prev, assistantMessage]);
            
            // Auto-download if structured content was generated
            if (isStructuredContent(response.answer)) {
                setTimeout(() => {
                    downloadMessage(response.answer, updatedMessages.length - 1);
                }, 500); // Small delay to ensure message is rendered
            }
            
            // Save or update conversation
            const conversationToSave = {
                id: activeConversation?.id || currentSessionId,
                sessionId: currentSessionId,
                title: activeConversation?.title || userMessage.substring(0, 50),
                preview: userMessage.substring(0, 60) + (userMessage.length > 60 ? '...' : ''),
                timestamp: new Date().toLocaleString(),
                messages: updatedMessages,
                files: uploadedFiles,
                lastUpdated: Date.now()
            };
            
            api.saveConversation(conversationToSave);
            
            // Update conversations list
            const updatedConversations = api.getConversations();
            setConversations(updatedConversations);
            
            // Set as active conversation if it was a new chat
            if (!activeConversation) {
                setActiveConversation(conversationToSave);
            }
            
        } catch (err) {
            console.error('Error sending message:', err);
            setError(err.message || 'Failed to send message. Please try again.');
            // Remove the user message on error
            setMessages(prev => prev.slice(0, -1));
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    // RAG upload (sends files to backend for processing into vector store)
    const handleRagUpload = async (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        const currentSessionId = sessionId || api.generateSessionId();
        if (!sessionId) setSessionId(currentSessionId);

        try {
            setIsLoading(true);
            setError('');

            // Upload files to backend for RAG processing
            const result = await api.uploadFiles(files, currentSessionId);

            // Add files to UI state
            const newFiles = Array.from(files).map(file => ({
                id: Date.now() + Math.random(),
                name: file.name,
                size: file.size,
                type: file.type,
                uploadedAt: new Date().toLocaleString(),
                status: 'uploaded',
                rag: true
            }));

            setUploadedFiles(prev => [...prev, ...newFiles]);

            // Show success message
            const successMsg = {
                role: 'assistant',
                content: `Successfully uploaded ${result.files.length} file(s) and processed ${result.total_chunks} document chunks. You can now ask questions about these documents!`,
                isDownloadable: false
            };
            setMessages(prev => [...prev, successMsg]);

        } catch (error) {
            console.error('Upload error:', error);
            setError(`Failed to upload files: ${error.message}`);
        } finally {
            setIsLoading(false);
            e.target.value = '';
        }
    };

    // Regular upload: attach files to conversation context for the agent to reference
    const handleRegularUpload = async (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        try {
            setIsLoading(true);
            setError('');

            const fileArray = Array.from(files);
            
            // Add files to uploaded files list
            const newFiles = fileArray.map(file => ({
                id: Date.now() + Math.random(),
                name: file.name,
                size: file.size,
                type: file.type,
                uploadedAt: new Date().toLocaleString(),
                status: 'uploaded',
                rag: false
            }));
            
            setUploadedFiles(prev => [...prev, ...newFiles]);

            // Show confirmation message
            const confirmMsg = {
                role: 'assistant',
                content: `📎 Attached ${fileArray.length} file(s): ${fileArray.map(f => f.name).join(', ')}. You can now ask me questions about ${fileArray.length > 1 ? 'these files' : 'this file'} or request help with assignments.`,
                isDownloadable: false
            };
            setMessages(prev => [...prev, confirmMsg]);

        } catch (error) {
            console.error('Regular upload error:', error);
            setError(`Failed to process uploaded files: ${error.message}`);
        } finally {
            setIsLoading(false);
            e.target.value = '';
        }
    };

    const removeFile = (fileId) => {
        setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
    };

    const isStructuredContent = (content) => {
        // Check if content is JSON (quiz, flashcard, todo list, etc.)
        if (!content || typeof content !== 'string') return false;
        
        // Try to parse as JSON
        try {
            const parsed = JSON.parse(content);
            // Check for common structured content indicators
            return !!(parsed.quiz_title || parsed.deck_title || parsed.list_title || 
                     parsed.schedule_title || parsed.questions || parsed.cards || parsed.tasks);
        } catch {
            return false;
        }
    };

    const downloadMessage = (content, index) => {
        let textContent = content;
        
        // Try to format structured content into readable text
        try {
            const data = JSON.parse(content);
            
            // Format To-Do List
            if (data.list_title && data.tasks) {
                textContent = `${data.list_title}\n${'='.repeat(data.list_title.length)}\n\n`;
                data.tasks.forEach((task, idx) => {
                    textContent += `${idx + 1}. ${task.task_description}\n`;
                    if (task.priority !== 'Not specified') {
                        textContent += `   Priority: ${task.priority}\n`;
                    }
                    if (task.due_date !== 'No due date') {
                        textContent += `   Due: ${task.due_date}\n`;
                    }
                    textContent += '\n';
                });
            }
            // Format Quiz
            else if (data.quiz_title && data.questions) {
                textContent = `${data.quiz_title}\n${'='.repeat(data.quiz_title.length)}\n\n`;
                data.questions.forEach((q, idx) => {
                    textContent += `Question ${idx + 1}: ${q.question_text}\n\n`;
                    if (q.options && q.options.length > 0) {
                        q.options.forEach((opt, optIdx) => {
                            textContent += `   ${String.fromCharCode(65 + optIdx)}. ${opt}\n`;
                        });
                        textContent += '\n';
                    }
                    textContent += `Answer: ${q.correct_answer}\n`;
                    textContent += `Explanation: ${q.explanation}\n\n`;
                    textContent += '-'.repeat(50) + '\n\n';
                });
            }
            // Format Flashcards
            else if (data.deck_title && data.cards) {
                textContent = `${data.deck_title}\n${'='.repeat(data.deck_title.length)}\n\n`;
                data.cards.forEach((card, idx) => {
                    textContent += `Card ${idx + 1}\n`;
                    textContent += `Term: ${card.term}\n`;
                    textContent += `Definition: ${card.definition}\n\n`;
                });
            }
            // Format Schedule
            else if (data.schedule_title && data.activities) {
                textContent = `${data.schedule_title}\n${'='.repeat(data.schedule_title.length)}\n`;
                textContent += `${data.day}\n\n`;
                data.activities.forEach((activity) => {
                    textContent += `${activity.time_slot}\n  ${activity.activity_description}\n\n`;
                });
            }
        } catch (e) {
            // Not JSON or parsing failed, use content as-is
        }
        
        // Create a blob with the formatted content
        const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
        
        // Create download link
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        
        // Generate filename with timestamp
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        link.download = `study-assistant-response-${timestamp}.txt`;
        
        // Trigger download
        document.body.appendChild(link);
        link.click();
        
        // Cleanup
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };



    return(
        <div className='chat-interface'>
            <div className='chat-sidebar'>
                <div className='sidebar-header'>
                    <div className='sidebar-header-top'>
                        <h3>Previous Chats</h3>
                    </div>
                    <button className='new-chat-btn' onClick={startNewChat}>+ New</button>
                </div>
                <div className='conversations-list'>
                    {conversations.map(conv => (
                        <div 
                            key={conv.id} 
                            className={`conversation-item ${activeConversation?.id === conv.id ? 'active' : ''}`}
                            onClick={() => selectConversation(conv)}
                        >
                            <div className='conversation-content'>
                                <div className='conversation-title'>{conv.title}</div>
                                <div className='conversation-preview'>{conv.preview}</div>
                                <div className='conversation-timestamp'>{conv.timestamp}</div>
                            </div>
                            <button 
                                className='delete-conversation-btn'
                                onClick={(e) => deleteConversation(conv.id, e)}
                                title='Delete conversation'
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <polyline points="3 6 5 6 21 6"></polyline>
                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                    <line x1="10" y1="11" x2="10" y2="17"></line>
                                    <line x1="14" y1="11" x2="14" y2="17"></line>
                                </svg>
                            </button>
                        </div>
                    ))}
                </div>
            </div>
            
            <div className='chat-main'>
                <div className='chat-header'>
                    <h2>{activeConversation ? activeConversation.title : 'New Conversation'}</h2>
                </div>
                
                {uploadedFiles.length > 0 && (
                    <div className='files-section'>
                        <h4>Documents Uploaded for RAG Search ({uploadedFiles.length})</h4>
                        <div className='files-list'>
                            {uploadedFiles.map(file => (
                                <div key={file.id} className='file-item'>
                                    <span className='file-name'>📄 {file.name}</span>
                                    <button 
                                        className='remove-file-btn' 
                                        onClick={() => removeFile(file.id)}
                                        title='Remove file'
                                    >
                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                            <line x1="18" y1="6" x2="6" y2="18"></line>
                                            <line x1="6" y1="6" x2="18" y2="18"></line>
                                        </svg>
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
                
                <div className='messages-container'>
                    {messages.length === 0 ? (
                        <div className='empty-chat'>
                            <h3>Start a new conversation</h3>
                            <p>Ask me anything about your studies!</p>
                        </div>
                    ) : (
                        <>
                            {messages.map((msg, idx) => (
                                <div key={idx} className='message-wrapper'>
                                    <div className={`message-bubble ${msg.role}`}>
                                        {isStructuredContent(msg.content) ? (
                                            <StructuredContent content={msg.content} />
                                        ) : (
                                            <ReactMarkdown
                                                children={msg.content}
                                                components={{
                                                    code({node, inline, className, children, ...props}) {
                                                        const match = /language-(\w+)/.exec(className || '');
                                                        return !inline && match ? (
                                                            <SyntaxHighlighter
                                                                children={String(children).replace(/\n$/, '')}
                                                                style={vscDarkPlus}
                                                                language={match[1]}
                                                                PreTag="div"
                                                                {...props}
                                                            />
                                                        ) : (
                                                            <code className={className} {...props}>
                                                                {children}
                                                            </code>
                                                        );
                                                    }
                                                }}
                                            />
                                        )}
                                    </div>
                                    {msg.role === 'assistant' && (
                                        <div className='message-actions'>
                                            <button 
                                                className='message-action-btn copy-btn'
                                                onClick={() => {
                                                    navigator.clipboard.writeText(msg.content);
                                                }}
                                                title='Copy to clipboard'
                                            >
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                                                </svg>
                                            </button>
                                            <button 
                                                className='message-action-btn download-btn'
                                                onClick={() => downloadMessage(msg.content, idx)}
                                                title='Download this response'
                                            >
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                                    <polyline points="7 10 12 15 17 10"></polyline>
                                                    <line x1="12" y1="15" x2="12" y2="3"></line>
                                                </svg>
                                            </button>
                                        </div>
                                    )}
                                </div>
                            ))}
                            {isLoading && (
                                <div className='message-bubble assistant typing'>
                                    <span className='typing-indicator'>
                                        <span></span>
                                        <span></span>
                                        <span></span>
                                    </span>
                                </div>
                            )}
                        </>
                    )}
                    {error && (
                        <div className='error-message'>
                            ⚠️ {error}
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
                
                <div className='input-area'>
                    {/* Hidden input for RAG upload */}
                    <input
                        type='file'
                        id='rag-file-upload'
                        multiple
                        accept='.pdf,.txt,.doc,.docx'
                        onChange={handleRagUpload}
                        style={{ display: 'none' }}
                    />
                    <button 
                        className='upload-btn rag-upload'
                        onClick={() => document.getElementById('rag-file-upload').click()}
                        title='Upload documents to search/query (adds to RAG database)'
                    >
                        RAG Tool
                    </button>

                    {/* Hidden input for regular upload (assignments, instructions, images) */}
                    <input
                        type='file'
                        id='regular-file-upload'
                        multiple
                        accept='*'
                        onChange={handleRegularUpload}
                        style={{ display: 'none' }}
                    />
                    <button 
                        className='upload-btn regular-upload'
                        onClick={() => document.getElementById('regular-file-upload').click()}
                        title='Attach files (assignments, instructions, images) to discuss with AI'
                    >
                        📎 Attach
                    </button>
                    <textarea
                        className='chat-textarea'
                        placeholder='Type message'
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        disabled={isLoading}
                        rows={1}
                        onInput={(e) => {
                            e.target.style.height = 'auto';
                            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                        }}
                    />
                    <button 
                        className='send-btn' 
                        onClick={sendMessage}
                        disabled={isLoading || inputMessage.trim() === ''}
                    >
                        {isLoading ? 'Sending...' : 'Send'}
                    </button>
                </div>
            </div>
        </div>
    );
}

export default Chat;