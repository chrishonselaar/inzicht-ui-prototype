import React, { useState } from 'react';
import { Clock, MessageSquare, Search, AlertCircle, ChevronRight } from 'lucide-react';

const TranscriptionUI = () => {
  const [activeTab, setActiveTab] = useState('live');
  
  const transcriptSegments = [
    {
      timeRange: "00:00:00.764 - 00:00:01.284",
      text: "Ehm..."
    },
    {
      timeRange: "00:00:02.240 - 00:00:05.287",
      text: "zoals in de sessie al aangegeven zijn tegen de motie om dat bij een onderzoek."
    },
    {
      timeRange: "00:00:05.891 - 00:00:23.160",
      text: "Naar de veiligheid over de motie straatintimidatie, zoals gezegd altijd blij met extra aandacht hiervoor. Het is zoeken naar de juiste manier om dit gedrag van vaak mannen tegen te gaan."
    }
  ];

  const historicalDecisions = [
    "Historische vragen en antwoorden over straatintimidatie uit 2021 en 2024 in Groningen",
    "Eerdere initiatieven om straatintimidatie te bestrijden in verschillende steden",
    "Evaluaties van bestaande meldpunten en campagnes"
  ];

  const stakeholderPositions = [
    "Diverse politieke partijen pleiten voor een bredere aanpak van straatintimidatie",
    "Bewoners vragen om meer aandacht voor veiligheid en leefbaarheid",
    "Politie benadrukt de noodzaak van effectieve handhaving"
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      <div className="w-1/2 border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200 bg-white">
          <div className="flex items-center gap-2">
            <Clock className="text-red-500" size={20} />
            <span className="font-semibold">Live Transcriptie</span>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            {transcriptSegments.map((segment, index) => (
              <div key={index} className="bg-white p-3 rounded-lg shadow-sm">
                <div className="text-xs text-gray-500 mb-1">{segment.timeRange}</div>
                <div className="text-gray-800">{segment.text}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="w-1/2 flex flex-col">
        <div className="border-b border-gray-200 bg-white">
          <div className="flex gap-2 p-2">
            <button
              onClick={() => setActiveTab('live')}
              className={`px-4 py-2 rounded-lg ${activeTab === 'live' ? 'bg-blue-50 text-blue-600' : 'text-gray-600'}`}
            >
              Live Analyse
            </button>
            <button
              onClick={() => setActiveTab('search')}
              className={`px-4 py-2 rounded-lg ${activeTab === 'search' ? 'bg-blue-50 text-blue-600' : 'text-gray-600'}`}
            >
              Archief Zoeken
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            <div className="bg-white p-4 rounded-lg shadow-sm">
              <h3 className="font-semibold mb-2 flex items-center gap-2">
                <AlertCircle size={16} className="text-amber-500" />
                Gerelateerde Historische Besluiten
              </h3>
              <div className="space-y-2">
                {historicalDecisions.map((decision, index) => (
                  <div key={index} className="flex items-center gap-2 text-gray-700">
                    <ChevronRight size={14} className="text-gray-400" />
                    {decision}
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white p-4 rounded-lg shadow-sm">
              <h3 className="font-semibold mb-2 flex items-center gap-2">
                <MessageSquare size={16} className="text-blue-500" />
                Standpunten Belanghebbenden
              </h3>
              <div className="space-y-2">
                {stakeholderPositions.map((position, index) => (
                  <div key={index} className="flex items-center gap-2 text-gray-700">
                    <ChevronRight size={14} className="text-gray-400" />
                    {position}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TranscriptionUI;