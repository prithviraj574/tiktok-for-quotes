import React, { useState, useRef, useEffect } from 'react';
import { Heart, HeartOff } from 'lucide-react';
import Cookies from 'js-cookie';

const API_BASE_URL = 'http://localhost:8000';

// Helper function to generate user ID
const generateUserId = () => {
  return 'user_' + Math.random().toString(36).substr(2, 9);
};

// API functions
const fetchRecommendations = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/get_recommendations`, {
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
      }
    });
    if (!response.ok) throw new Error('Failed to fetch recommendations');
    return await response.json();
  } catch (error) {
    console.error('Error fetching recommendations:', error);
    throw error;
  }
};

const postInteraction = async (quoteId, isLiked) => {
  try {
    const response = await fetch(`${API_BASE_URL}/post_interaction`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        quote_id: quoteId,
        is_liked: isLiked
      })
    });
    if (!response.ok) throw new Error('Failed to post interaction');
    return await response.json();
  } catch (error) {
    console.error('Error posting interaction:', error);
    throw error;
  }
};

function App() {
  const [quotes, setQuotes] = useState([]);
  const [likedQuotes, setLikedQuotes] = useState(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const wrapperRef = useRef(null);
  const seenQuotes = useRef(new Set());
  const retryCount = useRef({});

  // Initialize user ID
  useEffect(() => {
    let userId = Cookies.get('userId');
    if (!userId) {
      userId = generateUserId();
      Cookies.set('userId', userId, { expires: 365 });
    }
  }, []);

  // Load initial quotes
  useEffect(() => {
    loadQuotes();
  }, []);

  // Function to load quotes with retry
  const loadQuotes = async () => {
    if (isLoading) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const newQuotes = await fetchRecommendations();
      setQuotes(prev => [...prev, ...newQuotes]);
    } catch (error) {
      const retryKey = 'load-quotes';
      retryCount.current[retryKey] = (retryCount.current[retryKey] || 0) + 1;
      
      if (retryCount.current[retryKey] <= 1) {
        console.log('Retrying quote fetch...');
        setTimeout(loadQuotes, 2000);
      } else {
        setError('Unable to fetch quotes. Please try again later.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const toggleLike = async (quoteId) => {
    if ('vibrate' in navigator) {
      navigator.vibrate(50);
    }
    
    setLikedQuotes(prev => {
      const newSet = new Set(prev);
      const isLiked = !newSet.has(quoteId);
      
      if (isLiked) {
        newSet.add(quoteId);
      } else {
        newSet.delete(quoteId);
      }
      
      // Post interaction asynchronously
      postInteraction(quoteId, isLiked).catch(console.error);
      
      return newSet;
    });
  };

  // Scroll tracking and interaction posting
  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    let lastFullyVisibleQuote = null;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          const quoteId = parseInt(entry.target.dataset.quoteId);
          
          // If quote is no longer visible and was previously fully visible
          if (!entry.isIntersecting && lastFullyVisibleQuote === quoteId) {
            if (!seenQuotes.current.has(quoteId)) {
              seenQuotes.current.add(quoteId);
              postInteraction(quoteId, likedQuotes.has(quoteId)).catch(console.error);
            }
            lastFullyVisibleQuote = null;
          }
          
          // Update last fully visible quote
          if (entry.isIntersecting && entry.intersectionRatio === 1) {
            lastFullyVisibleQuote = quoteId;
          }
        });
      },
      {
        threshold: 1.0,
        root: wrapper
      }
    );

    // Observe all quote elements
    document.querySelectorAll('.quote-container').forEach(quote => {
      observer.observe(quote);
    });

    return () => observer.disconnect();
  }, [quotes, likedQuotes]);

  // Prevent scroll up and handle infinite scroll
  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    let lastScrollTop = 0;
    const handleScroll = (e) => {
      const currentScrollTop = wrapper.scrollTop;
      
      // If trying to scroll up
      if (currentScrollTop < lastScrollTop) {
        wrapper.scrollTop = lastScrollTop;
        return;
      }
      
      lastScrollTop = currentScrollTop;

      // Check if we need to load more quotes
      const scrolledToBottom = 
        wrapper.scrollHeight - wrapper.scrollTop === wrapper.clientHeight;
      
      if (scrolledToBottom && !isLoading && !error) {
        loadQuotes();
      }
    };

    wrapper.addEventListener('scroll', handleScroll, { passive: false });
    return () => wrapper.removeEventListener('scroll', handleScroll);
  }, [isLoading, error]);

  
  function getDynamicFontSize(text) {
    const wordCount = text.trim().split(/\s+/).length;
    const maxWordCount = 500;      // Maximum word count for scaling
    const maxFontSize = 24;        // Font size at 100 words (or fewer)
    const minFontSize = 10;        // Font size at 400 words
  
    const fontSize = Math.max(Math.min((-30/350) * wordCount + 26,maxFontSize),minFontSize)
    // const effectiveCount = wordCount <= 100 ? 0 : Math.min(wordCount - 100, maxWordCount - 100);
    // const scalingRange = maxWordCount - 100;
    // const fontSize = maxFontSize - ((maxFontSize - minFontSize) * effectiveCount) / scalingRange;    
    

    return `${fontSize}px`;
  }  

  return (
    <>
      <div 
        ref={wrapperRef} 
        className="quotes-wrapper overflow-y-auto"
        style={{
          height: '100vh',
          overscrollBehavior: 'contain',
          WebkitOverflowScrolling: 'touch'
        }}
      >
        {quotes.map((quote) => (
          <div 
            key={quote.id} 
            data-quote-id={quote.id}
            className="quote-container relative flex items-center justify-center paper-texture min-h-screen"
            style={{
              height: '100vh',
              overflowY: 'hidden'
            }}
          >
            <div className="w-full px-6 text-center max-w-3xl mx-auto flex flex-col justify-center h-full">
              <div className="space-y-6">
                {/* <p 
                  className="text-lg sm:text-xl lg:text-2xl leading-relaxed animate-fade-in"
                  style={{ 
                    fontFamily: 'Special Elite',
                    // Removed WebkitLineClamp and related properties
                    // Removed maxHeight constraint
                  }}
                >
                  {quote.text}
                </p> */}
                <p
                  className="leading-relaxed animate-fade-in"
                  style={{ 
                    fontFamily: 'Special Elite',
                    fontSize: getDynamicFontSize(quote.text),
                    lineHeight: '1.5' // Adjust as needed (this will multiply the computed font size)
                  }}
                >
                  {quote.text}
                </p>
                <p 
                  className="text-xl sm:text-2xl text-gray-700 animate-slide-up" 
                  style={{ fontFamily: 'Style Script' }}
                >
                  — {quote.author}
                </p>
              </div>
              <button
                onClick={() => toggleLike(quote.id)}
                className="absolute bottom-20 right-6 p-3 rounded-full bg-white/80 shadow-lg transition-all active:scale-95 hover:bg-white"
              >
                {likedQuotes.has(quote.id) ? (
                  <Heart className="w-8 h-8 text-red-500 fill-current animate-like" />
                ) : (
                  <HeartOff className="w-8 h-8 text-gray-500" />
                )}
              </button>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="fixed bottom-4 left-0 w-full flex justify-center">
            <div className="loading-dot-pulse">
              <div></div>
              <div></div>
              <div></div>
            </div>
          </div>
        )}
        
        {error && (
          <div className="fixed bottom-4 left-0 w-full flex justify-center">
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          </div>
        )}
      </div>

      <style jsx global>{`
        .quotes-wrapper {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        
        .quotes-wrapper::-webkit-scrollbar {
          display: none;
        }

        .quote-container {
          scroll-snap-align: start;
          scroll-snap-stop: always;
        }
      `}</style>
    </>
  );
}

export default App;