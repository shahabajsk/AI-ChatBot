document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const chatLauncher = document.getElementById('chat-launcher');
    const chatWidget = document.getElementById('chat-widget');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const fileInput = document.getElementById('file-input');
    const minimizeBtn = document.getElementById('minimize-btn');
    const closeBtn = document.getElementById('close-btn');
    const refreshBtn = document.getElementById('refresh-btn');
    const helpBtn = document.getElementById('help-btn');
    const uploadStatus = document.getElementById('upload-status');
    const suggestedReplies = document.getElementById('suggested-replies');
    const imageModal = document.getElementById('image-modal');
    const modalImage = document.getElementById('modal-image');
    const closeModal = document.querySelector('.close-modal');
    const downloadBtn = document.getElementById('download-image');
    
    // Dataset status
    let datasetLoaded = false;
    let generalQuestionAsked = false;
    
    // Initialize by showing chat widget (for development)
    chatWidget.classList.add('active');
    chatLauncher.style.display = 'none';
    
    // Toggle chat widget
    chatLauncher.addEventListener('click', function() {
        chatWidget.classList.add('active');
        chatLauncher.style.display = 'none';
    });
    
    // Minimize chat
    minimizeBtn.addEventListener('click', function() {
        chatWidget.classList.remove('active');
        chatLauncher.style.display = 'flex';
    });
    
    // Close chat
    closeBtn.addEventListener('click', function() {
        chatWidget.classList.remove('active');
        chatLauncher.style.display = 'flex';
    });
    
    // Refresh chat
    refreshBtn.addEventListener('click', function() {
        location.reload();
    });
    
    // Help button
    helpBtn.addEventListener('click', function() {
        showHelpMessage();
    });
    
    // Close modal
    closeModal.addEventListener('click', function() {
        imageModal.style.display = 'none';
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === imageModal) {
            imageModal.style.display = 'none';
        }
    });
    
    // Download image
    downloadBtn.addEventListener('click', function() {
        const link = document.createElement('a');
        link.href = modalImage.src;
        link.download = 'rateguru-analysis-' + new Date().toISOString().slice(0, 10) + '.png';
        link.click();
    });
    
    // Suggested replies
    updateSuggestedReplies([
        'Upload a file',
        'What can you analyze?',
        'Help me compare car prices'
    ]);
    
    // Send message when Send button is clicked
    sendButton.addEventListener('click', function() {
        const message = userInput.value.trim();
        if (message) {
            handleUserMessage(message);
        }
    });

    // Send message when Enter key is pressed
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const message = userInput.value.trim();
            if (message) {
                handleUserMessage(message);
            }
        }
    });

    // Handle file selection and automatic upload
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            const file = this.files[0];
            uploadFile(file);
        }
    });
    
    // Handle user message
    function handleUserMessage(message) {
        // Add user message to chat
        addMessage(message, 'user');
        
        // Clear input field
        userInput.value = '';
        
        // Check if first normal question has been asked
        if (!datasetLoaded && !message.toLowerCase().includes('upload') && 
            !message.toLowerCase().includes('file') && !generalQuestionAsked) {
            generalQuestionAsked = true;
        }
        
        // Send message to backend
        fetchChatResponse(message);
    }
    
    // Show help message with all supported questions
    function showHelpMessage() {
        const helpMessage = `
<h3>🔍 Questions RateGuru Can Answer</h3>

<strong>PRICE ANALYSIS</strong>
- What's the cheapest compact car for April 5?
- Which supplier has the best rates for SUVs?
- Compare rates between Enterprise and Hertz for midsize cars
- What's the price difference between economy and luxury cars?
- Show me all deals more than 30% below average price
- Which car category is most affordable?
- Find luxury cars under $150 per day
- What's the average price for a midsize car?

<strong>COMPARISONS</strong>
- Is Travelocity or Alamo offering better deals right now?
- Which supplier has the lowest prices?
- Compare Budget and Avis prices
- Which car category has the best value?
- How much cheaper is Supplier X than Supplier Y?
- Show me price differences between websites
- Which supplier offers the best luxury cars?

<strong>TIME TRENDS</strong>
- When is the best time to rent a car in Las Vegas in April?
- Which day of the week has the lowest rates?
- Show price trends over time
- Are weekends more expensive than weekdays?
- How do prices change throughout April?
- Which date has the lowest average price?
- Compare first week vs last week of April prices

<strong>VISUALIZATIONS</strong>
- Show me a graph of prices by supplier
- Plot price trends over time
- Show me a visualization of prices by car category
- Compare Enterprise and Hertz for SUVs (graph)
- Create a chart of weekend vs weekday prices
- Visualize the best deals across suppliers
- Plot price differences between luxury and economy cars
`;

        addMessageWithTyping(helpMessage, 'bot');
    }
    
    // Upload file
    function uploadFile(file) {
        if (!file.name.toLowerCase().endsWith('.csv')) {
            showUploadNotification('Please upload a CSV file.', 'error');
            return;
        }
        
        showUploadNotification('Uploading and analyzing file...', '');
        
        const formData = new FormData();
        formData.append('file', file);
        
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showUploadNotification('File uploaded successfully!', 'success');
                datasetLoaded = true;
                
                // Add message from bot about successful upload with typing animation
                const summaryText = `I've analyzed your file. Here's a summary:

Total records: ${data.summary.total_records}
Unique suppliers: ${data.summary.unique_suppliers}
Unique car categories: ${data.summary.unique_categories}
Date range: ${data.summary.date_range.min} to ${data.summary.date_range.max}

You can now ask me analytical questions about this data!`;
                           
                addMessageWithTyping(summaryText, 'bot');
                
                // Update suggested replies based on the loaded data
                updateSuggestedRepliesForDataset(data.summary);
            } else {
                showUploadNotification(data.error || 'An error occurred during upload.', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showUploadNotification('An error occurred during upload.', 'error');
        });
    }
    
    // Update suggested replies based on dataset
    function updateSuggestedRepliesForDataset(summary) {
        let suggestions = [];
        
        // Add data-specific suggestions
        if (summary.unique_suppliers > 5) {
            suggestions.push('Show supplier price comparison');
        }
        
        suggestions.push('Show me the best deals');
        suggestions.push('Plot price trends over time');
        
        if (summary.unique_categories > 10) {
            suggestions.push('Compare car categories');
        }
        
        if (summary.websites && summary.websites.length > 1) {
            suggestions.push(`Compare ${summary.websites[0]} vs ${summary.websites[1]}`);
        }
        
        // Limit to 3 suggestions for UI space
        updateSuggestedReplies(suggestions.slice(0, 3));
    }
    
    // Fetch chat response from backend
    function fetchChatResponse(message) {
        // Show typing indicator
        const typingIndicator = addTypingIndicator();
        
        // Send message to backend
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message }),
        })
        .then(response => response.json())
        .then(data => {
            // Remove typing indicator
            chatMessages.removeChild(typingIndicator);
            
            // Format response properly
            const formattedResponse = formatBotResponse(data.response);
            
            // Add bot response with typing animation
            addMessageWithTyping(formattedResponse, 'bot');
            
            // If this is a general response, recommend uploading a file
            // But only if not already uploaded and this is the first general question
            if (!datasetLoaded && generalQuestionAsked && 
                !message.toLowerCase().includes('upload') && 
                !message.toLowerCase().includes('file')) {
                
                generalQuestionAsked = false; // Reset so we don't show this after every general question
                
                // Wait a bit before showing the upload suggestion
                setTimeout(() => {
                    addMessageWithTyping("To get detailed car rental analysis, please upload a rate shopping CSV file using the paperclip icon below.", 'bot');
                }, 1000);
            }
            
            // Check if response includes visualization info
            if (data.visualization) {
                // Show loading message
                const loadingMsg = addMessage('Generating visualization...', 'bot');
                
                // Request the graph
                fetch('/generate_graph', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data.visualization),
                })
                .then(response => response.json())
                .then(graphData => {
                    // Remove loading message
                    chatMessages.removeChild(loadingMsg);
                    
                    if (graphData.image) {
                        // Create container for the image
                        const imgContainer = document.createElement('div');
                        imgContainer.className = 'message bot';
                        
                        const imgContent = document.createElement('div');
                        imgContent.className = 'message-content graph-container';
                        
                        // Create the image element
                        const img = document.createElement('img');
                        img.src = 'data:image/png;base64,' + graphData.image;
                        img.className = 'graph-image';
                        img.alt = 'Data Visualization';
                        
                        // Add click event to open modal
                        img.addEventListener('click', function() {
                            modalImage.src = this.src;
                            imageModal.style.display = 'block';
                        });
                        
                        // Add image to container
                        imgContent.appendChild(img);
                        imgContainer.appendChild(imgContent);
                        
                        // Add container to chat
                        chatMessages.appendChild(imgContainer);
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                        
                        // Add tip about clicking the image
                        setTimeout(() => {
                            addMessageWithTyping("Tip: Click on the graph to enlarge and download it.", 'bot');
                            
                            // Update suggestions to ask about the visualization
                            updateContextualSuggestions(data.visualization.type);
                        }, 1000);
                    } else if (graphData.error) {
                        addMessageWithTyping('Error generating visualization: ' + graphData.error, 'bot');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    chatMessages.removeChild(loadingMsg);
                    addMessageWithTyping('Sorry, I couldn\'t generate the visualization.', 'bot');
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            
            // Remove typing indicator
            chatMessages.removeChild(typingIndicator);
            
            // Add error message
            addMessageWithTyping('Sorry, an error occurred. Please try again.', 'bot');
        });
    }
    
    // Update contextual suggestions based on visualization type
    function updateContextualSuggestions(visualizationType) {
        let suggestions = [];
        
        switch(visualizationType) {
            case 'price_by_supplier':
                suggestions = [
                    'Which supplier is cheapest?',
                    'Compare Enterprise and Hertz',
                    'Show price by category instead'
                ];
                break;
            case 'price_by_date':
                suggestions = [
                    'When is the best time to rent?',
                    'Show weekend vs weekday prices',
                    'Which day has lowest rates?'
                ];
                break;
            case 'price_by_category':
                suggestions = [
                    'Compare SUV and Economy prices',
                    'Which category has best value?',
                    'Show supplier prices instead'
                ];
                break;
            case 'supplier_comparison':
                suggestions = [
                    'Which has better SUV prices?',
                    'Show all suppliers comparison',
                    'Compare by pickup date'
                ];
                break;
            default:
                return;
        }
        
        updateSuggestedReplies(suggestions);
    }
    
    // Format bot response to fix any formatting issues
    function formatBotResponse(text) {
        // Fix common formatting issues
        let formatted = text;
        
        // Fix list numbering issues
        formatted = formatted.replace(/(\d+)\.\s*\*\*/g, '$1. **');
        
        // Fix broken lists by adding proper line breaks
        formatted = formatted.replace(/\*Sign up/g, '\n* Sign up');
        formatted = formatted.replace(/\*Follow/g, '\n* Follow');
        formatted = formatted.replace(/\*Use coupons/g, '\n* Use coupons');
        formatted = formatted.replace(/\*Look for/g, '\n* Look for');
        formatted = formatted.replace(/\*Shop during/g, '\n* Shop during');
        formatted = formatted.replace(/\*Consider/g, '\n* Consider');
        formatted = formatted.replace(/\*Use cashback/g, '\n* Use cashback');
        
        // Fix broken categories list
        formatted = formatted.replace(/\*Fashion/g, '\n* Fashion');
        formatted = formatted.replace(/\*Home/g, '\n* Home');
        formatted = formatted.replace(/\*Toys/g, '\n* Toys');
        formatted = formatted.replace(/\*Travel/g, '\n* Travel');
        
        // Fix "ue" to "Unique"
        formatted = formatted.replace(/ue suppliers/g, 'Unique suppliers');
        formatted = formatted.replace(/ue car categories/g, 'Unique car categories');
        formatted = formatted.replace(/ range:/g, 'Date range:');
        
        return formatted;
    }
    
    // Add typing indicator
    function addTypingIndicator() {
        const messageEl = document.createElement('div');
        messageEl.className = 'message bot typing-indicator';
        
        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        
        contentEl.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
        messageEl.appendChild(contentEl);
        
        chatMessages.appendChild(messageEl);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageEl;
    }
    
    // Add message to chat
    function addMessage(text, sender) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${sender}`;
        
        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        
        // Check if message is long
        const isLongMessage = text.length > 300;
        if (isLongMessage && sender === 'bot') {
            contentEl.classList.add('long-message');
        }
        
        // Format the text - convert URLs to links, enhance formatting
        const formattedText = formatTextWithHTML(text);
        contentEl.innerHTML = formattedText;
        
        messageEl.appendChild(contentEl);
        chatMessages.appendChild(messageEl);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageEl;
    }
    
    // Format text with HTML enhancements
    function formatTextWithHTML(text) {
        // Convert newlines to <br> tags
        let formatted = text.replace(/\n/g, '<br>');
        
        // Convert URLs to clickable links
        formatted = formatted.replace(
            /(https?:\/\/[^\s]+)/g, 
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // Convert ** bold ** to <strong>
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Convert bullet points to proper HTML lists
        if (formatted.includes('• ')) {
            const lines = formatted.split('<br>');
            let inList = false;
            
            for (let i = 0; i < lines.length; i++) {
                if (lines[i].trim().startsWith('• ')) {
                    if (!inList) {
                        lines[i] = '<ul>' + lines[i].replace('• ', '<li>') + '</li>';
                        inList = true;
                    } else {
                        lines[i] = lines[i].replace('• ', '<li>') + '</li>';
                    }
                } else if (inList) {
                    lines[i-1] += '</ul>';
                    inList = false;
                }
            }
            
            if (inList) {
                lines[lines.length-1] += '</ul>';
            }
            
            formatted = lines.join('<br>');
        }
        
        return formatted;
    }
    
    // Add message with typing animation
    function addMessageWithTyping(text, sender) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${sender}`;
        
        const contentEl = document.createElement('div');
        contentEl.className = 'message-content typing-animation';
        
        // Check if message is long
        const isLongMessage = text.length > 400;
        if (isLongMessage && sender === 'bot') {
            contentEl.classList.add('long-message');
        }
        
        // Start with empty content
        contentEl.innerHTML = `<p></p>`;
        
        messageEl.appendChild(contentEl);
        chatMessages.appendChild(messageEl);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Animate the typing effect
        const paragraph = contentEl.querySelector('p');
        let charIndex = 0;
        let html = '';
        const typingSpeed = isLongMessage ? 1 : 5; // much faster for long messages
        
        // Format the text with HTML before animation
        const formattedText = formatTextWithHTML(text);
        
        // Extract plain text (without HTML) for typing animation
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = formattedText;
        const plainText = tempDiv.textContent || tempDiv.innerText || '';
        
        // Set up the typing interval
        const typingInterval = setInterval(() => {
            if (charIndex < plainText.length) {
                // Add one character at a time
                html += plainText.charAt(charIndex);
                paragraph.textContent = html;
                charIndex++;
                
                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } else {
                // When done typing, replace with the fully formatted HTML
                clearInterval(typingInterval);
                
                // Remove the paragraph used for animation
                contentEl.removeChild(paragraph);
                
                // Add formatted content with HTML
                contentEl.innerHTML = formattedText;
                
                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
                
                // Remove animation class
                contentEl.classList.remove('typing-animation');
                
                // If message is very long, add a "show more" button
                if (isLongMessage && text.length > 800) {
                    const showMoreBtn = document.createElement('button');
                    showMoreBtn.className = 'show-more-btn';
                    showMoreBtn.textContent = 'Show more';
                    showMoreBtn.addEventListener('click', function() {
                        contentEl.style.maxHeight = contentEl.scrollHeight + 'px';
                        this.style.display = 'none';
                    });
                    messageEl.appendChild(showMoreBtn);
                }
            }
        }, typingSpeed);
        
        return messageEl;
    }
    
    // Update suggested replies
    function updateSuggestedReplies(replies) {
        suggestedReplies.innerHTML = '';
        
        replies.forEach(reply => {
            const button = document.createElement('button');
            button.className = 'suggested-reply-btn';
            
            // Check for special data commands
            if (reply === 'What can you analyze?') {
                button.dataset.command = 'help';
            }
            
            button.textContent = reply;
            
            button.addEventListener('click', function() {
                handleUserMessage(this.textContent);
            });
            
            suggestedReplies.appendChild(button);
        });
    }
    
    // Show upload notification
    function showUploadNotification(message, type) {
        uploadStatus.textContent = message;
        uploadStatus.className = 'upload-notification show';
        
        if (type) {
            uploadStatus.classList.add(type);
        }
        
        setTimeout(() => {
            uploadStatus.classList.remove('show');
        }, 3000);
    }
    
    // Special handling for help command
    document.addEventListener('click', function(e) {
        // Handle clicking on graph images
        if (e.target.classList.contains('graph-image')) {
            const src = e.target.src;
            modalImage.src = src;
            imageModal.style.display = 'block';
        }
        
        // Handle special data commands
        if (e.target.classList.contains('suggested-reply-btn') && e.target.dataset.command === 'help') {
            e.preventDefault();
            showHelpMessage();
        }
    });
});