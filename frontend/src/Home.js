// Home Page Component
import React from 'react';
function Home() {
    return(
        <>
            <div className='Home'>
                <div className='hero-content'>
                    <div className='title-wrapper'>
                        <h1 className='main-title'>STUDY ASSISTANT</h1>
                        <div className='title-underline'></div>
                    </div>
                    <h2 className='subtitle'>Your AI-Powered Learning Companion</h2>
                    <p className='tagline'>Unlock your potential with intelligent tools<br/>designed to enhance the learning experience.</p>
                </div>
            </div>

            {/* Capabilities Section */}
            <div className='capabilities-section'>
                <div className='section-header'>
                    <span className='section-badge'>CAPABILITIES</span>
                    <h2 className='capabilities-title'>Autonomous Tools</h2>
                    <p className='capabilities-subtitle'>Powered by artificial intelligence to transform your learning journey</p>
                </div>

                <div className='tools-grid'>
                    {/* Tool 1 */}
                    <div className='tool-item'>
                        <div className='tool-number'>01</div>
                        <div className='tool-content'>
                            <h3 className='tool-title'>RAG Search</h3>
                            <p className='tool-description'>Searches through your personal notes and course materials stored in a vector database. Uses semantic similarity to find the most relevant information from your uploaded documents.</p>
                            <div className='tool-tags'>
                                <span className='tag'>Retrieval</span>
                                <span className='tag'>Semantic Search</span>
                            </div>
                        </div>
                    </div>

                    {/* Tool 2 */}
                    <div className='tool-item'>
                        <div className='tool-number'>02</div>
                        <div className='tool-content'>
                            <h3 className='tool-title'>Web Search</h3>
                            <p className='tool-description'>Performs live Google Custom Search queries to retrieve up-to-date information from the web. Provides current facts, news, and supplementary content to enhance study materials.</p>
                            <div className='tool-tags'>
                                <span className='tag'>Real-time</span>
                                <span className='tag'>Web Intelligence</span>
                            </div>
                        </div>
                    </div>

                    {/* Tool 3 */}
                    <div className='tool-item'>
                        <div className='tool-number'>03</div>
                        <div className='tool-content'>
                            <h3 className='tool-title'>Code Execution</h3>
                            <p className='tool-description'>Executes Python code in a secure subprocess environment. Run calculations, solve mathematical problems, test algorithms, or verify programming concepts in real-time.</p>
                            <div className='tool-tags'>
                                <span className='tag'>Sandbox</span>
                                <span className='tag'>Python Runtime</span>
                            </div>
                        </div>
                    </div>

                    {/* Tool 4 */}
                    <div className='tool-item'>
                        <div className='tool-number'>04</div>
                        <div className='tool-content'>
                            <h3 className='tool-title'>Content Formatter</h3>
                            <p className='tool-description'>Generates structured learning materials including quizzes, flashcards, study schedules, and to-do lists. Automatically saves formatted content as timestamped JSON files.</p>
                            <div className='tool-tags'>
                                <span className='tag'>Autonomous</span>
                                <span className='tag'>File Generation</span>
                            </div>
                        </div>
                    </div>

                    {/* Tool 5 */}
                    <div className='tool-item'>
                        <div className='tool-number'>05</div>
                        <div className='tool-content'>
                            <h3 className='tool-title'>Learning Tracker</h3>
                            <p className='tool-description'>Monitors and tracks your learning progress over time. Automatically saves detailed progress reports with goals, status updates, and session summaries to timestamped files.</p>
                            <div className='tool-tags'>
                                <span className='tag'>Analytics</span>
                                <span className='tag'>Progress Tracking</span>
                            </div>
                        </div>
                    </div>

                    {/* Tool 6 */}
                    <div className='tool-item'>
                        <div className='tool-number'>06</div>
                        <div className='tool-content'>
                            <h3 className='tool-title'>Solution Validator</h3>
                            <p className='tool-description'>Validates Python code against AI-generated test cases in a sandboxed environment. Automatically generates and saves detailed validation reports with execution results and feedback.</p>
                            <div className='tool-tags'>
                                <span className='tag'>Testing</span>
                                <span className='tag'>Validation</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}

export default Home;