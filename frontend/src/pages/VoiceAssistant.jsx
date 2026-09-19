import { useState } from 'react';
import { useVoice } from '../hooks/useVoice';
import { useTTS } from '../hooks/useTTS';
import { Mic, Square, Check, X, Volume2, AlertTriangle, Send, BarChart3, PackageSearch } from 'lucide-react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const WRITE_INTENTS = ['ADD_STOCK', 'REMOVE_STOCK'];
const READ_INTENTS = ['CHECK_STOCK', 'LOW_STOCK', 'SALES_SUMMARY'];

export default function VoiceAssistant() {
  const { isRecording, isProcessing, proposal, setProposal, startRecording, stopRecording, processText } = useVoice();
  const { speak } = useTTS();
  const [typedText, setTypedText] = useState('');
  const [isConfirming, setIsConfirming] = useState(false);

  const isWriteIntent = proposal && WRITE_INTENTS.includes(proposal.intent);
  const isReadIntent = proposal && READ_INTENTS.includes(proposal.intent);

  const handleConfirm = async () => {
    if (!proposal || isConfirming) return;
    setIsConfirming(true);
    try {
      await axios.post(`${API_BASE}/voice/${proposal.command_id}/confirm`);
      speak("Transaction confirmed successfully.", proposal.language);
      setProposal(null);
    } catch (err) {
      alert("Error confirming proposal: " + (err.response?.data?.detail || err.message));
    } finally {
      setIsConfirming(false);
    }
  };

  const handleCancel = async () => {
    if (!proposal || isConfirming) return;
    setIsConfirming(true);
    try {
      await axios.post(`${API_BASE}/voice/${proposal.command_id}/cancel`);
      setProposal(null);
    } catch (err) {
      alert("Error cancelling: " + (err.response?.data?.detail || err.message));
    } finally {
      setIsConfirming(false);
    }
  };

  const submitTyped = (e) => {
    e.preventDefault();
    if (typedText.trim()) {
      processText(typedText);
      setTypedText('');
    }
  };

  // Build TTS text based on intent type
  const getTTSText = () => {
    if (!proposal) return '';
    if (proposal.clarification_question) return proposal.clarification_question;
    if (proposal.analytics_result?.message) return proposal.analytics_result.message;
    if (proposal.stock_query_result?.message) return proposal.stock_query_result.message;
    if (isWriteIntent && proposal.resolved_lines?.length > 0) {
      const lines = proposal.resolved_lines.map(l => `${l.quantity} ${l.unit} ${l.product_name || l.product_mention}`);
      return `${proposal.intent === 'ADD_STOCK' ? 'Add' : 'Remove'}: ${lines.join(', ')}. Please confirm.`;
    }
    return `Intent: ${proposal.intent}`;
  };

  // H1 FIX: Intent-appropriate status badge
  const getStatusBadge = () => {
    if (!proposal) return null;
    if (proposal.needs_clarification) {
      return { text: 'Clarification Required', color: 'text-yellow-600' };
    }
    if (isReadIntent) {
      return { text: 'Query Result', color: 'text-emerald-600' };
    }
    if (isWriteIntent) {
      return { text: 'Proposal Created', color: 'text-blue-600' };
    }
    return { text: 'Response', color: 'text-gray-600' };
  };

  const badge = proposal ? getStatusBadge() : null;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-800">Voice Kirana Assistant</h2>
        <p className="text-gray-500 text-sm">Speak or type in English, Telugu, Hindi, or Hinglish</p>
      </div>

      <div className="flex flex-col items-center justify-center p-8 bg-white rounded-2xl shadow-sm border border-gray-100">
        {/* H6 FIX: Use Pointer Events instead of mouse+touch combo */}
        <button
          onMouseDown={(e) => { if (e.button === 0) startRecording(); }}
          onMouseUp={stopRecording}
          onMouseLeave={stopRecording}
          onTouchStart={(e) => { e.preventDefault(); startRecording(); }}
          onTouchEnd={(e) => { e.preventDefault(); stopRecording(); }}
          disabled={isProcessing}
          className={`w-36 h-36 rounded-full flex flex-col items-center justify-center transition-all touch-none select-none ${
            isRecording ? 'bg-red-500 animate-pulse ring-8 ring-red-100' : 'bg-blue-600 hover:bg-blue-700'
          } ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'} text-white shadow-lg`}
        >
          {isRecording ? <Square size={40} /> : <Mic size={48} />}
          <span className="text-xs mt-2 font-medium">{isRecording ? 'Listening (Max 15s)' : 'Hold to Speak'}</span>
        </button>

        <form onSubmit={submitTyped} className="w-full mt-6 flex gap-2">
          <input
            type="text"
            value={typedText}
            onChange={(e) => setTypedText(e.target.value)}
            placeholder='Or type e.g. "Anna 5 kilo biyyam add cheyyi"'
            disabled={isProcessing}
            className="flex-1 border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isProcessing || !typedText.trim()}
            className="bg-gray-800 text-white px-4 py-2 rounded-lg text-sm flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={16} /> Send
          </button>
        </form>
      </div>

      {isProcessing && <div className="text-center text-blue-600 font-medium animate-pulse">Processing pipeline...</div>}

      {proposal && (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 space-y-4">
          <div className="flex justify-between items-center border-b pb-3">
            {badge && <span className={`text-xs font-bold uppercase tracking-wider ${badge.color}`}>{badge.text}</span>}
            <button onClick={() => speak(getTTSText(), proposal.language)} className="text-gray-500 hover:text-blue-600">
              <Volume2 size={20} />
            </button>
          </div>

          <div className="text-sm bg-gray-50 p-3 rounded-lg italic">"{proposal.transcript}"</div>

          {/* READ: Stock Query Result */}
          {proposal.stock_query_result && (
            <div className="p-4 bg-blue-50 text-blue-800 rounded-lg text-sm font-medium flex items-start gap-3">
              <PackageSearch className="shrink-0 mt-0.5" size={20} />
              <div>
                <p>{proposal.stock_query_result.message}</p>
                {proposal.stock_query_result.low_stock_products && proposal.stock_query_result.low_stock_products.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {proposal.stock_query_result.low_stock_products.map((name, i) => (
                      <li key={i} className="text-xs bg-red-100 text-red-700 inline-block px-2 py-0.5 rounded-full mr-1">{name}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          {/* READ: Analytics/Sales Result */}
          {proposal.analytics_result && (
            <div className="p-4 bg-purple-50 text-purple-800 rounded-lg text-sm font-medium">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 size={18} />
                <span className="font-bold">Sales Summary ({proposal.analytics_result.period})</span>
              </div>
              <p>{proposal.analytics_result.message}</p>
              {proposal.analytics_result.top_selling_products?.length > 0 && (
                <div className="mt-3 space-y-1">
                  {proposal.analytics_result.top_selling_products.map((p, i) => (
                    <div key={i} className="flex justify-between text-xs bg-white p-2 rounded">
                      <span>{p.name}</span>
                      <span className="font-bold">{p.quantity} units</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* CLARIFICATION */}
          {proposal.needs_clarification ? (
            <div className="p-4 bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg flex items-start gap-3 text-sm">
              <AlertTriangle className="shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Clarification Required</p>
                <p>{proposal.clarification_question}</p>
              </div>
            </div>
          ) : (
            /* WRITE: Show resolved lines */
            isWriteIntent && proposal.resolved_lines.length > 0 && (
              <div className="space-y-2">
                {proposal.resolved_lines.map((line, idx) => (
                  <div key={idx} className="flex justify-between items-center text-sm p-2 border rounded-lg">
                    <div>
                      <span className="font-bold text-gray-800">{line.product_name}</span>
                      <span className="text-xs text-gray-500 ml-2">({line.product_mention})</span>
                    </div>
                    <div className="font-semibold">{line.quantity} {line.unit}</div>
                  </div>
                ))}
              </div>
            )
          )}

          {/* H2 FIX: Only show Confirm/Cancel for WRITE intents, never for READ */}
          {isWriteIntent && (
            <div className="flex gap-3 pt-2">
              <button
                onClick={handleCancel}
                disabled={isConfirming}
                className="flex-1 border border-gray-300 hover:bg-gray-50 text-gray-700 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <X size={16} /> Cancel
              </button>
              {!proposal.needs_clarification && (
                <button
                  onClick={handleConfirm}
                  disabled={isConfirming}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isConfirming ? (
                    <span className="animate-spin">⏳</span>
                  ) : (
                    <Check size={16} />
                  )}
                  {isConfirming ? 'Confirming...' : 'Confirm'}
                </button>
              )}
            </div>
          )}

          {/* Dismiss button for READ results */}
          {isReadIntent && !proposal.needs_clarification && (
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setProposal(null)}
                className="text-xs text-gray-500 hover:text-gray-800 px-3 py-1 border rounded-lg"
              >
                Dismiss
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}