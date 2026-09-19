import { useCallback, useEffect, useState } from 'react';

export function useTTS() {
  const [voicesLoaded, setVoicesLoaded] = useState(false);

  useEffect(() => {
    if (!('speechSynthesis' in window)) return;
    const updateVoices = () => setVoicesLoaded(true);
    
    // Initial check
    if (window.speechSynthesis.getVoices().length > 0) {
      updateVoices();
    }
    
    window.speechSynthesis.onvoiceschanged = updateVoices;
    return () => {
      window.speechSynthesis.onvoiceschanged = null;
    };
  }, []);

  const speak = useCallback((text, lang = 'en') => {
    if (!('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    
    let targetLang = 'en-IN';
    if (lang === 'hi') targetLang = 'hi-IN';
    if (lang === 'te') targetLang = 'te-IN';
    
    const voices = window.speechSynthesis.getVoices();
    
    // 1. Try exact locale match (e.g. 'en-IN')
    const exactMatch = voices.find(v => v.lang.toLowerCase() === targetLang.toLowerCase());
    
    // 2. Try base language match (e.g. 'en-US' or 'en-GB' if 'en-IN' is missing)
    const baseMatch = voices.find(v => v.lang.toLowerCase().startsWith(lang.toLowerCase()));
    
    if (exactMatch) {
      utterance.voice = exactMatch;
    } else if (baseMatch) {
      utterance.voice = baseMatch;
    }

    utterance.lang = targetLang;
    window.speechSynthesis.speak(utterance);
  }, [voicesLoaded]);

  return { speak };
}