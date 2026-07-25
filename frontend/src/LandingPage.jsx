import React from 'react';
import { motion } from 'framer-motion';
import { Play, Search, Bell, ChevronRight, MoreVertical, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import './landing.css';

export default function LandingPage() {
  return (
    <div className="landing-page-root h-screen flex flex-col bg-background overflow-hidden text-foreground">
      {/* Floating Navbar */}
      <div className="absolute top-0 left-0 right-0 z-50 flex justify-center pt-6 px-4">
        <nav className="w-full max-w-5xl flex items-center justify-between px-8 py-4 font-body bg-background/40 backdrop-blur-md rounded-full border border-white/30 shadow-lg shadow-black/5">
          <div className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <span className="text-accent text-2xl">✦</span> Vigil
          </div>
          <div className="hidden md:flex gap-10 text-sm font-medium">
            <a href="#" className="no-underline text-gray-600 hover:text-black transition-colors">Platform</a>
            <a href="#" className="no-underline text-gray-600 hover:text-black transition-colors">Solutions</a>
            <a href="#" className="no-underline text-gray-600 hover:text-black transition-colors">Resources</a>
            <a href="#" className="no-underline text-gray-600 hover:text-black transition-colors">Pricing</a>
          </div>
          <Link to="/dashboard" className="no-underline rounded-full px-6 py-2.5 text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-md shadow-primary/20">
            Open Dashboard
          </Link>
        </nav>
      </div>

      {/* Hero Section */}
      <main className="relative flex-1 w-full flex flex-col items-center pt-32">
        <video 
          autoPlay 
          loop 
          muted 
          playsInline 
          className="absolute inset-0 w-full h-full object-cover z-0 opacity-60"
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260319_015952_e1deeb12-8fb7-4071-a42a-60779fc64ab6.mp4"
        />
        
        <div className="relative z-10 flex flex-col items-center w-full px-4">
          
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background/80 backdrop-blur-sm px-4 py-1.5 text-sm text-muted-foreground font-body mb-6 shadow-sm"
          >
            <span>Now powered by Gemini 2.0 ✨</span>
          </motion.div>

          <motion.h1 
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-center font-display text-5xl md:text-6xl lg:text-[5rem] leading-[0.95] tracking-tight text-foreground max-w-xl"
          >
            The Future of <span className="italic text-accent">Smarter</span> Threat Detection
          </motion.h1>

          <motion.p 
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mt-4 text-center text-base md:text-lg text-muted-foreground max-w-[650px] leading-relaxed font-body"
          >
            Automate your security operations with intelligent agents that learn, adapt, and execute—so your SOC team can focus on what matters most.
          </motion.p>

          <motion.div 
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-6 flex items-center gap-3"
          >
            <Link to="/dashboard" className="no-underline rounded-full px-6 py-4 text-sm font-medium font-body bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20">
              Start Free Trial
            </Link>
            <button className="flex items-center justify-center h-12 w-12 rounded-full border-0 bg-background shadow-[0_2px_12px_rgba(0,0,0,0.08)] hover:bg-background/80 transition-colors text-foreground">
              <Play className="h-4 w-4 fill-foreground" />
            </button>
          </motion.div>

          {/* Dashboard Preview */}
          <motion.div 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="mt-12 w-full max-w-5xl"
          >
            <div 
              className="rounded-2xl overflow-hidden p-3 md:p-4 mx-auto"
              style={{
                background: 'rgba(255, 255, 255, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.5)',
                boxShadow: 'var(--shadow-dashboard)',
                backdropFilter: 'blur(12px)'
              }}
            >
              {/* Fake Dashboard Inner Container */}
              <div className="bg-background rounded-xl overflow-hidden flex flex-col h-[500px] border border-border shadow-sm text-[11px] font-body select-none pointer-events-none">
                
                {/* Top bar */}
                <div className="h-12 border-b border-border flex items-center justify-between px-4">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded bg-accent flex items-center justify-center text-white font-bold text-xs">V</div>
                    <span className="font-semibold text-sm">Vigil</span>
                    <ChevronRight className="w-3 h-3 text-muted-foreground ml-1" />
                  </div>
                  <div className="flex-1 max-w-md mx-6">
                    <div className="relative">
                      <Search className="w-3 h-3 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                      <div className="w-full bg-secondary rounded-md py-1.5 pl-8 pr-3 text-muted-foreground flex justify-between items-center border border-transparent">
                        <span>Search alerts or IP...</span>
                        <span className="bg-background border border-border rounded px-1 text-[9px]">⌘K</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-muted-foreground">
                    <span className="font-medium text-foreground">Export Data</span>
                    <Bell className="w-4 h-4" />
                    <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-medium">SA</div>
                  </div>
                </div>

                {/* Main Body */}
                <div className="flex flex-1 overflow-hidden">
                  
                  {/* Sidebar */}
                  <div className="w-44 border-r border-border p-3 flex flex-col gap-1 text-muted-foreground">
                    <div className="font-medium text-xs mb-2 text-foreground/50 px-2 mt-1">OPERATIONS</div>
                    <div className="bg-secondary text-foreground font-medium rounded-md px-2 py-1.5 flex justify-between items-center">
                      Command Center
                    </div>
                    <div className="rounded-md px-2 py-1.5 flex justify-between items-center">
                      Alert Queue
                      <span className="bg-accent/10 text-accent font-medium rounded-full px-1.5 py-0.5 text-[9px]">12</span>
                    </div>
                    <div className="rounded-md px-2 py-1.5 flex justify-between items-center">
                      Entity Profiling
                    </div>
                    <div className="font-medium text-xs mb-2 text-foreground/50 px-2 mt-4">SYSTEM</div>
                    <div className="rounded-md px-2 py-1.5 flex justify-between items-center">
                      Models & Metrics
                    </div>
                    <div className="rounded-md px-2 py-1.5 flex justify-between items-center">
                      Settings
                    </div>
                  </div>

                  {/* Content Area */}
                  <div className="flex-1 bg-secondary/30 p-6 flex flex-col gap-6 overflow-hidden">
                    
                    <div>
                      <h2 className="text-sm font-semibold text-foreground">Welcome, Security Analyst</h2>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="bg-accent text-white px-3 py-1.5 rounded-full font-medium">Analyze Alerts</div>
                      <div className="bg-background border border-border text-foreground px-3 py-1.5 rounded-full font-medium">Request Data</div>
                      <div className="bg-background border border-border text-foreground px-3 py-1.5 rounded-full font-medium">Generate Report</div>
                      <div className="bg-background border border-border text-foreground px-3 py-1.5 rounded-full font-medium flex items-center gap-1"><Plus className="w-3 h-3"/> Add Entity</div>
                      <div className="text-muted-foreground px-3 py-1.5 ml-2 font-medium">Customize</div>
                    </div>

                    <div className="flex gap-4">
                      
                      {/* Risk Pulse Card */}
                      <div className="flex-1 bg-background border border-border rounded-xl p-4 flex flex-col">
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-medium text-foreground">System Risk Pulse</span>
                          <span className="w-4 h-4 rounded-full bg-accent text-white flex items-center justify-center text-[8px]">✓</span>
                        </div>
                        <div className="text-2xl font-display text-foreground mt-2">
                          12.4 <span className="text-xs text-muted-foreground font-body align-top">avg score</span>
                        </div>
                        <div className="flex gap-3 mt-1 mb-4 text-[10px]">
                          <span className="text-muted-foreground">Last 30 Days</span>
                          <span className="text-emerald-500 font-medium">↓ 2.4 points</span>
                          <span className="text-rose-500 font-medium">↑ 1 critical</span>
                        </div>
                        <div className="mt-auto h-16 w-full relative">
                          <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                            <path d="M0,80 C20,60 40,90 60,40 C80,-10 100,50 100,50 L100,100 L0,100 Z" fill="hsl(var(--tw-accent) / 0.15)" />
                            <path d="M0,80 C20,60 40,90 60,40 C80,-10 100,50 100,50" fill="none" stroke="hsl(var(--tw-accent))" strokeWidth="2" vectorEffect="non-scaling-stroke" />
                          </svg>
                        </div>
                      </div>

                      {/* System Overview Card */}
                      <div className="flex-1 bg-background border border-border rounded-xl p-4 flex flex-col">
                        <div className="flex justify-between items-center mb-3">
                          <span className="font-medium text-foreground">System Overview</span>
                          <div className="flex gap-2 text-muted-foreground">
                            <Plus className="w-3 h-3"/>
                            <MoreVertical className="w-3 h-3"/>
                          </div>
                        </div>
                        <div className="flex flex-col gap-3 mt-2">
                          <div className="flex justify-between items-center py-1">
                            <span className="text-muted-foreground">Active Anomalies</span>
                            <span className="font-medium text-foreground">1,245</span>
                          </div>
                          <div className="flex justify-between items-center py-1">
                            <span className="text-muted-foreground">Monitored Entities</span>
                            <span className="font-medium text-foreground">42,890</span>
                          </div>
                          <div className="flex justify-between items-center py-1">
                            <span className="text-muted-foreground">Analyzed Sessions</span>
                            <span className="font-medium text-foreground">8.4M</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Table */}
                    <div className="flex-1 flex flex-col">
                      <div className="font-medium text-foreground mb-3">Recent Alerts</div>
                      <div className="bg-background border border-border rounded-xl overflow-hidden">
                        <div className="flex text-muted-foreground font-medium px-4 py-2 border-b border-border">
                          <div className="w-1/4">Time</div>
                          <div className="w-1/3">Entity</div>
                          <div className="w-1/4">Pattern</div>
                          <div className="flex-1 text-right">Status</div>
                        </div>
                        <div className="flex px-4 py-2.5 border-b border-border items-center">
                          <div className="w-1/4 text-muted-foreground">10:42 AM</div>
                          <div className="w-1/3 font-medium text-foreground">admin-svc-04</div>
                          <div className="w-1/4">Multiple Failures</div>
                          <div className="flex-1 text-right text-rose-500 font-medium">Critical</div>
                        </div>
                        <div className="flex px-4 py-2.5 border-b border-border items-center">
                          <div className="w-1/4 text-muted-foreground">10:15 AM</div>
                          <div className="w-1/3 font-medium text-foreground">user-jdoe</div>
                          <div className="w-1/4">Geographic Anomaly</div>
                          <div className="flex-1 text-right text-amber-500 font-medium">Pending</div>
                        </div>
                        <div className="flex px-4 py-2.5 items-center">
                          <div className="w-1/4 text-muted-foreground">09:30 AM</div>
                          <div className="w-1/3 font-medium text-foreground">db-node-02</div>
                          <div className="w-1/4">Data Exfiltration</div>
                          <div className="flex-1 text-right text-emerald-500 font-medium">Resolved</div>
                        </div>
                      </div>
                    </div>

                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}
