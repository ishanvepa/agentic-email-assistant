"use client"
import React, { useState } from 'react';
import {Sparkles, Send, Mail, Calendar, Bot, FileText, Clock, Check, AlertCircle } from 'lucide-react';

const EmailAssistantDashboard = () => {
  const [prompt, setPrompt] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState('summaries');
  const [summaries, setSummaries] = useState([]);

    const [calendarEvents, setCalendarEvents] = useState([
    {
      id: 1,
      title: "Q3 Planning Meeting",
      date: "2025-07-02",
      time: "14:00",
      attendees: ["sarah@company.com"],
      source: "Email parsing",
      status: "scheduled"
    },
    {
      id: 2,
      title: "Invoice Payment Deadline",
      date: "2025-07-01",
      time: "09:00",
      attendees: [],
      source: "Email parsing",
      status: "reminder"
    }
  ]);

   // Mock data for demonstration
  const [emailSummaries] = useState([
    {
      id: 1,
      subject: "Invoice #2024-001 Payment Reminder",
      sender: "accounts@techcorp.com",
      summary: "Payment reminder for outstanding invoice of $2,450 due within 7 days.",
      priority: "high",
      date: "2025-06-25"
    },
    {
      id: 2,
      subject: "Meeting Request - Q3 Planning",
      sender: "sarah@company.com",
      summary: "Request to schedule Q3 planning meeting for next week, suggested times included.",
      priority: "medium",
      date: "2025-06-24"
    }
  ]);

  

  const [agentLogs, setAgentLogs] = useState([
    { id: 1, timestamp: "3:02 pm", action: "Fetching emails from inbox", status: "completed" },
    { id: 2, timestamp: "3:05 pm", action: "Analyzing email content for invoices", status: "completed" },
    { id: 3, timestamp: "3:08 pm", action: "Generating summary for 5 emails", status: "completed" },
    { id: 4, timestamp: "3:12 pm", action: "Creating draft responses", status: "completed" },
    { id: 5, timestamp: "3:15 pm", action: "Scheduling calendar events", status: "completed" }
  ]);


  const handleSubmit = async () => {
    setIsProcessing(true);
    const res = await fetch("http://localhost:5000/agent", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ prompt })
    });

    const data = await res.json();
    console.log("Response from server:", data);
    setIsProcessing(false);
    if (data.response){
      const filteredLogs = data.response.filter(log => log.action && log.action.trim() !== "");
      const updatedAgentLogs = [...agentLogs, ...filteredLogs];
      setAgentLogs(updatedAgentLogs);

      // Broaden filter to include both 'summarize' and 'summary'
      const summaryActions = updatedAgentLogs
        .filter(log => log.action && (
          log.action.toLowerCase().includes("summary") ||
          log.action.toLowerCase().includes("summarize")
        ))
        .map(log => ({ id: log.id, action: log.action }));
      setSummaries(summaryActions);

      // Filter for calendar events with the word 'scheduled'
      const scheduledEvents = updatedAgentLogs
        .filter(log => log.action && log.action.toLowerCase().includes("scheduled"))
        .map(log => ({ id: log.id, action: log.action }));
      setCalendarEvents(scheduledEvents);

      console.log("Logs2 updated:", updatedAgentLogs);
      console.log("Summaries updated:", summaryActions); // log the array directly
      console.log("Calendar Events updated:", scheduledEvents);
    } else {
      alert(data.error || "Something went wrong");
    }
  };



 

  const [draftResponses] = useState([
    {
      id: 1,
      to: "accounts@techcorp.com",
      subject: "Re: Invoice #2024-001 Payment Reminder",
      content: "Thank you for the reminder. Payment will be processed within 3 business days. Please confirm receipt of this message.",
      status: "ready"
    },
    {
      id: 2,
      to: "sarah@company.com",
      subject: "Re: Meeting Request - Q3 Planning",
      content: "I'm available for the Q3 planning meeting. Tuesday at 2 PM works best for my schedule. Please send the calendar invite.",
      status: "ready"
    }
  ]);

  
  // const handleSubmit = () => {
  //   if (!prompt.trim()) return;
    
  //   setIsProcessing(true);
  //   // Simulate processing
  //   setTimeout(() => {
  //     setIsProcessing(false);
  //   }, 3000);
  // };

  const TabButton = ({ id, label, icon: Icon, isActive, onClick }) => (
    <button
      onClick={() => onClick(id)}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 cursor-pointer ${
        isActive 
          ? 'bg-white/10 text-blue-300 shadow-lg backdrop-blur-sm' 
          : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
      }`}
    >
      <Icon size={16} />
      <span className="text-sm font-medium">{label}</span>
    </button>
  );

  const PriorityBadge = ({ priority }) => {
    const colors = {
      high: 'bg-red-500/20 text-red-300 border-red-500/30',
      medium: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
      low: 'bg-green-500/20 text-green-300 border-green-500/30'
    };
    
    return (
      <span className={`px-2 py-1 text-xs rounded-full border ${colors[priority]}`}>
        {priority}
      </span>
    );
  };

  const StatusIcon = ({ status }) => {
    const icons = {
      completed: <Check size={14} className="text-green-400" />,
      'in-progress': <Clock size={14} className="text-blue-400" />,
      pending: <AlertCircle size={14} className="text-yellow-400" />
    };
    return icons[status];
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-light tracking-wide">Email Assistant</h1>
          <p className="text-gray-400 text-sm">AI-powered email management and automation</p>
        </div>

        {/* Prompt Input */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6">
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">AI Assistant Prompt</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Example: Summarize my last 5 emails and prepare draft replies concerning anything related to invoices or scheduling."
                className="w-full h-24 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent resize-none"
              />
            </div>
            <button
              onClick={handleSubmit}
              disabled={isProcessing || !prompt.trim()}
              className="flex items-center gap-2 px-6 py-3 bg-blue-600/80 hover:bg-blue-600 disabled:bg-gray-600/50 rounded-xl transition-all duration-200 backdrop-blur-sm disabled:cursor-not-allowed cursor-pointer"
            >
              {isProcessing ? (
                <>
                  <div className="animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Execute Task</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
          <div className="flex justify-center gap-2 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-2">
            <TabButton id="summaries" label="Email Summaries" icon={Mail} isActive={activeTab === 'summaries'} onClick={setActiveTab} />
            {/* <TabButton id="responses" label="Draft Responses" icon={FileText} isActive={activeTab === 'responses'} onClick={setActiveTab} /> */}
            <TabButton id="logs" label="Agent Logs" icon={Bot} isActive={activeTab === 'logs'} onClick={setActiveTab} />
            <TabButton id="calendar" label="Calendar Events" icon={Calendar} isActive={activeTab === 'calendar'} onClick={setActiveTab} />
          </div>

          {/* Content Area */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 min-h-[400px]">
          {activeTab === 'summaries' && (
            <div className="space-y-4">
              <h2 className="text-xl font-light mb-4">Email Summaries</h2>
              {[...summaries].reverse().map((email) => (
                <div key={email.id} className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-3">
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-gray-500 font-mono">ID: {email.id}</span>
                    <p className="text-gray-300 text-sm leading-relaxed flex-1">{email.action}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'responses' && (
            <div className="space-y-4">
              <h2 className="text-xl font-light mb-4">Draft Responses</h2>
              {[...draftResponses].reverse().map((response) => (
                <div key={response.id} className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-3">
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <h3 className="font-medium text-gray-200">{response.subject}</h3>
                      <p className="text-sm text-gray-400">To: {response.to}</p>
                    </div>
                    <span className="px-3 py-1 bg-green-500/20 text-green-300 text-xs rounded-full border border-green-500/30">
                      {response.status}
                    </span>
                  </div>
                  <div className="bg-white/5 rounded-lg p-3">
                    <p className="text-gray-300 text-sm leading-relaxed">{response.content}</p>
                  </div>
                  <div className="flex gap-2">
                    <button className="px-4 py-2 bg-blue-600/80 hover:bg-blue-600 rounded-lg text-sm transition-colors">
                      Send Now
                    </button>
                    <button className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm transition-colors">
                      Edit Draft
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-light">Agent Activity Logs</h2>
                <button
                  onClick={() => setAgentLogs([])}
                  className="px-4 py-2 bg-red-800/80 hover:bg-red-800 text-white text-xs rounded-lg transition-colors hover:cursor-pointer"
                >
                  Clear Logs
                </button>
              </div>
              <div className="space-y-2">
                {[...agentLogs].reverse().map((log) => (
                  <div key={log.id} className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-lg p-3">
                    <StatusIcon status={log.status} />
                    <span className="text-xs text-gray-400 font-mono w-16">{log.timestamp}</span>
                    <span className="text-sm text-gray-300 flex-1">{log.action}</span>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      log.status === 'completed' ? 'bg-green-500/20 text-green-300' :
                      log.status === 'in-progress' ? 'bg-blue-500/20 text-blue-300' :
                      'bg-yellow-500/20 text-yellow-300'
                    }`}>
                      {log.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'calendar' && (
            <div className="space-y-4">
              <h2 className="text-xl font-light mb-4">Calendar Events</h2>
              {[...calendarEvents].reverse().map((event) => (
                <div key={event.id} className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-3">
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-gray-500 font-mono">ID: {event.id}</span>
                    <p className="text-gray-300 text-sm leading-relaxed flex-1">{event.action}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EmailAssistantDashboard;